from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
import resend
from datetime import datetime
import time
import os

# Load environment variables from .env file
load_dotenv()

app = FastAPI()
calls = {}

# Resend API Configuration (works on Railway!)
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")  # Default Resend test email
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# Initialize Resend
resend.api_key = RESEND_API_KEY

MAX_CALL_DURATION = 180  # 3 minutes
MAX_SILENCE_WARNINGS = 2

def send_email(caller_name, reason, phone):
    """Send email notification using Resend API"""
    try:
        # Create HTML email body
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                    <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                        📞 New Call Received
                    </h2>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p style="margin: 10px 0;"><strong>👤 Caller Name:</strong> {caller_name}</p>
                        <p style="margin: 10px 0;"><strong>📱 Phone Number:</strong> {phone}</p>
                        <p style="margin: 10px 0;"><strong>⏰ Time:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    </div>
                    
                    <div style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #856404;">💼 Reason for Call:</h3>
                        <p style="margin: 0;">{reason}</p>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    
                    <p style="color: #666; font-size: 12px; text-align: center;">
                        This is an automated notification from your AI Call Assistant
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Send email using Resend API
        params = {
            "from": SENDER_EMAIL,
            "to": [RECIPIENT_EMAIL],
            "subject": f"📞 New Call for Mr. Anmol from {caller_name}",
            "html": html_body,
        }
        
        email = resend.Emails.send(params)
        print(f"✅ Email sent successfully to {RECIPIENT_EMAIL} (ID: {email['id']})")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

@app.post("/exotel")
async def exotel_webhook(request: Request):
    data = await request.form()

    call_sid = data.get("CallSid")
    speech = (data.get("SpeechResult") or "").strip()
    caller = data.get("From")

    now = time.time()

    if call_sid not in calls:
        calls[call_sid] = {
            "start": now,
            "silence": 0,
            "phone": caller
        }
        return PlainTextResponse(
            "Hello, you have reached Mr. Anmol's assistant. May I know your name?"
        )

    call = calls[call_sid]

    # Hard stop after 3 minutes
    if now - call["start"] > MAX_CALL_DURATION:
        del calls[call_sid]
        return PlainTextResponse(
            "No response detected. Ending the call now. Goodbye."
        )

    # Silence handling
    if not speech:
        call["silence"] += 1

        if call["silence"] == 1:
            return PlainTextResponse(
                "I could not hear you. Please respond."
            )

        if call["silence"] >= MAX_SILENCE_WARNINGS:
            del calls[call_sid]
            return PlainTextResponse(
                "No response detected. Ending the call now. Goodbye."
            )

    call["silence"] = 0

    if "name" not in call:
        call["name"] = speech
        return PlainTextResponse(
            "Thank you. What is the work or reason for which you are calling Mr. Anmol?"
        )

    if "reason" not in call:
        call["reason"] = speech
        # Send email
        email_success = send_email(call["name"], speech, call["phone"])
        
        del calls[call_sid]
        
        if email_success:
            return PlainTextResponse(
                "Thank you for calling. If the matter is relevant, Mr. Anmol will reach out to you. Goodbye. (Email Sent)"
            )
        else:
            return PlainTextResponse(
                "Thank you for calling. If the matter is relevant, Mr. Anmol will reach out to you. Goodbye. (Email Failed - Check Logs)"
            )
