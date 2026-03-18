import os
import sqlite3
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
DB_FILE = "database.db"
# =================================================

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Create tables for persistent storage
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (uid TEXT PRIMARY KEY, bal REAL, daily_count INTEGER, 
                  last_claim TEXT, last_daily TEXT, refs INTEGER, 
                  ad_total INTEGER, ref_by TEXT, bonus_paid INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payouts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, 
                  amt REAL, status TEXT, date TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def send_welcome(chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": (
            "💎 *Welcome to MyEarn TON Pro!*\n\n"
            "The #1 platform to earn TON by completing simple tasks. [cite: 2]\n\n"
            "📊 *Earnings:*\n"
            "• 0.0002 TON per Ad View\n"
            "• 0.0005 TON Daily Login\n"
            "• 0.0050 TON per Referral\n\n"
            "Ready to start? Click below! 👇 [cite: 3]"
        ),
        "parse_mode": "Markdown",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "🚀 OPEN MINI APP", "web_app": {"url": WEB_APP_URL}}],
                [{"text": "👥 Invite Friends", "switch_inline_query": "I am earning TON here! Join me: [cite: 4]"}],
                [{"text": "💬 Support", "url": f"https://t.me/{ADMIN_HANDLE}"}]
            ]
        }
    }
    requests.post(url, json=payload)

@app.route('/get_user_info')
def info():
    uid = request.args.get('user_id')
    ref_by = request.args.get('ref_by')
    today = datetime.now().strftime("%Y-%m-%d")
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE uid = ?', (uid,)).fetchone()
    
    if not user:
        # Create new user and track referral [cite: 6]
        conn.execute('''INSERT INTO users (uid, bal, daily_count, last_claim, last_daily, refs, ad_total, ref_by, bonus_paid) 
                        VALUES (?, 0.0, 0, ?, "", 0, 0, ?, 0)''', (uid, today, ref_by))
        conn.commit()
        user = conn.execute('SELECT * FROM users WHERE uid = ?', (uid,)).fetchone()

    if user['last_claim'] != today:
        conn.execute('UPDATE users SET daily_count = 0, last_claim = ? WHERE uid = ?', (today, uid))
        conn.commit()

    payouts = conn.execute('SELECT amt, status, date FROM payouts WHERE uid = ? ORDER BY id DESC LIMIT 3', (uid,)).fetchall()
    conn.close()

    return jsonify({
        "bal": round(user['bal'], 4),
        "daily_count": user['daily_count'],
        "refs": user['refs'],
        "can_daily": user['last_daily'] != today,
        "payouts": [dict(p) for p in payouts]
    })

@app.route('/reward')
def reward():
    uid = request.args.get('user_id')
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE uid = ?', (uid,)).fetchone()
    
    if not user: return jsonify({"error": "User not found"}), 404
    if user['daily_count'] >= 15: return jsonify({"error": "Limit"}), 400 [cite: 7]

    new_bal = user['bal'] + 0.0002
    new_ad_total = user['ad_total'] + 1
    
    conn.execute('UPDATE users SET bal = ?, daily_count = daily_count + 1, ad_total = ? WHERE uid = ?', (new_bal, new_ad_total, uid))
    
    # Referral bonus logic: Paid after 5 ads watched [cite: 8]
    if user['ref_by'] and new_ad_total == 5 and not user['bonus_paid']:
        conn.execute('UPDATE users SET bal = bal + 0.005, refs = refs + 1 WHERE uid = ?', (user['ref_by'],))
        conn.execute('UPDATE users SET bonus_paid = 1 WHERE uid = ?', (uid,))
        
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "new_bal": f"{new_bal:.4f}"})

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if "message" in data:
        chat_id = data["message"]["chat"]["id"] [cite: 5]
        text = data["message"].get("text", "")
        if "/start" in text:
            send_welcome(chat_id)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
