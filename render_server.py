from flask import Flask, request
import requests
import os
import hashlib
import hmac
import time
import json

app = Flask(__name__)

# === הגדרות ראשוניות ===
CLIENT_ID = "520232"  # AppKey שלך
CLIENT_SECRET = "k0UqqVGIldwk5pZhMwGJGZOQhQpvZsf2"  # AppSecret שלך
REDIRECT_URI = "https://nerianet-render-callback-ali.onrender.com/callback"

# כתובת API ליצירת Access Token
TOKEN_URL = "https://api-sg.aliexpress.com/rest/auth/token/create"

# --- פונקציה לחישוב חתימה לפי AliExpress TOP API ---
def generate_top_sign(params, secret):
    """
    חתימה לפי סטנדרט HMAC_SHA256 של AliExpress
    """
    sorted_params = sorted(params.items())
    concatenated = secret + ''.join(f"{k}{v}" for k, v in sorted_params) + secret
    hashed = hmac.new(secret.encode('utf-8'), concatenated.encode('utf-8'), hashlib.sha256)
    return hashed.hexdigest().upper()

@app.route('/')
def index():
    # קישור הרשאה מדויק לפי הדוקומנטציה
    auth_url = (
        f"https://api-sg.aliexpress.com/oauth/authorize"
        f"?response_type=code"
        f"&force_auth=true"
        f"&redirect_uri={REDIRECT_URI}"
        f"&client_id={CLIENT_ID}"
    )
    return f"""
    <h2>AliExpress OAuth</h2>
    <a href='{auth_url}'>התחבר לחשבון AliExpress</a>
    """

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "שגיאה: לא התקבל קוד."

    # פרמטרים ליצירת Access Token
    params = {
        "app_key": CLIENT_ID,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "HMAC_SHA256",
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "need_refresh_token": "true",
    }

    # יצירת חתימה
    sign = generate_top_sign(params, CLIENT_SECRET)
    params["sign"] = sign

    try:
        response = requests.post(TOKEN_URL, data=params)
        data = response.json()
    except Exception as e:
        return f"שגיאה בבקשה: {e}"

    # הצגת התוצאה בדפדפן
    return f"<pre>{json.dumps(data, indent=2, ensure_ascii=False)}</pre>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

# --- requirements.txt ---
# flask
# requests
