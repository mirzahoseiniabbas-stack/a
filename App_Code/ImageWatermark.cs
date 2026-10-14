using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Drawing.Text;
using System.Globalization;
using System.IO;

/// <summary>
/// واترمارک متنی یا تصویری برای ASP.NET Web Forms روی .NET Framework 4.
/// استریم ورودی را نمی‌بندد؛ بستن آن با فراخواننده است.
/// </summary>
public static class ImageWatermark
{
    public enum WatermarkPosition
    {
        TopLeft,
        TopRight,
        BottomLeft,
        BottomRight,
        Center,
        Tile
    }

    public sealed class Options
    {
        public string Text { get; set; }
        public Stream Logo { get; set; }
        public WatermarkPosition Position { get; set; }
        public float Opacity { get; set; }
        public string FontName { get; set; }
        public Color TextColor { get; set; }
        public int Margin { get; set; }
        public long JpegQuality { get; set; }

        public Options()
        {
            Position = WatermarkPosition.BottomRight;
            Opacity = 0.45f;
            FontName = "Tahoma";
            TextColor = Color.White;
            Margin = 16;
            JpegQuality = 90L;
        }
    }

    public sealed class WatermarkResult
    {
        public byte[] Bytes { get; private set; }
        public string ContentType { get; private set; }
        public string Extension { get; private set; }

        public WatermarkResult(byte[] bytes, string contentType, string extension)
        {
            Bytes = bytes;
            ContentType = contentType;
            Extension = extension;
        }
    }

    public static WatermarkResult Apply(Stream source, Options options)
    {
        if (source == null)
            throw new ArgumentNullException("source");
        if (options == null)
            options = new Options();

        bool hasText = !string.IsNullOrEmpty(options.Text) && options.Text.Trim().Length > 0;
        bool hasLogo = options.Logo != null;
        if (!hasText && !hasLogo)
            throw new ArgumentException("متن واترمارک یا لوگو را مشخص کنید.");
        if (hasText && options.Text.Trim().Length > 200)
            throw new ArgumentException("متن واترمارک بلندتر از ۲۰۰ نویسه است.");

        float opacity = Clamp(options.Opacity, 0.05f, 1f);
        long quality = options.JpegQuality;
        if (quality < 40L)
            quality = 40L;
        if (quality > 100L)
            quality = 100L;

        using (MemoryStream buffer = CopyToMemory(source))
        {
            if (!LooksLikeImage(buffer))
                throw new ArgumentException("فرمت تصویر پشتیبانی نمی‌شود. jpg، png، gif یا bmp بفرستید.");

            using (Image image = Image.FromStream(buffer, false, true))
            {
                NormalizeOrientation(image);
                if (image.Width < 1 || image.Height < 1 || image.Width > 8000 || image.Height > 8000)
                    throw new ArgumentException("اندازه تصویر خارج از محدوده مجاز است.");

                using (Bitmap bitmap = new Bitmap(image.Width, image.Height, PixelFormat.Format32bppArgb))
                using (Graphics graphics = Graphics.FromImage(bitmap))
                {
                    if (image.HorizontalResolution > 0 && image.VerticalResolution > 0)
                        bitmap.SetResolution(image.HorizontalResolution, image.VerticalResolution);

                    graphics.SmoothingMode = SmoothingMode.AntiAlias;
                    graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
                    graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;
                    graphics.CompositingQuality = CompositingQuality.HighQuality;
                    graphics.TextRenderingHint = TextRenderingHint.AntiAliasGridFit;
                    graphics.DrawImage(image, 0, 0, image.Width, image.Height);

                    if (options.Position == WatermarkPosition.Tile && hasText)
                    {
                        DrawTiledText(graphics, bitmap.Width, bitmap.Height, options.Text.Trim(), options, opacity);
                        if (hasLogo)
                            DrawLogoBlock(graphics, bitmap.Width, bitmap.Height, options, opacity, WatermarkPosition.BottomRight, false);
                    }
                    else
                    {
                        WatermarkPosition position = options.Position == WatermarkPosition.Tile
                            ? WatermarkPosition.Center
                            : options.Position;
                        DrawLogoBlock(graphics, bitmap.Width, bitmap.Height, options, opacity, position, hasText);
                    }

                    return Encode(bitmap, PreferPng(buffer), quality);
                }
            }
        }
    }

    public static bool TryParsePosition(string value, out WatermarkPosition position)
    {
        if (!string.IsNullOrEmpty(value) && Enum.TryParse(value, true, out position))
            return true;

        position = WatermarkPosition.BottomRight;
        return false;
    }

    public static bool TryParseOpacity(string value, out float opacity)
    {
        if (!string.IsNullOrEmpty(value) &&
            float.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out opacity))
        {
            opacity = Clamp(opacity, 0.05f, 1f);
            return true;
        }

        opacity = 0.45f;
        return false;
    }

    private static void DrawLogoBlock(Graphics graphics, int canvasW, int canvasH, Options options, float opacity, WatermarkPosition position, bool drawText)
    {
        string text = drawText ? options.Text.Trim() : null;
        bool hasText = !string.IsNullOrEmpty(text);
        Image logo = null;
        MemoryStream logoBuffer = null;
        Font font = null;
        StringFormat format = null;

        try
        {
            Size logoSize = Size.Empty;
            if (options.Logo != null)
            {
                logoBuffer = CopyToMemory(options.Logo);
                if (!LooksLikeImage(logoBuffer))
                    throw new ArgumentException("فرمت لوگو پشتیبانی نمی‌شود.");

                logo = Image.FromStream(logoBuffer, false, true);
                NormalizeOrientation(logo);
                int maxW = Math.Max(32, (int)(canvasW * 0.22));
                int maxH = Math.Max(32, (int)(canvasH * 0.22));
                logoSize = Fit(logo.Width, logo.Height, maxW, maxH);
            }

            SizeF textSize = SizeF.Empty;
            if (hasText)
            {
                format = CreateTextFormat(text);
                float fontSize = Math.Max(16f, Math.Min(canvasW, canvasH) / 18f);
                float maxTextWidth = Math.Max(32f, canvasW - Math.Max(0, options.Margin) * 2);
                font = CreateFont(options.FontName, fontSize);
                textSize = graphics.MeasureString(text, font, 100000, format);
                while (textSize.Width > maxTextWidth && font.Size > 12f)
                {
                    fontSize = Math.Max(12f, font.Size * 0.85f);
                    font.Dispose();
                    font = CreateFont(options.FontName, fontSize);
                    textSize = graphics.MeasureString(text, font, 100000, format);
                }
            }

            float gap = logo != null && hasText ? 8f : 0f;
            float blockW = Math.Max(textSize.Width, logoSize.Width);
            float blockH = logoSize.Height + gap + textSize.Height;
            PointF origin = Anchor(position, canvasW, canvasH, blockW, blockH, Math.Max(0, options.Margin));

            float y = origin.Y;
            if (logo != null)
            {
                float x = Align(position, origin.X, blockW, logoSize.Width);
                Rectangle dest = new Rectangle((int)Math.Round(x), (int)Math.Round(y), logoSize.Width, logoSize.Height);
                DrawLogoImage(graphics, logo, dest, opacity);
                y += logoSize.Height + gap;
            }

            if (hasText)
            {
                float x = Align(position, origin.X, blockW, textSize.Width);
                DrawTextAt(graphics, text, font, format, x, y, textSize, opacity, options.TextColor);
            }
        }
        finally
        {
            if (font != null)
                font.Dispose();
            if (format != null)
                format.Dispose();
            if (logo != null)
                logo.Dispose();
            if (logoBuffer != null)
                logoBuffer.Dispose();
        }
    }

    private static void DrawTiledText(Graphics graphics, int width, int height, string text, Options options, float opacity)
    {
        GraphicsState state = graphics.Save();
        Font font = null;
        StringFormat format = null;
        try
        {
            float fontSize = Math.Max(18f, Math.Min(width, height) / 16f);
            font = CreateFont(options.FontName, fontSize);
            format = CreateTextFormat(text);
            SizeF size = graphics.MeasureString(text, font, 100000, format);
            float stepX = size.Width + 56f;
            float stepY = size.Height + 42f;
            float span = (float)Math.Sqrt(width * (double)width + height * (double)height);

            graphics.TranslateTransform(width / 2f, height / 2f);
            graphics.RotateTransform(-32f);

            using (SolidBrush brush = new SolidBrush(Color.FromArgb(Alpha(opacity), options.TextColor)))
            {
                float y = -span;
                while (y < span)
                {
                    float x = -span;
                    while (x < span)
                    {
                        graphics.DrawString(text, font, brush, new RectangleF(x, y, size.Width, size.Height), format);
                        x += stepX;
                    }
                    y += stepY;
                }
            }
        }
        finally
        {
            if (font != null)
                font.Dispose();
            if (format != null)
                format.Dispose();
            graphics.Restore(state);
        }
    }

    private static void DrawTextAt(Graphics graphics, string text, Font font, StringFormat format, float x, float y, SizeF size, float opacity, Color color)
    {
        RectangleF shadowRect = new RectangleF(x + 2f, y + 2f, size.Width, size.Height);
        RectangleF textRect = new RectangleF(x, y, size.Width, size.Height);
        Color shadow = color.GetBrightness() > 0.5f ? Color.Black : Color.White;

        using (SolidBrush shadowBrush = new SolidBrush(Color.FromArgb(Alpha(opacity * 0.6f), shadow)))
        using (SolidBrush brush = new SolidBrush(Color.FromArgb(Alpha(opacity), color)))
        {
            graphics.DrawString(text, font, shadowBrush, shadowRect, format);
            graphics.DrawString(text, font, brush, textRect, format);
        }
    }

    private static void DrawLogoImage(Graphics graphics, Image logo, Rectangle dest, float opacity)
    {
        using (ImageAttributes attributes = new ImageAttributes())
        {
            ColorMatrix matrix = new ColorMatrix();
            matrix.Matrix33 = opacity;
            attributes.SetColorMatrix(matrix, ColorMatrixFlag.Default, ColorAdjustType.Bitmap);
            graphics.DrawImage(logo, dest, 0, 0, logo.Width, logo.Height, GraphicsUnit.Pixel, attributes);
        }
    }

    private static StringFormat CreateTextFormat(string text)
    {
        StringFormat format = ContainsRtl(text)
            ? new StringFormat(StringFormatFlags.DirectionRightToLeft | StringFormatFlags.NoWrap)
            : new StringFormat(StringFormatFlags.NoWrap);
        format.Alignment = StringAlignment.Near;
        format.LineAlignment = StringAlignment.Near;
        return format;
    }

    private static bool ContainsRtl(string text)
    {
        for (int i = 0; i < text.Length; i++)
        {
            char c = text[i];
            if ((c >= '\u0600' && c <= '\u06FF') ||
                (c >= '\u0750' && c <= '\u077F') ||
                (c >= '\uFB50' && c <= '\uFDFF') ||
                (c >= '\uFE70' && c <= '\uFEFF'))
                return true;
        }
        return false;
    }

    private static Font CreateFont(string fontName, float size)
    {
        if (string.IsNullOrEmpty(fontName))
            fontName = "Tahoma";

        try
        {
            return new Font(fontName, size, FontStyle.Bold, GraphicsUnit.Pixel);
        }
        catch (ArgumentException)
        {
            return new Font(FontFamily.GenericSansSerif, size, FontStyle.Bold, GraphicsUnit.Pixel);
        }
    }

    private static PointF Anchor(WatermarkPosition position, int canvasW, int canvasH, float blockW, float blockH, int margin)
    {
        float x;
        float y;
        switch (position)
        {
            case WatermarkPosition.TopLeft:
                x = margin;
                y = margin;
                break;
            case WatermarkPosition.TopRight:
                x = canvasW - blockW - margin;
                y = margin;
                break;
            case WatermarkPosition.BottomLeft:
                x = margin;
                y = canvasH - blockH - margin;
                break;
            case WatermarkPosition.BottomRight:
                x = canvasW - blockW - margin;
                y = canvasH - blockH - margin;
                break;
            default:
                x = (canvasW - blockW) / 2f;
                y = (canvasH - blockH) / 2f;
                break;
        }

        if (x < 4f)
            x = 4f;
        if (y < 4f)
            y = 4f;
        return new PointF(x, y);
    }

    private static float Align(WatermarkPosition position, float originX, float blockW, float itemW)
    {
        if (position == WatermarkPosition.TopRight || position == WatermarkPosition.BottomRight)
            return originX + blockW - itemW;
        if (position == WatermarkPosition.Center)
            return originX + (blockW - itemW) / 2f;
        return originX;
    }

    private static Size Fit(int srcW, int srcH, int maxW, int maxH)
    {
        double scale = Math.Min((double)maxW / srcW, (double)maxH / srcH);
        if (scale > 1d)
            scale = 1d;
        return new Size(Math.Max(1, (int)Math.Round(srcW * scale)), Math.Max(1, (int)Math.Round(srcH * scale)));
    }

    private static void NormalizeOrientation(Image image)
    {
        const int ExifOrientationId = 0x0112;
        if (image.PropertyIdList == null || Array.IndexOf(image.PropertyIdList, ExifOrientationId) < 0)
            return;

        ushort orientation;
        try
        {
            orientation = BitConverter.ToUInt16(image.GetPropertyItem(ExifOrientationId).Value, 0);
        }
        catch (ArgumentException)
        {
            return;
        }

        RotateFlipType flip;
        switch (orientation)
        {
            case 2:
                flip = RotateFlipType.RotateNoneFlipX;
                break;
            case 3:
                flip = RotateFlipType.Rotate180FlipNone;
                break;
            case 4:
                flip = RotateFlipType.Rotate180FlipX;
                break;
            case 5:
                flip = RotateFlipType.Rotate90FlipX;
                break;
            case 6:
                flip = RotateFlipType.Rotate90FlipNone;
                break;
            case 7:
                flip = RotateFlipType.Rotate270FlipX;
                break;
            case 8:
                flip = RotateFlipType.Rotate270FlipNone;
                break;
            default:
                return;
        }

        image.RotateFlip(flip);
    }

    private static WatermarkResult Encode(Bitmap bitmap, bool preferPng, long jpegQuality)
    {
        using (MemoryStream output = new MemoryStream())
        {
            if (preferPng)
            {
                bitmap.Save(output, ImageFormat.Png);
                return new WatermarkResult(output.ToArray(), "image/png", ".png");
            }

            ImageCodecInfo jpeg = FindEncoder(ImageFormat.Jpeg);
            if (jpeg == null)
            {
                bitmap.Save(output, ImageFormat.Png);
                return new WatermarkResult(output.ToArray(), "image/png", ".png");
            }

            using (EncoderParameters parameters = new EncoderParameters(1))
            {
                parameters.Param[0] = new EncoderParameter(Encoder.Quality, jpegQuality);
                bitmap.Save(output, jpeg, parameters);
            }
            return new WatermarkResult(output.ToArray(), "image/jpeg", ".jpg");
        }
    }

    private static bool PreferPng(Stream stream)
    {
        long previous = stream.Position;
        byte[] header = new byte[4];
        int read;
        try
        {
            stream.Position = 0;
            read = stream.Read(header, 0, header.Length);
        }
        finally
        {
            stream.Position = previous;
        }

        if (read >= 4 && header[0] == 0x89 && header[1] == 0x50 && header[2] == 0x4E && header[3] == 0x47)
            return true;
        if (read >= 3 && header[0] == 0x47 && header[1] == 0x49 && header[2] == 0x46)
            return true;
        return false;
    }

    private static int Alpha(float opacity)
    {
        return (int)Math.Round(Clamp(opacity, 0f, 1f) * 255f);
    }

    private static ImageCodecInfo FindEncoder(ImageFormat format)
    {
        ImageCodecInfo[] codecs = ImageCodecInfo.GetImageEncoders();
        for (int i = 0; i < codecs.Length; i++)
        {
            if (codecs[i].FormatID == format.Guid)
                return codecs[i];
        }
        return null;
    }

    private static MemoryStream CopyToMemory(Stream source)
    {
        MemoryStream memory = new MemoryStream();
        if (source.CanSeek)
            source.Position = 0;
        source.CopyTo(memory);
        if (memory.Length == 0)
            throw new ArgumentException("فایل تصویر خالی است.");
        memory.Position = 0;
        return memory;
    }

    private static bool LooksLikeImage(Stream stream)
    {
        if (stream == null || !stream.CanSeek)
            return false;

        long previous = stream.Position;
        byte[] header = new byte[8];
        int read;
        try
        {
            stream.Position = 0;
            read = stream.Read(header, 0, header.Length);
        }
        finally
        {
            stream.Position = previous;
        }

        if (read >= 3 && header[0] == 0xFF && header[1] == 0xD8 && header[2] == 0xFF)
            return true;
        if (read >= 4 && header[0] == 0x89 && header[1] == 0x50 && header[2] == 0x4E && header[3] == 0x47)
            return true;
        if (read >= 3 && header[0] == 0x47 && header[1] == 0x49 && header[2] == 0x46)
            return true;
        if (read >= 2 && header[0] == 0x42 && header[1] == 0x4D)
            return true;
        return false;
    }

    private static float Clamp(float value, float min, float max)
    {
        if (value < min)
            return min;
        if (value > max)
            return max;
        return value;
    }
}
