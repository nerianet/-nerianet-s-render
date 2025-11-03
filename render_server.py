from flask import Flask, request
import requests
import os
import hashlib
import hmac
import time
import json # ייבוא חדש לטובת הצגת JSON יפה

app = Flask(__name__)

# ===== הגדרות שצריך למלא =====
CLIENT_ID = "520232"  # App Key שלך
CLIENT_SECRET = "k0UqqVGIldwk5pZhMwGJGZOQhQpvZsf2"  # App Secret שלך
REDIRECT_URI = "https://nerianet-render-callback-ali.onrender.com/callback"

# הגדרת כתובות ה-API
AUTH_URL = (
    f"https://auth.aliexpress.com/oauth/authorize?"
    f"response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state=1234"
)
TOKEN_URL = "https://oauth.aliexpress.com/token" 
API_METHOD_PATH = "aliexpress.trade.auth.token.create"

# --- פונקציה לחישוב חתימת API (Signature) ---
def generate_sign(params, secret, method_name):
    """
    מחשבת חתימת HMAC-SHA256 ל-AliExpress API.
    הנוסחה: SIGN = HMAC_SHA256(API_METHOD_NAME + סדר הפרמטרים, SECRET)
    """
    # 1. מיון הפרמטרים לפי סדר אלפביתי (ללא 'sign')
    # חשוב: אנחנו לא מוציאים את client_secret כי הוא נשלח כעת גם בנתונים
    params_for_sign = {k: v for k, v in params.items() if k != 'sign'}
    sorted_params = sorted(params_for_sign.items())
    
    # 2. שרשור הפרמטרים
    concatenated_string = ""
    for k, v in sorted_params:
        concatenated_string += f"{k}{str(v)}"
    
    # 3. יצירת המחרוזת לחתימה: METHOD_NAME + CONCATENATED_PARAMS
    # לפי תיעוד AliExpress, ה-Secret הוא המפתח ל-HMAC.
    data_to_sign = method_name + concatenated_string
    
    # 4. חישוב חתימת HMAC-SHA256
    hashed = hmac.new(
        secret.encode('utf-8'),
        data_to_sign.encode('utf-8'),
        hashlib.sha256
    )
    
    # 5. המרת התוצאה להקסה (hex) ורישום באותיות גדולות (Uppercase)
    sign = hashed.hexdigest().upper()
    return sign, data_to_sign

# --- Flask Routes ---

@app.route('/')
def index():
    # ... (HTML של דף הבית) ...
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
        # ... (שגיאה אם אין קוד) ...
        return """
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #fff0f0; border: 1px solid #ffdddd; border-radius: 10px;">
            <h3 style="color: #d9534f;">❌ שגיאה: לא התקבל קוד אימות</h3>
            <p>חסר פרמטר <code>?code=</code> בכתובת.</p>
        </div>
        """

    # 1. הכנת הפרמטרים הנדרשים
    # **שינוי קריטי:** הוספת client_secret בחזרה לנתונים הנשלחים, כדי להתאים לדרישה החריגה של Ali.
    token_params = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET, # הוחזר לנתונים הנשלחים
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "need_refresh_token": "true",
        "timestamp": int(time.time() * 1000), 
        "method": API_METHOD_PATH, 
        "v": "2.0", 
    }
    
    # 2. חישוב החתימה
    # generate_sign מחזירה כעת גם את המחרוזת הגולמית לחתימה
    calculated_sign, data_to_sign_raw = generate_sign(token_params, CLIENT_SECRET, API_METHOD_PATH)
    token_params["sign"] = calculated_sign
    
    # 3. ביצוע בקשת ה-POST
    response = None
    try:
        response = requests.post(TOKEN_URL, data=token_params)
        response.raise_for_status() 
        tokens = response.json()
        
    except Exception as e:
        error_message = f"❌ שגיאה בשליפת טוקנים: {e}"
        response_text = response.text if response is not None else "אין תגובה מהשרת."
        
        # --- הצגת לוגים מפורטים בדפדפן ---
        log_html = f"""
        <div style="margin-top: 20px; border-top: 2px dashed #ccc; padding-top: 15px;">
            <h4 style="color: #007bff;">נתוני דיבוג (DEBUG)</h4>
            <p><strong>URL של הבקשה:</strong> <code>{TOKEN_URL}</code></p>
            <p><strong>שגיאה שהתקבלה:</strong> <code>{e}</code></p>

            <h5>JSON שנשלח (Form Data):</h5>
            <pre style="text-align: left; background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap;">{json.dumps(token_params, indent=2)}</pre>

            <h5>מחרוזת גולמית לחתימה (Data to Sign):</h5>
            <pre style="text-align: left; background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto; word-break: break-all;">{data_to_sign_raw}</pre>
            
            <h5>החתימה שחושבה (Calculated SIGN):</h5>
            <code style="display: block; background-color: #e0e0ff; padding: 5px; border-radius: 3px; font-weight: bold; word-break: break-all;">{calculated_sign}</code>

            <h5>תוכן התגובה הגולמי:</h5>
            <pre style="text-align: left; background-color: #fdd; padding: 10px; border-radius: 5px; overflow-x: auto;">{response_text}</pre>
        </div>
        """
        
        return f"""
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #fff0f0; border: 1px solid #ffdddd; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <h3 style="color: #d9534f;">{error_message}</h3>
            {log_html}
        </div>
        """

    # ... (קוד הצלחה אם מתקבלים טוקנים) ...
    # ... (הקוד של הצגת הטוקנים נשאר זהה) ...
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    if access_token and refresh_token:
        # הצגת הטוקנים
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
            <pre style="text-align: left; background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto;">{json.dumps(tokens, indent=2)}</pre>
        </div>
        """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
