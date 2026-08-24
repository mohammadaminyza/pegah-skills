#!/usr/bin/env python3
"""نمره ارزیابی فروشنده پگاه از روی متریک‌های خام. قواعد در rules.json است."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent.parent / "rules.json"


def ratio(numerator, denominator, scale=100.0):
    if numerator is None or not denominator:
        return None
    return float(numerator) / float(denominator) * scale


def weighted_shops(person, rules):
    shops = person.get("shops")
    if not shops:
        return None
    weights = rules["shop_weights"]
    unknown = sorted(key for key in shops if key not in weights)
    if unknown:
        known = ", ".join(weights)
        raise SystemExit(
            f"نوع مشتری ناشناخته در shops: {', '.join(unknown)}. نوع‌های تعریف‌شده: {known}."
        )
    return float(sum(weights[key] * (shops[key] or 0) for key in shops))


def measure(key, person, rules):
    direct = person.get(key)
    if direct is not None:
        return float(direct)
    if key == "weighted_shops":
        return weighted_shops(person, rules)
    if key == "positive_visit_pct":
        return ratio(person.get("visits_positive"), person.get("visits_total"))
    if key == "avg_items_per_invoice":
        return ratio(person.get("invoice_line_count"), person.get("invoice_count"), 1.0)
    if key == "purchasing_customer_pct":
        return ratio(person.get("customers_purchased"), person.get("customers_assigned"))
    if key == "return_pct":
        if rules.get("return_basis") == "quantity":
            return ratio(person.get("returns_qty"), person.get("sold_qty"))
        return ratio(person.get("returns_amount"), person.get("gross_sales_amount"))
    return None


def points(criterion, value, stepping):
    gap = value - criterion["baseline"]
    if criterion["direction"] == "lower_is_better":
        gap = -gap
    steps = gap / criterion["step"]
    if stepping == "stepped":
        steps = math.trunc(steps)
    return steps * criterion["points_per_step"]


def group_result(criterion, person, stepping):
    """نمره معیار گروه محصول: هر گروه جدا، و میانگین نمره گروه‌ها."""
    detail = []
    for group in person.get("product_groups") or []:
        achieved = group.get("achievement_pct")
        if achieved is None:
            achieved = ratio(group.get("sales"), group.get("target"))
        if achieved is None:
            continue
        detail.append(
            {
                "name": group.get("name") or "—",
                "achievement_pct": round(achieved, 2),
                "score": round(points(criterion, achieved, stepping), 2),
            }
        )
    if not detail:
        return None, None, []
    mean_pct = sum(item["achievement_pct"] for item in detail) / len(detail)
    mean_score = sum(item["score"] for item in detail) / len(detail)
    return mean_pct, mean_score, detail


def evaluate(person, period, rules):
    stepping = rules.get("stepping", "continuous")
    rows = []
    total = 0.0
    missing = []
    knockout = None

    for criterion in period["criteria"]:
        groups = []
        if criterion.get("aggregate") == "mean_of_groups":
            value, score, groups = group_result(criterion, person, stepping)
        else:
            value = measure(criterion["key"], person, rules)
            score = None if value is None else points(criterion, value, stepping)

        limit = criterion.get("zero_total_above")
        if limit is not None and value is not None and value > limit:
            knockout = criterion.get("zero_total_note") or (
                f"{criterion['label']} بیش از {limit} — نمره کل صفر."
            )

        if value is None:
            missing.append(criterion["label"])
        else:
            total += score

        rows.append(
            {
                "key": criterion["key"],
                "label": criterion["label"],
                "unit": criterion.get("unit", ""),
                "baseline": criterion["baseline"],
                "value": None if value is None else round(value, 2),
                "score": None if score is None else round(score, 2),
                "assumed": criterion.get("assumed"),
                "groups": groups,
            }
        )

    return {
        "name": person.get("name") or person.get("code") or "—",
        "code": person.get("code"),
        "criteria": rows,
        "scored_count": len(rows) - len(missing),
        "criteria_count": len(rows),
        "missing": missing,
        "knockout": knockout,
        "raw_total": round(total, 2),
        "total": 0.0 if knockout else round(total, 2),
    }


def number(value):
    if value is None:
        return "—"
    return f"{value:g}"


def render(report):
    heading = f"## {report['period_label']}"
    if report.get("scope"):
        heading += f" — {report['scope']}"
    lines = [heading, ""]
    lines.append("| رتبه | فروشنده | نمره کل | معیارهای محاسبه‌شده | توضیح |")
    lines.append("|---:|---|---:|:---:|---|")
    for rank, result in enumerate(report["results"], start=1):
        note = result["knockout"] or ""
        if not note and result["missing"]:
            note = "بدون داده: " + "، ".join(result["missing"])
        lines.append(
            f"| {rank} | {result['name']} | {number(result['total'])} | "
            f"{result['scored_count']}/{result['criteria_count']} | {note} |"
        )

    if report["summary_only"]:
        return "\n".join(lines)

    for result in report["results"]:
        lines += ["", f"### {result['name']}", ""]
        lines.append("| معیار | مقدار | مبنا | نمره |")
        lines.append("|---|---:|---:|---:|")
        for row in result["criteria"]:
            unit = f" {row['unit']}" if row["unit"] else ""
            mark = " *" if row["assumed"] else ""
            shown = (
                "بدون داده"
                if row["value"] is None
                else f"{number(row['value'])}{unit}"
            )
            lines.append(
                f"| {row['label']}{mark} | {shown} | "
                f"{number(row['baseline'])}{unit} | {number(row['score'])} |"
            )
        lines.append(f"| **جمع** | | | **{number(result['total'])}** |")

        for row in result["criteria"]:
            if not row["groups"]:
                continue
            lines += ["", "گروه‌های محصول:", "", "| گروه | تحقق هدف | نمره |", "|---|---:|---:|"]
            for group in row["groups"]:
                lines.append(
                    f"| {group['name']} | {number(group['achievement_pct'])} ٪ | "
                    f"{number(group['score'])} |"
                )

        if result["knockout"]:
            lines += ["", f"> {result['knockout']}"]
        for row in result["criteria"]:
            if row["assumed"]:
                lines += ["", f"\\* {row['assumed']}"]

    return "\n".join(lines)


def read_input(path):
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    payload = json.loads(text)
    if isinstance(payload, list):
        return {"salespeople": payload}
    return payload


def main():
    parser = argparse.ArgumentParser(description="نمره ارزیابی فروشنده پگاه")
    parser.add_argument("input", help="فایل JSON متریک‌ها، یا - برای ورودی استاندارد")
    parser.add_argument("--period", choices=["daily", "cumulative"])
    parser.add_argument("--rules", default=str(RULES_PATH))
    parser.add_argument("--json", action="store_true", help="خروجی JSON به جای جدول")
    parser.add_argument("--summary", action="store_true", help="فقط جدول خلاصه")
    args = parser.parse_args()

    # وگرنه روی کنسول ویندوز، خروجی فارسی با UnicodeEncodeError می‌افتد.
    sys.stdout.reconfigure(encoding="utf-8")

    rules = json.loads(Path(args.rules).read_text(encoding="utf-8"))
    payload = read_input(args.input)
    name = args.period or payload.get("period")
    if name not in rules["periods"]:
        available = ", ".join(rules["periods"])
        raise SystemExit(f"دوره '{name}' تعریف نشده. دوره‌های موجود: {available}.")
    period = rules["periods"][name]

    people = payload.get("salespeople") or []
    if not people:
        raise SystemExit("ورودی هیچ فروشنده‌ای ندارد (کلید salespeople خالی است).")

    # فروشنده‌ای که به‌خاطر مرجوعی حذف شده نباید بالاتر از کسی بنشیند که نمره
    # منفی گرفته اما حذف نشده — نمره‌اش صفر است، رتبه‌اش ته جدول.
    results = sorted(
        (evaluate(person, period, rules) for person in people),
        key=lambda result: (not result["knockout"], result["total"]),
        reverse=True,
    )
    report = {
        "period": name,
        "period_label": period["label"],
        "scope": payload.get("scope"),
        "stepping": rules.get("stepping", "continuous"),
        "results": results,
        "summary_only": args.summary,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render(report))


if __name__ == "__main__":
    main()
