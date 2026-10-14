using System;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Web.UI;

public partial class _Default : Page
{
    protected void btnApply_Click(object sender, EventArgs e)
    {
        lblMessage.CssClass = "message error";
        imgResult.Visible = false;
        lnkDownload.Visible = false;

        if (!fuImage.HasFile)
        {
            lblMessage.Text = "یک عکس انتخاب کنید.";
            return;
        }

        if (string.IsNullOrEmpty(txtText.Text.Trim()) && !fuLogo.HasFile)
        {
            lblMessage.Text = "متن واترمارک یا یک تصویر لوگو را مشخص کنید.";
            return;
        }

        ImageWatermark.WatermarkPosition position;
        ImageWatermark.TryParsePosition(ddlPosition.SelectedValue, out position);

        float opacity;
        ImageWatermark.TryParseOpacity(ddlOpacity.SelectedValue, out opacity);

        ImageWatermark.Options options = new ImageWatermark.Options();
        options.Text = txtText.Text.Trim();
        options.Position = position;
        options.Opacity = opacity;
        options.TextColor = ddlColor.SelectedValue == "Black" ? Color.Black : Color.White;

        try
        {
            ImageWatermark.WatermarkResult result;
            if (fuLogo.HasFile)
            {
                using (Stream logo = fuLogo.PostedFile.InputStream)
                {
                    options.Logo = logo;
                    result = ImageWatermark.Apply(fuImage.PostedFile.InputStream, options);
                }
            }
            else
            {
                result = ImageWatermark.Apply(fuImage.PostedFile.InputStream, options);
            }

            string folder = Server.MapPath("~/uploads");
            Directory.CreateDirectory(folder);
            string name = DateTime.UtcNow.ToString("yyyyMMddHHmmss", CultureInfo.InvariantCulture)
                + "-"
                + Guid.NewGuid().ToString("N").Substring(0, 8)
                + result.Extension;
            string fullPath = Path.Combine(folder, name);
            File.WriteAllBytes(fullPath, result.Bytes);

            imgResult.ImageUrl = ResolveUrl("~/uploads/" + name);
            imgResult.Visible = true;
            lnkDownload.NavigateUrl = imgResult.ImageUrl;
            lnkDownload.Visible = true;
            lblMessage.CssClass = "message ok";
            lblMessage.Text = "واترمارک اعمال شد.";
        }
        catch (ArgumentException ex)
        {
            lblMessage.Text = ex.Message;
        }
        catch (OutOfMemoryException)
        {
            lblMessage.Text = "تصویر خیلی بزرگ است یا فایل آسیب دیده است.";
        }
    }
}
