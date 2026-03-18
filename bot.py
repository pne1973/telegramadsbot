import os, requests, time
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
BOT_TOKEN = "8609038498:AAFzTSVCg2XzwAFsfc8xiA20jEIiPMIxmzc"
CHANNEL_ID = "-1003836027199"
ADMIN_ID = "5401881400"

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
            supabase.table("users").insert({"uid": uid, "bal": 0.0, "referrals_count": 0, "referred_by": ref_by}).execute()
            if ref_by and ref_by != uid:
                r = supabase.table("users").select("bal", "referrals_count").eq("uid", ref_by).execute()
                if r.data:
                    supabase.table("users").update({"bal": r.data[0]['bal'] + 0.001, "referrals_count": r.data[0]['referrals_count'] + 1}).eq("uid", ref_by).execute()

        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": uid, "text": "💎 *Welcome to MyEarn TON!*\nEarn by watching ads.", "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": [[{"text": "🚀 Open App", "web_app": {"url": "https://pne1973.github.io/mini-app/"}}]]}
        })
    return "OK", 200

@app.route('/check_eligibility')
def check_eligibility():
    uid = request.args.get('user_id')
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id={CHANNEL_ID}&user_id={uid}"
    try:
        r = requests.get(url).json()
        is_subbed = r.get("result", {}).get("status") in ['member', 'administrator', 'creator']
    except: is_subbed = False
    u = supabase.table("users").select("*").eq("uid", uid).execute().data
    bal = u[0]['bal'] if u else 0.0
    refs = u[0]['referrals_count'] if u else 0
    return jsonify({"bal": bal, "is_subbed": is_subbed, "ref_count": refs, "eligible": (is_subbed and refs >= 3)})

@app.route('/reward')
def reward():
    uid = request.args.get('user_id')
    u = supabase.table("users").select("bal").eq("uid", uid).execute().data
    new_bal = u[0]['bal'] + 0.0002
    supabase.table("users").update({"bal": new_bal}).eq("uid", uid).execute()
    return jsonify({"new_bal": new_bal})

@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.get_json()
    uid, addr = str(data.get('user_id')), data.get('address')
    u = supabase.table("users").select("bal").eq("uid", uid).execute().data
    if not u or u[0]['bal'] < 0.001: return jsonify({"error": "Min 0.001 TON required"}), 400
    
    amount = u[0]['bal']
    supabase.table("withdrawals").insert({"uid": uid, "address": addr, "amount": amount}).execute()
    supabase.table("users").update({"bal": 0.0}).eq("uid", uid).execute()
    
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": ADMIN_ID, "text": f"💰 *NEW WITHDRAWAL*\nUser: `{uid}`\nAmount: {amount} TON\nAddress: `{addr}`", "parse_mode": "Markdown"
    })
    return jsonify({"status": "ok"})

@app.route('/history')
def history():
    uid = request.args.get('user_id')
    res = supabase.table("withdrawals").select("*").eq("uid", uid).order("created_at", desc=True).execute().data
    return jsonify(res)

@app.route('/broadcast', methods=['POST'])
def broadcast():
    data = request.get_json()
    if str(data.get("admin_id")) != ADMIN_ID: return jsonify({"error": "No"}), 403
    users = supabase.table("users").select("uid").execute().data
    for u in users:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": u['uid'], "text": data.get("message"), "parse_mode": "Markdown"})
    return jsonify({"total": len(users)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
