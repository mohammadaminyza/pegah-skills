# کوئری‌ها

روی دیتابیس `pakhsh` تست شده‌اند.

> **`DECLARE` ننویس.** `run_query` فقط **یک** دستور می‌پذیرد که با `SELECT` یا
> `WITH` شروع شود؛ `DECLARE` کوئری را دو‌دستوری می‌کند و کل آن رد می‌شود. به
> همین دلیل بازه با `params` ساخته می‌شود. `WITH` خودش مجاز است — اگر خطای
> ردشدن دیدی دنبال `DECLARE` بگرد، نه دنبال CTE.

## ۰. آخرین تاریخِ داده — قبل از هر چیز

```sql
SELECT MAX(Tarikh) AS akharin FROM Sales.AmarForosh_Arshive
```

## ۱. کوئری کامل — شش معیار، جمع امتیاز، رتبه‌بندی

**تنها بلوک `params` را عوض می‌کنی:**

```sql
SELECT CAST('2026-08-22' AS date) AS rooz_arzyabi,   -- روز ارزیابی
       1                          AS mahaneh,         -- ۱ = تا روز ، ۰ = روزانه
       5                          AS hadeaghal_faktor,-- کف تعداد فاکتور
       CAST(NULL AS int)          AS sazman_forosh    -- لاین فروش: NULL = همه
```

**لاین فروش (سازمان فروش)** از `Global.SazmanForosh`:
۱ لاین یک، ۲ نوشيدني، ۳ لاین دو، ۴ مشتريان ويژه. `NULL` یعنی بدون فیلتر.
در مرداد ۱۴۰۵، ۱۱۷ فروشنده در لاین یک بودند و ۳ نفر در لاین دو — پس اگر فیلتر
نگذاری، دو لاین با مبناهای یکسان با هم مقایسه می‌شوند.

بقیه خودکار است:

- `bazeh` برای «تا روز» یک ماه متحرک می‌سازد که به روز ارزیابی ختم می‌شود
  (`DATEADD(month, -1, ...)`) — سرتیتر برگه می‌گوید «هر روز تا یک ماه قبلی».
- `taghvim` روز کاری را از `Global.Taghvim` می‌شمارد (`CodeNoeTatili IS NULL`).
- مبنای معیار ۱ بین ۲۵ (روزانه) و ۲۸۰ (ماهانه) عوض می‌شود.
- معیار ۴ و معیار ۶ در دوره‌ی روزانه محاسبه **نمی‌شوند** (`NULL` می‌مانند) —
  دوره‌ی روزانه چهار معیار دارد.
- `marjoee` مرجوعیِ **مبنادار** را می‌آورد: اقلامی که علتشان مسئولیتِ «فروش»
  دارد (`Warehouse.ElatMarjoeeKala.MasoleiatElat = 1`). خرابی، ضایعات تولید و
  آسیب انبار مسئولیتِ تولید و پخش‌اند و در این عدد نیستند. مخرجش `tedad_forosh`
  است، پس نسبت **کالا ÷ کالا** است نه فاکتور ÷ فاکتور.
- حذفِ مرجوعی بالای ۲٪ فقط در دوره‌ی «تا روز» اعمال می‌شود.
- `hadeaghal_faktor` فروشنده‌هایی را که در بازه یکی‌دو فاکتور دارند کنار
  می‌گذارد.

```sql
WITH params AS (
    SELECT CAST('2026-08-22' AS date) AS rooz_arzyabi,
           1                          AS mahaneh,
           5                          AS hadeaghal_faktor,
           CAST(NULL AS int)          AS sazman_forosh
),
bazeh AS (
    SELECT CASE WHEN p.mahaneh = 1
                THEN DATEADD(day, 1, DATEADD(month, -1, CAST(p.rooz_arzyabi AS datetime)))
                ELSE CAST(p.rooz_arzyabi AS datetime) END AS d_from,
           DATEADD(day, 1, CAST(p.rooz_arzyabi AS datetime)) AS d_to,
           p.rooz_arzyabi, p.mahaneh, p.hadeaghal_faktor, p.sazman_forosh
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
      AND (b.sazman_forosh IS NULL OR a.ccSazmanForosh = b.sazman_forosh)
    GROUP BY a.ccForoshandeh, a.Tarikh
),
shop AS (
    SELECT ccForoshandeh, SUM(zarib_rooz) AS tedad_ba_zarib FROM rooz GROUP BY ccForoshandeh
),
faktor AS (
    SELECT a.ccForoshandeh,
           COUNT(DISTINCT a.ccDarkhastFaktor) AS kol_faktor,
           SUM(a.Tedad)                       AS tedad_forosh
    FROM Sales.AmarForosh_Arshive a CROSS JOIN bazeh b
    WHERE a.Tarikh >= b.d_from AND a.Tarikh < b.d_to AND a.IsMarjoee = 0
      AND (b.sazman_forosh IS NULL OR a.ccSazmanForosh = b.sazman_forosh)
    GROUP BY a.ccForoshandeh
),
marjoee AS (
    SELECT h.ccForoshandeh, SUM(CAST(s.Tedad1 AS bigint)) AS tedad_marjoee
    FROM Sales.ElamMarjoee h
    JOIN Sales.ElamMarjoeeSatr s ON s.ccElamMarjoee = h.ccElamMarjoee
    JOIN Warehouse.ElatMarjoeeKala e ON e.ccElatMarjoeeKala = s.ccElatMarjoeeKala
    CROSS JOIN bazeh b
    WHERE h.TarikhElamMarjoee >= b.d_from AND h.TarikhElamMarjoee < b.d_to
      AND e.MasoleiatElat = 1
    GROUP BY h.ccForoshandeh
),
satr AS (
    SELECT d.ccForoshandeh, COUNT(*) AS tedad_satr
    FROM Sales.DarkhastFaktorSatr t
    JOIN Sales.DarkhastFaktor d ON d.ccDarkhastFaktor = t.ccDarkhastFaktor
    CROSS JOIN bazeh b
    WHERE d.TarikhDarkhast >= b.d_from AND d.TarikhDarkhast < b.d_to
    GROUP BY d.ccForoshandeh
),
vis AS (
    SELECT v.ccForoshandeh,
           SUM(v.MorajehShodeh)                                            AS vizit_rafteh,
           SUM(v.VisitMosbat)                                              AS vizit_mosbat,
           COUNT(DISTINCT CASE WHEN v.MorajehShodeh=1 THEN v.ccMoshtary END) AS moshtary_rafteh,
           COUNT(DISTINCT CASE WHEN v.VisitMosbat=1  THEN v.ccMoshtary END) AS moshtary_kharid
    FROM Sales.VisitForoshandeh_Arshiv v CROSS JOIN bazeh b
    WHERE v.TarikhVisit >= b.d_from AND v.TarikhVisit < b.d_to AND v.IsTatil = 0
      AND (b.sazman_forosh IS NULL OR v.ccSazmanForosh = b.sazman_forosh)
    GROUP BY v.ccForoshandeh
),
goroh_hadaf AS (
    SELECT h.ccForoshandeh, h.ccGorohKala,
           SUM(h.TedadHadaf)  AS hadaf,
           SUM(h.TedadForosh) AS forosh
    FROM Sales.HadafForoshRoozanehNew h CROSS JOIN bazeh b
    WHERE h.Tarikh >= b.d_from AND h.Tarikh < b.d_to
      AND (b.sazman_forosh IS NULL OR h.ccSazmanForosh = b.sazman_forosh)
    GROUP BY h.ccForoshandeh, h.ccGorohKala
    HAVING SUM(h.TedadHadaf) > 0
),
goroh AS (
    SELECT ccForoshandeh,
           100.0 * SUM(forosh) / NULLIF(SUM(hadaf), 0)        AS tahaghogh_pct,
           100.0 * SUM(forosh) / NULLIF(SUM(hadaf), 0) - 75   AS s_target,
           COUNT(*)                                           AS n_goroh
    FROM goroh_hadaf GROUP BY ccForoshandeh
),
nafar AS (
    SELECT a.ccForoshandeh, a.ccAfradForoshandeh, SUM(a.Rial) AS rial
    FROM Sales.AmarForosh_Arshive a CROSS JOIN bazeh b
    WHERE a.Tarikh >= b.d_from AND a.Tarikh < b.d_to AND a.IsMarjoee = 0
      AND (b.sazman_forosh IS NULL OR a.ccSazmanForosh = b.sazman_forosh)
    GROUP BY a.ccForoshandeh, a.ccAfradForoshandeh
),
asli AS (
    SELECT ccForoshandeh, ccAfradForoshandeh,
           ROW_NUMBER() OVER (PARTITION BY ccForoshandeh ORDER BY rial DESC) AS rn,
           COUNT(*)    OVER (PARTITION BY ccForoshandeh)                     AS n_people
    FROM nafar
),
calc AS (
    SELECT f.ccForoshandeh, b.d_from, b.d_to, b.mahaneh, b.sazman_forosh, tv.rooz_kari,
           LTRIM(RTRIM(ISNULL(p.FName, '') + ' ' + ISNULL(p.LName, ''))) AS person,
           n.n_people, sh.tedad_ba_zarib, fk.kol_faktor,
           fk.tedad_forosh, ISNULL(mj.tedad_marjoee, 0) AS tedad_marjoee,
           100.0 * v.vizit_mosbat   / NULLIF(v.vizit_rafteh, 0)    AS vizit_pct,
           1.0   * s.tedad_satr     / NULLIF(fk.kol_faktor, 0)     AS satr_per_faktor,
           100.0 * v.moshtary_kharid / NULLIF(v.moshtary_rafteh, 0) AS moshtary_pct,
           100.0 * ISNULL(mj.tedad_marjoee, 0) / NULLIF(fk.tedad_forosh, 0) AS marjoee_pct,
           gr.tahaghogh_pct, gr.s_target, gr.n_goroh
    FROM Sales.Foroshandeh f
    CROSS JOIN bazeh b
    CROSS JOIN taghvim tv
    JOIN faktor fk        ON fk.ccForoshandeh = f.ccForoshandeh
    JOIN shop sh          ON sh.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN marjoee mj  ON mj.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN satr s      ON s.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN vis  v      ON v.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN goroh gr    ON gr.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN asli n      ON n.ccForoshandeh = f.ccForoshandeh AND n.rn = 1
    LEFT JOIN Global.Afrad p ON p.ccAfrad = n.ccAfradForoshandeh
    WHERE f.ccNoeForoshandeh = 1
      AND fk.kol_faktor >= b.hadeaghal_faktor
),
emtiaz AS (
    SELECT calc.*,
           (tedad_ba_zarib - CASE WHEN mahaneh = 1 THEN 280 ELSE 25 END)
             / CASE WHEN mahaneh = 1 THEN 5.0 ELSE 1.0 END       AS s_shop,
           (vizit_pct - 40) * 0.5                                AS s_vizit,
           (satr_per_faktor - 6) * 0.5                           AS s_satr,
           CASE WHEN mahaneh = 1 THEN (moshtary_pct - 80) * 0.5 END AS s_moshtary,
           (1 - marjoee_pct) / 0.25                              AS s_marjoee,
           CASE WHEN mahaneh = 1 THEN s_target END                  AS s_hadaf
    FROM calc
),
jam AS (
    SELECT emtiaz.*,
           CASE WHEN mahaneh = 1 AND marjoee_pct > 2 THEN 0 ELSE
                ISNULL(s_shop,0)+ISNULL(s_vizit,0)+ISNULL(s_satr,0)
               +ISNULL(s_moshtary,0)+ISNULL(s_marjoee,0)+ISNULL(s_hadaf,0) END AS jam_emtiaz,
           CASE WHEN mahaneh = 1 AND marjoee_pct > 2 THEN 1 ELSE 0 END AS hazf
    FROM emtiaz
)
SELECT ROW_NUMBER() OVER (ORDER BY hazf, jam_emtiaz DESC)       AS "رتبه",
       person        AS "فروشنده",
       ccForoshandeh AS "کد مسیر",
       n_people      AS "نفرات مسیر",
       CAST(jam_emtiaz AS decimal(9,2)) AS "جمع امتیاز",
       CASE WHEN hazf = 1 THEN N'حذف — مرجوعی بالای ۲٪'
            WHEN jam_emtiaz > 0  THEN N'عالی'
            WHEN jam_emtiaz >= -5 THEN N'معمولی'
            ELSE N'نیازمند تصمیم اساسی' END AS "وضعیت",
       CAST(s_shop AS decimal(9,2))     AS "امتیاز تعداد مغازه",
       CAST(s_vizit AS decimal(9,2))    AS "امتیاز ویزیت مثبت",
       CAST(s_satr AS decimal(9,2))     AS "امتیاز سطر فاکتور",
       CAST(s_moshtary AS decimal(9,2)) AS "امتیاز مشتری خرید کرده",
       CAST(s_marjoee AS decimal(9,2))  AS "امتیاز مرجوعی",
       CAST(s_hadaf AS decimal(9,2))    AS "امتیاز هدف گروه",
       tedad_ba_zarib AS "تعداد مغازه با ضریب",
       kol_faktor     AS "تعداد فاکتور",
       rooz_kari      AS "روز کاری",
       CAST(vizit_pct AS decimal(6,2))       AS "درصد ویزیت مثبت",
       CAST(satr_per_faktor AS decimal(6,2)) AS "میانگین سطر فاکتور",
       CAST(moshtary_pct AS decimal(6,2))    AS "درصد مشتری خرید کرده",
       tedad_marjoee  AS "تعداد مرجوعی فروش",
       tedad_forosh   AS "تعداد فروش",
       CAST(marjoee_pct AS decimal(6,3))     AS "درصد مرجوعی مبنادار",
       CAST(tahaghogh_pct AS decimal(8,2))   AS "تحقق هدف گروه",
       n_goroh AS "تعداد گروه",
       CAST(d_from AS date) AS "از", CAST(DATEADD(day,-1,d_to) AS date) AS "تا",
       ISNULL(sz.NameSazmanForosh, N'همه لاین‌ها') AS "لاین فروش"
FROM jam
LEFT JOIN Global.SazmanForosh sz ON sz.ccSazmanForosh = jam.sazman_forosh
ORDER BY hazf, jam_emtiaz DESC
```

## ۲. تغییر آستانه‌ها

عددهای مبنا و گام در `rules.json` هستند و کاربر می‌تواند عوضشان کند. اگر عوض
شدند، در کوئری این جاها را دست ببر — همه در CTE `emtiaz` کنار هم‌اند:

```sql
(tedad_ba_zarib - CASE WHEN mahaneh = 1 THEN 280 ELSE 25 END)
  / CASE WHEN mahaneh = 1 THEN 5.0 ELSE 1.0 END       AS s_shop
(vizit_pct - 40) * 0.5                                AS s_vizit
(satr_per_faktor - 6) * 0.5                           AS s_satr
CASE WHEN mahaneh = 1 THEN (moshtary_pct - 80) * 0.5 END AS s_moshtary
(1 - marjoee_pct) / 0.25                              AS s_marjoee
```

و خودِ `marjoee_pct` در CTE `calc`:
`100.0 * ISNULL(mj.tedad_marjoee, 0) / NULLIF(fk.tedad_forosh, 0)`.

و معیار ۶ در CTE `goroh`: `100.0 * SUM(forosh) / SUM(hadaf) - 75`.

باندهای وضعیت هم در `SELECT` نهایی‌اند: بالای صفر «عالی»، تا ۵− «معمولی»،
زیر آن «نیازمند تصمیم اساسی».

## ۳. ورودی برای `score.py`

اگر ارزیابی کامل با اسکریپت می‌خواهی، همین کوئری را با ستون‌های خام بگیر و
کلیدهای `score.py` را از این جدول پر کن. معیار ۳ روی فاکتور
است و معیار ۵ روی کالا، پس مخرجشان یکی نیست.

| ستون کوئری | کلید `score.py` |
|---|---|
| `tedad_ba_zarib` | `weighted_shops` |
| `vizit_rafteh` | `visits_total` |
| `vizit_mosbat` | `visits_positive` |
| `tedad_satr` | `invoice_line_count` |
| `moshtary_rafteh` | `customers_assigned` |
| `moshtary_kharid` | `customers_purchased` |
| `kol_faktor` | `invoice_count` |
| `tedad_marjoee` | `returns_qty` |
| `tedad_forosh` | `sold_qty` |
| گروه‌های هدف | `product_groups` |

`returns_qty` را **حتی وقتی صفر است** بفرست — و در مرداد ۱۴۰۵ برای ۱۲ فروشنده
صفر بود. اگر کلید را جا بیندازی، اسکریپت آن را «بدون داده» می‌گیرد و از جمع
کنار می‌گذارد؛ یعنی فروشنده‌ای که هیچ مرجوعی ندارد به‌جای ۴+ نمره صفر می‌گیرد
و «۵ از ۶» می‌خورد.

```python
import subprocess, sys
r = subprocess.run(
    [sys.executable, "skills/ارزیابی-فروشنده-پگاه/scripts/score.py",
     "input.json", "--period", "cumulative"],
    capture_output=True, text=True, encoding="utf-8")
print(r.stdout or r.stderr)
```

با `kind='python'` اجرا کن. `kind='bash'` روی میزبان ویندوزی خروجی فارسی را
خراب می‌کند.

### چرا معیار ۶ در دوره‌ی روزانه نیست

`TedadHadaf` در `HadafForoshRoozanehNew` هدفِ **روزانه** است و هر روز عدد یکسانی
دارد (ماه تقسیم بر روزها). ولی فروش روزانه انفجاری است — فروشنده هر روز
یک‌سی‌ویکمِ ماه را نمی‌فروشد. نتیجه: یک روز پرفروش ۱۳۰۰٪ هدفِ آن روز درمی‌آید و
جمع امتیاز را نابود می‌کند.

در دوره‌ی ماهانه همین نسبت بین صفر و ۱۲۰٪ می‌ماند، چون فراز و فرود روزها روی هم
هموار می‌شود. معیار ۶ ذاتاً ماهانه است.

اگر مدیر فروش اصرار داشت در ارزیابی روزانه هم باشد، تنها شکل معقولش مقایسه‌ی
**ماه تا امروز** است، نه فروشِ همان یک روز.

## ۴. چرا مرجوعی از `AmarForosh_Arshive` درنمی‌آید

این را روی داده زدیم و جواب قطعی است، دوباره نگرد:

```sql
SELECT IsMarjoee, COUNT(*) AS radif, COUNT(DISTINCT ccDarkhastFaktor) AS asnad
FROM Sales.AmarForosh_Arshive
WHERE Tarikh >= '2026-07-23' AND Tarikh < '2026-08-23'
GROUP BY IsMarjoee
```

مرداد ۱۴۰۵: `IsMarjoee=0` ⇒ ۲۲۷٬۷۰۵ سطر روی ۲۸٬۱۸۴ فاکتور. `IsMarjoee=1` ⇒
۶٬۳۴۷ سطر روی **یک** «سند» — چون `ccDarkhastFaktor` روی سطر مرجوعی `NULL` است.
هیچ فاکتوری هم‌زمان سطر فروش و سطر مرجوعی ندارد.

نتیجه‌ها:

- **هر شمارشِ «تعداد فاکتور مرجوعی» از این جدول عدد جعلی می‌دهد** — برای هر
  فروشنده یک، چون همه‌ی سطرهایش یک کلید `NULL` دارند.
- **علتِ مرجوعی هم در این جدول نیست**، پس مبنادار از غیرمبنادار جدا نمی‌شود.
- `Tedad` سطر مرجوعی از قبل **منفی** است. اگر جایی خودت منفی‌اش کنی، دو بار
  منفی می‌شود.

برای همین معیار ۵ از `Sales.ElamMarjoee` می‌آید. جزئیات در
[metrics.md](metrics.md#۵-درصد-مرجوعی-مبنادار-ویزیتور).

## اندازه‌ها، برای اینکه بفهمی جواب معقول است

مرداد ۱۴۰۵ (۲۰۲۶-۰۷-۲۳ تا ۲۰۲۶-۰۸-۲۲) با فیلتر درخواست‌گیر و کف ۵ فاکتور —
از اجرای واقعی همین کوئری: **۱۰۸ فروشنده**، ۲۳ روز کاری، **صفر حذف‌شده**.

- میانگین ویزیت مثبت ۴۰.۲٪ در برابر مبنای ۴۰٪
- میانگین سطر هر فاکتور ۶.۸ در برابر مبنای ۶
- میانگین تحقق هدف ۷۳.۴٪ در برابر مبنای ۷۵٪
- میانگین مرجوعی مبنادار ۰.۴۴٪ در برابر مبنای ۱٪؛ بیشترین ۱.۷۸٪، و ۱۰۰ از ۱۰۸
  زیر ۱٪
- میانگین جمع امتیاز ۱۶.۴−

اگر هر کدام از این‌ها خیلی دور از مبنا درآمد، جایی از کوئری عوض شده.
