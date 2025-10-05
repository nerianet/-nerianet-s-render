from flask import Flask, request, redirect
import requests
import os

app = Flask(__name__)

# ===== הגדרות שצריך למלא =====
CLIENT_ID = "הכנס_כאן_את_CLIENT_ID_שלך"
CLIENT_SECRET = "הכנס_כאן_את_CLIENT_SECRET_שלך"
REDIRECT_URI = "https://neria-callback.onrender.com/callback"

# כתובת האימות של עליאקספרס
AUTH_URL = f"https://auth.aliexpress.com/oauth/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state=1234"

@app.route('/')
def index():
    return f'<h2>לחץ <a href="{AUTH_URL}" target="_blank">כאן</a> כדי להתחבר ל-AliExpress ולקבל טוקנים</h2>'

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "❌ לא התקבל קוד אימות"

    # שלב 2 – המרת authorization code ל־access_token ו־refresh_token
    token_url = "https://api-sg.aliexpress.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    response = requests.post(token_url, data=data)
    tokens = response.json()
    print("========== TOKENS ==========")
    print(tokens)
    print("============================")

    return f"<h3>✅ התקבלו הטוקנים! בדוק את קונסול Render.</h3>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

