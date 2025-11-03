from flask import Flask, request
import requests
import hashlib
import hmac
import time
import json

app = Flask(__name__)

# === הגדרות ראשוניות ===
CLIENT_ID = "520232"  # App Key
CLIENT_SECRET = "k0UqqVGIldwk5pZhMwGJGZOQhQpvZsf2"  # App Secret
REDIRECT_URI = "https://nerianet-render-callback-ali.onrender.com/callback"

# כתובת API להחלפת קוד ב-access token
TOKEN_URL = "https://api-sg.aliexpress.com/rest/auth/token/create"

# --- פונקציה לחישוב חתימה ---
def generate_top_sign(params, secret):
    """
    החתימה לפי HMAC_SHA256 עם כל הפרמטרים כולל method
    """
    sorted_params = sorted(params.items())
    concatenated = ''.join(f"{k}{v}" for k, v in sorted_params)
    hashed = hmac.new(secret.encode('utf-8'), concatenated.encode('utf-8'), hashlib.sha256)
    return hashed.hexdigest().upper()

# --- עמוד הבית --- 
@app.route('/')
def index():
    auth_url = (
        f"https://api-sg.aliexpress.com/oauth/authorize?"
        f"response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state=1234"
    )
    return f"""
    <h2>AliExpress OAuth</h2>
    <a href='{auth_url}'>לחץ כאן כדי להתחבר ל-AliExpress</a>
    """

# --- Callback לקבלת הקוד הזמני ---
@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "שגיאה: לא התקבל קוד זמני."

    # פרמטרים לקריאה ל-TOKEN API
    params = {
        "app_key": CLIENT_ID,
        "timestamp": str(int(time.time() * 1000)),
        "sign_method": "HMAC_SHA256",
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "need_refresh_token": "true",
        "method": "/auth/token/create",  # חשוב לכלול בפרמטרים של החתימה
    }

    # חישוב חתימה תקינה
    params["sign"] = generate_top_sign(params, CLIENT_SECRET)

    try:
        response = requests.post(TOKEN_URL, data=params)
        data = response.json()
    except Exception as e:
        return f"שגיאה בבקשה: {e}"

    return f"<h3>Access Token & Refresh Token</h3><pre>{json.dumps(data, indent=2, ensure_ascii=False)}</pre>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
