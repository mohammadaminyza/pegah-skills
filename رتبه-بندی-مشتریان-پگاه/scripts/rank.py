#!/usr/bin/env python3
"""رتبه مشتریان پگاه از روی سه معیار خام. قواعد در rules.json است."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent.parent / "rules.json"


def ratio(numerator, denominator, scale=100.0):
    if numerator is None or not denominator:
        return None
    return float(numerator) / float(denominator) * scale


def as_code(value):
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return value


def type_key(customer, rules):
    """کلید نوع مشتری از روی کلید انگلیسی، برچسب فارسی یا کد ccNoeMoshtary."""
    given = as_code(customer.get("type", customer.get("ccNoeMoshtary")))
    for key, entry in rules["customer_types"].items():
        if given in (key, entry["label"], *(entry.get("codes") or [])):
            return key
    known = "، ".join(
        f"{key} ({entry['label']}: {', '.join(str(c) for c in entry.get('codes') or [])})"
        for key, entry in rules["customer_types"].items()
    )
    raise SystemExit(
        f"نوع مشتری ناشناخته: {given!r} برای مشتری {customer.get('code')}. "
        f"نوع‌های تعریف‌شده: {known}."
    )


def measure(key, customer):
    direct = customer.get(key)
    if direct is not None:
        return float(direct)
    if key == "positive_visit_pct":
        return ratio(customer.get("visits_positive"), customer.get("visits_total"))
    return None


def rank_of(criterion, kind, value):
    """رتبه ۱ تا ۵. حد پایینِ هر بازه شامل است — ۴۵۰ قلم رتبه ۲ می‌گیرد نه ۱."""
    thresholds = criterion["thresholds"].get(kind)
    if thresholds is None:
        raise SystemExit(
            f"معیار «{criterion['label']}» برای نوع مشتری '{kind}' آستانه ندارد."
        )
    return 1 + sum(1 for threshold in thresholds if value >= threshold)


def grade(total, rules):
    for entry in rules["grades"]:
        if entry["min"] is None or total >= entry["min"]:
            return entry["label"]
    return ""


def evaluate(customer, rules):
    kind = type_key(customer, rules)
    min_visits = rules.get("min_visits") or 0
    visits = customer.get("visits_total")
    weak_visits = visits is not None and 0 < visits < min_visits

    rows = []
    total = 0
    possible = 0
    missing = []
    for criterion in rules["criteria"]:
        value = measure(criterion["key"], customer)
        if value is None:
            missing.append(criterion["label"])
            rank = score = None
        else:
            rank = rank_of(criterion, kind, value)
            score = rank * criterion["weight"]
            total += score
            possible += 5 * criterion["weight"]
        rows.append(
            {
                "key": criterion["key"],
                "label": criterion["label"],
                "unit": criterion.get("unit", ""),
                "weight": criterion["weight"],
                "value": None if value is None else round(value, 2),
                "rank": rank,
                "score": score,
                "weak": weak_visits and criterion["key"] == "positive_visit_pct",
            }
        )

    return {
        "code": customer.get("code"),
        "name": customer.get("name") or customer.get("code") or "—",
        "type": kind,
        "type_label": rules["customer_types"][kind]["label"],
        "criteria": rows,
        "missing": missing,
        "scored_count": len(rows) - len(missing),
        "criteria_count": len(rows),
        "total": total,
        "possible": possible,
        "grade": "" if missing else grade(total, rules),
        "weak_visits": weak_visits,
        "visits_total": visits,
    }


def number(value):
    if value is None:
        return "—"
    return f"{value:g}"


def cell(row):
    if row["value"] is None:
        return "بدون داده"
    return f"{number(row['value'])} ({row['rank']})"


def distribution(results, rules):
    lines = ["| رتبه | تعداد مشتری | سهم |", "|---|---:|---:|"]
    total = len(results)
    for entry in rules["grades"] + [{"label": "ناقص"}]:
        label = entry["label"]
        count = sum(1 for result in results if (result["grade"] or "ناقص") == label)
        if label == "ناقص" and not count:
            continue
        share = 100.0 * count / total if total else 0.0
        lines.append(f"| {label} | {count} | {share:.1f}٪ |")
    return lines


def render(report, rules):
    heading = "## رتبه‌بندی مشتریان پگاه"
    if report.get("scope"):
        heading += f" — {report['scope']}"
    lines = [heading, ""]

    for kind, entry in rules["customer_types"].items():
        results = [result for result in report["results"] if result["type"] == kind]
        if not results:
            continue
        lines += [f"### {entry['label']} — {len(results)} مشتری", ""]

        if not report["summary_only"]:
            header = "| # | مشتری | کد | " + " | ".join(
                criterion["label"] for criterion in rules["criteria"]
            )
            lines.append(header + " | نمره | رتبه | توضیح |")
            lines.append(
                "|---:|---|---|" + "---:|" * len(rules["criteria"]) + "---:|---|---|"
            )
            for position, result in enumerate(results, start=1):
                note = ""
                if result["missing"]:
                    note = (
                        f"{result['scored_count']}/{result['criteria_count']} معیار — "
                        f"بدون داده: {'، '.join(result['missing'])}"
                    )
                elif result["weak_visits"]:
                    note = f"* ویزیت مثبت از {result['visits_total']} ویزیت"
                cells = " | ".join(cell(row) for row in result["criteria"])
                score = f"{result['total']}"
                if result["missing"]:
                    score += f" از {result['possible']}"
                lines.append(
                    f"| {position} | {result['name']} | {result['code']} | {cells} | "
                    f"{score} | {result['grade'] or '—'} | {note} |"
                )
            lines.append("")

        lines += distribution(results, rules) + [""]

    if not report["summary_only"] and any(
        result["weak_visits"] for result in report["results"]
    ):
        lines += [
            f"\\* درصد ویزیت مثبت از کمتر از {rules.get('min_visits')} ویزیت درآمده — "
            "رتبه‌ی این معیار برای این مشتری کم‌اعتبار است.",
            "",
        ]

    lines.append(
        "نمره = (رتبه اقلام × ۳) + (رتبه ویزیت مثبت × ۴) + (رتبه SKU × ۵). "
        "عدد داخل پرانتز رتبه‌ی همان معیار است."
    )
    return "\n".join(lines)


def read_input(path):
    # utf-8-sig نه utf-8: خروجی پایپ در PowerShell و فایلِ ذخیره‌شده با Notepad
    # هر دو BOM دارند و json آن را رد می‌کند.
    if path == "-":
        text = sys.stdin.buffer.read().decode("utf-8-sig")
    else:
        text = Path(path).read_text(encoding="utf-8-sig")
    payload = json.loads(text)
    if isinstance(payload, list):
        return {"customers": payload}
    return payload


def main():
    parser = argparse.ArgumentParser(description="رتبه‌بندی مشتریان پگاه")
    parser.add_argument("input", help="فایل JSON متریک‌ها، یا - برای ورودی استاندارد")
    parser.add_argument("--type", help="فقط یک نوع مشتری: khord یا omde")
    parser.add_argument("--rules", default=str(RULES_PATH))
    parser.add_argument("--json", action="store_true", help="خروجی JSON به جای جدول")
    parser.add_argument("--summary", action="store_true", help="فقط توزیع رتبه‌ها")
    args = parser.parse_args()

    # وگرنه روی کنسول ویندوز، خروجی فارسی با UnicodeEncodeError می‌افتد.
    sys.stdout.reconfigure(encoding="utf-8")

    rules = json.loads(Path(args.rules).read_text(encoding="utf-8-sig"))
    payload = read_input(args.input)
    customers = payload.get("customers") or []
    if not customers:
        raise SystemExit("ورودی هیچ مشتری‌ای ندارد (کلید customers خالی است).")

    if args.type and args.type not in rules["customer_types"]:
        available = ", ".join(rules["customer_types"])
        raise SystemExit(f"نوع '{args.type}' تعریف نشده. نوع‌های موجود: {available}.")

    # مشتریِ ناقص پایین‌تر از مشتریِ کامل می‌نشیند؛ نمره‌ی ناقص با نمره‌ی کامل
    # قابل مقایسه نیست.
    results = sorted(
        (evaluate(customer, rules) for customer in customers),
        key=lambda result: (not result["missing"], result["total"]),
        reverse=True,
    )
    if args.type:
        results = [result for result in results if result["type"] == args.type]

    report = {
        "scope": payload.get("scope"),
        "rules_version": rules.get("version"),
        "results": results,
        "summary_only": args.summary,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render(report, rules))


if __name__ == "__main__":
    main()
