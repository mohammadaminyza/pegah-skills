# کوئری‌های آماده

روی دیتابیس `pakhsh` تست شده‌اند. تاریخ‌ها را عوض کن، بقیه را دست نزن.

> **`DECLARE` ننویس.** `run_query` فقط **یک** دستور می‌پذیرد که با `SELECT` یا
> `WITH` شروع شود. `DECLARE @From date = ...;` کوئری را دو‌دستوری می‌کند و کل
> آن رد می‌شود. تاریخ را مستقیم داخل `WHERE` بنویس، همان‌طور که پایین آمده.
>
> **CTE مشکلی ندارد.** `WITH` مجاز است و کوئری‌های زیر سه‌تا CTE دارند و اجرا
> می‌شوند. اگر خطای ردشدن دیدی، دنبال `DECLARE` بگرد نه دنبال `WITH`.

## ۰. آخرین تاریخِ داده — قبل از هر چیز

```sql
SELECT MAX(Tarikh) AS akharin FROM Sales.AmarForosh_Arshive;
```

## ۱. پنج متریک اول، به تفکیک فروشنده

بازه میلادی و **نیم‌باز** است: `>= from` و `< to`.

> **`to` روزِ آخر نیست، فردای روزِ آخر است.** این پرتکرارترین اشتباه این کوئری
> است و بی‌صدا رخ می‌دهد: یک روز کامل از دوره می‌افتد، همه‌ی متریک‌ها کمی کم
> می‌آیند و هیچ خطایی نمی‌بینی.
>
> | دوره | `from` | `to` |
> |---|---|---|
> | مرداد ۱۴۰۵ (۰۵/۰۱ تا ۰۵/۳۱) | `'2026-07-23'` | `'2026-08-23'` |
> | یک روز: ۱۴۰۵/۰۶/۰۱ | `'2026-08-23'` | `'2026-08-24'` |
>
> ۱۴۰۵/۰۵/۳۱ برابر ۲۰۲۶-۰۸-۲۲ است، پس `to` می‌شود ۲۰۲۶-۰۸-۲۳. اگر `to` را
> `'2026-08-22'` بگذاری، ۳۱ مرداد حذف می‌شود: در یک اجرای واقعی «تعداد مغازه با ضریب»
> یک فروشنده از ۳۸۸ به ۳۶۹ افتاد، مرجوعی از ۰٫۶۵۷٪ به ۰٫۷۰۶٪ رفت، و یک نفر
> کلاً از جدول افتاد (۱۱۴ به ۱۱۳).
>
> **آزمون سلامت:** `rooz_kari` را در خروجی نگاه کن. برای یک ماه کامل باید برابر
> تعداد روزهای آن ماه باشد. ۲۵ به‌جای ۲۶ یعنی همین اشتباه.

اینجا مرداد ۱۴۰۵ نمونه گرفته شده — **هر پنج جای تاریخ** را با بازه خودت عوض کن
(`rooz`، `amar`، `satr`، `vis`، `nafar`).

```sql
WITH rooz AS (
    SELECT ccForoshandeh, Tarikh,
           COUNT(DISTINCT CASE WHEN ccNoeMoshtary=347 THEN ccMoshtary END) * 1
         + COUNT(DISTINCT CASE WHEN ccNoeMoshtary=348 THEN ccMoshtary END) * 3
         + COUNT(DISTINCT CASE WHEN ccNoeMoshtary=350 THEN ccMoshtary END) * 5 AS vazni_rooz
    FROM Sales.AmarForosh_Arshive
    WHERE Tarikh >= '2026-07-23' AND Tarikh < '2026-08-23' AND IsMarjoee = 0
    GROUP BY ccForoshandeh, Tarikh
),
shop AS (
    SELECT ccForoshandeh, SUM(vazni_rooz) AS weighted_shops, COUNT(*) AS rooz_kari
    FROM rooz GROUP BY ccForoshandeh
),
amar AS (
    SELECT ccForoshandeh,
           COUNT(DISTINCT CASE WHEN IsMarjoee=0 THEN ccDarkhastFaktor END) AS invoice_count,
           SUM(CASE WHEN IsMarjoee=0 THEN Rial ELSE 0 END)                 AS gross_sales_amount,
          -SUM(CASE WHEN IsMarjoee=1 THEN Rial ELSE 0 END)                 AS returns_amount
    FROM Sales.AmarForosh_Arshive
    WHERE Tarikh >= '2026-07-23' AND Tarikh < '2026-08-23'
    GROUP BY ccForoshandeh
),
satr AS (
    SELECT d.ccForoshandeh,
           COUNT(DISTINCT CAST(t.ccDarkhastFaktor AS varchar(20)) + '-'
                        + CAST(t.ccKala AS varchar(12))) AS invoice_line_count
    FROM Sales.DarkhastFaktorSatr t
    JOIN Sales.DarkhastFaktor d ON d.ccDarkhastFaktor = t.ccDarkhastFaktor
    WHERE d.TarikhDarkhast >= '2026-07-23' AND d.TarikhDarkhast < '2026-08-23'
    GROUP BY d.ccForoshandeh
),
vis AS (
    SELECT ccForoshandeh,
           SUM(MorajehShodeh) AS visits_total,
           SUM(VisitMosbat)   AS visits_positive
    FROM Sales.VisitForoshandeh_Arshiv
    WHERE TarikhVisit >= '2026-07-23' AND TarikhVisit < '2026-08-23' AND IsTatil = 0
    GROUP BY ccForoshandeh
),
faal AS (
    SELECT DISTINCT ccForoshandeh, ccMoshtary FROM Sales.MoshtaryfaalForoshandeh_Arshive
    WHERE Tarikh >= '2026-07-23' AND Tarikh < '2026-08-23'
),
tour AS (
    SELECT DISTINCT ccForoshandeh, ccMoshtary FROM Sales.VisitForoshandeh_Arshiv
    WHERE TarikhVisit >= '2026-07-23' AND TarikhVisit < '2026-08-23' AND IsTatil = 0
),
kharid AS (
    SELECT DISTINCT ccForoshandeh, ccMoshtary FROM Sales.AmarForosh_Arshive
    WHERE Tarikh >= '2026-07-23' AND Tarikh < '2026-08-23' AND IsMarjoee = 0
),
moshtary AS (
    SELECT fa.ccForoshandeh,
           COUNT(*)                                                 AS customers_assigned,
           SUM(CASE WHEN k.ccMoshtary IS NOT NULL THEN 1 ELSE 0 END) AS customers_purchased
    FROM faal fa
    JOIN tour t        ON t.ccForoshandeh = fa.ccForoshandeh AND t.ccMoshtary = fa.ccMoshtary
    LEFT JOIN kharid k ON k.ccForoshandeh = fa.ccForoshandeh AND k.ccMoshtary = fa.ccMoshtary
    GROUP BY fa.ccForoshandeh
)
SELECT f.ccForoshandeh AS code, f.SharhForoshandeh AS name,
       sh.weighted_shops, sh.rooz_kari,
       v.visits_total, v.visits_positive,
       s.invoice_line_count, a.invoice_count,
       mo.customers_assigned, mo.customers_purchased,
       CAST(a.gross_sales_amount AS bigint) AS gross_sales_amount,
       CAST(a.returns_amount AS bigint)     AS returns_amount
FROM Sales.Foroshandeh f
JOIN amar a      ON a.ccForoshandeh = f.ccForoshandeh
JOIN shop sh     ON sh.ccForoshandeh = f.ccForoshandeh
LEFT JOIN satr s ON s.ccForoshandeh = f.ccForoshandeh
LEFT JOIN vis  v ON v.ccForoshandeh = f.ccForoshandeh
LEFT JOIN moshtary mo ON mo.ccForoshandeh = f.ccForoshandeh
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

همان `params` کوئری کامل: یک تاریخ و یک پرچم. سال و ماه شمسی، بازه، و خرد کردن
هدف همه خودکار درمی‌آیند.

```sql
WITH params AS (
    SELECT CAST('2026-08-22' AS date) AS rooz_arzyabi,
           1                          AS mahaneh
),
taghvim AS (
    SELECT TOP 1 c.Sal, c.Mah FROM Sales.HadafForoshRoozaneh c
    JOIN params p ON c.Tarikh = p.rooz_arzyabi
),
dore AS (
    SELECT t.Sal, t.Mah,
           CASE WHEN p.mahaneh = 1
                THEN DATEADD(day, 1, DATEADD(month, -1, CAST(p.rooz_arzyabi AS datetime)))
                ELSE CAST(p.rooz_arzyabi AS datetime) END AS d_from,
           DATEADD(day, 1, CAST(p.rooz_arzyabi AS datetime)) AS d_to,
           (SELECT COUNT(DISTINCT c3.Tarikh) FROM Sales.HadafForoshRoozaneh c3
            WHERE c3.Sal = t.Sal AND c3.Mah = t.Mah) AS rooz_mah,
           CASE WHEN p.mahaneh = 1
                THEN (SELECT COUNT(DISTINCT c4.Tarikh) FROM Sales.HadafForoshRoozaneh c4
                      WHERE c4.Sal = t.Sal AND c4.Mah = t.Mah AND c4.Tarikh <= p.rooz_arzyabi)
                ELSE 1 END AS rooz_dore
    FROM params p CROSS JOIN taghvim t
),
naghsheh AS (
    SELECT DISTINCT ccKalaCode, ccGorohKala FROM Sales.AmarForosh_Arshive
    WHERE Tarikh >= '2026-01-01'
),
hadaf AS (
    SELECT h.ccForoshandeh, k.ccGorohKala,
           SUM(h.TedadHadaf) * MAX(d.rooz_dore) * 1.0 / NULLIF(MAX(d.rooz_mah), 0) AS target
    FROM Sales.HadafForoshandeh_PG h
    CROSS JOIN dore d
    JOIN naghsheh k ON k.ccKalaCode = h.ccKalaCode
    WHERE h.Sal = d.Sal AND h.Mah = d.Mah AND h.TedadHadaf > 0
    GROUP BY h.ccForoshandeh, k.ccGorohKala
),
actual AS (
    SELECT a.ccForoshandeh, a.ccGorohKala, SUM(a.Tedad) AS tedad
    FROM Sales.AmarForosh_Arshive a CROSS JOIN dore d
    WHERE a.Tarikh >= d.d_from AND a.Tarikh < d.d_to AND a.IsMarjoee = 0
    GROUP BY a.ccForoshandeh, a.ccGorohKala
)
SELECT h.ccForoshandeh AS code, h.ccGorohKala AS goroh,
       CAST(h.target AS decimal(18,2)) AS target,
       ISNULL(a.tedad, 0) AS sales
FROM hadaf h
LEFT JOIN actual a ON a.ccForoshandeh = h.ccForoshandeh AND a.ccGorohKala = h.ccGorohKala
WHERE h.target > 0
```

**گروه محصول یعنی `ccGorohKala` (۱۹ تا)، نه `ccKalaCode` (۱۳۳ تا).** هدف در
`HadafForoshandeh_PG` به تفکیک کد کالا ثبت می‌شود، پس باید روی گروه جمع شود.
نگاشت کد به گروه از خودِ `AmarForosh_Arshive` می‌آید که هر دو ستون را دارد —
`Warehouse.Kala` ستون `ccGorohKala` ندارد.

چرا مهم است: با ۱۳۳ کد، هر فروشنده ۱۴۵ سطر هدف می‌گیرد که بیشترشان را اصلاً
نمی‌فروشد، میانه تحقق ۲۶٪ می‌شود و میانگینِ نسبت‌ها را چند گروهِ ریز منفجر
می‌کند. با ۱۹ گروه، هر فروشنده ۱۴ گروه دارد و میانه تحقق ماهانه **۶۹٪** است —
کنار مبنای ۷۵٪. مبنای برگه با همین تعریف نوشته شده.

`rooz_dore / rooz_mah` هدف ماهانه را به بازه می‌برد: برای «تا روز» به نسبت
روزهای سپری‌شده، برای یک روز یک‌سی‌ویکم. بدون آن، ارزیابی روزانه تحقق ۳٪
می‌دهد و همه نمره‌ی حدود ۹۰− می‌گیرند.

معیار ۶ در ارزیابی **یک روز** همچنان پرنوسان است: فروشنده در یک روز به همه ۱۴
گروه سر نمی‌زند، پس میانه تحققِ گروه صفر می‌ماند. در گزارش روزانه بگو.

جدول `Sales.HadafForoshRoozaneh` با اینکه اسمش «هدف فروش روزانه» است، ستون
`TedadHadaf` آن در کل ۱۴۰۵ صفر است — فقط به‌عنوان تقویم شمسی (`Sal`/`Mah`/
`Tarikh`) به کار می‌آید، نه به‌عنوان منبع هدف.

## ۳. نام واقعی فروشنده

`SharhForoshandeh` در این نصب کد است («فروشنده 1104106») و حتی تکراری — چند رکورد
«فروشنده 0101» وجود دارد. برای گزارشی که آدم می‌خواند، نام لازم است:

```sql
WITH act AS (
    SELECT ccForoshandeh, ccAfradForoshandeh, SUM(Rial) AS rial
    FROM Sales.AmarForosh_Arshive
    WHERE Tarikh >= '2026-07-23' AND Tarikh < '2026-08-23' AND IsMarjoee = 0
    GROUP BY ccForoshandeh, ccAfradForoshandeh
),
ranked AS (
    SELECT act.ccForoshandeh, act.ccAfradForoshandeh,
           ROW_NUMBER() OVER (PARTITION BY act.ccForoshandeh ORDER BY act.rial DESC) AS rn,
           COUNT(*)    OVER (PARTITION BY act.ccForoshandeh) AS n_people
    FROM act
)
SELECT r.ccForoshandeh AS code,
       LTRIM(RTRIM(ISNULL(p.FName, '') + ' ' + ISNULL(p.LName, ''))) AS person,
       r.n_people
FROM ranked r
LEFT JOIN Global.Afrad p ON p.ccAfrad = r.ccAfradForoshandeh
WHERE r.rn = 1;
```

**از `ccAfradForoshandeh` جدول آمار برو، نه از `Sales.Foroshandeh.ccAfrad`.** دومی
برای ۵۲۱ رکورد از ۶۲۶ خالی است؛ اولی برای همه‌ی فروشنده‌های فعال نام می‌دهد
(۱۱۴ از ۱۱۵ در مرداد ۱۴۰۵).

### `ccForoshandeh` مسیر است، نه آدم

در مرداد ۱۴۰۵: ۷۵ مسیر یک نفره، ۱۸ مسیر دونفره، ۱۸ مسیر سه‌نفره، ۳ مسیر
چهارنفره. یعنی یک‌سوم مسیرها را در طول ماه بیش از یک نفر کار کرده‌اند و
عددهایشان روی هم جمع شده.

کوئری بالا نامِ نفری را می‌دهد که بیشترین فروش را روی آن مسیر داشته، و `n_people`
می‌گوید چند نفر بوده‌اند. در گزارش، مسیرِ چندنفره را علامت بزن (مثلاً
«احسان سپهری (+۱)») تا کسی نمره‌ی مشترک را به یک نفر نسبت ندهد.

برگه‌ی اصلی اسمش «ارزیابی فروشنده **پرسنل**» است، پس اگر مدیر فروش ارزیابیِ
شخص می‌خواهد نه مسیر، باید همه‌جا `ccAfradForoshandeh` کلیدِ گروه‌بندی شود نه
`ccForoshandeh` — و آن‌وقت همه‌ی عددها عوض می‌شوند. این یک تصمیم است؛ خودت
نگیرش.

## ۴. ساختن ورودی اسکریپت

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

## ۵. کوئری کامل — نمره‌دهی، بازه‌ی داینامیک، روزانه و ماهانه

**تنها دو چیز را عوض می‌کنی، هر دو در `params` بالای کوئری:**

```sql
SELECT CAST('2026-08-22' AS date) AS rooz_arzyabi,   -- روز ارزیابی
       1                          AS mahaneh          -- 1 = تا روز (ماهانه) ، 0 = روزانه
```

بقیه خودش درمی‌آید. `bazeh` اول ماه شمسیِ آن روز را از تقویمِ
`Sales.HadafForoshRoozaneh` (ستون‌های `Sal`/`Mah`) پیدا می‌کند و `d_to` را فردای
روز ارزیابی می‌گذارد. پس دیگر تاریخ را در پنج جا تکرار نمی‌کنی و اشتباهِ
یک‌روز‌کم ممکن نیست.

مبنای معیار ۱ هم خودکار عوض می‌شود: `rooz_kari = 1` یعنی ارزیابی روز و مبنا ۲۵
با گام ۱؛ بیشتر از یک روز یعنی «تا روز» و مبنا ۲۸۰ با گام ۵.

```sql
WITH params AS (
    SELECT CAST('2026-08-22' AS date) AS rooz_arzyabi,
           1                          AS mahaneh
),
bazeh AS (
    SELECT CASE WHEN p.mahaneh = 1
                THEN DATEADD(day, 1, DATEADD(month, -1, CAST(p.rooz_arzyabi AS datetime)))
                ELSE CAST(p.rooz_arzyabi AS datetime) END AS d_from,
           DATEADD(day, 1, CAST(p.rooz_arzyabi AS datetime)) AS d_to,
           p.rooz_arzyabi, p.mahaneh
    FROM params p
),
taghvim AS (
    SELECT COUNT(*) AS rooz_kari
    FROM Global.Taghvim g CROSS JOIN bazeh b
    WHERE g.Tarikh >= b.d_from AND g.Tarikh < b.d_to AND g.CodeNoeTatili IS NULL
),
rooz AS (
    SELECT a.ccForoshandeh, a.Tarikh,
           COUNT(DISTINCT CASE WHEN a.ccNoeMoshtary=347 THEN a.ccMoshtary END) * 1
         + COUNT(DISTINCT CASE WHEN a.ccNoeMoshtary=348 THEN a.ccMoshtary END) * 3
         + COUNT(DISTINCT CASE WHEN a.ccNoeMoshtary=350 THEN a.ccMoshtary END) * 5 AS zarib_rooz
    FROM Sales.AmarForosh_Arshive a CROSS JOIN bazeh b
    WHERE a.Tarikh >= b.d_from AND a.Tarikh < b.d_to AND a.IsMarjoee = 0
    GROUP BY a.ccForoshandeh, a.Tarikh
),
shop AS (
    SELECT ccForoshandeh, SUM(zarib_rooz) AS tedad_ba_zarib FROM rooz GROUP BY ccForoshandeh
),
amar AS (
    SELECT a.ccForoshandeh,
           COUNT(DISTINCT CASE WHEN a.IsMarjoee=0 THEN a.ccDarkhastFaktor END) AS invoice_count,
           SUM(CASE WHEN a.IsMarjoee=0 THEN a.Rial ELSE 0 END)                 AS gross_sales_amount,
          -SUM(CASE WHEN a.IsMarjoee=1 THEN a.Rial ELSE 0 END)                 AS returns_amount
    FROM Sales.AmarForosh_Arshive a CROSS JOIN bazeh b
    WHERE a.Tarikh >= b.d_from AND a.Tarikh < b.d_to
    GROUP BY a.ccForoshandeh
),
satr AS (
    SELECT d.ccForoshandeh,
           COUNT(DISTINCT CAST(t.ccDarkhastFaktor AS varchar(20)) + '-'
                        + CAST(t.ccKala AS varchar(12))) AS invoice_line_count
    FROM Sales.DarkhastFaktorSatr t
    JOIN Sales.DarkhastFaktor d ON d.ccDarkhastFaktor = t.ccDarkhastFaktor
    CROSS JOIN bazeh b
    WHERE d.TarikhDarkhast >= b.d_from AND d.TarikhDarkhast < b.d_to
    GROUP BY d.ccForoshandeh
),
vis AS (
    SELECT v.ccForoshandeh, SUM(v.MorajehShodeh) AS visits_total,
           SUM(v.VisitMosbat) AS visits_positive
    FROM Sales.VisitForoshandeh_Arshiv v CROSS JOIN bazeh b
    WHERE v.TarikhVisit >= b.d_from AND v.TarikhVisit < b.d_to AND v.IsTatil = 0
    GROUP BY v.ccForoshandeh
),
faal AS (
    SELECT DISTINCT m.ccForoshandeh, m.ccMoshtary
    FROM Sales.MoshtaryfaalForoshandeh_Arshive m CROSS JOIN bazeh b
    WHERE m.Tarikh >= b.d_from AND m.Tarikh < b.d_to
),
tour AS (
    SELECT DISTINCT v.ccForoshandeh, v.ccMoshtary
    FROM Sales.VisitForoshandeh_Arshiv v CROSS JOIN bazeh b
    WHERE v.TarikhVisit >= b.d_from AND v.TarikhVisit < b.d_to AND v.IsTatil = 0
),
kharid AS (
    SELECT DISTINCT a.ccForoshandeh, a.ccMoshtary
    FROM Sales.AmarForosh_Arshive a CROSS JOIN bazeh b
    WHERE a.Tarikh >= b.d_from AND a.Tarikh < b.d_to AND a.IsMarjoee = 0
),
moshtary AS (
    SELECT fa.ccForoshandeh,
           COUNT(*)                                                 AS faal_dar_tour,
           SUM(CASE WHEN k.ccMoshtary IS NOT NULL THEN 1 ELSE 0 END) AS kharid_karde
    FROM faal fa
    JOIN tour t        ON t.ccForoshandeh = fa.ccForoshandeh AND t.ccMoshtary = fa.ccMoshtary
    LEFT JOIN kharid k ON k.ccForoshandeh = fa.ccForoshandeh AND k.ccMoshtary = fa.ccMoshtary
    GROUP BY fa.ccForoshandeh
),
nafar AS (
    SELECT a.ccForoshandeh, a.ccAfradForoshandeh, SUM(a.Rial) AS rial
    FROM Sales.AmarForosh_Arshive a CROSS JOIN bazeh b
    WHERE a.Tarikh >= b.d_from AND a.Tarikh < b.d_to AND a.IsMarjoee = 0
    GROUP BY a.ccForoshandeh, a.ccAfradForoshandeh
),
asli AS (
    SELECT ccForoshandeh, ccAfradForoshandeh,
           ROW_NUMBER() OVER (PARTITION BY ccForoshandeh ORDER BY rial DESC) AS rn,
           COUNT(*)    OVER (PARTITION BY ccForoshandeh)                     AS n_people
    FROM nafar
),
calc AS (
    SELECT f.ccForoshandeh, b.d_from, b.d_to, b.mahaneh, tv.rooz_kari,
           LTRIM(RTRIM(ISNULL(p.FName, '') + ' ' + ISNULL(p.LName, ''))) AS person,
           n.n_people, sh.tedad_ba_zarib,
           100.0 * v.visits_positive / NULLIF(v.visits_total, 0)      AS visit_pct,
           1.0 * s.invoice_line_count / NULLIF(a.invoice_count, 0)    AS items,
           100.0 * mo.kharid_karde / NULLIF(mo.faal_dar_tour, 0)      AS cust_pct,
           100.0 * a.returns_amount / NULLIF(a.gross_sales_amount, 0) AS return_pct
    FROM Sales.Foroshandeh f
    CROSS JOIN bazeh b
    CROSS JOIN taghvim tv
    JOIN amar a           ON a.ccForoshandeh = f.ccForoshandeh
    JOIN shop sh          ON sh.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN satr s      ON s.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN vis  v      ON v.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN moshtary mo ON mo.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN asli n      ON n.ccForoshandeh = f.ccForoshandeh AND n.rn = 1
    LEFT JOIN Global.Afrad p ON p.ccAfrad = n.ccAfradForoshandeh
    WHERE f.ccNoeForoshandeh = 1 AND a.gross_sales_amount > 0
),
emtiaz AS (
    SELECT calc.*,
           (tedad_ba_zarib - CASE WHEN mahaneh = 1 THEN 280 ELSE 25 END)
             / CASE WHEN mahaneh = 1 THEN 5.0 ELSE 1.0 END AS s_shop,
           (visit_pct - 40) * 0.5  AS s_visit,
           (items - 6) * 0.5       AS s_items,
           (cust_pct - 80) * 0.5   AS s_cust,
           (1 - return_pct) / 0.25 AS s_return
    FROM calc
)
SELECT ROW_NUMBER() OVER (ORDER BY CASE WHEN mahaneh = 1 AND return_pct > 2 THEN 1 ELSE 0 END,
                                   CASE WHEN mahaneh = 1 AND return_pct > 2 THEN 0 ELSE
                                        ISNULL(s_shop,0)+ISNULL(s_visit,0)+ISNULL(s_items,0)
                                       +ISNULL(s_cust,0)+ISNULL(s_return,0) END DESC) AS "رتبه",
       person        AS "فروشنده",
       ccForoshandeh AS "کد مسیر",
       n_people      AS "نفرات مسیر",
       CAST(CASE WHEN mahaneh = 1 AND return_pct > 2 THEN 0 ELSE
                 ISNULL(s_shop,0)+ISNULL(s_visit,0)+ISNULL(s_items,0)
                +ISNULL(s_cust,0)+ISNULL(s_return,0) END AS decimal(9,2)) AS "جمع امتیاز",
       CASE WHEN mahaneh = 1 AND return_pct > 2 THEN N'حذف — مرجوعی بالای ۲٪' ELSE N'' END AS "وضعیت",
       CAST(s_shop AS decimal(9,2))   AS "امتیاز تعداد مغازه",
       CAST(s_visit AS decimal(9,2))  AS "امتیاز ویزیت",
       CAST(s_items AS decimal(9,2))  AS "امتیاز اقلام",
       CAST(s_cust AS decimal(9,2))   AS "امتیاز مشتری",
       CAST(s_return AS decimal(9,2)) AS "امتیاز مرجوعی",
       tedad_ba_zarib AS "تعداد مغازه با ضریب",
       rooz_kari      AS "روز کاری",
       CAST(visit_pct AS decimal(6,2))  AS "ویزیت مثبت",
       CAST(items AS decimal(6,2))      AS "اقلام هر فاکتور",
       CAST(cust_pct AS decimal(6,2))   AS "مشتری خرید کرده",
       CAST(return_pct AS decimal(6,3)) AS "درصد مرجوعی",
       CAST(d_from AS date) AS "از", CAST(DATEADD(day,-1,d_to) AS date) AS "تا"
FROM emtiaz
ORDER BY CASE WHEN mahaneh = 1 AND return_pct > 2 THEN 1 ELSE 0 END,
         CASE WHEN mahaneh = 1 AND return_pct > 2 THEN 0 ELSE
              ISNULL(s_shop,0)+ISNULL(s_visit,0)+ISNULL(s_items,0)
             +ISNULL(s_cust,0)+ISNULL(s_return,0) END DESC
```

### «تا روز» یعنی یک ماه متحرک، نه از اول ماه شمسی

سرتیتر برگه: **«ارزیابی فروشنده تا روز (هر روز تا یک ماه قبلی)»**. یعنی پنجره‌ی
همیشه یک‌ماهه که به روز ارزیابی ختم می‌شود، نه انباشت از اول ماه شمسی.

```sql
d_from = DATEADD(day, 1, DATEADD(month, -1, rooz_arzyabi))
d_to   = DATEADD(day, 1, rooz_arzyabi)
```

روی آخرین روز ماه این دو یکی می‌شوند (۳۱ مرداد ⇒ هر دو ۰۷-۲۳ تا ۰۸-۲۳)، ولی هر
روز دیگری فرق دارند و فرقش فاجعه است:

| روز ارزیابی ۳ شهریور | میانگین تعداد مغازه با ضریب | بالای مبنای ۲۸۰ |
|---|---:|---:|
| از اول ماه شمسی (غلط) | ۲۵ | **۰ از ۱۰۹** |
| یک ماه متحرک (درست) | ۲۲۶ | ۳۱ از ۱۱۵ |

با انباشت از اول ماه، در روز سوم ماه هر فروشنده سه روز داده دارد در برابر مبنایی
که برای یک ماه نوشته شده — همه حدود ۵۱− می‌گیرند و رتبه‌بندی بی‌معنی می‌شود.
مبنای ثابت ۲۸۰ فقط با پنجره‌ی ثابت یک‌ماهه معنا دارد.

### روز کاری از تقویم می‌آید، نه از فعالیت فروش

`Global.Taghvim` تقویم شمسی شرکت است: یک سطر به ازای هر روز، با `Tarikh`،
`TarikhShamsi`، `Sal`، `Mah`، `Rooz` و `CodeNoeTatili` — کد تعطیلی که `NULL`
یعنی روز کاری. `Global.NoeTatili` کدها را نام می‌دهد: ۱ جمعه، ۲ تعطیل رسمی،
۳ تعطیلی شیفت، ۴ تعطیلی شرکت.

```sql
SELECT COUNT(*) FROM Global.Taghvim g
WHERE g.Tarikh >= d_from AND g.Tarikh < d_to AND g.CodeNoeTatili IS NULL
```

شمردن روزهایی که فروش داشته‌اند جای این کار را نمی‌گیرد: روزی که تعطیل بوده با
روزی که فروشنده کار نکرده یک شکل درمی‌آیند. مرداد ۱۴۰۵ با تقویم **۲۳ روز کاری**
دارد (۵ جمعه و ۳ تعطیل رسمی از ۳۱ روز)، در حالی که شمارش از روی فروش ۲۶ می‌داد.
سه روز خطا یعنی هدف روزانه ۱۳٪ کمتر از واقع خرد می‌شود.

`Sales.HadafForoshRoozaneh` هم `Sal`/`Mah` دارد ولی جدول هدف است نه تقویم و روز
تعطیل را علامت نمی‌زند. برای تقویم `Global.Taghvim` را بردار.

**این کوئری معیار ششم را ندارد** — پنج معیار از شش. سطر معیار ۶ به ازای
فروشنده×گروه است و join کردنش بقیه را ۱۱۰ برابر می‌کند. برای ارزیابی کامل،
کوئری ۲ را جدا بگیر و `score.py` را با هر شش معیار اجرا کن. این میان‌بر است،
نه جایگزین.

ستون‌های «از» و «تا» در خروجی هستند تا در گزارش بنویسی و کسی بازه را حدس نزند.

## اندازه‌ها، برای اینکه بفهمی جواب معقول است

مرداد ۱۴۰۵ با فیلتر درخواست‌گیر: **۱۱۵ فروشنده**، حدود **۱۵٬۸۰۰ سطر گروه
محصول**، و **۱۵ نفر** با مرجوعی بالای ۲٪ (یعنی نمره کل صفر). مرجوعی کل شرکت در
آن ماه ۱٫۰۴٪ بود — درست روی مبنای ۱٪، که نشان می‌دهد مبنای برگه با همین تعریف
نوشته شده.

نمره‌ها بین حدود ۱۲۵+ و ۵۰− می‌افتند. نمره‌ی سه‌رقمیِ گروهی یعنی فیلتر
`ccNoeForoshandeh` جا افتاده. مرجوعیِ نزدیک صفر برای همه یعنی از جدول اشتباه
خوانده‌ای.
