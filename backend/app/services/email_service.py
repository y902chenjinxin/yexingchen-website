import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


def send_verification_email(to_email: str, code: str):
    """发送验证码邮件"""
    msg = MIMEMultipart()
    msg['From'] = settings.SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = "【叶兴辰的个人网站】注册验证码"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; background: #0D1F27; margin: 0; padding: 20px; }}
            .container {{ background: linear-gradient(135deg, #1A3A4A 0%, #2D5A6B 100%); max-width: 500px; margin: 0 auto; padding: 40px; border-radius: 12px; border: 1px solid rgba(78,205,196,0.3); box-shadow: 0 8px 32px rgba(0,0,0,0.4); }}
            .title {{ color: #E8F4F0; font-size: 22px; text-align: center; margin-bottom: 30px; }}
            .code-box {{ background: rgba(78,205,196,0.15); border: 2px dashed #4ECDC4; border-radius: 8px; padding: 30px; text-align: center; margin: 20px 0; }}
            .code {{ color: #4ECDC4; font-size: 36px; font-weight: bold; letter-spacing: 8px; }}
            .desc {{ color: #8BA5B5; font-size: 14px; text-align: center; margin-top: 20px; }}
            .footer {{ color: #6B7B8B; font-size: 12px; text-align: center; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="title">叶兴辰的个人网站</div>
            <div class="code-box">
                <div class="code">{code}</div>
            </div>
            <div class="desc">验证码有效期为3分钟，请尽快完成验证</div>
            <div class="footer">如果您没有进行注册操作，请忽略此邮件</div>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)