from flask import Flask, request
import requests
import os
import hashlib
import hmac
import time
import json
import urllib.parse

app = Flask(__name__)

# === הגדרות ראשוניות ===
CLIENT_ID = os.environ.get("ALI_CLIENT_ID", "520232")
CLIENT_SECRET = os.environ.get("ALI_CLIENT_SECRET", "k0UqqVGIldwk5pZhMwGJGZOQhQpvZsf2")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "https://nerianet-render-callback-ali.onrender.com/callback")

# כתובת ה־API הרשמית ליצירת טוקן
TOKEN_URL = "https://api-sg.aliexpress.com/rest/auth/token/create"

# --- פונקציה לחישוב חתימה לפי תקן AliExpress ---
def generate_top_sign(params, secret):
    """
    לפי הסטנדרט הרשמי של AliExpress TOP API:
    sign = HMAC_SHA256(secret, secret + (key1value1key2value2...) + secret)
    * הסדר לפי מפתחות (ascending)
    * חלק מהערכים צריכים להיות URL-encoded (כולל redirect_uri)
    """
    sorted_params = sorted(params.items())
    concatenated = ''.join(f"{k}{urllib.parse.quote(str(v), safe='')}" for k, v in sorted_params)
    string_to_sign = f"{secret}{concatenated}{secret}"
    sign = hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest().upper()
    return sign

@app.route('/')
def index():
    auth_url = (
        "https://auth.aliexpress.com/oauth/authorize?"
        f"response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        "&state=nerianet_demo"
    )
    return f"""
    <html>
    <head><title>AliExpress OAuth</title></head>
    <body style="font-family:Arial; text-align:center; margin-top:100px;">
        <h2>🔗 התחברות לחשבון AliExpress</h2>
        <p>לחץ על הכפתור כדי להתחבר:</p>
        <a href="{auth_url}" style="font-size:18px; background:#f44336; color:white; padding:10px 20px; text-decoration:none; border-radius:6px;">התחבר לחשבון AliExpress</a>
    </body>
    </html>
    """

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "❌ שגיאה: לא התקבל קוד הרשאה."

    timestamp = str(int(time.time() * 1000))
    params = {
        "app_key": CLIENT_ID,
        "timestamp": timestamp,
        "sign_method": "HMAC_SHA256",
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "need_refresh_token": "true",
    }

    # חישוב החתימה לפי התקן המעודכן
    sign = generate_top_sign(params, CLIENT_SECRET)
    params["sign"] = sign

    print("=== DEBUG MODE ===")
    print("POST URL:", TOKEN_URL)
    print("Form Data Sent:", json.dumps(params, indent=2, ensure_ascii=False))

    try:
        response = requests.post(TOKEN_URL, data=params, timeout=10)
        data = response.json()
    except Exception as e:
        return f"<h3>❌ שגיאה בבקשה:</h3><pre>{str(e)}</pre>"

    # הצגה יפה של תוצאת ה־API בדפדפן
    return f"""
    <html>
    <head><title>AliExpress Token Result</title></head>
    <body style="font-family:Arial; margin:40px;">
        <h2>✅ תוצאת קריאת ה־API:</h2>
        <pre style="background:#f4f4f4; padding:15px; border-radius:8px;">{json.dumps(data, indent=2, ensure_ascii=False)}</pre>
    </body>
    </html>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
