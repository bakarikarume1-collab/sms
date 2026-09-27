import os

import resend
from dotenv import load_dotenv


load_dotenv()


def send_otp_email(recipient_email, otp):
    """
    Send password-reset OTP using Resend API.

    Returns:
        True  -> email request accepted by Resend
        False -> sending failed
    """

    api_key = os.getenv("RESEND_API_KEY")
    mail_from = os.getenv(
        "MAIL_FROM",
        "onboarding@resend.dev"
    )
    mail_from_name = os.getenv(
        "MAIL_FROM_NAME",
        "KarumeStore"
    )

    # ---------------------------------------------------------
    # Validate configuration
    # ---------------------------------------------------------

    if not api_key:
        print("[EMAIL] RESEND_API_KEY is missing.")
        return False

    if not recipient_email:
        print("[EMAIL] Recipient email is missing.")
        return False

    if not otp:
        print("[EMAIL] OTP is missing.")
        return False

    # ---------------------------------------------------------
    # Configure Resend
    # ---------------------------------------------------------

    resend.api_key = api_key

    sender = f"{mail_from_name} <{mail_from}>"

    # ---------------------------------------------------------
    # Email content
    # ---------------------------------------------------------

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>KarumeStore Password Reset</title>
</head>

<body style="
    margin: 0;
    padding: 0;
    background-color: #f5f5f5;
    font-family: Arial, sans-serif;
">

    <div style="
        max-width: 600px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 12px;
        padding: 30px;
        box-sizing: border-box;
    ">

        <h2 style="
            margin-top: 0;
            color: #222222;
        ">
            KarumeStore Password Reset
        </h2>

        <p style="
            color: #444444;
            font-size: 15px;
            line-height: 1.6;
        ">
            Hello,
        </p>

        <p style="
            color: #444444;
            font-size: 15px;
            line-height: 1.6;
        ">
            We received a request to reset your KarumeStore
            account password.
        </p>

        <p style="
            color: #444444;
            font-size: 15px;
            line-height: 1.6;
        ">
            Your verification code is:
        </p>

        <div style="
            margin: 25px 0;
            padding: 20px;
            background: #f1f1f1;
            border-radius: 10px;
            text-align: center;
        ">

            <span style="
                font-size: 32px;
                font-weight: bold;
                letter-spacing: 8px;
                color: #111111;
            ">
                {otp}
            </span>

        </div>

        <p style="
            color: #444444;
            font-size: 15px;
            line-height: 1.6;
        ">
            This code will expire in <strong>10 minutes</strong>.
        </p>

        <p style="
            color: #444444;
            font-size: 15px;
            line-height: 1.6;
        ">
            Do not share this code with anyone.
        </p>

        <p style="
            color: #666666;
            font-size: 14px;
            line-height: 1.6;
        ">
            If you did not request a password reset,
            you can safely ignore this email.
        </p>

        <hr style="
            border: none;
            border-top: 1px solid #eeeeee;
            margin: 30px 0;
        ">

        <p style="
            color: #777777;
            font-size: 13px;
        ">
            Regards,<br>
            <strong>{mail_from_name}</strong>
        </p>

    </div>

</body>
</html>
"""

    # ---------------------------------------------------------
    # Send through Resend API
    # ---------------------------------------------------------

    try:

        print(
            f"[EMAIL] Sending OTP to {recipient_email} "
            f"through Resend..."
        )

        params = {
            "from": sender,
            "to": [recipient_email],
            "subject": "Your KarumeStore Reset OTP Code",
            "html": html_content,
        }

        response = resend.Emails.send(params)

        print(
            f"[EMAIL] Resend accepted email request: "
            f"{response}"
        )

        return True

    except Exception as error:

        print(
            f"[EMAIL] Resend sending failed: {error}"
        )

        return False
