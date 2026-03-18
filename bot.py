import os, requests, time, random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# --- CONFIG ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BOT_TOKEN = "8609038498:AAFzTSVCg2XzwAFsfc8xiA20jEIiPMIxmzc"
ADMIN_ID = "5401881400"
CHANNEL_ID = "-1003836027199"
MIN_WITHDRAW = 0.05 

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    if "message" in data:
        msg = data["message"]
        uid = str(msg["from"]["id"])
        text = msg.get("text", "")
        ref_by = text.split(" ")[1] if text.startswith("/start ") and len(text.split(" ")) > 1 else None

        res = supabase.table("users").select("*").eq("uid", uid).execute()
        if not res.data:
            supabase.table("users").insert({"uid": uid, "bal": 0.0, "referrals_count": 0, "weekly_refs": 0, "referred_by": ref_by}).execute()
            if ref_by and ref_by != uid:
                r = supabase.table("users").select("*").eq("uid", ref_by).execute()
                if r.data:
                    supabase.table("users").update({
                        "bal": r.data[0]['bal'] + 0.001,
                        "referrals_count": r.data[0]['referrals_count'] + 1,
                        "weekly_refs": r.data[0]['weekly_refs'] + 1
                    }).eq("uid", ref_by).execute()
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": ref_by, "text": "👥 New Referral! Your weekly score increased!"})

        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": uid, "text": "💎 *Welcome to MyEarn TON V4*", "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": [[{"text": "🚀 Open App", "web_app": {"url": "https://pne1973.github.io/mini-app/"}}]]}
        })
    return "OK", 200

@app.route('/reward_spin')
def reward_spin():
    uid = request.args.get('user_id')
    u = supabase.table("users").select("bal").eq("uid", uid).execute().data[0]
    roll = random.random()
    # Logic: 80% small, 15% medium, 5% Jackpot
    win = 0.0001 if roll < 0.8 else 0.0005 if roll < 0.95 else 0.0025
    new_bal = u['bal'] + win
    supabase.table("users").update({"bal": new_bal}).eq("uid", uid).execute()
    return jsonify({"new_bal": new_bal, "win": win, "type": "Jackpot" if win == 0.0025 else "Win"})

@app.route('/daily_claim')
def daily_claim():
    uid = request.args.get('user_id')
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    now = datetime.now()
    if u['last_checkin']:
        last = datetime.fromisoformat(u['last_checkin'].replace('Z', '+00:00'))
        if now - last < timedelta(hours=24): return jsonify({"error": "Wait 24h"}), 400
        streak = u['streak_days'] + 1 if now - last < timedelta(hours=48) else 1
    else: streak = 1
    
    reward = min(streak, 7) * 0.0001
    new_bal = u['bal'] + reward
    supabase.table("users").update({"bal": new_bal, "streak_days": streak, "last_checkin": now.isoformat()}).eq("uid", uid).execute()
    return jsonify({"new_bal": new_bal, "streak": streak, "reward": reward})

@app.route('/referral_leaderboard')
def ref_leaderboard():
    res = supabase.table("users").select("uid", "weekly_refs").order("weekly_refs", desc=True).limit(5).execute().data
    return jsonify([{"name": str(u['uid'])[:4]+"***", "count": u['weekly_refs']} for u in res])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
