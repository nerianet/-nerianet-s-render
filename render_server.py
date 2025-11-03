from flask import Flask, request
import requests
import os

app = Flask(__name__)

# ===== הגדרות שצריך למלא =====
# **הערה: רצוי לשלוף את הנתונים הרגישים (כמו ה-SECRET) ממשתני סביבה ב-Render,
# ולא לקודד אותם ישירות בקוד המקור.**
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
    <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #f7f7f7; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        <h2 style="color: #FF6600;">💡 התחברות ל-AliExpress API</h2>
        <p style="color: #333; font-size: 1.1em;">לחץ על הקישור למטה כדי להתחבר ולבצע את האימות ב-AliExpress:</p>
        <a href="{AUTH_URL}" target="_blank" style="display: inline-block; padding: 12px 25px; margin-top: 15px; background-color: #FF6600; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 1.2em; transition: background-color 0.3s;">
            <b>התחבר עכשיו ל-AliExpress</b>
        </a>
        <p style="margin-top: 20px; font-size: 0.9em; color: #666;">לאחר האישור, המערכת תפנה אותך אוטומטית ל-Callback.</p>
    </div>
    '''

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return """
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #fff0f0; border: 1px solid #ffdddd; border-radius: 10px;">
            <h3 style="color: #d9534f;">❌ שגיאה: לא התקבל קוד אימות</h3>
            <p>חסר פרמטר <code>?code=</code> בכתובת.</p>
        </div>
        """

    # === שלב 2 – בקשת טוקנים (POST) ===
    # התיקון בוצע כאן: שימוש בכתובת OAuth הנכונה להחלפת קוד.
    token_url = "https://oauth.aliexpress.com/token" 
    
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "need_refresh_token": "true"
    }

    response = None
    try:
        # שליחת הבקשה להחלפת קוד האימות לטוקנים
        response = requests.post(token_url, data=data)
        response.raise_for_status() # מפעיל Exception אם הסטטוס הוא 4xx או 5xx
        tokens = response.json()
    except Exception as e:
        error_message = f"❌ שגיאה בשליפת טוקנים: {e}"
        response_text = response.text if response is not None else "אין תגובה מהשרת."
        
        return f"""
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #fff0f0; border: 1px solid #ffdddd; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <h3 style="color: #d9534f;">{error_message}</h3>
            <p style="color: #333;">תוכן התגובה הגולמי (לבדיקה):</p>
            <pre style="text-align: left; background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto;">{response_text}</pre>
        </div>
        """

    print("========== TOKENS ==========")
    print(tokens)
    print("============================")

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    if access_token and refresh_token:
        # הצגת הטוקנים באופן ברור ועיצוב יפה
        return f"""
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 30px; background-color: #e6ffe6; border: 1px solid #ccffcc; border-radius: 15px; box-shadow: 0 6px 12px rgba(40,167,69,0.2);">
            <h3 style="color: #28a745; font-size: 1.5em;">✅ קיבלת בהצלחה את הטוקנים!</h3>
            <p style="margin-top: 20px; text-align: left; padding: 0 10%; font-size: 1.1em;">
                <b style="color: #007bff;">Access Token:</b> <code style="display: block; background-color: #fff; padding: 8px; border-radius: 4px; border: 1px solid #ccc; word-break: break-all;">{access_token}</code>
            </p>
            <p style="margin-top: 10px; text-align: left; padding: 0 10%; font-size: 1.1em;">
                <b style="color: #17a2b8;">Refresh Token:</b> <code style="display: block; background-color: #fff; padding: 8px; border-radius: 4px; border: 1px solid #ccc; word-break: break-all;">{refresh_token}</code>
            </p>
            <p style="margin-top: 25px; font-weight: bold; color: #333;">העתק את הערכים האלו לשימוש בקוד הפייתון הראשי שלך!</p>
            <hr style="margin-top: 20px; border-color: #ccc;">
            <p style="font-size: 0.9em; color: #666;">בדוק גם בלוגים של Render – שם תראה את ההדפסה המלאה של התגובה (למקרה שתצטרך אותה).</p>
        </div>
        """
    else:
        # טיפול במקרה של תגובה מוצלחת (סטטוס 200) אך ללא טוקנים ב-JSON
        return f"""
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #fff8e1; border: 1px solid #ffe0b2; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <h3 style="color: #ff9800;">⚠️ לא נמצאו טוקנים בתגובה</h3>
            <p style="color: #333;">תוכן התגובה המלאה (JSON):</p>
            <pre style="text-align: left; background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto;">{tokens}</pre>
        </div>
        """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
