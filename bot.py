import os
import requests
import urllib.parse
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# ================= CONFIGURATION =================
# Double-check these in Render Settings -> Environment
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BOT_TOKEN = "8609038498:AAFzTSVCg2XzwAFsfc8xiA20jEIiPMIxmzc"
WEB_APP_URL = "https://pne1973.github.io/mini-app/"
# =================================================

@app.route('/')
def home():
    print("LOG: Someone visited the Home Page")
    return "Server is Live", 200

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    # THIS LINE MUST APPEAR IN RENDER LOGS IF TELEGRAM IS WORKING
    print("--- DEBUG: REQUEST RECEIVED AT /WEBHOOK ---")
    
    try:
        data = request.get_json(force=True)
        print(f"--- DEBUG: DATA FROM TELEGRAM: {data}")
        
        if data and "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")
            
            if "/start" in text:
                print(f"LOG: Handling /start for user {chat_id}")
                # Extract ref if present
                parts = text.split(" ")
                ref_id = parts[1] if len(parts) > 1 else None
                send_welcome(chat_id, ref_id)
        
    except Exception as e:
        print(f"--- ERROR IN WEBHOOK: {e}")
        
    return "OK", 200

def send_welcome(chat_id, ref_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Safe URL Encoding
    if ref_id:
        params = {'ref': ref_id}
        final_app_url = f"{WEB_APP_URL}?{urllib.parse.urlencode(params)}"
    else:
        final_app_url = WEB_APP_URL

    payload = {
        "chat_id": chat_id,
        "text": "🚀 *Welcome to MyEarn TON!*\n\nTap below to launch the app.",
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
    
    res = requests.post(url, json=payload)
    print(f"LOG: Telegram Send Status: {res.status_code} - {res.text}")

@app.route('/get_user_info')
def info():
    uid = request.args.get('user_id')
    ref_by = request.args.get('ref_by')
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        res = supabase.table("users").select("*").eq("uid", uid).execute()
        user = res.data[0] if res.data else None
        
        if not user:
            new_user = {"uid": uid, "bal": 0.0, "daily_count": 0, "last_claim": today, "ref_by": ref_by}
            supabase.table("users").insert(new_user).execute()
            user = new_user
        
        return jsonify({"bal": round(user.get('bal', 0), 4), "daily_count": user.get('daily_count', 0)})
    except Exception as e:
        print(f"DB ERROR: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/reward')
def reward():
    uid = request.args.get('user_id')
    try:
        res = supabase.table("users").select("*").eq("uid", uid).execute()
        user = res.data[0]
        new_bal = user['bal'] + 0.0002
        supabase.table("users").update
