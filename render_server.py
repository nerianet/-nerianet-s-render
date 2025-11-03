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

# הגדרת כתובות ה-API
AUTH_URL = (
    f"https://auth.aliexpress.com/oauth/authorize?"
    f"response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state=1234"
)
# כתובת ה-REST החדשה ל-TOP API:
TOKEN_URL = "https://api-sg.aliexpress.com/rest" 
API_METHOD_PATH = "aliexpress.trade.auth.token.create" # שם המתודה בפורמט TOP

# --- פונקציה לחישוב חתימת API (Signature) באמצעות HMAC-SHA256 ---
# כעת הפונקציה מחשבת חתימה על כל פרמטרי ה-SDK
def generate_top_sign(params, secret):
    """
    מחשבת חתימת HMAC-SHA256 על פי פרוטוקול TOP API של Alibaba.
    החתימה מחושבת על כל הפרמטרים הממוינים אלפביתית (ללא ה-secret),
    כאשר ה-secret משמש כמפתח (Key) ל-HMAC.
    """
    # 1. סינון פרמטרים לחתימה
    # אין לכלול את sign, sign_method, או client_secret במחרוזת לחתימה.
    params_to_sign = {
        k: v for k, v in params.items() 
        if k not in ['sign', 'client_secret', 'sign_method'] 
    }
    
    # 2. מיון הפרמטרים לפי סדר אלפביתי
    # חשוב לוודא שכל המפתחות והערכים הם מחרוזות.
    sorted_params = sorted(params_to_sign.items())
    
    # 3. שרשור הפרמטרים לפורמט 'keyvaluekeyvalue...'
    concatenated_string = ""
    for k, v in sorted_params:
        concatenated_string += f"{k}{str(v)}"

    # 4. יצירת המחרוזת לחישוב
    data_to_sign_raw = concatenated_string
    
    # 5. חישוב חתימת HMAC-SHA256
    hashed = hmac.new(
        secret.encode('utf-8'), # SECRET משמש כמפתח (Key)
        data_to_sign_raw.encode('utf-8'), # המחרוזת לחישוב
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
    
    if not code:
        return f"""
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #fff0f0; border: 1px solid #ffdddd; border-radius: 10px;">
            <h3 style="color: #d9534f;">❌ שגיאה: לא התקבל קוד אימות</h3>
            <p>חסר פרמטר <code>?code=</code> בכתובת. ודא שהאפליקציה אושרה.</p>
        </div>
        """

    # 1. הכנת פרמטרי ה-TOP API (כולל אלו שהיו חסרים)
    token_params_post = {
        # פרמטרי TOP חובה:
        "app_key": CLIENT_ID, # שם חדש ל-CLIENT_ID
        "method": API_METHOD_PATH, # aliexpress.trade.auth.token.create
        "timestamp": str(int(time.time() * 1000)), # זמן יוניקס במילישניות
        "v": "2.0",
        "sign_method": "HMAC_SHA256",
        
        # פרמטרי ה-OAuth שנשלחים בגוף הבקשה (form data):
        "grant_type": "authorization_code",
        "client_secret": CLIENT_SECRET, # לא נכלל בחתימה, אבל נשלח ב-POST
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "need_refresh_token": "true",

        # הערה: מכיוון שזה פורמט TOP API, כל הפרמטרים הלא-חתימתיים
        # אמורים להישלח כ-JSON בתוך פרמטר 'paramter_list' או משהו דומה,
        # אך ננסה לשלוח את כולם כ-Form Data קודם, כפי שהיה ב-OAuth.
    }
    
    # 2. חישוב החתימה (כולל כל פרמטרי ה-TOP)
    # שימו לב: client_secret לא נכלל במחרוזת לחתימה!
    calculated_sign, data_to_sign_raw = generate_top_sign(token_params_post, CLIENT_SECRET)
    
    # 3. הוספת החתימה לפרמטרים הנשלחים ב-POST
    token_params_post["sign"] = calculated_sign
    
    # 4. ביצוע בקשת ה-POST
    response = None
    tokens = {}
    response_text = "אין תגובה מהשרת."
    error_msg = "שגיאה לא ידועה."

    try:
        # הפרמטרים שאנחנו שולחים ב-POST (ללא ה-client_secret, כפי שנדרש בחתימה)
        post_data = {k: v for k, v in token_params_post.items() if k != 'client_secret'}
        
        response = requests.post(TOKEN_URL, data=post_data) # שליחה ל-URL החדש
        response_text = response.text
        
        # מכיוון שזה TOP API, התגובה עשויה להיות מקוננת:
        try:
            full_response = response.json()
            if 'error_response' in full_response:
                tokens = full_response['error_response']
                error_msg = tokens.get('msg', 'Error in error_response')
                raise Exception(error_msg)
            
            # אם יש תגובה מוצלחת, היא כנראה תהיה בשם המתודה:
            response_key = API_METHOD_PATH.replace('.', '_') + '_response'
            if response_key in full_response:
                tokens = full_response[response_key]
            else:
                tokens = full_response # אם אין קינון
                
        except json.JSONDecodeError:
            raise Exception("תגובה לא תקינה (לא JSON)")
        
        # בדיקה לפרטי הטוקן בתוך התגובה
        if 'access_token' not in tokens:
             # אם הגענו לכאן, זה עדיין שגיאה
             error_msg = tokens.get('message', tokens.get('error_msg', 'Token not found in response structure'))
             raise Exception(error_msg)
        
        response.raise_for_status() 
        
    except Exception as e:
        error_msg = str(e)
        
        # יצירת ה-HTML של נתוני הדיבוג (DEBUG) 
        log_html = f"""
        <div style="margin-top: 20px; border-top: 2px dashed #ccc; padding-top: 15px; text-align: left;">
            <h4 style="color: #007bff; text-align: center;">נתוני דיבוג (DEBUG)</h4>
            <p><strong>שיטת חתימה:</strong> <code>TOP API HMAC-SHA256 (Final, Final, Final Attempt)</code></p>
            <p><strong>URL של הבקשה:</strong> <code>{TOKEN_URL}</code></p>
            <p><strong>Method:</strong> <code>{API_METHOD_PATH}</code></p>
            
            <h5>JSON שנשלח (Form Data - ללא client_secret):</h5>
            <pre style="background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap;">{json.dumps(post_data, indent=2)}</pre>

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

    if access_token and refresh_token:
        # הצגת הטוקנים
        return f"""
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 30px; background-color: #e6ffe6; border: 1px solid #ccffcc; border-radius: 15px; box-shadow: 0 6px 12px rgba(40,167,69,0.2);">
            <h3 style="color: #28a745; font-size: 1.5em;">🎉 הצלחה! הטוקנים התקבלו!</h3>
            <p style="margin-top: 20px; text-align: left; padding: 0 10%; font-size: 1.1em;">
                <b style="color: #007bff;">Access Token:</b> <code style="display: block; background-color: #fff; padding: 8px; border-radius: 4px; border: 1px solid #ccc; word-break: break-all;">{access_token}</code>
            </p>
            <p style="margin-top: 10px; text-align: left; padding: 0 10%; font-size: 1.1em;">
                <b style="color: #17a2b8;">Refresh Token:</b> <code style="display: block; background-color: #fff; padding: 8px; border-radius: 4px; border: 1px solid #ccc; word-break: break-all;">{refresh_token}</code>
            </p>
            <p style="margin-top: 25px; font-weight: bold; color: #333;">מעולה נריה! זה עבד! עכשיו תוכל להשתמש בהם לבקשות API נוספות.</p>
        </div>
        """
    else:
        # טיפול בשגיאה סופית
        log_html = f"""
        <div style="margin-top: 20px; border-top: 2px dashed #ccc; padding-top: 15px; text-align: left;">
            <h4 style="color: #007bff; text-align: center;">נתוני דיבוג (DEBUG)</h4>
            <p><strong>שיטת חתימה:</strong> <code>TOP API HMAC-SHA256 (Final, Final, Final Attempt)</code></p>
            <p><strong>URL של הבקשה:</strong> <code>{TOKEN_URL}</code></p>
            
            <h5>JSON שנשלח (Form Data - ללא client_secret):</h5>
            <pre style="background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap;">{json.dumps(post_data, indent=2)}</pre>

            <h5 style="color: #d9534f;">מחרוזת גולמית לחתימה (Data to Sign):</h5>
            <pre style="background-color: #fce8e8; padding: 10px; border-radius: 5px; overflow-x: auto; word-break: break-all;">{data_to_sign_raw}</pre>
            
            <h5>החתימה שחושבה (Calculated SIGN):</h5>
            <code style="display: block; background-color: #e0e0ff; padding: 5px; border-radius: 3px; font-weight: bold; word-break: break-all;">{calculated_sign}</code>

            <h5>תוכן התגובה הגולמי:</h5>
            <pre style="background-color: #fdd; padding: 10px; border-radius: 5px; overflow-x: auto;">{response_text}</pre>
        </div>
        """
        
        return f"""
        <div style="font-family: Arial, sans-serif; text-align: center; padding: 20px; background-color: #fff0f0; border: 1px solid #ffdddd; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            <h3 style="color: #d9534f;">❌ שגיאה בשליפת טוקנים: {error_msg}</h3>
            {log_html}
        </div>
        """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
