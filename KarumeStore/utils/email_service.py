import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv


load_dotenv()


def send_otp_email(recipient_email, otp):

    # =====================================================
    # MAIL CONFIGURATION
    # =====================================================

    mail_server = os.getenv("MAIL_SERVER")

    mail_port = int(
        os.getenv("MAIL_PORT", "465")
    )

    mail_username = os.getenv("MAIL_USERNAME")

    mail_password = os.getenv("MAIL_PASSWORD")

    mail_from = os.getenv("MAIL_FROM")

    mail_from_name = os.getenv(
        "MAIL_FROM_NAME",
        "KarumeStore"
    )


    # =====================================================
    # VALIDATE CONFIGURATION
    # =====================================================

    missing = []

    if not mail_server:
        missing.append("MAIL_SERVER")

    if not mail_username:
        missing.append("MAIL_USERNAME")

    if not mail_password:
        missing.append("MAIL_PASSWORD")

    if not mail_from:
        missing.append("MAIL_FROM")


    if missing:

        print(
            "[EMAIL] Missing environment variables:",
            ", ".join(missing)
        )

        return False


    # =====================================================
    # CREATE EMAIL
    # =====================================================

    message = EmailMessage()

    message["Subject"] = (
        "Your KarumeStore Reset OTP Code"
    )

    message["From"] = (
        f"{mail_from_name} <{mail_from}>"
    )

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

Thank you for choosing KarumeStore.

You can reply to this email if you have any questions.
"""
    )


    # =====================================================
    # SEND EMAIL
    # =====================================================

    try:

        print(
            f"[EMAIL] Connecting to {mail_server}:{mail_port}..."
        )


        with smtplib.SMTP_SSL(
            mail_server,
            mail_port,
            timeout=15
        ) as smtp:

            print(
                "[EMAIL] SMTP connection established."
            )


            smtp.login(
                mail_username,
                mail_password
            )


            print(
                "[EMAIL] SMTP authentication successful."
            )


            smtp.send_message(
                message
            )


        print(
            "[EMAIL] OTP email sent successfully."
        )

        return True


    except smtplib.SMTPAuthenticationError as exc:

        print(
            "[EMAIL] SMTP authentication failed:",
            exc
        )

        return False


    except (TimeoutError, OSError) as exc:

        print(
            "[EMAIL] SMTP connection failed:",
            exc
        )

        return False


    except smtplib.SMTPException as exc:

        print(
            "[EMAIL] SMTP error:",
            exc
        )

        return False


    except Exception as exc:

        print(
            "[EMAIL] Unexpected email error:",
            exc
        )

        return False
