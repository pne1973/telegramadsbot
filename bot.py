import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ================= CONFIGURATION =================
BOT_TOKEN = "8609038498:AAFzTSVCg2XzwAFsfc8xiA20jEIiPMIxmzc" 
WEB_APP_URL = "https://pne1973.github.io/mini-app/"
ADMIN_HANDLE = "@pine1971" 
ADMIN_PASSWORD = "sporting" 
# =================================================

db = {}

def send_welcome(chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": (
            "💎 *Welcome to MyEarn TON Pro!*\n\n"
            "The #1 platform to earn TON by completing simple tasks. "
            "Watch ads, invite friends, and grow your balance!\n\n"
            "📊 *Earnings:*\n"
            "• 0.0002 TON per Ad View\n"
            "• 0.0005 TON Daily Login\n"
            "• 0.0050 TON per Referral\n\n"
            "Ready to start? Click below! 👇"
        ),
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "🚀 OPEN MINI APP", "web_app": {"url": WEB_APP_URL}}],
                [{"text": "👥 Invite Friends", "switch_inline_query": "I am earning TON here! Join me:"},
                 {"text": "💬 Support", "url": f"https://t.me/{ADMIN_HANDLE}"}]
            ]
        }
    }
    requests.post(url, json=payload)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # This line will show exactly what Telegram sends in your Render Logs
    print(f"DEBUG: Received update: {data}") 
    
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        
        if "/start" in text:
            print(f"DEBUG: Sending welcome to {chat_id}")
            send_welcome(chat_id)
            
    return "OK", 200

@app.route('/get_user_info')
def info():
    uid = request.args.get('user_id')
    ref_by = request.args.get('ref_by')
    today = datetime.now().strftime("%Y-%m-%d")
    if uid not in db:
        db[uid] = {"bal": 0.0, "daily_count": 0, "last_claim": today, "last_daily": "", "refs": 0, "ad_total": 0, "ref_by": ref_by, "bonus_paid": False, "payouts": []}
    if db[uid]["last_claim"] != today:
        db[uid]["daily_count"] = 0
        db[uid]["last_claim"] = today
    return jsonify({"bal": float(f"{db[uid]['bal']:.4f}"), "daily_count": db[uid]["daily_count"], "refs": db[uid]["refs"], "payouts": db[uid]["payouts"][-3:], "can_daily": db[uid]["last_daily"] != today})

@app.route('/reward')
def reward():
    uid = request.args.get('user_id')
    if uid in db:
        if db[uid]["daily_count"] >= 15: return jsonify({"error": "Limit"}), 400
        db[uid]["bal"] += 0.0002
        db[uid]["daily_count"] += 1
        db[uid]["ad_total"] += 1
        ref_id = db[uid].get("ref_by")
        if ref_id and ref_id in db and db[uid]["ad_total"] == 5 and not db[uid]["bonus_paid"]:
            db[ref_id]["bal"] += 0.005
            db[ref_id]["refs"] += 1
            db[uid]["bonus_paid"] = True
        return jsonify({"status": "ok", "new_bal": f"{db[uid]['bal']:.4f}"})
    return jsonify({"error": "Error"}), 404

@app.route('/daily_claim')
def daily_claim():
    uid = request.args.get('user_id')
    today = datetime.now().strftime("%Y-%m-%d")
    if uid in db:
        if db[uid].get("last_daily") == today: return jsonify({"error": "Already claimed"}), 400
        db[uid]["bal"] += 0.0005
        db[uid]["last_daily"] = today
        return jsonify({"status": "ok", "new_bal": f"{db[uid]['bal']:.4f}"})
    return jsonify({"error": "User not found"}), 404

@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    uid, wallet = data.get('user_id'), data.get('wallet')
    if uid in db and db[uid]["bal"] >= 1.0:
        amt = db[uid]["bal"]
        db[uid]["bal"] = 0 
        db[uid]["payouts"].append({"amt": float(f"{amt:.4f}"), "status": "Pending", "date": datetime.now().strftime("%b %d")})
        return jsonify({"status": "success"})
    return jsonify({"error": "Min 1.0 TON"}), 400

@app.route('/admin_pay')
def admin_pay():
    if request.args.get('pass') != ADMIN_PASSWORD: return "Unauthorized", 401
    uid = request.args.get('user_id')
    if uid in db and db[uid]["payouts"]:
        for p in db[uid]["payouts"]:
            if p["status"] == "Pending": p["status"] = "Paid"
        return "Paid!"
    return "Not found", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
