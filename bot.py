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
REF_REQUIRED = 3

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
            supabase.table("users").insert({
                "uid": uid, "bal": 0.0, "referrals_count": 0, "energy": 10, "referred_by": ref_by
            }).execute()
            if ref_by and ref_by != uid:
                r = supabase.table("users").select("*").eq("uid", ref_by).execute()
                if r.data:
                    supabase.table("users").update({
                        "bal": r.data[0]['bal'] + 0.001,
                        "referrals_count": r.data[0]['referrals_count'] + 1
                    }).eq("uid", ref_by).execute()
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": ref_by, "text": "👥 New Referral! +0.001 TON"})

        welcome = "💎 *Welcome to MyEarn TON V6*\n\nEarn TON by watching ads and inviting friends!"
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": uid, "text": welcome, "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": [[{"text": "🚀 Open App", "web_app": {"url": "https://pne1973.github.io/mini-app/"}}]]}
        })
    return "OK", 200

@app.route('/check_eligibility')
def check_eligibility():
    uid = request.args.get('user_id')
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    now = datetime.now()
    last_reset = datetime.fromisoformat(u['last_energy_reset'].replace('Z', '+00:00'))
    energy = u['energy']
    if now - last_reset > timedelta(hours=24):
        energy = 10
        supabase.table("users").update({"energy": 10, "last_energy_reset": now.isoformat()}).eq("uid", uid).execute()
    return jsonify({"bal": u['bal'], "energy": energy, "is_vip": u.get('is_vip', False), "ref_count": u.get('referrals_count', 0), "joined_channel": u.get('joined_channel', False)})

@app.route('/reward_spin')
def reward_spin():
    uid = request.args.get('user_id')
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    if not u['is_vip'] and u['energy'] <= 0: return jsonify({"error": "No energy!"}), 403
    
    mult = 2.0 if u['is_vip'] else 1.0
    win = (0.0001 if random.random() < 0.8 else 0.0005 if random.random() < 0.95 else 0.0025) * mult
    new_energy = u['energy'] if u['is_vip'] else u['energy'] - 1
    supabase.table("users").update({"bal": u['bal'] + win, "energy": new_energy, "last_spin": datetime.now().isoformat()}).eq("uid", uid).execute()
    return jsonify({"win": win, "new_bal": u['bal'] + win, "energy": new_energy})

@app.route('/daily_claim')
def daily_claim():
    uid = request.args.get('user_id')
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    now = datetime.now()
    if u['last_checkin']:
        last = datetime.fromisoformat(u['last_checkin'].replace('Z', '+00:00'))
        if now - last < timedelta(hours=24): return jsonify({"error": "Wait 24h"}), 400
    reward = 0.0005
    supabase.table("users").update({"bal": u['bal'] + reward, "last_checkin": now.isoformat()}).eq("uid", uid).execute()
    return jsonify({"reward": reward})

@app.route('/verify_channel')
def verify_channel():
    uid = request.args.get('user_id')
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    if u['joined_channel']: return jsonify({"error": "Done"}), 400
    r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id={CHANNEL_ID}&user_id={uid}").json()
    if r.get("result", {}).get("status") in ['member', 'administrator', 'creator']:
        supabase.table("users").update({"bal": u['bal'] + 0.005, "joined_channel": True}).eq("uid", uid).execute()
        return jsonify({"msg": "Claimed!"})
    return jsonify({"error": "Not joined"}), 400

@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.get_json()
    uid, addr = str(data.get('user_id')), data.get('address')
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    if u['referrals_count'] < REF_REQUIRED: return jsonify({"error": f"Need {REF_REQUIRED} refs"}), 403
    if u['bal'] < MIN_WITHDRAW: return jsonify({"error": f"Min {MIN_WITHDRAW}"}), 400
    supabase.table("withdrawals").insert({"uid": uid, "address": addr, "amount": u['bal']}).execute()
    supabase.table("users").update({"bal": 0.0}).eq("uid", uid).execute()
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
