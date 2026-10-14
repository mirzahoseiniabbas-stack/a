<%@ Page Language="C#" AutoEventWireup="true" CodeFile="Default.aspx.cs" Inherits="_Default" ResponseEncoding="utf-8" ClientIDMode="Static" %>
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head runat="server">
    <meta charset="utf-8" />
    <title>واترمارک عکس</title>
    <style type="text/css">
        body {
            margin: 0;
            background: #f3efe6;
            color: #1d1a16;
            font-family: Tahoma, Arial, sans-serif;
        }
        main {
            max-width: 760px;
            margin: 28px auto;
            padding: 28px 28px 32px;
            background: #fffdf8;
            border: 1px solid #e3d9c8;
        }
        h1 {
            margin: 0 0 8px;
            font-size: 24px;
            font-weight: normal;
        }
        p.lead {
            margin: 0 0 22px;
            color: #5c564c;
            line-height: 1.7;
        }
        label {
            display: block;
            margin: 14px 0 6px;
        }
        input[type="text"], select {
            width: 100%;
            box-sizing: border-box;
            padding: 8px 10px;
            border: 1px solid #d9d0c2;
            background: #fff;
            font-family: inherit;
            font-size: 14px;
        }
        .row {
            display: table;
            width: 100%;
            border-collapse: separate;
            border-spacing: 12px 0;
            margin: 0 -12px;
        }
        .row .cell {
            display: table-cell;
            width: 33.33%;
            vertical-align: top;
        }
        button, .button, input[type="submit"] {
            display: inline-block;
            margin-top: 18px;
            padding: 9px 16px;
            border: 0;
            background: #1f4d3a;
            color: #fff;
            font-family: inherit;
            font-size: 14px;
            cursor: pointer;
            text-decoration: none;
        }
        .message {
            min-height: 1.4em;
            margin: 16px 0 0;
        }
        .message.error { color: #8c2f2f; }
        .message.ok { color: #1f4d3a; }
        .preview {
            margin-top: 18px;
        }
        .preview img {
            max-width: 100%;
            height: auto;
            border: 1px solid #e3d9c8;
        }
        code {
            direction: ltr;
            unicode-bidi: embed;
            font-family: Consolas, monospace;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <form id="form1" runat="server" enctype="multipart/form-data">
        <main>
            <h1>درج واترمارک روی عکس</h1>
            <p class="lead">عکس را انتخاب کنید. می‌توانید متن، لوگو، یا هر دو را روی آن بگذارید. برای عکس‌هایی که از قبل روی سرور هستند از <code>Watermark.ashx</code> استفاده کنید.</p>

            <label for="fuImage">عکس</label>
            <asp:FileUpload ID="fuImage" runat="server" />

            <label for="txtText">متن واترمارک</label>
            <asp:TextBox ID="txtText" runat="server" Text="سایت من" />

            <label for="fuLogo">لوگو (اختیاری)</label>
            <asp:FileUpload ID="fuLogo" runat="server" />

            <div class="row">
                <div class="cell">
                    <label for="ddlPosition">جایگاه</label>
                    <asp:DropDownList ID="ddlPosition" runat="server">
                        <asp:ListItem Value="BottomRight" Selected="True">پایین راست</asp:ListItem>
                        <asp:ListItem Value="BottomLeft">پایین چپ</asp:ListItem>
                        <asp:ListItem Value="TopRight">بالا راست</asp:ListItem>
                        <asp:ListItem Value="TopLeft">بالا چپ</asp:ListItem>
                        <asp:ListItem Value="Center">وسط</asp:ListItem>
                        <asp:ListItem Value="Tile">تکرار مورب</asp:ListItem>
                    </asp:DropDownList>
                </div>
                <div class="cell">
                    <label for="ddlOpacity">شفافیت</label>
                    <asp:DropDownList ID="ddlOpacity" runat="server">
                        <asp:ListItem Value="0.25">۲۵٪</asp:ListItem>
                        <asp:ListItem Value="0.45" Selected="True">۴۵٪</asp:ListItem>
                        <asp:ListItem Value="0.65">۶۵٪</asp:ListItem>
                        <asp:ListItem Value="0.85">۸۵٪</asp:ListItem>
                        <asp:ListItem Value="1">کامل</asp:ListItem>
                    </asp:DropDownList>
                </div>
                <div class="cell">
                    <label for="ddlColor">رنگ متن</label>
                    <asp:DropDownList ID="ddlColor" runat="server">
                        <asp:ListItem Value="White" Selected="True">سفید</asp:ListItem>
                        <asp:ListItem Value="Black">مشکی</asp:ListItem>
                    </asp:DropDownList>
                </div>
            </div>

            <asp:Button ID="btnApply" runat="server" Text="اعمال واترمارک" OnClick="btnApply_Click" />
            <asp:Label ID="lblMessage" runat="server" CssClass="message" />

            <div class="preview">
                <asp:Image ID="imgResult" runat="server" Visible="false" AlternateText="نتیجه واترمارک" />
                <div>
                    <asp:HyperLink ID="lnkDownload" runat="server" Visible="false" CssClass="button" Text="دانلود تصویر" />
                </div>
            </div>
        </main>
    </form>
</body>
</html>
