#!/usr/bin/env python3
"""نمایش و تغییر قاعده‌های رتبه‌بندی — آستانه‌ها، ضریب‌ها و باندهای رتبه."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent.parent / "rules.json"

GREGORIAN_MONTH_DAYS = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]


def today_jalali():
    """تاریخ شمسی امروز، برای فیلد version."""
    today = date.today()
    year, month, day = today.year, today.month, today.day
    shifted = year - 1600
    days = (
        365 * shifted
        + (shifted + 3) // 4
        - (shifted + 99) // 100
        + (shifted + 399) // 400
        + GREGORIAN_MONTH_DAYS[month - 1]
        + day
        - 1
    )
    if month > 2 and (year % 4 == 0 and year % 100 != 0 or year % 400 == 0):
        days += 1
    days -= 79
    cycles, days = divmod(days, 12053)
    jy = 979 + 33 * cycles + 4 * (days // 1461)
    days %= 1461
    if days >= 366:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return f"{jy:04d}-{jm:02d}-{jd:02d}"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(rules, path):
    rules["version"] = today_jalali()
    Path(path).write_text(
        json.dumps(rules, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def criterion_of(rules, key):
    for criterion in rules["criteria"]:
        if criterion["key"] == key:
            return criterion
    keys = "، ".join(item["key"] for item in rules["criteria"])
    raise SystemExit(f"معیار '{key}' تعریف نشده. معیارهای موجود: {keys}.")


def type_of(rules, key):
    if key not in rules["customer_types"]:
        keys = "، ".join(rules["customer_types"])
        raise SystemExit(f"نوع مشتری '{key}' تعریف نشده. نوع‌های موجود: {keys}.")
    return rules["customer_types"][key]


def numbers(values, label):
    parsed = []
    for value in values:
        try:
            parsed.append(int(value) if float(value).is_integer() else float(value))
        except ValueError:
            raise SystemExit(f"{label}: '{value}' عدد نیست.") from None
    return parsed


def score_span(rules):
    """کمترین و بیشترین نمره‌ای که با ضریب‌های فعلی ممکن است."""
    weights = [criterion["weight"] for criterion in rules["criteria"]]
    return sum(weights), 5 * sum(weights)


def reachability(rules):
    """باندهایی که با ضریب‌های فعلی هیچ نمره‌ای به آن‌ها نمی‌رسد."""
    low, high = score_span(rules)
    warnings = []
    ceiling = None
    for entry in rules["grades"]:
        floor = entry["min"]
        top = high if ceiling is None else min(high, ceiling - 1)
        bottom = low if floor is None else max(low, floor)
        if bottom > top:
            warnings.append(
                f"- **{entry['label']}** دست‌نیافتنی است — نمره بین {low} و {high} "
                f"است و این باند بیرون آن می‌افتد."
            )
        elif bottom == top:
            warnings.append(
                f"- **{entry['label']}** فقط با نمره‌ی دقیقاً {top} به دست می‌آید."
            )
        ceiling = floor
    return warnings


def show(rules):
    low, high = score_span(rules)
    lines = [
        f"## قاعده‌های رتبه‌بندی — نسخه‌ی {rules['version']}",
        "",
        f"نمره بین **{low}** و **{high}** است. حد پایینِ هر بازه شامل است.",
        "",
        "### باندهای رتبه",
        "",
        "| رتبه | نمره |",
        "|---|---|",
    ]
    ceiling = None
    for entry in rules["grades"]:
        if entry["min"] is None:
            span = f"کمتر از {ceiling}"
        elif ceiling is None:
            span = f"{entry['min']} و بالاتر"
        else:
            span = f"{entry['min']} تا کمتر از {ceiling}"
        lines.append(f"| {entry['label']} | {span} |")
        ceiling = entry["min"]

    types = list(rules["customer_types"])
    lines += [
        "",
        "### معیارها و آستانه‌ها",
        "",
        "| معیار | کلید | ضریب | "
        + " | ".join(rules["customer_types"][key]["label"] for key in types)
        + " |",
        "|---|---|---:|" + "---|" * len(types),
    ]
    for criterion in rules["criteria"]:
        cells = " | ".join(
            " / ".join(str(value) for value in criterion["thresholds"][key])
            for key in types
        )
        lines.append(
            f"| {criterion['label']} | `{criterion['key']}` | "
            f"{criterion['weight']} | {cells} |"
        )

    codes = "، ".join(
        f"{entry['label']} = {', '.join(str(code) for code in entry['codes'])}"
        for entry in rules["customer_types"].values()
    )
    lines += [
        "",
        f"چهار عدد هر ستون، حد پایینِ رتبه‌های ۲ تا ۵ است. کدهای نوع مشتری: {codes}. "
        f"کف ویزیت: {rules['min_visits']}.",
    ]

    warnings = reachability(rules)
    if warnings:
        lines += ["", "**هشدار:**", "", *warnings]
    return "\n".join(lines)


def set_grades(rules, values):
    bounds = numbers(values, "باندهای رتبه")
    expected = len(rules["grades"]) - 1
    if len(bounds) != expected:
        labels = "، ".join(entry["label"] for entry in rules["grades"])
        raise SystemExit(
            f"باندهای رتبه {expected} عدد می‌خواهد (حد پایینِ {labels} — آخری کف است "
            f"و عدد نمی‌گیرد)، {len(bounds)} داده شد."
        )
    if bounds != sorted(bounds, reverse=True) or len(set(bounds)) != len(bounds):
        raise SystemExit(f"باندهای رتبه باید نزولی و بدون تکرار باشند: {bounds}.")
    for entry, bound in zip(rules["grades"], bounds):
        entry["min"] = bound
    return f"باندهای رتبه شد {' / '.join(str(bound) for bound in bounds)}"


def set_thresholds(rules, criterion_key, type_key, values):
    criterion = criterion_of(rules, criterion_key)
    label = type_of(rules, type_key)["label"]
    thresholds = numbers(values, f"آستانه‌های {criterion['label']} ({label})")
    if len(thresholds) != 4:
        raise SystemExit(
            f"آستانه‌ی هر معیار ۴ عدد است (حد پایینِ رتبه‌های ۲ تا ۵)، "
            f"{len(thresholds)} داده شد."
        )
    if thresholds != sorted(thresholds) or len(set(thresholds)) != len(thresholds):
        raise SystemExit(f"آستانه‌ها باید صعودی و بدون تکرار باشند: {thresholds}.")
    criterion["thresholds"][type_key] = thresholds
    return (
        f"آستانه‌ی «{criterion['label']}» برای {label} شد "
        f"{' / '.join(str(value) for value in thresholds)}"
    )


def set_weight(rules, criterion_key, values):
    criterion = criterion_of(rules, criterion_key)
    weight = numbers(values, "ضریب")
    if len(weight) != 1 or weight[0] <= 0:
        raise SystemExit("ضریب یک عدد مثبت است.")
    criterion["weight"] = weight[0]
    return f"ضریب «{criterion['label']}» شد {weight[0]}"


def set_codes(rules, type_key, values):
    entry = type_of(rules, type_key)
    codes = numbers(values, "کد نوع مشتری")
    if not codes:
        raise SystemExit("دست‌کم یک کد لازم است.")
    entry["codes"] = codes
    return f"کدهای «{entry['label']}» شد {', '.join(str(code) for code in codes)}"


def set_min_visits(rules, values):
    visits = numbers(values, "کف ویزیت")
    if len(visits) != 1 or visits[0] < 0:
        raise SystemExit("کف ویزیت یک عدد نامنفی است.")
    rules["min_visits"] = visits[0]
    return f"کف ویزیت شد {visits[0]}"


def apply(rules, target, values):
    """یک تغییر روی قاعده‌ها. target یکی از grades، min_visits یا <چیز>.<کلید> است."""
    if target == "grades":
        return set_grades(rules, values)
    if target == "min_visits":
        return set_min_visits(rules, values)
    if "." not in target:
        raise SystemExit(
            f"هدف '{target}' را نمی‌شناسم. شکل‌های مجاز: grades، min_visits، "
            "<معیار>.<نوع>، weight.<معیار>، codes.<نوع>."
        )
    head, key = target.split(".", 1)
    if head == "weight":
        return set_weight(rules, key, values)
    if head == "codes":
        return set_codes(rules, key, values)
    return set_thresholds(rules, head, key, values)


def main():
    parser = argparse.ArgumentParser(description="نمایش و تغییر قاعده‌های رتبه‌بندی")
    parser.add_argument("command", choices=["show", "set"])
    parser.add_argument("target", nargs="?", help="grades، min_visits، <معیار>.<نوع>")
    parser.add_argument("values", nargs="*", help="عددهای جدید")
    parser.add_argument("--rules", default=str(RULES_PATH))
    parser.add_argument("--dry-run", action="store_true", help="فقط نتیجه را نشان بده")
    args = parser.parse_args()

    # وگرنه روی کنسول ویندوز، خروجی فارسی با UnicodeEncodeError می‌افتد.
    # stderr هم لازم است: پیام‌های خطا فارسی‌اند و از همان‌جا بیرون می‌روند.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    rules = load(args.rules)
    if args.command == "show":
        print(show(rules))
        return

    if not args.target or not args.values:
        raise SystemExit("شکل دستور: rules.py set <هدف> <عددها>. نمونه‌ها در SKILL.md.")

    changed = apply(rules, args.target, args.values)
    if args.dry_run:
        print(f"**{changed}** — ذخیره نشد (`--dry-run`).")
    else:
        save(rules, args.rules)
        print(f"**{changed}.** نسخه‌ی قواعد شد `{rules['version']}`.")
    print()
    print(show(rules))


if __name__ == "__main__":
    main()
