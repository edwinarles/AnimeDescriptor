import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config

def send_login_email(email, api_key, host_url):
    """Send an email with the magic link/API key"""
    if not Config.SMTP_USERNAME or not Config.SMTP_PASSWORD:
        print("⚠️ SMTP not configured. Cannot send email.")
        print(f"   SMTP_USERNAME: {'SET' if Config.SMTP_USERNAME else 'NOT SET'}")
        print(f"   SMTP_PASSWORD: {'SET' if Config.SMTP_PASSWORD else 'NOT SET'}")
        return False
    
    try:
        print(f"📧 Attempting to send login email to: {email}")
        print(f"   SMTP Server: {Config.SMTP_SERVER}:{Config.SMTP_PORT}")
        print(f"   From: {Config.EMAIL_FROM}")
        
        msg = MIMEMultipart()
        msg['From'] = Config.EMAIL_FROM
        msg['To'] = email
        msg['Subject'] = "Your OtakuDescriptor Access"
        
        base_url = host_url.rstrip('/')
        magic_link = f"{base_url}/?api_key={api_key}"
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <h2 style="color: #FF6B6B;">Welcome to OtakuDescriptor</h2>
                    <p>You requested to log in. Click the button below to access your account:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{magic_link}" style="background-color: #FF6B6B; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Log In</a>
                    </div>
                    <p>Or copy your API Key directly:</p>
                    <code style="background: #f4f4f4; padding: 5px 10px; border-radius: 4px; display: block; text-align: center; margin: 10px 0;">{api_key}</code>
                    <p style="font-size: 0.9em; color: #888; margin-top: 30px;">If you didn't request this email, you can safely ignore it.</p>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        print("   Connecting to SMTP server...")
        # CRITICAL: Add timeout to prevent Gunicorn from killing worker
        server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=10)
        print("   Starting TLS...")
        server.starttls()
        print("   Authenticating...")
        server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        print("   Sending message...")
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Login email sent successfully to {email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP Authentication failed: {e}")
        print("   Check SMTP_USERNAME and SMTP_PASSWORD")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP Error: {type(e).__name__} - {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error sending email: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return False

def send_verification_email(email, verification_token, host_url):
    """Send a verification email to confirm the account"""
    if not Config.SMTP_USERNAME or not Config.SMTP_PASSWORD:
        print("⚠️ SMTP not configured. Cannot send verification email.")
        print(f"   SMTP_USERNAME: {'SET' if Config.SMTP_USERNAME else 'NOT SET'}")
        print(f"   SMTP_PASSWORD: {'SET' if Config.SMTP_PASSWORD else 'NOT SET'}")
        return False
    
    try:
        print(f"📧 Attempting to send verification email to: {email}")
        print(f"   SMTP Server: {Config.SMTP_SERVER}:{Config.SMTP_PORT}")
        print(f"   From: {Config.EMAIL_FROM}")
        print(f"   Host URL: {host_url}")
        
        msg = MIMEMultipart()
        msg['From'] = Config.EMAIL_FROM
        msg['To'] = email
        msg['Subject'] = "Confirm Your OtakuDescriptor Account"
        
        base_url = host_url.rstrip('/')
        # CORRECTION: Add /api/auth to the path
        verification_link = f"{base_url}/api/auth/verify-email?token={verification_token}"
        
        print(f"   Verification link: {verification_link}")
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <h2 style="color: #8b5cf6;">Welcome to OtakuDescriptor! 🎉</h2>
                    <p>Thank you for registering. To activate your account, please confirm your email address.</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_link}" style="background-color: #8b5cf6; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">Confirm My Email</a>
                    </div>
                    <p style="color: #666; font-size: 14px;">This link is valid for 24 hours.</p>
                    <p style="font-size: 0.9em; color: #888; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
                        If you didn't create an account on OtakuDescriptor, you can safely ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        print("   Connecting to SMTP server...")
        # CRITICAL: Add timeout to prevent Gunicorn from killing worker
        server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=10)
        print("   Starting TLS...")
        server.starttls()
        print("   Authenticating...")
        server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        print("   Sending message...")
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Verification email sent successfully to {email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ SMTP Authentication failed: {e}")
        print("   Check your SMTP_USERNAME and SMTP_PASSWORD in Render environment variables")
        print("   For Gmail: use App Password, not regular password")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP Error: {type(e).__name__} - {e}")
        return False
    except TimeoutError as e:
        print(f"❌ SMTP Connection timeout: {e}")
        print("   The SMTP server took too long to respond")
        print("   This might be a firewall/network issue on Render")
        return False
    except OSError as e:
        print(f"❌ Network/Socket error: {e}")
        print("   Cannot connect to SMTP server - possible firewall block")
        return False
    except Exception as e:
        print(f"❌ Unexpected error sending verification email: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return False

def send_reset_password_email(email, token, host_url):
    """Send password recovery email"""
    if not Config.SMTP_USERNAME: return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = Config.EMAIL_FROM
        msg['To'] = email
        msg['Subject'] = "Password Recovery - OtakuDescriptor"
        
        # NOTE: In the frontend you'll need to implement a page that captures this token
        # For now we assume a theoretical url /reset-password.html?token=...
        reset_link = f"{host_url.rstrip('/')}/reset-password.html?token={token}"
        
        html = f"""
        <p>You have requested to reset your password.</p>
        <p><a href="{reset_link}">Click here to create a new password</a></p>
        <p>If this wasn't you, please ignore this message.</p>
        """
        
        msg.attach(MIMEText(html, 'html'))
        server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=10)
        server.starttls()
        server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Error sending reset password email: {e}")
        return False
