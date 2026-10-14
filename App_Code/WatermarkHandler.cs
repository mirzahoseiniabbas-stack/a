using System;
using System.Globalization;
using System.IO;
using System.Web;

/// <summary>
/// واترمارک روی عکس‌های پوشه photos، بدون ذخیره فایل جدید.
/// نمونه: Watermark.ashx?file=sample.png&amp;text=سایت من&amp;pos=BottomRight&amp;opacity=0.45
/// </summary>
public class WatermarkHandler : IHttpHandler
{
    public bool IsReusable
    {
        get { return true; }
    }

    public void ProcessRequest(HttpContext context)
    {
        HttpResponse response = context.Response;
        string fileName = context.Request.QueryString["file"];
        if (!IsSafeFileName(fileName))
        {
            WriteError(response, 400, "نام فایل نامعتبر است.");
            return;
        }

        string extension = Path.GetExtension(fileName);
        if (!IsImageExtension(extension))
        {
            WriteError(response, 400, "پسوند فایل مجاز نیست.");
            return;
        }

        string photosRoot = Path.GetFullPath(context.Server.MapPath("~/photos"));
        string fullPath = Path.GetFullPath(Path.Combine(photosRoot, fileName));
        if (!IsInsideDirectory(photosRoot, fullPath) || !File.Exists(fullPath))
        {
            WriteError(response, 404, "تصویر پیدا نشد.");
            return;
        }

        ImageWatermark.WatermarkPosition position;
        ImageWatermark.TryParsePosition(context.Request.QueryString["pos"], out position);

        float opacity;
        ImageWatermark.TryParseOpacity(context.Request.QueryString["opacity"], out opacity);

        ImageWatermark.Options options = new ImageWatermark.Options();
        options.Text = context.Request.QueryString["text"];
        options.Position = position;
        options.Opacity = opacity;

        string logoName = context.Request.QueryString["logo"];
        Stream logoStream = null;
        try
        {
            if (!string.IsNullOrEmpty(logoName))
            {
                if (!IsSafeFileName(logoName) || !IsImageExtension(Path.GetExtension(logoName)))
                {
                    WriteError(response, 400, "نام فایل لوگو نامعتبر است.");
                    return;
                }

                string logoPath = Path.GetFullPath(Path.Combine(photosRoot, logoName));
                if (!IsInsideDirectory(photosRoot, logoPath) || !File.Exists(logoPath))
                {
                    WriteError(response, 404, "لوگو پیدا نشد.");
                    return;
                }

                logoStream = File.OpenRead(logoPath);
                options.Logo = logoStream;
            }

            if (string.IsNullOrEmpty(options.Text) && options.Logo == null)
            {
                WriteError(response, 400, "پارامتر text یا logo را بفرستید.");
                return;
            }

            ImageWatermark.WatermarkResult result;
            using (FileStream input = File.OpenRead(fullPath))
            {
                result = ImageWatermark.Apply(input, options);
            }

            response.ContentType = result.ContentType;
            response.Cache.SetCacheability(HttpCacheability.Public);
            response.Cache.SetExpires(DateTime.UtcNow.AddHours(1));
            response.Cache.SetValidUntilExpires(true);
            response.BinaryWrite(result.Bytes);
        }
        catch (ArgumentException ex)
        {
            WriteError(response, 400, ex.Message);
        }
        catch (OutOfMemoryException)
        {
            WriteError(response, 400, "تصویر خیلی بزرگ است یا فایل آسیب دیده است.");
        }
        finally
        {
            if (logoStream != null)
                logoStream.Dispose();
        }
    }

    private static void WriteError(HttpResponse response, int statusCode, string message)
    {
        response.Clear();
        response.StatusCode = statusCode;
        response.ContentType = "text/plain; charset=utf-8";
        response.Write(message);
    }

    private static bool IsSafeFileName(string name)
    {
        if (string.IsNullOrEmpty(name))
            return false;
        if (name != Path.GetFileName(name))
            return false;
        if (name.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0)
            return false;
        return true;
    }

    private static bool IsImageExtension(string extension)
    {
        if (string.IsNullOrEmpty(extension))
            return false;

        switch (extension.ToLower(CultureInfo.InvariantCulture))
        {
            case ".jpg":
            case ".jpeg":
            case ".png":
            case ".gif":
            case ".bmp":
                return true;
            default:
                return false;
        }
    }

    private static bool IsInsideDirectory(string root, string fullPath)
    {
        string prefix = root.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)
            + Path.DirectorySeparatorChar;
        return fullPath.StartsWith(prefix, StringComparison.OrdinalIgnoreCase);
    }
}
