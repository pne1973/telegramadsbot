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
# Ensure these are set in Render -> Environment
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BOT_TOKEN = "8609038498:AAFzTSVCg2XzwAFsfc8xiA20jEIiPMIxmzc"
WEB_APP_URL = "https://pne1973.github.io/mini-app/"
# =================================================

@app.route('/')
def home():
    return "Bot Server is Online", 200

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json(force=True)
    
    if data and "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if "/start" in text:
            # Handle referrals: /start 12345
            parts = text.split(" ")
            ref_id = parts[1] if len(parts) > 1 else None
            send_welcome(chat_id, ref_id)
            
    return "OK", 200

def send_welcome(chat_id, ref_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # 1. Safely encode the URL for the Mini App
    if ref_id:
        params = {'ref': ref_id}
        final_app_url = f"{WEB_APP_URL}?{urllib.parse.urlencode(params)}"
    else:
        final_app_url = WEB_APP_URL

    # 2. Correct Keyboard Structure
    payload = {
        "chat_id": chat_id,
        "text": "💎 *Welcome to MyEarn TON!*\n\nWatch ads to earn TON and invite friends for bonuses.\nMinimum withdrawal: 1.0 TON.",
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "🚀 Open Mini App", 
                        "web_app": {"url": final_app_url}
                    }
                ]
            ]
        }
    }
    
    # 3. Send and Print Result to Render Logs
    response = requests.post(url, json=payload)
    print(f"Telegram Response: {response.status_code} - {response.text}")

@app.route('/get_user_info')
def info():
    uid = request.args.get('user_id')
    ref_by = request.args.get('ref_by')
    today = datetime.now().strftime("%Y-%m-%d")
    
    if not uid:
        return jsonify({"error": "No User ID"}), 400

    # Get user from Supabase
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    user = res.data[0] if res.data else None
    
    if not user:
        # Create new user
        new_user = {
            "uid": uid, 
            "bal": 0.0, 
            "daily_count": 0, 
            "last_claim": today, 
            "ref_by": ref_by, 
            "refs": 0, 
            "ad_total": 0, 
            "bonus_paid": 0
        }
        supabase.table("users").insert(new_user).execute()
        user = new_user
    
    # Reset daily limit if it's a new day
    if user.get('last_claim') != today:
        supabase.table("users").update({"daily_count": 0, "last_claim": today}).eq("uid", uid).execute()
        user['daily_count'] = 0

    return jsonify({
        "bal": round(user.get('bal', 0), 4),
        "daily_count": user.get('daily_count', 0),
        "refs": user.get('refs', 0)
    })

@app.route('/reward')
def reward():
    uid = request.args.get('user_id')
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data: return jsonify({"error": "No user"}), 404
    user = res.data[0]

    if user['daily_count'] >= 15:
        return jsonify({"error": "Limit reached"}), 400

    new_bal = user['bal'] + 0.0002
    supabase.table("users").update({
        "bal": new_bal, 
        "daily_count": user['daily_count'] + 1
    }).eq("uid", uid).execute()

    return jsonify({"status": "ok", "new_bal": round(new_bal, 4)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
