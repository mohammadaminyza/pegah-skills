# کوئری‌ها

دیتابیس `pakhsh`.

> **کوئری فقط متریکِ خام می‌دهد؛ رتبه و نمره کارِ `rank.py` است.** آستانه‌ها یک
> جا زندگی می‌کنند — `rules.json`. اگر `CASE`ی برای رتبه‌دادن به SQL اضافه کنی،
> اولین باری که کسی آستانه را با `rules.py` عوض کند، کوئری و اسکریپت دو جواب
> متفاوت می‌دهند و هیچ‌کدام غلط به نظر نمی‌رسند.

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

## ۱. متریکِ خام مشتریانِ فعال

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
)
SELECT k.ccMoshtary                                          AS "کد مشتری",
       k.noe_moshtary                                        AS "نوع",
       k.tedad_aghlam                                        AS "تعداد اقلام",
       z.vizit_rafteh                                        AS "ویزیت رفته",
       z.vizit_mosbat                                        AS "ویزیت مثبت",
       k.tedad_sku                                           AS "تعداد SKU",
       k.tedad_faktor                                        AS "تعداد فاکتور",
       CAST(b.d_from AS date)                                AS "از",
       CAST(DATEADD(day, -1, b.d_to) AS date)                AS "تا",
       ISNULL(sz.NameSazmanForosh, N'همه لاین‌ها')            AS "لاین فروش"
FROM kharid k
CROSS JOIN bazeh b
LEFT JOIN vizit z ON z.ccMoshtary = k.ccMoshtary
LEFT JOIN Global.SazmanForosh sz ON sz.ccSazmanForosh = b.sazman_forosh
WHERE k.noe_moshtary IN (347, 348)
ORDER BY k.noe_moshtary, k.tedad_aghlam DESC
```

سه نکته‌ی این کوئری که اگر دست ببری خراب می‌شود:

- **`ORDER BY` اینجا رتبه‌بندی نیست**، فقط برای خواندن است. مشتریِ بالای این
  خروجی «مشتری برتر» نیست — نمره را `rank.py` می‌دهد.
- **ویزیتِ نبوده `NULL` می‌ماند، نه صفر.** مشتریِ ویزیت‌نشده با مشتریِ ویزیت‌شده‌ی
  نخریده یکی نیست؛ `rank.py` اولی را «بدون داده» می‌گیرد و رتبه نمی‌دهد. اگر
  اینجا `ISNULL(...,0)` بگذاری، آن مشتری به‌جای «ناقص»، رتبه ۱ می‌گیرد.
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
CROSS JOIN bazeh b
LEFT JOIN kharid k ON k.ccMoshtary = m.ccMoshtary
LEFT JOIN vizit  z ON z.ccMoshtary = m.ccMoshtary
WHERE m.ccNoeMoshtary IN (347, 348)
  AND m.<پرچم فعال> = 1
```

و `ISNULL(k.tedad_aghlam, 0)` و `ISNULL(k.tedad_sku, 0)` بگذار — مشتریِ بی‌خرید
صفر می‌گیرد و رتبه ۱، که درست است. ویزیتش را `ISNULL` **نکن**؛ نبودِ ویزیت
همچنان «بدون داده» است.

تا وقتی این را نساخته‌ای، در تیتر گزارش بنویس «مشتریان **فعال** (دارای خرید در
بازه)» — نه «مشتریان».

## ۳. ورودی برای `rank.py`

ستون‌های خام همان کوئری را به کلیدهای اسکریپت بده:

| ستون کوئری | کلید JSON |
|---|---|
| `کد مشتری` | `code` |
| نام (از مستر) | `name` |
| `نوع` | `type` — کد ۳۴۷/۳۴۸، یا `khord`/`omde`، یا `خرد`/`عمده` |
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

**۳. آستانه‌ها باید تمایز بدهند — از دو طرف.** خروجی را به `rank.py --summary`
بده. `rank.py` خودش هشدار می‌دهد وقتی یک معیار به بیش از ۸۰٪ مشتریانِ یک نوع
**یک** رتبه داده؛ آن هشدار را جدی بگیر، چون معیارِ اشباع‌شده در نمره هست ولی
هیچ‌کس را از هیچ‌کس جدا نمی‌کند:

- **همه ته جدول** (رتبه ۱) — معمولاً بازه کوتاه‌تر از آن است که آستانه فرض
  می‌کند، یا «تعداد اقلام» را سطر گرفته‌ای نه واحد. اول بازه را چک کن.
- **همه سرِ جدول** (رتبه ۵) — آستانه برای این نوع مشتری خیلی پایین است. این همان
  چیزی است که در گزارش مرداد ۱۴۰۵ رخ داد: کم‌ترین عمده‌ی جدول ۱۱٬۱۹۰ قلم خرید
  داشت و سقفِ آستانه‌ی عمده ۷۵۰۱ قلم بود، پس هر ده مشتری نمره‌ی کامل گرفتند و
  جدول عملاً بی‌ترتیب شد.
- **میانه‌ی هر نوع** را نگاه کن: باید حوالی وسط جدول آستانه‌ها بیفتد، نه بیرونش.

اگر آستانه‌ای باید عوض شود، اول کوئری کالیبراسیون پایین را بزن، بعد
`scripts/rules.py set <معیار>.<نوع> ...` — نه دستی و نه با حدس.

**۴. سهم مشتریانِ بدون رکورد ویزیت.** اگر بالاست، یعنی `VisitForoshandeh_Arshiv`
آن لاین را ندارد و رتبه‌ی ویزیت برای بخش بزرگی از جدول محاسبه نشده — این را باید
بالای گزارش گفت.

## کالیبره کردن آستانه — وقتی هشدار اشباع آمد

**آستانه را از توزیعِ همه‌ی مشتریانِ آن نوع دربیاور، نه از چند نفر بالای جدول.**
پنج مشتریِ برترِ عمده همه ته توزیع نیستند، سرش‌اند؛ آستانه‌ای که از آن‌ها ساخته
شود همان اشباع را از آن طرف تکرار می‌کند.

صدک‌های ۲۰ / ۴۰ / ۶۰ / ۸۰ چهار عددی‌اند که هر رتبه را حدوداً یک‌پنجم مشتریان
می‌کنند — نقطه‌ی شروعِ گفت‌وگو با مدیر فروش، نه جواب نهایی:

```sql
WITH params AS (
    SELECT CAST('2026-08-22' AS date) AS rooz_payan,
           1                          AS tedad_mah,
           CAST(NULL AS int)          AS sazman_forosh
),
bazeh AS (
    SELECT DATEADD(day, 1, DATEADD(month, -p.tedad_mah, CAST(p.rooz_payan AS datetime))) AS d_from,
           DATEADD(day, 1, CAST(p.rooz_payan AS datetime))                                AS d_to,
           p.sazman_forosh
    FROM params p
),
kharid AS (
    SELECT a.ccMoshtary,
           MAX(a.ccNoeMoshtary)         AS noe_moshtary,
           SUM(a.Tedad)                 AS tedad_aghlam,
           COUNT(DISTINCT a.ccKalaCode) AS tedad_sku
    FROM Sales.AmarForosh_Arshive a CROSS JOIN bazeh b
    WHERE a.Tarikh >= b.d_from AND a.Tarikh < b.d_to
      AND a.IsMarjoee = 0
      AND (b.sazman_forosh IS NULL OR a.ccSazmanForosh = b.sazman_forosh)
    GROUP BY a.ccMoshtary
)
SELECT DISTINCT
    CASE noe_moshtary WHEN 347 THEN N'خرد' WHEN 348 THEN N'عمده' END                AS "نوع",
    COUNT(*)       OVER (PARTITION BY noe_moshtary)                                 AS "تعداد مشتری",
    MIN(tedad_aghlam) OVER (PARTITION BY noe_moshtary)                              AS "اقلام کمینه",
    PERCENTILE_CONT(0.20) WITHIN GROUP (ORDER BY tedad_aghlam) OVER (PARTITION BY noe_moshtary) AS "اقلام ۲۰٪",
    PERCENTILE_CONT(0.40) WITHIN GROUP (ORDER BY tedad_aghlam) OVER (PARTITION BY noe_moshtary) AS "اقلام ۴۰٪",
    PERCENTILE_CONT(0.60) WITHIN GROUP (ORDER BY tedad_aghlam) OVER (PARTITION BY noe_moshtary) AS "اقلام ۶۰٪",
    PERCENTILE_CONT(0.80) WITHIN GROUP (ORDER BY tedad_aghlam) OVER (PARTITION BY noe_moshtary) AS "اقلام ۸۰٪",
    MAX(tedad_aghlam) OVER (PARTITION BY noe_moshtary)                              AS "اقلام بیشینه",
    PERCENTILE_CONT(0.20) WITHIN GROUP (ORDER BY tedad_sku) OVER (PARTITION BY noe_moshtary) AS "SKU ۲۰٪",
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY tedad_sku) OVER (PARTITION BY noe_moshtary) AS "SKU ۵۰٪",
    PERCENTILE_CONT(0.80) WITHIN GROUP (ORDER BY tedad_sku) OVER (PARTITION BY noe_moshtary) AS "SKU ۸۰٪"
FROM kharid
WHERE noe_moshtary IN (347, 348)
```

`PERCENTILE_CONT` پنجره‌ای است و برای هر سطر تکرار می‌شود؛ `DISTINCT` یک سطر
به‌ازای هر نوع می‌دهد.

بعد:

```bash
python scripts/rules.py set item_count.omde <۲۰٪> <۴۰٪> <۶۰٪> <۸۰٪>
```

سه نکته:

- **عدد را گرد کن.** آستانه‌ی ۱۸٬۴۳۷ چیزی به دقت اضافه نمی‌کند و در جلسه قابل
  دفاع نیست؛ ۱۸٬۰۰۰ همان کار را می‌کند.
- **این کوئری فقط مشتریِ خریدکرده را می‌بیند.** اگر جمعیت واقعی شامل مشتریِ
  بی‌خرید هم هست، صدک‌ها به بالا منحرف‌اند — کوئری ۲ را اول بساز.
- **صدک، قاعده‌ی کسب‌وکار نیست.** خروجی را به مدیر فروش نشان بده و بگو با این
  آستانه‌ها توزیع رتبه‌ها چه می‌شود. تصمیم اوست.
