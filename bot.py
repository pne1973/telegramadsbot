import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# ================= CONFIGURATION =================
# These are pulled from your Render Environment Variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BOT_TOKEN = "8609038498:AAFzTSVCg2XzwAFsfc8xiA20jEIiPMIxmzc"
WEB_APP_URL = "https://pne1973.github.io/mini-app/"
# =================================================

@app.route('/')
def home():
    # This keeps Render happy and shows the server is alive
    return "MyEarn TON Server is Online", 200

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    
    # Check if this is a standard message (like /start)
    if data and "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if "/start" in text:
            # Extract referral ID if user joined via link (e.g. /start 12345)
            parts = text.split(" ")
            ref_id = parts[1] if len(parts) > 1 else None
            
            send_welcome(chat_id, ref_id)
            
    return "OK", 200

def send_welcome(chat_id, ref_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # If there's a referral, we attach it to the WebApp URL
    final_app_url = f"{WEB_APP_URL}?ref={ref_id}" if ref_id else WEB_APP_URL
    
    payload = {
        "chat_id": chat_id,
        "text": "💎 *Welcome to MyEarn TON!*\n\nWatch ads to earn TON and invite friends for huge bonuses. Minimum withdrawal is 1.0 TON.",
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [[
                {
                    "text": "🚀 Open Mini App", 
                    "web_app": {"url": final_app_url}
                }
            ]]
        }
    }
    requests.post(url, json=payload)

@app.route('/get_user_info')
def info():
    uid = request.args.get('user_id')
    ref_by = request.args.get('ref_by')
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Get or Create User
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    user = res.data[0] if res.data else None
    
    if not user:
        user_data = {
            "uid": uid, "bal": 0.0, "daily_count":
