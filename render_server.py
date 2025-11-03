from flask import Flask, request
import requests
import os
import hashlib
import hmac
import time
import json

app = Flask(__name__)

# === הגדרות ראשוניות ===
CLIENT_ID = "520232"
CLIENT_SECRET = "k0UqqVGIldwk5pZhMwGJGZOQhQpvZsf2"
REDIRECT_URI = "https://nerianet-render-callback-ali.onrender.com/callback"

# כתובת ה-API לבקשת טוקן
TOKEN_URL = "https://api-sg.aliexpress.com/rest/auth/token/create"

# --- פונקציה לחישוב חתימה (TOP API HMAC_SHA256 לפי AliExpress) ---
def generate_top_sign(params, secret):
    """
    חישוב HMAC_SHA256 TOP API:
    1. ממיינים את כל הפרמטרים לפי key (ascending)
    2. מחברים key + value רצוף
    3. חותמים עם secret כמפתח ל-HMAC
    4. HEX uppercase
    """
    sorted_params = sorted(params.items())
    concatenated = ''.join(f"{k}{v}" for k, v in sorted_params)
    print("=== DEBUG ===\nRaw string to sign:\n", concatenated)
    sign = hmac.new(secret.encode('utf-8'),
                    concatenated.encode('utf-8'),
                    hashlib.sha256).hexdigest().upper()
    return sign

@app.route('/')
def index():
    auth_url = (
        f"https://auth.aliexpress.com/oauth/authorize?"
        f"response_type=code&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&state=nerianet_demo"
    )
    return f"""
    <div style="font-family:Arial;text-align:center;margin-top:50px;">
        <h2>💡 התחברות ל-AliExpress API</h2>
        <p>לחץ על הכפתור למטה כדי להתחבר לחשבון שלך ולקבל Access Token:</p>
        <a href="{auth_url}" style="padding:10px 20px;background:#FF6600;color:white;border-radius:8px;text-decoration:none;">התחבר עכשיו</a>
    </div>
    """

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "<h3 style='color:red'>❌ שגיאה: לא התקבל קוד אימות מהשרת</h3>"

    # יצירת הפרמטרים לבקשת ה-token
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

    # חישוב החתימה
    sign = generate_top_sign(params, CLIENT_SECRET)
    params["sign"] = sign

    print("\n=== DEBUG INFO ===")
    print("POST URL:", TOKEN_URL)
    print("Form Data Sent:", json.dumps(params, indent=2, ensure_ascii=False))

    try:
        response = requests.post(TOKEN_URL, data=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return f"<h3 style='color:red'>❌ שגיאה בשליחת בקשה: {e}</h3>"

    # הצגה יפה של תוצאות ה-API
    return f"""
    <div style="font-family:Arial; margin:20px;">
        <h3>✅ תוצאת קריאת ה־API:</h3>
        <pre style="background:#f4f4f4;padding:10px;border-radius:8px;">{json.dumps(data, indent=2, ensure_ascii=False)}</pre>

        <h4>🔍 פרטי הדיבוג (Debug Info):</h4>
        <pre style="background:#eef;padding:10px;border-radius:8px;">
POST URL: {TOKEN_URL}
Form Data: {json.dumps(params, indent=2, ensure_ascii=False)}
        </pre>
    </div>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
