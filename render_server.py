from flask import Flask, request
import requests
import os
import hashlib
import hmac
import time
import json 

app = Flask(__name__)

# ===== הגדרות שצריך למלא =====
# הערכים האלה אומתו ונמצאו תקינים
CLIENT_ID = "520232"  
CLIENT_SECRET = "k0UqqVGIldwk5pZhMwGJGZOQhQpvZsf2"  
REDIRECT_URI = "https://nerianet-render-callback-ali.onrender.com/callback"

# הגדרת כתובות ה-API
AUTH_URL = (
    f"https://auth.aliexpress.com/oauth/authorize?"
    f"response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state=1234"
)
# זו הכתובת הנכונה להחלפת טוקנים
TOKEN_URL = "https://oauth.aliexpress.com/token" 
# נשמר כדי להשתמש בו בחתימה אם נצטרך, אך לא נשלח בבקשת ה-OAuth
API_METHOD_PATH = "aliexpress.trade.auth.token.create" 

# --- פונקציה לחישוב חתימת API (Signature) באמצעות HMAC-SHA256 ---
def generate_hmac_sha256_sign(params, secret):
    """
    מחשבת חתימת HMAC-SHA256 על פי הפרוטוקול של AliExpress OAuth.
    הנוסחה ככל הנראה היא HMAC-SHA256(SECRET, (SECRET + פרמטרים ממוינים + SECRET)),
    אך ללא METHOD, V, ו-TIMESTAMP.
    """
    # 1. סינון פרמטרים לחתימה
    # אין לכלול את sign או client_secret במחרוזת לחתימה.
    params_to_sign = {
        k: v for k, v in params.items() 
        if k not in ['sign', 'client_secret'] 
    }
    
    # 2. מיון הפרמטרים לפי סדר אלפביתי
    sorted_params = sorted(params_to_sign.items())
    
    # 3. שרשור הפרמטרים לפורמט 'keyvaluekeyvalue...'
    concatenated_string = ""
    for k, v in sorted_params:
        concatenated_string += f"{k}{str(v)}"

    # 4. יצירת המחרוזת לחתימה: SECRET + CONCATENATED_PARAMS + SECRET
    data_to_sign_raw = secret + concatenated_string + secret
    
    # 5. חישוב חתימת HMAC-SHA256
    hashed = hmac.new(
        secret.encode('utf-8'),
        data_to_sign_raw.encode('utf-8'),
        hashlib.sha256
    )
    
    # 6. המרת התוצאה להקסה (hex) ורישום באותיות גדולות (Uppercase)
    sign = hashed.hexdigest().upper()
    return sign, data_to_sign_raw

# --- Flask Routes ---

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
    
    # 1. הכנת הפרמטרים הנדרשים (הפעם רק פרמטרי OAuth בסיסיים)
    token_params = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code if code else "NO_CODE_PROVIDED",
        "redirect_uri": REDIRECT_URI,
        "need_refresh_token": "true",
    }

    # 2. אם חסר קוד, מציגים שגיאה פשוטה ויוצאים
    if not code:
        # למרות שזה לא המקרה שלך, משאירים את הבדיקה
        return f"""
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #fff0f0; border: 1px solid #ffdddd; border-radius: 10px;">
            <h3 style="color: #d9534f;">❌ שגיאה: לא התקבל קוד אימות</h3>
            <p>חסר פרמטר <code>?code=</code> בכתובת. ודא שהאפליקציה אושרה.</p>
        </div>
        """

    # 3. חישוב החתימה (ללא Method, V, Timestamp)
    # מעבירים רק את הפרמטרים הבסיסיים לחישוב החתימה
    calculated_sign, data_to_sign_raw = generate_hmac_sha256_sign(token_params, CLIENT_SECRET)
    token_params["sign"] = calculated_sign
    
    # 4. ביצוע בקשת ה-POST
    response = None
    tokens = {}
    response_text = "אין תגובה מהשרת."
    error_msg = "שגיאה לא ידועה."

    try:
        response = requests.post(TOKEN_URL, data=token_params)
        response_text = response.text
        tokens = response.json()
        
        # אם יש שגיאה מפורשת בתוך ה-JSON, משתמשים בה
        if 'error_msg' in tokens:
            error_msg = tokens['error_msg']
            raise Exception(error_msg) # מעבירים לבלוק ה-except
        
        response.raise_for_status() 
        
    except Exception as e:
        error_msg = str(e)
        
        # יצירת ה-HTML של נתוני הדיבוג (DEBUG) 
        log_html = f"""
        <div style="margin-top: 20px; border-top: 2px dashed #ccc; padding-top: 15px; text-align: left;">
            <h4 style="color: #007bff; text-align: center;">נתוני דיבוג (DEBUG)</h4>
            <p><strong>URL של הבקשה:</strong> <code>{TOKEN_URL}</code></p>
            
            <h5>JSON שנשלח (Form Data):</h5>
            <pre style="background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap;">{json.dumps(token_params, indent=2)}</pre>

            <h5 style="color: #d9534f;">מחרוזת גולמית לחתימה (Data to Sign):</h5>
            <pre style="background-color: #fce8e8; padding: 10px; border-radius: 5px; overflow-x: auto; word-break: break-all;">{data_to_sign_raw}</pre>
            
            <h5>החתימה שחושבה (Calculated SIGN):</h5>
            <code style="display: block; background-color: #e0e0ff; padding: 5px; border-radius: 3px; font-weight: bold; word-break: break-all;">{calculated_sign}</code>

            <h5>תוכן התגובה הגולמי:</h5>
            <pre style="background-color: #fdd; padding: 10px; border-radius: 5px; overflow-x: auto;">{response_text}</pre>
        </div>
        """
        
        # מחזירים דף שגיאה עם נתוני הדיבוג
        return f"""
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #fff0f0; border: 1px solid #ffdddd; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <h3 style="color: #d9534f;">❌ שגיאה בשליפת טוקנים: {error_msg}</h3>
            {log_html}
        </div>
        """

    # 5. קוד הצלחה אם מתקבלים טוקנים
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    # ... הצגת טוקנים בהצלחה (נותר זהה) ...
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
        </div>
        """
    else:
        # טיפול במקרה של תגובה מוצלחת (סטטוס 200) אך ללא טוקנים ב-JSON
        log_html = f"""
        <div style="margin-top: 20px; border-top: 2px dashed #ccc; padding-top: 15px; text-align: left;">
            <h4 style="color: #007bff; text-align: center;">נתוני דיבוג (DEBUG)</h4>
            <p><strong>URL של הבקשה:</strong> <code>{TOKEN_URL}</code></p>
            
            <h5>JSON שנשלח (Form Data):</h5>
            <pre style="background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap;">{json.dumps(token_params, indent=2)}</pre>

            <h5 style="color: #d9534f;">מחרוזת גולמית לחתימה (Data to Sign):</h5>
            <pre style="background-color: #fce8e8; padding: 10px; border-radius: 5px; overflow-x: auto; word-break: break-all;">{data_to_sign_raw}</pre>
            
            <h5>החתימה שחושבה (Calculated SIGN):</h5>
            <code style="display: block; background-color: #e0e0ff; padding: 5px; border-radius: 3px; font-weight: bold; word-break: break-all;">{calculated_sign}</code>

            <h5>תוכן התגובה הגולמי:</h5>
            <pre style="background-color: #fdd; padding: 10px; border-radius: 5px; overflow-x: auto;">{response_text}</pre>
        </div>
        """
        
        return f"""
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #fff8e1; border: 1px solid #ffe0b2; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <h3 style="color: #ff9800;">⚠️ לא נמצאו טוקנים בתגובה</h3>
            <p style="color: #333;">תוכן התגובה המלאה (JSON):</p>
            <pre style="text-align: left; background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto;">{json.dumps(tokens, indent=2)}</pre>
            {log_html}
        </div>
        """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
