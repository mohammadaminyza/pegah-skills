# شش متریک، و جدول‌هایی که واقعاً دارندشان

این صفحه از روی خودِ دیتابیس `pakhsh` نوشته شده، نه از روی حدس. جدول‌ها و
ستون‌های زیر تست شده‌اند و جواب می‌دهند. کوئری کامل و آماده در
[queries.md](queries.md) است — اول آن را بخوان، این صفحه توضیحِ آن است.

## دو جدولی که مرده‌اند

| جدول | آخرین داده |
|---|---|
| `Sales.AmalkardRozanehForosh` | **۲۴ ژوئیه ۲۰۱۸** |
| `Sales.HadafForosh` | **۲۲ اکتبر ۲۰۱۸** |

اسمشان دقیقاً همان چیزی است که این اسکیل می‌خواهد («عملکرد روزانه فروش»، «هدف
فروش»)، و هر دو هشت سال است به‌روز نمی‌شوند. `search_schema` آنها را بالای نتایج
می‌آورد. **از هیچ‌کدام استفاده نکن.** اگر ارزیابی روی این جدول‌ها ساخته شود،
جواب «برای این بازه داده‌ای نیست» است در حالی که داده هست.

جدول‌های زنده تا امروز به‌روزند: `Sales.DarkhastFaktor`،
`Sales.VisitForoshandeh_Arshiv`، `Sales.ElamMarjoee`،
`Sales.TedadMoshtarianBaZaribSenf`، `Sales.HadafForoshandeh_PG`. پسوند
`_Arshiv` روی بعضی از اینها گمراه‌کننده است — آرشیو نیستند، جدول اصلی‌اند.

## فیلتری که بدون آن رتبه‌بندی بی‌معنی است

```sql
JOIN Sales.Foroshandeh f ON f.ccForoshandeh = v.ccForoshandeh
WHERE f.ccNoeForoshandeh = 1        -- درخواست‌گیر
```

`Sales.NoeForoshandeh` یازده نوع دارد: ۱ درخواست‌گیر، ۲ سیار، ۳ آمارگر، ۴ مقیم،
۵ تلفنی، ۶ زنجیره‌ای، ۷ کترینگ، ۸ سرپرست، ۹ رییس مرکز، ۱۰ مدیر منطقه، ۱۱ ویژه.

مبناهای این ارزیابی (۲۵ مغازه در روز، ۲۸۰ در ماه، ۴۰٪ ویزیت مثبت) برای فروشنده
مویرگیِ مسیررو نوشته شده‌اند. بدون این فیلتر، سرپرست (۸) و رییس مرکز (۹) — که
عددهایشان تجمیع تیم است — با نمره‌هایی مثل ۱۳۵۲ و ۱۰۱۲ صدر جدول را می‌گیرند،
در حالی که یک فروشنده خوب حدود ۲۰ تا ۳۰ می‌گیرد. این باگ نیست، مقایسه غلط است.

اگر مدیر فروش نوع دیگری هم می‌خواهد، فهرست بالا را نشانش بده و بگذار انتخاب کند.

## ۱. تعداد مغازه وزنی — `Sales.DarkhastFaktor`

مشتریان **متمایزی** که در بازه فاکتور خورده‌اند، به تفکیک نوع، با ضریب ۱/۳/۵.

`ccNoeMoshtary` روی خودِ سرِ فاکتور است، پس نیازی به join با جدول مشتری نیست:

| کد | نوع | ضریب |
|---:|---|---:|
| 347 | خرده | ۱ |
| 348 | عمده | ۳ |
| 350 | زنجیره ای | ۵ |

کدهای دیگری هم هستند که برگه ارزیابی نامی از آنها نبرده: ۳۴۹ تعاونی ویژه،
۳۵۱ نماينده، ۳۵۲ نماينده ۲، ۳۵۳ شبه عمده، ۶۰۷ تعاونی کارکنان. الان در وزن‌دهی
نمی‌آیند. **۳۵۳ (شبه عمده) را با مدیر فروش چک کن** — محتمل‌ترین چیزی است که
باید ضریب بگیرد.

```sql
COUNT(DISTINCT CASE WHEN ccNoeMoshtary = 347 THEN ccMoshtary END)
```

اعتبارسنجی: در ۲۰۲۶-۰۸-۲۳ بیشترین مقدار وزنیِ یک روز دقیقاً **۲۵** درآمد، و
مبنای برگه هم ۲۵ است. یعنی تعریف درست است — «مغازه‌ی روز» یعنی مشتریِ
فاکتورخورده، نه مشتریِ ویزیت‌شده.

جدول `Sales.TedadMoshtarianBaZaribSenf` هم همین سطل‌ها را دارد
(`TedadMoshtaryKhordeh` / `Omdeh` / `Zanjireei`) ولی عددهایش در حد ۲۰۰۰ است، یعنی
کل پرونده مشتریان فروشنده، نه مغازه‌های آن روز. برای این معیار به کارت نمی‌آید.

## ۲ و ۳ و ۴. ویزیت، اقلام، مشتری خریدکرده — `Sales.VisitForoshandeh_Arshiv`

یک سطر به ازای هر (روز، فروشنده، مشتریِ برنامه‌ی مسیر). هر سه متریک از همین
یک جدول درمی‌آید:

| ستون | یعنی |
|---|---|
| `TarikhVisit` | تاریخ (datetime میلادی) |
| `IsTatil` | روز تعطیل — در ارزیابی نیاید |
| `MorajehShodeh` | مراجعه شد (۰/۱) |
| `VisitMosbat` | ویزیت مثبت (۰/۱) |
| `TedadFaktor` | تعداد فاکتور |
| `Tedad_AghlamFaktor` | تعداد اقلام فاکتور |
| `MablaghForoshKala` | مبلغ فروش |

```sql
SUM(MorajehShodeh)                                          AS visits_total
SUM(VisitMosbat)                                            AS visits_positive
SUM(Tedad_AghlamFaktor)                                     AS invoice_line_count
SUM(TedadFaktor)                                            AS invoice_count
COUNT(DISTINCT ccMoshtary)                                  AS customers_assigned
COUNT(DISTINCT CASE WHEN TedadFaktor>0 THEN ccMoshtary END) AS customers_purchased
```

`customers_assigned` از `COUNT(DISTINCT ccMoshtary)` می‌آید و نه از
`SUM(MorajehShodeh)`: سطر برای هر مشتریِ برنامه ساخته می‌شود، چه سر زده باشد چه
نه. در ۲۰۲۶-۰۸-۲۳ برای یک فروشنده ۵۱ مشتری برنامه بود و ۴۷ مراجعه — همان فرقی که
معیار ۴ می‌سنجد.

`IsTatil = 0` را بگذار. روز تعطیل با صفر ویزیت، میانگین ماه را بی‌دلیل خراب
می‌کند.

## ۵. درصد مرجوعی — `Sales.ElamMarjoee` + `Sales.ElamMarjoeeSatr`

سرِ برگه مرجوعی `ccForoshandeh` و `TarikhElamMarjoee` دارد، سطرها `Tedad1` و
`Fee`. مبلغ ریالی مرجوعی:

```sql
SUM(s.Tedad1 * s.Fee) AS returns_amount
```

مخرج (`gross_sales_amount`) از `MablaghForoshKala` همان جدول ویزیت می‌آید، تا
صورت و مخرج از دو تعریف مختلفِ «فروش» نیایند.

`Sales.ForoshandehMarjoee_Arshive` دقیقاً همین را آماده دارد (`RialForosh`,
`RialMarjoee`) ولی فقط ۷۹۰۹ سطر از آوریل تا ژوئیه ۲۰۲۰ — رها شده. استفاده نکن.

`NoeFaktor` در `DarkhastFaktor` همیشه ۱ است؛ دنبال مرجوعی در آن نگرد. کدهای
وضعیت ۱۱ و ۱۲ («مرجوعی امانی فروش/انبار») هم در عمل خالی‌اند.

## ۶. درصد تحقق هدف گروه محصول — `Sales.HadafForoshandeh_PG`

هدف **تعدادی** است، نه ریالی، و **ماهانه**:

| ستون | یعنی |
|---|---|
| `ccForoshandeh` | فروشنده |
| `ccKalaCode` | گروه محصول |
| `Sal` / `Mah` | سال و ماه شمسی |
| `TedadHadaf` | هدف تعدادی |

عملکرد در برابرش از `Sales.DarkhastFaktorSatr.Tedad1` می‌آید که همان `ccKalaCode`
را دارد. نام گروه از `Warehouse.Kala.NameKala` با join روی `ccKalaCode`.

```sql
WHERE h.Sal = 1405 AND h.Mah = 5 AND h.TedadHadaf > 0
```

`TedadHadaf > 0` لازم است، وگرنه تقسیم بر صفر می‌شود.

**برای ارزیابی روز:** هدف ماهانه است. باید بر تعداد روزهای کاری ماه تقسیم شود.
تقویم کاری در `Sales.HadafForoshRoozaneh` هست (تا امروز به‌روز). اگر از آن
استفاده نکردی، در گزارش بنویس که هدف روزانه تخمینی است.

## تاریخ

`TarikhDarkhast`، `TarikhVisit`، `TarikhElamMarjoee` همه **datetime میلادی**‌اند،
نه رشته شمسی. پس بازه را میلادی بده و همیشه نیم‌باز:

```sql
WHERE TarikhVisit >= @From AND TarikhVisit < @To
```

`@To` روزِ بعد است، نه روزِ آخر — وگرنه فاکتورهای ساعت ۱۷ روز آخر جا می‌مانند.

فقط `Sales.HadafForoshandeh_PG` شمسی است (`Sal`/`Mah`)، چون هدف ماهانه ثبت
می‌شود. برای مرداد ۱۴۰۵ یعنی `Sal=1405, Mah=5`، و بازه میلادی‌اش
`>= '2026-07-23' AND < '2026-08-23'`. این تبدیل را حساب کن و در گزارش هر دو را
بنویس.

## اسم فروشنده

`Sales.Foroshandeh.SharhForoshandeh`. در این نصب مقدارها شبیه «فروشنده 1104106»
است — کد است نه نام. اگر نام واقعی خواستی، `Sales.Foroshandeh.ccAfrad` را به
`Global.Afrad` وصل کن (`FName`, `LName`).
