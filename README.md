# واترمارک عکس در ASP.NET Web Forms 4

سایت Web Forms روی .NET Framework 4 که متن یا لوگو را روی عکس می‌گذارد. منطق در `App_Code/ImageWatermark.cs` است و به کتابخانه اضافه‌ای نیاز ندارد؛ از `System.Drawing` خود فریم‌ورک استفاده می‌کند.

## اجرا

پوشه را در Visual Studio با File > Open > Web Site باز کنید، یا آن را به‌عنوان سایت در IIS با Application Pool نسخه .NET Framework 4 قرار دهید. هاست باید Full Trust باشد؛ `System.Drawing` در Medium Trust کار نمی‌کند. فونت Tahoma برای متن فارسی روی ویندوز موجود است.

## از صفحه

`Default.aspx` عکس را می‌گیرد، واترمارک را اعمال می‌کند و نتیجه را در پوشه `uploads` ذخیره می‌کند.

## از هندلر، برای عکس‌های روی سرور

فایل اصلی را در پوشه `photos` بگذارید:

```
Watermark.ashx?file=sample.png&text=سایت من&pos=BottomRight&opacity=0.45
```

`pos` یکی از این مقدارهاست: `TopLeft`، `TopRight`، `BottomLeft`، `BottomRight`، `Center`، `Tile`.

لوگوی کنار متن:

```
Watermark.ashx?file=sample.png&text=سایت من&logo=logo.png&pos=BottomRight&opacity=0.55
```

متن فارسی در آدرس باید URL-encode شود.

## استفاده در کد

```csharp
ImageWatermark.Options options = new ImageWatermark.Options();
options.Text = "سایت من";
options.Position = ImageWatermark.WatermarkPosition.BottomRight;
options.Opacity = 0.45f;

using (FileStream input = File.OpenRead(sourcePath))
{
    ImageWatermark.WatermarkResult result = ImageWatermark.Apply(input, options);
    File.WriteAllBytes(targetPath, result.Bytes);
}
```

برای لوگو، استریم تصویر لوگو را در `options.Logo` بگذارید. jpg به jpg (با کیفیت ۹۰) و png/gif به png تبدیل می‌شود. چرخش EXIF عکس موبایل قبل از درج واترمارک اصلاح می‌شود.
