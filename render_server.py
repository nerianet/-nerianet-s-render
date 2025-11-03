from flask import Flask, request, redirect
import requests
import os
import hashlib
import hmac
import time
import json
import logging


app = Flask(__name__)


# Configure logging to STDOUT so Render shows it
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


# Load configuration from environment (preferred) with fallbacks (not recommended for prod)
CLIENT_ID = os.environ.get('ALI_CLIENT_ID', '520232')
CLIENT_SECRET = os.environ.get('ALI_CLIENT_SECRET', 'k0UqqVGIldwk5pZhMwGJGZOQhQpvZsf2')
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'https://nerianet-render-callback-ali.onrender.com/callback')


API_BASE = 'https://api-sg.aliexpress.com'
API_METHOD_PATH = '/auth/token/create'
TOKEN_URL = f"{API_BASE}/rest{API_METHOD_PATH}"


# Helper: compute sign exactly as required by TOP protocol variant used here
def generate_top_sign(params: dict, secret: str):
"""
HMAC-SHA256 sign with pattern: client_secret + concat(sorted(key+value...)) + client_secret
Returns (SIGN_upper_hex, raw_string_used_for_signing)
"""
# Exclude keys that should not be part of signature
filtered = {k: v for k, v in params.items() if k not in ('sign', 'client_secret')}
# Sort keys by ASCII (default Python sort does this)
items = sorted(filtered.items(), key=lambda x: x[0])
concatenated = ''.join(f"{k}{v}" for k, v in items)
raw = f"{secret}{concatenated}{secret}"
mac = hmac.new(secret.encode('utf-8'), raw.encode('utf-8'), hashlib.sha256)
sign = mac.hexdigest().upper()
return sign, raw


@app.route('/')
def index():
# AliExpress OAuth authorize URL — user clicks it to approve
auth_url = (
f"https://auth.aliexpress.com/oauth/authorize?response_type=code"
f"&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&state=render"
)
return f"""
<div style='font-family: Arial, sans-serif; text-align: center; padding: 30px;'>
<h2>AliExpress OAuth callback on Render</h2>
<p>Click to authenticate and grant authorization to your AliExpress app.</p>
<a href='{auth_url}' style='display:inline-block;padding:12px 20px;background:#FF6600;color:#fff;border-radius:8px;text-decoration:none;'>Authorize AliExpress</a>
<p style='margin-top:20px;color:#666;font-size:0.9em;'>After approving, AliExpress will redirect back to <code>{REDIRECT_URI}</code>.</p>
</div>
"""


@app.route('/healthz')
def healthz():
return 'OK', 200


@app.route('/callback')
def callback():
code = request.args.get('code')
error = request.args.get('error')
if error:
return f"Error from provider: {error}", 400
if not code:
return 'No authorization code found in query parameters.', 400


# Build params for token request
timestamp = str(int(time.time() * 1000))
app.run(host='0.0.0.0', port=port)
