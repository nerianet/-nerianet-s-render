from flask import Flask, request
import requests
import os

app = Flask(__name__)

# ===== הגדרות שצריך למלא =====
CLIENT_ID = "520232"  # App Key שלך
CLIENT_SECRET = "k0UqqVGIldwk5pZhMwGJGZOQhQpvZsf2"  # App Secret שלך
REDIRECT_URI = "https://nerianet-render-callback-ali.onrender.com/callback"

# שלב 1 – קישור לאימות
AUTH_URL = (
    f"https://auth.aliexpress.com/oauth/authorize?"
    f"response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state=1234"
)

@app.route('/')
def index():
    return f'''
    <h2>💡 התחברות ל-AliExpress API</h2>
    <p>לחץ על הקישור למטה כדי להתחבר ולקבל את ה-access_token וה-refresh_token:</p>
    <a href="{AUTH_URL}" target="_blank"><b>התחבר עכשיו ל-AliExpress</b></a>
    '''

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "❌ לא התקבל קוד אימות (missing ?code=)"

    # === שלב 2 – בקשת טוקנים (POST) ===
    token_url = "https://api-sg.aliexpress.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "need_refresh_token": "true"
    }

    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        tokens = response.json()
    except Exception as e:
        return f"""
        ❌ שגיאה בשליפת טוקנים: {e}
        <br><br>
        <pre>{response.text if 'response' in locals() else ''}</pre>
        """

    print("========== TOKENS ==========")
    print(tokens)
    print("============================")

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    if access_token and refresh_token:
        return f"""
        <h3>✅ קיבלת בהצלחה את הטוקנים!</h3>
        <p><b>Access Token:</b> {access_token}</p>
        <p><b>Refresh Token:</b> {refresh_token}</p>
        <p>העתק את הערכים האלו לקובץ tokens.json במחשב שלך.</p>
        <hr>
        <p>בדוק גם בלוגים של Render — שם תראה את ההדפסה המלאה של התגובה.</p>
        """
    else:
        return f"<h3>⚠️ לא נמצאו טוקנים בתגובה</h3><pre>{tokens}</pre>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
