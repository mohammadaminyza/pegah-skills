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
- معیار ۱ **مغازه‌روز** می‌شمارد نه مغازه: مشتریانِ متمایزِ هر روز، ضریب‌خورده،
  بعد جمعِ روزها. یک مغازه که در ماه ۳ بار فاکتور خورده ۳ مغازه‌روز است. ستون‌های
  «مغازه یکتا» تعداد واقعی مغازه را جدا نشان می‌دهند. مبنا بین ۲۵ (روزانه) و
  ۲۸۰ (ماهانه) عوض می‌شود.
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
    SELECT
        CAST('2026-08-22' AS date) AS rooz_arzyabi,
        1                          AS mahaneh,            -- ۱ = تا روز، ۰ = فقط همان روز
        5                          AS hadeaghal_faktor,
        CAST(NULL AS int)          AS sazman_forosh,      -- NULL = همه لاین‌ها
        1                          AS cc_noe_foroshandeh, -- ۱ = درخواست‌گیر
        347                        AS cc_khord,
        348                        AS cc_omde,
        350                        AS cc_zanjireh,
        CAST(0.0 AS float)         AS zarib_pishfarz,     -- نوعی که در جدول ضرایب نیست
        1                          AS masoleiat_marjoee,  -- ۱ فروش، ۲ پخش، ۳ تولید، ۴ هردو
        25.0  AS mabna_magazeh_rooz, 1.0  AS gam_magazeh_rooz,
        280.0 AS mabna_magazeh_mah,  5.0  AS gam_magazeh_mah,  1.0 AS nomre_magazeh,
        40.0  AS mabna_vizit,        1.0  AS gam_vizit,        0.5 AS nomre_vizit,
        6.0   AS mabna_satr,         1.0  AS gam_satr,         0.5 AS nomre_satr,
        80.0  AS mabna_moshtary,     1.0  AS gam_moshtary,     0.5 AS nomre_moshtary,
        1.0   AS mabna_marjoee,      0.25 AS gam_marjoee,      1.0 AS nomre_marjoee,
        75.0  AS mabna_hadaf,        1.0  AS gam_hadaf,        1.0 AS nomre_hadaf,
        2.0   AS hazf_marjoee_bala,
        0.0   AS band_ali,           -5.0 AS band_maamouli
),
bazeh AS (
    SELECT p.*,
           CASE WHEN p.mahaneh = 1
                THEN DATEADD(day, 1, DATEADD(month, -1, CAST(p.rooz_arzyabi AS datetime)))
                ELSE CAST(p.rooz_arzyabi AS datetime) END AS d_from,
           DATEADD(day, 1, CAST(p.rooz_arzyabi AS datetime)) AS d_to
    FROM params p
),
zarib AS (
    -- ضریب نوع مشتری از خودِ سیستم. برای ضریب دستی، این را با یک VALUES عوض کن:
    -- SELECT * FROM (VALUES (347,1.0),(348,2.0),(349,1.5),(350,4.0)) v(ccNoeMoshtary, zarib)
    SELECT z.ccNoeMoshtary, CAST(z.Zarib AS float) AS zarib
    FROM Sales.ZaribNoeMoshtary z
),
taghvim AS (
    SELECT COUNT(*) AS rooz_kari
    FROM Global.Taghvim g CROSS JOIN bazeh b
    WHERE g.Tarikh >= b.d_from AND g.Tarikh < b.d_to AND g.CodeNoeTatili IS NULL
),
rooz AS (
    SELECT a.ccForoshandeh, a.Tarikh, a.ccNoeMoshtary,
           COUNT(DISTINCT a.ccMoshtary) AS magazeh
    FROM Sales.AmarForosh_Arshive a CROSS JOIN bazeh b
    WHERE a.Tarikh >= b.d_from AND a.Tarikh < b.d_to AND a.IsMarjoee = 0
      AND (b.sazman_forosh IS NULL OR a.ccSazmanForosh = b.sazman_forosh)
    GROUP BY a.ccForoshandeh, a.Tarikh, a.ccNoeMoshtary
),
shop AS (
    SELECT r.ccForoshandeh,
           SUM(CASE WHEN r.ccNoeMoshtary = b.cc_khord    THEN r.magazeh ELSE 0 END) AS mr_khord,
           SUM(CASE WHEN r.ccNoeMoshtary = b.cc_omde     THEN r.magazeh ELSE 0 END) AS mr_omde,
           SUM(CASE WHEN r.ccNoeMoshtary = b.cc_zanjireh THEN r.magazeh ELSE 0 END) AS mr_zanjireh,
           SUM(CASE WHEN r.ccNoeMoshtary NOT IN (b.cc_khord, b.cc_omde, b.cc_zanjireh)
                    THEN r.magazeh ELSE 0 END)                                      AS mr_digar,
           SUM(CASE WHEN z.zarib IS NULL THEN r.magazeh ELSE 0 END)                 AS mr_bi_zarib,
           SUM(r.magazeh)                                                           AS mr_kol,
           SUM(r.magazeh * ISNULL(z.zarib, b.zarib_pishfarz))                       AS vahed_ba_zarib
    FROM rooz r CROSS JOIN bazeh b
    LEFT JOIN zarib z ON z.ccNoeMoshtary = r.ccNoeMoshtary
    GROUP BY r.ccForoshandeh
),
forosh AS (
    SELECT a.ccForoshandeh,
           COUNT(DISTINCT a.ccDarkhastFaktor)  AS kol_faktor,
           SUM(a.Tedad)                        AS tedad_forosh,
           COUNT(DISTINCT a.ccMoshtary)        AS magazeh_yekta,
           COUNT(DISTINCT CASE WHEN a.ccNoeMoshtary = b.cc_khord    THEN a.ccMoshtary END) AS khord_yekta,
           COUNT(DISTINCT CASE WHEN a.ccNoeMoshtary = b.cc_omde     THEN a.ccMoshtary END) AS omde_yekta,
           COUNT(DISTINCT CASE WHEN a.ccNoeMoshtary = b.cc_zanjireh THEN a.ccMoshtary END) AS zanjireh_yekta
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
      AND e.MasoleiatElat = b.masoleiat_marjoee
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
           SUM(v.MorajehShodeh)                                              AS vizit_rafteh,
           SUM(v.VisitMosbat)                                                AS vizit_mosbat,
           COUNT(DISTINCT CASE WHEN v.MorajehShodeh=1 THEN v.ccMoshtary END) AS moshtary_rafteh,
           COUNT(DISTINCT CASE WHEN v.VisitMosbat=1   THEN v.ccMoshtary END) AS moshtary_kharid,
           COUNT(DISTINCT CASE WHEN v.MorajehShodeh=1 AND m.ccNoeMoshtary = b.cc_khord
                               THEN v.ccMoshtary END)                        AS vizit_khord,
           COUNT(DISTINCT CASE WHEN v.MorajehShodeh=1 AND m.ccNoeMoshtary = b.cc_omde
                               THEN v.ccMoshtary END)                        AS vizit_omde,
           COUNT(DISTINCT CASE WHEN v.MorajehShodeh=1 AND m.ccNoeMoshtary = b.cc_zanjireh
                               THEN v.ccMoshtary END)                        AS vizit_zanjireh
    FROM Sales.VisitForoshandeh_Arshiv v CROSS JOIN bazeh b
    LEFT JOIN Sales.vMoshtary m ON m.ccMoshtary = v.ccMoshtary
    WHERE v.TarikhVisit >= b.d_from AND v.TarikhVisit < b.d_to AND v.IsTatil = 0
      AND (b.sazman_forosh IS NULL OR v.ccSazmanForosh = b.sazman_forosh)
    GROUP BY v.ccForoshandeh
),
goroh AS (
    SELECT ccForoshandeh,
           100.0 * SUM(forosh) / NULLIF(SUM(hadaf), 0) AS tahaghogh_pct,
           COUNT(*)                                    AS n_goroh
    FROM (
        SELECT h.ccForoshandeh, h.ccGorohKala,
               SUM(h.TedadHadaf)  AS hadaf,
               SUM(h.TedadForosh) AS forosh
        FROM Sales.HadafForoshRoozanehNew h CROSS JOIN bazeh b
        WHERE h.Tarikh >= b.d_from AND h.Tarikh < b.d_to
          AND (b.sazman_forosh IS NULL OR h.ccSazmanForosh = b.sazman_forosh)
        GROUP BY h.ccForoshandeh, h.ccGorohKala
        HAVING SUM(h.TedadHadaf) > 0
    ) gh
    GROUP BY ccForoshandeh
),
asli AS (
    SELECT ccForoshandeh, ccAfradForoshandeh,
           ROW_NUMBER() OVER (PARTITION BY ccForoshandeh ORDER BY rial DESC) AS rn,
           COUNT(*)    OVER (PARTITION BY ccForoshandeh)                     AS n_people
    FROM (
        SELECT a.ccForoshandeh, a.ccAfradForoshandeh, SUM(a.Rial) AS rial
        FROM Sales.AmarForosh_Arshive a CROSS JOIN bazeh b
        WHERE a.Tarikh >= b.d_from AND a.Tarikh < b.d_to AND a.IsMarjoee = 0
          AND (b.sazman_forosh IS NULL OR a.ccSazmanForosh = b.sazman_forosh)
        GROUP BY a.ccForoshandeh, a.ccAfradForoshandeh
    ) nafar
),
calc AS (
    SELECT f.ccForoshandeh, b.d_from, b.d_to, b.mahaneh, b.sazman_forosh, tv.rooz_kari,
           LTRIM(RTRIM(ISNULL(p.FName, '') + ' ' + ISNULL(p.LName, ''))) AS person,
           n.n_people,
           fr.kol_faktor, fr.tedad_forosh, fr.magazeh_yekta,
           fr.khord_yekta, fr.omde_yekta, fr.zanjireh_yekta,
           sh.mr_khord, sh.mr_omde, sh.mr_zanjireh, sh.mr_digar, sh.mr_bi_zarib,
           sh.mr_kol, sh.vahed_ba_zarib,
           v.vizit_rafteh, v.vizit_mosbat, v.moshtary_rafteh, v.moshtary_kharid,
           v.vizit_khord, v.vizit_omde, v.vizit_zanjireh,
           ISNULL(mj.tedad_marjoee, 0) AS tedad_marjoee,
           100.0 * v.vizit_mosbat    / NULLIF(v.vizit_rafteh, 0)     AS vizit_pct,
           1.0   * s.tedad_satr      / NULLIF(fr.kol_faktor, 0)      AS satr_per_faktor,
           100.0 * v.moshtary_kharid / NULLIF(v.moshtary_rafteh, 0)  AS moshtary_pct,
           100.0 * ISNULL(mj.tedad_marjoee, 0) / NULLIF(fr.tedad_forosh, 0) AS marjoee_pct,
           gr.tahaghogh_pct, gr.n_goroh
    FROM Sales.Foroshandeh f
    CROSS JOIN bazeh b
    CROSS JOIN taghvim tv
    JOIN forosh fr        ON fr.ccForoshandeh = f.ccForoshandeh
    JOIN shop sh          ON sh.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN marjoee mj  ON mj.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN satr s      ON s.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN vis  v      ON v.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN goroh gr    ON gr.ccForoshandeh = f.ccForoshandeh
    LEFT JOIN asli n      ON n.ccForoshandeh = f.ccForoshandeh AND n.rn = 1
    LEFT JOIN Global.Afrad p ON p.ccAfrad = n.ccAfradForoshandeh
    WHERE f.ccNoeForoshandeh = b.cc_noe_foroshandeh
      AND fr.kol_faktor >= b.hadeaghal_faktor
),
emtiaz AS (
    SELECT c.*,
           (c.vahed_ba_zarib - CASE WHEN c.mahaneh = 1 THEN b.mabna_magazeh_mah ELSE b.mabna_magazeh_rooz END)
             / CASE WHEN c.mahaneh = 1 THEN b.gam_magazeh_mah ELSE b.gam_magazeh_rooz END
             * b.nomre_magazeh                                                       AS s_shop,
           (c.vizit_pct - b.mabna_vizit) / b.gam_vizit * b.nomre_vizit                AS s_vizit,
           (c.satr_per_faktor - b.mabna_satr) / b.gam_satr * b.nomre_satr             AS s_satr,
           CASE WHEN c.mahaneh = 1 THEN
                (c.moshtary_pct - b.mabna_moshtary) / b.gam_moshtary * b.nomre_moshtary END AS s_moshtary,
           (b.mabna_marjoee - c.marjoee_pct) / b.gam_marjoee * b.nomre_marjoee        AS s_marjoee,
           CASE WHEN c.mahaneh = 1 THEN
                (c.tahaghogh_pct - b.mabna_hadaf) / b.gam_hadaf * b.nomre_hadaf END   AS s_hadaf
    FROM calc c CROSS JOIN bazeh b
),
jam AS (
    SELECT e.*,
           CASE WHEN e.mahaneh = 1 AND e.marjoee_pct > b.hazf_marjoee_bala THEN 0 ELSE
                ISNULL(e.s_shop,0)+ISNULL(e.s_vizit,0)+ISNULL(e.s_satr,0)
               +ISNULL(e.s_moshtary,0)+ISNULL(e.s_marjoee,0)+ISNULL(e.s_hadaf,0) END AS jam_emtiaz,
           CASE WHEN e.mahaneh = 1 AND e.marjoee_pct > b.hazf_marjoee_bala
                THEN 1 ELSE 0 END                                                    AS hazf
    FROM emtiaz e CROSS JOIN bazeh b
)
SELECT ROW_NUMBER() OVER (ORDER BY j.hazf, j.jam_emtiaz DESC)  AS "رتبه",
       j.person        AS "فروشنده",
       j.ccForoshandeh AS "کد مسیر",
       j.n_people      AS "نفرات مسیر",
       CAST(j.jam_emtiaz AS decimal(9,2)) AS "جمع امتیاز",
       CASE WHEN j.hazf = 1 THEN N'حذف — مرجوعی بالای ' + CAST(CAST(b.hazf_marjoee_bala AS decimal(4,2)) AS nvarchar(10)) + N'٪'
            WHEN j.jam_emtiaz > b.band_ali       THEN N'عالی'
            WHEN j.jam_emtiaz >= b.band_maamouli THEN N'معمولی'
            ELSE N'نیازمند تصمیم اساسی' END AS "وضعیت",
       CAST(j.s_shop AS decimal(9,2))     AS "امتیاز واحد مغازه‌روز",
       CAST(j.s_vizit AS decimal(9,2))    AS "امتیاز ویزیت مثبت",
       CAST(j.s_satr AS decimal(9,2))     AS "امتیاز سطر فاکتور",
       CAST(j.s_moshtary AS decimal(9,2)) AS "امتیاز مشتری خرید کرده",
       CAST(j.s_marjoee AS decimal(9,2))  AS "امتیاز مرجوعی",
       CAST(j.s_hadaf AS decimal(9,2))    AS "امتیاز هدف گروه",
       CAST(j.vahed_ba_zarib AS decimal(12,2)) AS "واحد مغازه‌روز با ضریب",
       j.mr_kol         AS "مغازه‌روز (بدون ضریب)",
       j.mr_khord       AS "مغازه‌روز خرده",
       j.mr_omde        AS "مغازه‌روز عمده",
       j.mr_zanjireh    AS "مغازه‌روز زنجیره‌ای",
       j.mr_digar       AS "مغازه‌روز سایر انواع",
       j.mr_bi_zarib    AS "مغازه‌روز بدون ضریب",
       j.magazeh_yekta  AS "مغازه یکتا",
       j.khord_yekta    AS "مغازه خرده",
       j.omde_yekta     AS "مغازه عمده",
       j.zanjireh_yekta AS "مغازه زنجیره‌ای",
       j.vizit_rafteh   AS "ویزیت رفته",
       j.vizit_mosbat   AS "ویزیت مثبت",
       CAST(j.vizit_pct AS decimal(6,2)) AS "درصد ویزیت مثبت",
       j.moshtary_rafteh  AS "مغازه ویزیت‌شده",
       j.vizit_khord      AS "مغازه ویزیت‌شده خرده",
       j.vizit_omde       AS "مغازه ویزیت‌شده عمده",
       j.vizit_zanjireh   AS "مغازه ویزیت‌شده زنجیره‌ای",
       j.moshtary_kharid  AS "مشتری خرید کرده",
       CAST(j.moshtary_pct AS decimal(6,2))    AS "درصد مشتری خرید کرده",
       j.kol_faktor  AS "تعداد فاکتور",
       CAST(j.satr_per_faktor AS decimal(6,2)) AS "میانگین سطر فاکتور",
       j.tedad_marjoee AS "تعداد مرجوعی فروش",
       j.tedad_forosh  AS "تعداد فروش",
       CAST(j.marjoee_pct AS decimal(6,3))     AS "درصد مرجوعی مبنادار",
       CAST(j.tahaghogh_pct AS decimal(8,2))   AS "تحقق هدف گروه",
       j.n_goroh   AS "تعداد گروه",
       j.rooz_kari AS "روز کاری",
       CAST(j.d_from AS date) AS "از", CAST(DATEADD(day,-1,j.d_to) AS date) AS "تا",
       ISNULL(sz.NameSazmanForosh, N'همه لاین‌ها') AS "لاین فروش"
FROM jam j
CROSS JOIN bazeh b
LEFT JOIN Global.SazmanForosh sz ON sz.ccSazmanForosh = j.sazman_forosh
ORDER BY j.hazf, j.jam_emtiaz DESC
```

## ۲. تغییر آستانه‌ها

عددهای مبنا و گام در `rules.json` هستند و کاربر می‌تواند عوضشان کند. اگر عوض
شدند، در کوئری این جاها را دست ببر — همه در CTE `emtiaz` کنار هم‌اند:

```sql
(vahed_ba_zarib - CASE WHEN mahaneh = 1 THEN 280 ELSE 25 END)
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
| `vahed_ba_zarib` | `weighted_shops` |
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
