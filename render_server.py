from flask import Flask, request
import requests
import os
import hashlib
import hmac
import time
import json

app = Flask(__name__)

# ===== הגדרות שצריך למלא =====
CLIENT_ID = "520232"
CLIENT_SECRET = "k0UqqVGIldwk5pZhMwGJGZOQhQpvZsf2"
REDIRECT_URI = "https://nerianet-render-callback-ali.onrender.com/callback"

# כתובת ה-REST הבסיסית
API_BASE = "https://api-sg.aliexpress.com"
API_METHOD_PATH_NAME = "/auth/token/create"   # הנתיב הקצר שישורשר לחתימה ונקרא ישירות
TOKEN_URL = API_BASE + "/rest" + API_METHOD_PATH_NAME

def generate_top_sign(params, secret, endpoint_path):
    """
    חישוב HMAC-SHA256 לפי דפוס שהצליח בעבודות קהילתיות:
    - ממיינים את הפרמטרים לפי שם המפתח (ASCII)
    - בונים מחרוזת כמו key1value1key2value2...
    - משרשרים את endpoint_path (למשל '/auth/token/create') בתחילת המחרוזת
    - מחשבים HMAC-SHA256 עם client_secret כמפתח
    - מחזירים hex upper-case
    """
    # 1. סינון פרמטרים שלא נחוצים לחתימה
    params_to_sign = {
        k: v for k, v in params.items()
        if k not in ['sign', 'client_secret', 'sign_method', 'method']
    }

    # 2. מיון לפי ASCII (מפתח)
    sorted_items = sorted(params_to_sign.items(), key=lambda x: x[0])

    # 3. שרשור key+value ללא קידוד
    concatenated = "".join(f"{k}{v}" for k, v in sorted_items)

    # 4. prepend הנתיב הקצר
    data_to_sign_raw = endpoint_path + concatenated

    # 5. חישוב HMAC-SHA256 (מפתח = client_secret)
    mac = hmac.new(secret.encode('utf-8'), data_to_sign_raw.encode('utf-8'), hashlib.sha256)
    sign = mac.hexdigest().upper()
    return sign, data_to_sign_raw

@app.route('/')
def index():
    AUTH_URL = (
        f"https://auth.aliexpress.com/oauth/authorize?"
        f"response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state=1234"
    )
    return f'''
    <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px;">
        <h2>התחבר ל-AliExpress</h2>
        <a href="{AUTH_URL}" target="_blank">התחבר עכשיו</a>
    </div>
    '''

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "Missing code", 400

    # הכנת פרמטרים
    # שים לב: timestamp כאן יכול להיות בשיטת millisecond UNIX, זה עובד ברבות מהדוגמאות
    timestamp = str(int(time.time() * 1000))

    params_for_sign = {
        "app_key": CLIENT_ID,
        "timestamp": timestamp,
        "sign_method": "HMAC_SHA256",   # שים לב: לפעמים השדה נקרא 'sha256' בדוגמאות — אם ידרוש שינוי, נשנה
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "need_refresh_token": "true",
        # שים לב: אין 'method' כאן לחתימה
    }

    # חישוב החתימה — משתמש בנתיב הקצר (endpoint path)
    calculated_sign, data_to_sign_raw = generate_top_sign(params_for_sign, CLIENT_SECRET, API_METHOD_PATH_NAME)

    # בונים את ה-form data לשליחה (ללא client_secret)
    post_data = params_for_sign.copy()
    post_data["method"] = API_METHOD_PATH_NAME  # עדיין שולחים את הנתיב הקצר כפרמטר אם הפורמט דורש
    post_data["sign"] = calculated_sign

    # שולחים POST ל־https://api-sg.aliexpress.com/rest/auth/token/create
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }

    try:
        response = requests.post(TOKEN_URL, data=post_data, headers=headers, timeout=15)
        response_text = response.text
        full_response = response.json()
    except Exception as e:
        return f"Request failed: {e}", 500

    # בדיקות פשוטות על תגובה
    if 'error_response' in full_response:
        return f"API error: {json.dumps(full_response['error_response'], indent=2)}", 500

    # ננסה למצוא access_token במפתחות הצפויים
    tokens = {}
    if 'access_token' in full_response:
        tokens = full_response
    else:
        response_key = "aliexpress_trade_auth_token_create_response"
        if response_key in full_response:
            tokens = full_response[response_key]
        else:
            tokens = full_response

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    debug_html = f"""
    <h3>DEBUG</h3>
    <pre>POST URL: {TOKEN_URL}</pre>
    <pre>Form data sent (no client_secret): {json.dumps(post_data, indent=2)}</pre>
    <pre>Data used for sign (raw): {data_to_sign_raw}</pre>
    <pre>Calculated sign: {calculated_sign}</pre>
    <pre>API response: {response_text}</pre>
    """

    if access_token and refresh_token:
        return f"<h2>Success</h2><p>access_token: {access_token}</p><p>refresh_token: {refresh_token}</p>"
    else:
        return f"<h2>Error retrieving tokens</h2>{debug_html}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))