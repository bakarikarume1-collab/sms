import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def send_otp_email(recipient_email, otp):

    mail_server = os.getenv("MAIL_SERVER")
    mail_port = int(os.getenv("MAIL_PORT", 465))

    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")

    mail_from = os.getenv("MAIL_FROM")
    mail_from_name = os.getenv("MAIL_FROM_NAME", "KarumeStore")

    message = EmailMessage()

    message["Subject"] = "Your KarumeStore Reset OTP Code"

    message["From"] = f"{mail_from_name} <{mail_from}>"

    message["To"] = recipient_email

    message.set_content(
        f"""
Hello,

We received your request to reset your KarumeStore password.

Your verification code is:

{otp}

Do not share this code with anyone.

This code will expire in 10 minutes.

If you did not request a password reset,
you can safely ignore this email.

Regards,
{mail_from_name}
thabk you for choosing us
you can reply on this email if there is any dault
"""
    )

    try:

        with smtplib.SMTP_SSL(mail_server, mail_port) as smtp:

            smtp.login(
                mail_username,
                mail_password
            )

            smtp.send_message(message)

        print("OTP email sent successfully.")

        return True

    except Exception as e:

        print(f"Email sending error: {e}")

        return False