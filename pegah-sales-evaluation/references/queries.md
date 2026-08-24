# کوئری‌های آماده

روی دیتابیس `pakhsh` تست شده‌اند. بازه را عوض کن، بقیه را دست نزن.

## ۰. آخرین تاریخِ داده — قبل از هر چیز

```sql
SELECT MAX(TarikhDarkhast) AS akharin_faktor FROM Sales.DarkhastFaktor;
```

## ۱. پنج متریک اول، به تفکیک فروشنده

`@From` و `@To` میلادی و نیم‌باز `[From, To)`. برای یک روز، `@To` فردای آن است.
برای «تا روز»، `@From` اول ماه شمسی است و `@To` فردای روز ارزیابی.

```sql
DECLARE @From date = '2026-07-23', @To date = '2026-08-23';

WITH visit AS (
    SELECT ccForoshandeh,
           SUM(MorajehShodeh)                                            AS visits_total,
           SUM(VisitMosbat)                                              AS visits_positive,
           SUM(TedadFaktor)                                              AS invoice_count,
           SUM(Tedad_AghlamFaktor)                                       AS invoice_line_count,
           COUNT(DISTINCT ccMoshtary)                                    AS customers_assigned,
           COUNT(DISTINCT CASE WHEN TedadFaktor > 0 THEN ccMoshtary END) AS customers_purchased,
           SUM(MablaghForoshKala)                                        AS gross_sales_amount
    FROM Sales.VisitForoshandeh_Arshiv
    WHERE TarikhVisit >= @From AND TarikhVisit < @To AND IsTatil = 0
    GROUP BY ccForoshandeh
),
shops AS (
    SELECT ccForoshandeh,
           COUNT(DISTINCT CASE WHEN ccNoeMoshtary = 347 THEN ccMoshtary END) AS khord,
           COUNT(DISTINCT CASE WHEN ccNoeMoshtary = 348 THEN ccMoshtary END) AS omde,
           COUNT(DISTINCT CASE WHEN ccNoeMoshtary = 350 THEN ccMoshtary END) AS chain
    FROM Sales.DarkhastFaktor
    WHERE TarikhDarkhast >= @From AND TarikhDarkhast < @To
    GROUP BY ccForoshandeh
),
marjoee AS (
    SELECT m.ccForoshandeh, SUM(s.Tedad1 * s.Fee) AS returns_amount
    FROM Sales.ElamMarjoee m
    JOIN Sales.ElamMarjoeeSatr s ON s.ccElamMarjoee = m.ccElamMarjoee
    WHERE m.TarikhElamMarjoee >= @From AND m.TarikhElamMarjoee < @To
    GROUP BY m.ccForoshandeh
)
SELECT f.ccForoshandeh                          AS code,
       f.SharhForoshandeh                       AS name,
       ISNULL(s.khord, 0)                       AS khord,
       ISNULL(s.omde, 0)                        AS omde,
       ISNULL(s.chain, 0)                       AS chain,
       v.visits_total, v.visits_positive,
       v.invoice_count, v.invoice_line_count,
       v.customers_assigned, v.customers_purchased,
       CAST(v.gross_sales_amount AS bigint)     AS gross_sales_amount,
       CAST(ISNULL(m.returns_amount, 0) AS bigint) AS returns_amount
FROM Sales.Foroshandeh f
JOIN visit v        ON v.ccForoshandeh = f.ccForoshandeh
LEFT JOIN shops s   ON s.ccForoshandeh = f.ccForoshandeh
LEFT JOIN marjoee m ON m.ccForoshandeh = f.ccForoshandeh
WHERE f.ccNoeForoshandeh = 1        -- درخواست‌گیر
  AND v.visits_total > 0
ORDER BY v.invoice_count DESC;
```

`JOIN` روی `visit` عمدی است نه `LEFT JOIN`: فروشنده‌ای که در کل بازه هیچ سطر
ویزیتی ندارد، مرخصی یا غیرفعال بوده و ردیفِ صفر او رتبه‌بندی را شلوغ می‌کند.
اگر ارزیابی حضور هم مدنظر است، `LEFT JOIN` کن و در گزارش جدایشان کن.

## ۲. معیار ششم — هدف گروه محصول

یک سطر به ازای هر (فروشنده، گروه محصول). `@Sal` و `@Mah` شمسی‌اند و باید با بازه
میلادی بالا یکی باشند.

```sql
DECLARE @From date = '2026-07-23', @To date = '2026-08-23';
DECLARE @Sal int = 1405, @Mah tinyint = 5;

WITH actual AS (
    SELECT d.ccForoshandeh, t.ccKalaCode, SUM(t.Tedad1) AS tedad
    FROM Sales.DarkhastFaktorSatr t
    JOIN Sales.DarkhastFaktor d ON d.ccDarkhastFaktor = t.ccDarkhastFaktor
    WHERE d.TarikhDarkhast >= @From AND d.TarikhDarkhast < @To
    GROUP BY d.ccForoshandeh, t.ccKalaCode
)
SELECT h.ccForoshandeh          AS code,
       MAX(k.NameKala)          AS name,
       SUM(h.TedadHadaf)        AS target,
       SUM(ISNULL(a.tedad, 0))  AS sales
FROM Sales.HadafForoshandeh_PG h
LEFT JOIN actual a       ON a.ccForoshandeh = h.ccForoshandeh AND a.ccKalaCode = h.ccKalaCode
LEFT JOIN Warehouse.Kala k ON k.ccKalaCode = h.ccKalaCode
WHERE h.Sal = @Sal AND h.Mah = @Mah AND h.TedadHadaf > 0
GROUP BY h.ccForoshandeh, h.ccKalaCode
HAVING SUM(h.TedadHadaf) > 0;
```

این را در کوئری اول ادغام نکن. هر فروشنده حدود ۱۱۰ گروه محصول دارد؛ join کردنش
با کوئری اول، تعداد فاکتور و مشتری را همان‌قدر برابر می‌کند.

### هدف ماهانه است — برای ارزیابی روز باید خرد شود

`TedadHadaf` هدفِ کل ماه است. اگر همان را با فروش یک روز مقایسه کنی، تحقق حدود
۳٪ درمی‌آید و **همه فروشنده‌ها نمره‌ای حدود ۹۰− می‌گیرند**. این نشانهٔ بدی
کارکردن نیست، نشانهٔ مقایسه غلط است.

روزهای کاری ماه:

```sql
SELECT COUNT(DISTINCT TarikhVisit) AS rooz_kari
FROM Sales.VisitForoshandeh_Arshiv
WHERE TarikhVisit >= @MonthFrom AND TarikhVisit < @MonthTo AND IsTatil = 0;
```

بعد در کوئری هدف، `h.TedadHadaf` را با `h.TedadHadaf / @RoozKari` عوض کن (برای
ارزیابی روز)، یا با `h.TedadHadaf * @RoozSepariShodeh / @RoozKari` (برای «تا
روز»، وقتی ماه هنوز تمام نشده).

جدول `Sales.HadafForoshRoozaneh` با اینکه اسمش «هدف فروش روزانه» است و تا امروز
هم به‌روز است، ستون `TedadHadaf` و `RialHadaf` آن در کل سال ۱۴۰۵ **صفر** است.
فقط عملکرد دارد (`TedadForosh`, `RialForosh`, `RialMarjoee`)، نه هدف. تنها منبع
هدف، `Sales.HadafForoshandeh_PG` ماهانه است.

حتی با خرد کردنِ درست، معیار ۶ در ارزیابی **یک روز** پرنوسان است: فروشنده در یک
روز به همه گروه‌ها سر نمی‌زند، پس میانگینِ نسبت‌ها روی ۱۱۰ گروه بین ۱۰۰٪ و ۴۰۰٪
بالا و پایین می‌رود. در گزارش روزانه این را بگو. معیار ۶ ذاتاً ماهانه است.

## ۳. ساختن ورودی اسکریپت

نتیجه کوئری اول یک شیء به ازای هر فروشنده، و سطرهای کوئری دوم زیر همان
`code` در `product_groups`. شکل دقیق در
[examples/sample-input.json](../examples/sample-input.json).

```json
{
  "period": "cumulative",
  "scope": "کل شرکت — مرداد ۱۴۰۵ (۲۰۲۶-۰۷-۲۳ تا ۲۰۲۶-۰۸-۲۲)",
  "salespeople": [
    { "code": "966", "name": "فروشنده 1104106",
      "shops": { "khord": 18, "omde": 0, "chain": 0 },
      "visits_total": 35, "visits_positive": 18,
      "invoice_count": 18, "invoice_line_count": 163,
      "customers_assigned": 35, "customers_purchased": 18,
      "gross_sales_amount": 8551358473, "returns_amount": 403189820,
      "product_groups": [{ "name": "...", "sales": 120, "target": 150 }] }
  ]
}
```

بعد:

```bash
python skills/pegah-sales-evaluation/scripts/score.py input.json --period cumulative
```

## اندازه‌ها، برای اینکه بفهمی جواب معقول است

مرداد ۱۴۰۵ با فیلتر درخواست‌گیر: حدود **۱۴۴ فروشنده** و **۱۵٬۸۰۰ سطر گروه
محصول**. نمره‌ها بین حدود ۵۰+ و ۵۰− می‌افتند. اگر نمره‌ای سه‌رقمی دیدی، تقریباً
همیشه یعنی فیلتر `ccNoeForoshandeh` جا افتاده.
