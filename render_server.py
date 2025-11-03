from flask import Flask, request
import requests
import os
import hashlib
import hmac
import time
import json

app = Flask(__name__)

# === הגדרות ראשוניות ===
CLIENT_ID = os.environ.get("ALI_CLIENT_ID", "520232")
CLIENT_SECRET = os.environ.get("ALI_CLIENT_SECRET", "k0UqqVGIldwk5pZhMwGJGZOQhQpvZsf2")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "https://nerianet-render-callback-ali.onrender.com/callback")

# כתובות API
TOKEN_URL = "https://api-sg.aliexpress.com/rest/auth/token/create"

# --- פונקציה לחישוב חתימה ---
def generate_top_sign(params, secret):
    """
    חישוב חתימת AliExpress TOP API: secret + keyvalue... + secret
    """
    sorted_params = sorted(params.items())
    concatenated = secret + ''.join(f"{k}{v}" for k, v in sorted_params) + secret
    hashed = hmac.new(secret.encode('utf-8'), concatenated.encode('utf-8'), hashlib.sha256)
    return hashed.hexdigest().upper()

@app.route('/')
def index():
    auth_url = (
        f"https://auth.aliexpress.com/oauth/authorize?response_type=code"
        f"&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state=1234"
    )
    return f"""
    <div style="font-family: Arial; text-align:center; padding:40px;">
        <h2>AliExpress OAuth</h2>
        <a href='{auth_url}' style="background:#FF6600;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;">
            התחבר לחשבון AliExpress
        </a>
    </div>
    """

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "❌ שגיאה: לא התקבל קוד מה-Redirect של AliExpress"

    params = {
        "app_key": CLIENT_ID,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "sha256",
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "need_refresh_token": "true",
    }

    # חישוב חתימה
    sign = generate_top_sign(params, CLIENT_SECRET)
    params["sign"] = sign

    try:
        response = requests.post(TOKEN_URL, data=params)
        data = response.json()
    except Exception as e:
        return f"❌ שגיאה בבקשה: {e}"

    return f"""
    <div style="font-family: Arial; padding: 30px; background-color: #f7f7f7;">
        <h3>תוצאת קריאת ה-API:</h3>
        <pre style="background:#fff;border:1px solid #ccc;padding:10px;border-radius:5px;">
{json.dumps(data, indent=2, ensure_ascii=False)}
        </pre>
    </div>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
