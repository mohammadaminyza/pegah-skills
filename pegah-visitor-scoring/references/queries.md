# کوئری‌های آماده

روی دیتابیس `pakhsh` تست شده‌اند. بازه را عوض کن، بقیه را دست نزن.

## ۰. آخرین تاریخِ داده — قبل از هر چیز

```sql
SELECT MAX(Tarikh) AS akharin FROM Sales.AmarForosh_Arshive;
```

## ۱. پنج متریک اول، به تفکیک فروشنده

`@From` و `@To` میلادی و نیم‌باز `[From, To)`. برای یک روز، `@To` فردای آن است.
برای «تا روز»، `@From` اول ماه شمسی است و `@To` فردای روز ارزیابی.

```sql
DECLARE @From date = '2026-07-23', @To date = '2026-08-23';

WITH amar AS (
    SELECT ccForoshandeh,
           COUNT(DISTINCT CASE WHEN IsMarjoee=0 AND ccNoeMoshtary=347 THEN ccMoshtary END) AS khord,
           COUNT(DISTINCT CASE WHEN IsMarjoee=0 AND ccNoeMoshtary=348 THEN ccMoshtary END) AS omde,
           COUNT(DISTINCT CASE WHEN IsMarjoee=0 AND ccNoeMoshtary=350 THEN ccMoshtary END) AS chain,
           COUNT(DISTINCT CASE WHEN IsMarjoee=0 THEN ccMoshtary END)       AS customers_purchased,
           COUNT(DISTINCT CASE WHEN IsMarjoee=0 THEN ccDarkhastFaktor END) AS invoice_count,
           SUM(CASE WHEN IsMarjoee=0 THEN Rial ELSE 0 END)                 AS gross_sales_amount,
          -SUM(CASE WHEN IsMarjoee=1 THEN Rial ELSE 0 END)                 AS returns_amount
    FROM Sales.AmarForosh_Arshive
    WHERE Tarikh >= @From AND Tarikh < @To
    GROUP BY ccForoshandeh
),
satr AS (
    SELECT d.ccForoshandeh,
           COUNT(DISTINCT CAST(t.ccDarkhastFaktor AS varchar(20)) + '-'
                        + CAST(t.ccKala AS varchar(12))) AS invoice_line_count
    FROM Sales.DarkhastFaktorSatr t
    JOIN Sales.DarkhastFaktor d ON d.ccDarkhastFaktor = t.ccDarkhastFaktor
    WHERE d.TarikhDarkhast >= @From AND d.TarikhDarkhast < @To
    GROUP BY d.ccForoshandeh
),
vis AS (
    SELECT ccForoshandeh,
           SUM(MorajehShodeh)         AS visits_total,
           SUM(VisitMosbat)           AS visits_positive,
           COUNT(DISTINCT ccMoshtary) AS customers_assigned
    FROM Sales.VisitForoshandeh_Arshiv
    WHERE TarikhVisit >= @From AND TarikhVisit < @To AND IsTatil = 0
    GROUP BY ccForoshandeh
)
SELECT f.ccForoshandeh AS code, f.SharhForoshandeh AS name,
       a.khord, a.omde, a.chain,
       v.visits_total, v.visits_positive,
       s.invoice_line_count, a.invoice_count,
       v.customers_assigned, a.customers_purchased,
       CAST(a.gross_sales_amount AS bigint) AS gross_sales_amount,
       CAST(a.returns_amount AS bigint)     AS returns_amount
FROM Sales.Foroshandeh f
JOIN amar a      ON a.ccForoshandeh = f.ccForoshandeh
LEFT JOIN satr s ON s.ccForoshandeh = f.ccForoshandeh
LEFT JOIN vis  v ON v.ccForoshandeh = f.ccForoshandeh
WHERE f.ccNoeForoshandeh = 1        -- درخواست‌گیر
  AND a.gross_sales_amount > 0
ORDER BY a.invoice_count DESC;
```

`Sales.AmarForosh_Arshive` مرکز ثقل است: یک سطر به ازای (تاریخ، فروشنده، مشتری،
کالا، فاکتور) با `Rial`، `Tedad`، `IsMarjoee`، `ccNoeMoshtary` و
`ccDarkhastFaktor`. چهار متریک از همین یکی درمی‌آید و صورت و مخرجِ مرجوعی از یک
جا می‌آیند، که مهم‌ترین ویژگی‌اش است.

دو چیز از جای دیگر می‌آید، چون این جدول ندارد:

- **مخرج ویزیت** (`visits_total`) — ویزیتی که به فاکتور نرسیده اصلاً سطری در
  `AmarForosh_Arshive` نمی‌سازد. فقط `Sales.VisitForoshandeh_Arshiv` می‌داند
  فروشنده کجا رفت و نفروخت.
- **تعداد اقلام** — `AmarForosh_Arshive` روی `ccKalaCode` تجمیع می‌کند، نه سطر
  فاکتور. سطرِ واقعی در `Sales.DarkhastFaktorSatr` است.

## ۲. معیار ششم — هدف گروه محصول

```sql
DECLARE @From date = '2026-07-23', @To date = '2026-08-23';
DECLARE @Sal int = 1405, @Mah tinyint = 5;

WITH actual AS (
    SELECT ccForoshandeh, ccKalaCode, SUM(Tedad) AS tedad
    FROM Sales.AmarForosh_Arshive
    WHERE Tarikh >= @From AND Tarikh < @To AND IsMarjoee = 0
    GROUP BY ccForoshandeh, ccKalaCode
)
SELECT h.ccForoshandeh         AS code,
       MAX(k.NameKala)         AS name,
       SUM(h.TedadHadaf)       AS target,
       SUM(ISNULL(a.tedad, 0)) AS sales
FROM Sales.HadafForoshandeh_PG h
LEFT JOIN actual a         ON a.ccForoshandeh = h.ccForoshandeh AND a.ccKalaCode = h.ccKalaCode
LEFT JOIN Warehouse.Kala k ON k.ccKalaCode = h.ccKalaCode
WHERE h.Sal = @Sal AND h.Mah = @Mah AND h.TedadHadaf > 0
GROUP BY h.ccForoshandeh, h.ccKalaCode
HAVING SUM(h.TedadHadaf) > 0;
```

هدف تعدادی است، پس عملکرد هم `Tedad` است نه `Rial`. `IsMarjoee = 0` لازم است،
وگرنه مرجوعی از تحقق هدف کم می‌شود و معیار ۵ دو بار جریمه می‌کند.

این را در کوئری اول ادغام نکن. هر فروشنده حدود ۱۱۰ گروه محصول دارد؛ join کردنش
با کوئری اول، تعداد فاکتور و مشتری را همان‌قدر برابر می‌کند.

### هدف ماهانه است — برای ارزیابی روز باید خرد شود

`TedadHadaf` هدفِ کل ماه است. اگر همان را با فروش یک روز مقایسه کنی، تحقق حدود
۳٪ درمی‌آید و **همه فروشنده‌ها نمره‌ای حدود ۹۰− می‌گیرند**. این نشانهٔ بدی
کارکردن نیست، نشانهٔ مقایسه غلط است.

```sql
SELECT COUNT(DISTINCT TarikhVisit) AS rooz_kari
FROM Sales.VisitForoshandeh_Arshiv
WHERE TarikhVisit >= @MonthFrom AND TarikhVisit < @MonthTo AND IsTatil = 0;
```

بعد `h.TedadHadaf` را با `h.TedadHadaf / @RoozKari` عوض کن (ارزیابی روز)، یا با
`h.TedadHadaf * @RoozSepariShodeh / @RoozKari` (ارزیابی «تا روز» وقتی ماه هنوز
تمام نشده).

جدول `Sales.HadafForoshRoozaneh` با اینکه اسمش «هدف فروش روزانه» است و تا امروز
هم به‌روز است، ستون `TedadHadaf` و `RialHadaf` آن در کل سال ۱۴۰۵ **صفر** است.
تنها منبع هدف، `Sales.HadafForoshandeh_PG` ماهانه است.

حتی با خرد کردنِ درست، معیار ۶ در ارزیابی **یک روز** پرنوسان است: فروشنده در یک
روز به همه گروه‌ها سر نمی‌زند. در گزارش روزانه این را بگو.

## ۳. ساختن ورودی اسکریپت

نتیجه کوئری اول یک شیء به ازای هر فروشنده، و سطرهای کوئری دوم زیر همان `code` در
`product_groups`. شکل دقیق در
[examples/sample-input.json](../examples/sample-input.json).

```python
import subprocess, sys
r = subprocess.run(
    [sys.executable, "skills/pegah-visitor-scoring/scripts/score.py",
     "input.json", "--period", "cumulative"],
    capture_output=True, text=True, encoding="utf-8")
print(r.stdout or r.stderr)
```

با `kind='python'` اجرا کن. `kind='bash'` روی میزبان ویندوزی خروجی فارسی را
خراب می‌کند.

## اندازه‌ها، برای اینکه بفهمی جواب معقول است

مرداد ۱۴۰۵ با فیلتر درخواست‌گیر: **۱۱۵ فروشنده**، حدود **۱۵٬۸۰۰ سطر گروه
محصول**، و **۱۵ نفر** با مرجوعی بالای ۲٪ (یعنی نمره کل صفر). مرجوعی کل شرکت در
آن ماه ۱٫۰۴٪ بود — درست روی مبنای ۱٪، که نشان می‌دهد مبنای برگه با همین تعریف
نوشته شده.

نمره‌ها بین حدود ۱۲۵+ و ۵۰− می‌افتند. نمره‌ی سه‌رقمیِ گروهی یعنی فیلتر
`ccNoeForoshandeh` جا افتاده. مرجوعیِ نزدیک صفر برای همه یعنی از جدول اشتباه
خوانده‌ای.
