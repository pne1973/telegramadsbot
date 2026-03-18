import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# ================= CONFIGURATION =================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BOT_TOKEN = "8609038498:AAFzTSVCg2XzwAFsfc8xiA20jEIiPMIxmzc"
WEB_APP_URL = "https://pne1973.github.io/mini-app/"
# =================================================

@app.route('/')
def home():
    return "Server is Awake!", 200

# THIS WAS MISSING: The actual webhook receiver
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if "/start" in text:
            # Extract referral ID if present (e.g., /start 12345)
            ref_id = text.split(" ")[1] if len(text.split(" ")) > 1 else None
            send_welcome(chat_id, ref_id)
            
    return "OK", 200

def send_welcome(chat_id, ref_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Create the referral link to show the user
    # If they were referred, you can pass that info to the WebApp URL
    webapp_url = f"{WEB_APP_URL}?ref={ref_id}" if ref_id else WEB_APP_URL
    
    payload = {
        "chat_id": chat_id,
        "text": "💎 *Welcome to MyEarn TON Pro!*\n\nStart earning TON by watching ads and inviting friends.",
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "🚀 Open Mini App", "web_app": {"url": webapp_url}}
            ]]
        }
    }
    requests.post(url, json=payload)

@app.route('/get_user_info')
def info():
    uid = request.args.get('user_id')
    # ... rest of your existing Supabase info logic ...
    return jsonify({"status": "ok"}) # Placeholder for your logic

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
