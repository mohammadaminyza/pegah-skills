# کوئری‌ها

دیتابیس `pakhsh`.

> **این کوئری‌ها روی این دیتابیس اجرا نشده‌اند.** جدول‌ها، ستون‌ها و فیلترها از
> کوئری تست‌شده‌ی اسکیل «ارزیابی فروشنده پگاه» برداشته شده‌اند، ولی کلید
> گروه‌بندی عوض شده (`ccMoshtary` به جای `ccForoshandeh`). بار اول بخش
> **اعتبارسنجی** پایین همین فایل را انجام بده، بعد به عددها استناد کن.

> **`DECLARE` ننویس.** `run_query` فقط **یک** دستور می‌پذیرد که با `SELECT` یا
> `WITH` شروع شود؛ `DECLARE` کوئری را دو‌دستوری می‌کند و کل آن رد می‌شود. به
> همین دلیل بازه با `params` ساخته می‌شود.

## ۰. آخرین تاریخِ داده — قبل از هر چیز

```sql
SELECT MAX(Tarikh) AS akharin FROM Sales.AmarForosh_Arshive
```

## ۱. رتبه‌بندی مشتریانِ فعال — بدون هیچ ناشناخته‌ای

مشتریانی که در بازه خرید داشته‌اند. **تنها بلوک `params` را عوض می‌کنی.**

```sql
WITH params AS (
    SELECT CAST('2026-08-22' AS date) AS rooz_payan,      -- روز پایان بازه
           1                          AS tedad_mah,        -- طول بازه به ماه
           CAST(NULL AS int)          AS sazman_forosh     -- لاین فروش: NULL = همه
),
bazeh AS (
    SELECT DATEADD(day, 1, DATEADD(month, -p.tedad_mah, CAST(p.rooz_payan AS datetime))) AS d_from,
           DATEADD(day, 1, CAST(p.rooz_payan AS datetime))                                AS d_to,
           p.sazman_forosh
    FROM params p
),
kharid AS (
    SELECT a.ccMoshtary,
           MAX(a.ccNoeMoshtary)               AS noe_moshtary,
           SUM(a.Tedad)                       AS tedad_aghlam,
           COUNT(DISTINCT a.ccKalaCode)       AS tedad_sku,
           COUNT(DISTINCT a.ccDarkhastFaktor) AS tedad_faktor
    FROM Sales.AmarForosh_Arshive a CROSS JOIN bazeh b
    WHERE a.Tarikh >= b.d_from AND a.Tarikh < b.d_to
      AND a.IsMarjoee = 0
      AND (b.sazman_forosh IS NULL OR a.ccSazmanForosh = b.sazman_forosh)
    GROUP BY a.ccMoshtary
),
vizit AS (
    SELECT v.ccMoshtary,
           SUM(v.MorajehShodeh) AS vizit_rafteh,
           SUM(v.VisitMosbat)   AS vizit_mosbat
    FROM Sales.VisitForoshandeh_Arshiv v CROSS JOIN bazeh b
    WHERE v.TarikhVisit >= b.d_from AND v.TarikhVisit < b.d_to
      AND v.IsTatil = 0
      AND (b.sazman_forosh IS NULL OR v.ccSazmanForosh = b.sazman_forosh)
    GROUP BY v.ccMoshtary
),
calc AS (
    SELECT k.ccMoshtary, k.noe_moshtary, k.tedad_aghlam, k.tedad_sku, k.tedad_faktor,
           z.vizit_rafteh, z.vizit_mosbat,
           100.0 * z.vizit_mosbat / NULLIF(z.vizit_rafteh, 0) AS vizit_pct
    FROM kharid k
    LEFT JOIN vizit z ON z.ccMoshtary = k.ccMoshtary
    WHERE k.noe_moshtary IN (347, 348)
),
rotbeh AS (
    SELECT calc.*,
           CASE WHEN noe_moshtary = 347 THEN
                     CASE WHEN tedad_aghlam >= 751  THEN 5 WHEN tedad_aghlam >= 650  THEN 4
                          WHEN tedad_aghlam >= 550  THEN 3 WHEN tedad_aghlam >= 450  THEN 2 ELSE 1 END
                ELSE CASE WHEN tedad_aghlam >= 7501 THEN 5 WHEN tedad_aghlam >= 6500 THEN 4
                          WHEN tedad_aghlam >= 5500 THEN 3 WHEN tedad_aghlam >= 4500 THEN 2 ELSE 1 END
           END AS r_aghlam,
           CASE WHEN vizit_pct IS NULL THEN NULL
                WHEN vizit_pct >= 70 THEN 5 WHEN vizit_pct >= 60 THEN 4
                WHEN vizit_pct >= 50 THEN 3 WHEN vizit_pct >= 40 THEN 2 ELSE 1 END AS r_vizit,
           CASE WHEN tedad_sku >= 31 THEN 5 WHEN tedad_sku >= 26 THEN 4
                WHEN tedad_sku >= 21 THEN 3 WHEN tedad_sku >= 16 THEN 2 ELSE 1 END AS r_sku
    FROM calc
),
nomreh AS (
    SELECT rotbeh.*, r_aghlam * 3 + r_vizit * 4 + r_sku * 5 AS nomreh_kol
    FROM rotbeh
)
SELECT ROW_NUMBER() OVER (ORDER BY CASE WHEN nomreh_kol IS NULL THEN 1 ELSE 0 END,
                                   nomreh_kol DESC)              AS "ردیف",
       n.ccMoshtary                                              AS "کد مشتری",
       CASE n.noe_moshtary WHEN 347 THEN N'خرد' WHEN 348 THEN N'عمده' END AS "نوع",
       n.nomreh_kol                                              AS "نمره",
       CASE WHEN n.nomreh_kol IS NULL  THEN N'ناقص — بدون رکورد ویزیت'
            WHEN n.nomreh_kol >= 54    THEN N'سوپر ممتاز'
            WHEN n.nomreh_kol >= 42    THEN N'ممتاز'
            WHEN n.nomreh_kol >= 30    THEN N'درجه ۱'
            WHEN n.nomreh_kol >= 18    THEN N'درجه ۲'
            ELSE N'درجه ۳' END                                   AS "رتبه",
       n.tedad_aghlam                                            AS "تعداد اقلام",
       n.r_aghlam                                                AS "رتبه اقلام",
       CAST(n.vizit_pct AS decimal(6,2))                         AS "درصد ویزیت مثبت",
       n.r_vizit                                                 AS "رتبه ویزیت",
       n.tedad_sku                                               AS "تعداد SKU",
       n.r_sku                                                   AS "رتبه SKU",
       n.vizit_rafteh                                            AS "ویزیت رفته",
       n.vizit_mosbat                                            AS "ویزیت مثبت",
       n.tedad_faktor                                            AS "تعداد فاکتور",
       CAST(b.d_from AS date)                                    AS "از",
       CAST(DATEADD(day, -1, b.d_to) AS date)                    AS "تا",
       ISNULL(sz.NameSazmanForosh, N'همه لاین‌ها')                AS "لاین فروش"
FROM nomreh n
CROSS JOIN bazeh b
LEFT JOIN Global.SazmanForosh sz ON sz.ccSazmanForosh = b.sazman_forosh
ORDER BY CASE WHEN n.nomreh_kol IS NULL THEN 1 ELSE 0 END, n.nomreh_kol DESC
```

سه نکته‌ی این کوئری که اگر دست ببری خراب می‌شود:

- **`r_vizit` وقتی ویزیتی نیست `NULL` می‌ماند، نه ۱.** مشتریِ ویزیت‌نشده با
  مشتریِ ویزیت‌شده‌ی نخریده یکی نیست. `NULL` باعث می‌شود `nomreh_kol` هم `NULL`
  شود و آن مشتری «ناقص» گزارش شود — همان کاری که `rank.py` می‌کند.
- **`noe_moshtary` با `MAX` درمی‌آید.** اگر یک مشتری سطرهایی با دو کد نوع داشته
  باشد، بزرگ‌ترش برنده می‌شود. اعتبارسنجی پایین این را چک می‌کند.
- **`IsMarjoee = 0` در `kharid` هست ولی در `vizit` معنایی ندارد.** ویزیتِ منجر
  به فاکتورِ بعداً مرجوعی‌شده، همچنان ویزیت مثبت است.

## ۲. مشتری بی‌خرید و نام مشتری — احتیاج به مستر دارد

کوئری ۱ فقط مشتریِ خریدکرده را می‌بیند. برای رتبه‌بندیِ **همه‌ی** مشتریان دامنه
(از جمله کسی که در بازه هیچ نخریده و باید رتبه‌ی پایین بگیرد) و برای آوردن نام،
مستر مشتری لازم است. نامش در این دیتابیس تأیید نشده — اول پیدایش کن:

```sql
SELECT t.TABLE_SCHEMA, t.TABLE_NAME, COUNT(*) AS tedad_sotoon
FROM INFORMATION_SCHEMA.TABLES t
JOIN INFORMATION_SCHEMA.COLUMNS c
  ON c.TABLE_SCHEMA = t.TABLE_SCHEMA AND c.TABLE_NAME = t.TABLE_NAME
WHERE t.TABLE_TYPE = 'BASE TABLE'
  AND t.TABLE_NAME LIKE '%Moshtary%'
GROUP BY t.TABLE_SCHEMA, t.TABLE_NAME
ORDER BY tedad_sotoon DESC
```

بعد ستون‌هایش را ببین (`ccMoshtary`، نام، `ccNoeMoshtary`، و پرچم فعال بودن)، و
در کوئری ۱ این دو تغییر را بده:

```sql
-- به‌جای  FROM kharid k  LEFT JOIN vizit z ...
FROM <مستر مشتری> m
LEFT JOIN kharid k ON k.ccMoshtary = m.ccMoshtary
LEFT JOIN vizit  z ON z.ccMoshtary = m.ccMoshtary
WHERE m.ccNoeMoshtary IN (347, 348)
  AND m.<پرچم فعال> = 1
```

و در `calc`، `ISNULL(k.tedad_aghlam, 0)` و `ISNULL(k.tedad_sku, 0)` بگذار — مشتریِ
بی‌خرید صفر می‌گیرد و رتبه ۱، که درست است. ویزیتش را `ISNULL` **نکن**؛ نبودِ
ویزیت همچنان «بدون داده» است.

تا وقتی این را نساخته‌ای، در تیتر گزارش بنویس «مشتریان **فعال** (دارای خرید در
بازه)» — نه «مشتریان».

## ۳. ورودی برای `rank.py`

ستون‌های خام همان کوئری را به کلیدهای اسکریپت بده:

| ستون کوئری | کلید JSON |
|---|---|
| `کد مشتری` | `code` |
| نام (از مستر) | `name` |
| `نوع` یا `ccNoeMoshtary` | `type` — `khord`/`omde`، یا `خرد`/`عمده`، یا ۳۴۷/۳۴۸ |
| `تعداد اقلام` | `item_count` |
| `ویزیت رفته` | `visits_total` |
| `ویزیت مثبت` | `visits_positive` |
| `تعداد SKU` | `sku_count` |

`positive_visit_pct` را می‌توانی مستقیم بدهی، ولی اگر `visits_total` و
`visits_positive` را بدهی اسکریپت خودش حساب می‌کند و کف ویزیت را هم اعمال
می‌کند. مقدارِ نداشته را `null` بفرست، نه صفر.

```python
import subprocess, sys
r = subprocess.run(
    [sys.executable, "skills/رتبه-بندی-مشتریان-پگاه/scripts/rank.py",
     "input.json"],
    capture_output=True, text=True, encoding="utf-8")
print(r.stdout or r.stderr)
```

با `kind='python'` اجرا کن. `kind='bash'` روی میزبان ویندوزی خروجی فارسی را خراب
می‌کند.

## اعتبارسنجی — بار اول، قبل از استناد به عددها

**۱. جمع اقلام.** این را جدا بزن و با جمع ستون «تعداد اقلام» خروجی مقایسه کن:

```sql
SELECT SUM(Tedad) AS tedad_kol, COUNT(DISTINCT ccMoshtary) AS moshtary
FROM Sales.AmarForosh_Arshive
WHERE Tarikh >= '2026-07-23' AND Tarikh < '2026-08-23' AND IsMarjoee = 0
```

خروجی باید **کمتر یا مساوی** این باشد؛ اختلاف = مشتریانِ خارج از ۳۴۷/۳۴۸. اگر
خروجی **بیشتر** شد، جایی چندشمارشی شده — دنبال یک `JOIN` بگرد که ردیف تکثیر
می‌کند.

**۲. مشتری با بیش از یک کد نوع** (که `MAX` پنهانش می‌کند):

```sql
SELECT COUNT(*) AS moshtary_chand_noe FROM (
    SELECT ccMoshtary FROM Sales.AmarForosh_Arshive
    WHERE Tarikh >= '2026-07-23' AND Tarikh < '2026-08-23'
    GROUP BY ccMoshtary HAVING COUNT(DISTINCT ccNoeMoshtary) > 1
) x
```

اگر صفر نبود، در گزارش بگو چند نفر و با کدام قاعده نوعشان انتخاب شده.

**۳. سه عددی که باید معقول باشند.** خروجی را به `rank.py --summary` بده و نگاه
کن:

- **میانه‌ی تعداد اقلامِ خرد** باید حوالی وسط جدول (۵۵۰) باشد. اگر ۵۰ است،
  «تعداد اقلام» را سطر گرفته‌ای نه واحد. اگر ۵۰۰۰ است، بازه بلندتر از یک ماه
  است.
- **توزیع رتبه‌ها** باید پخش باشد. اگر بیش از نیمی درجه ۳ شدند، اول بازه را چک
  کن، نه آستانه‌ها را.
- **سهم مشتریانِ بدون رکورد ویزیت.** اگر بالاست، یعنی `VisitForoshandeh_Arshiv`
  آن لاین را ندارد و رتبه‌ی ویزیت برای بخش بزرگی از جدول محاسبه نشده — این را
  باید بالای گزارش گفت.
