import os
import requests
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
# These are pulled from your Render Environment Variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BOT_TOKEN = "8609038498:AAFzTSVCg2XzwAFsfc8xiA20jEIiPMIxmzc"
CHANNEL_ID = "-1003836027199"
ADMIN_ID = "5401881400"
MIN_WITHDRAW = 0.001  # Minimum TON to withdraw

# --- TELEGRAM WEBHOOK ---
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    if "message" in data:
        msg = data["message"]
        uid = str(msg["from"]["id"])
        first_name = msg["from"].get("first_name", "User")
        text = msg.get("text", "")
        
        # Check for Referral Link (/start 12345)
        ref_by = None
        if text.startswith("/start ") and len(text.split(" ")) > 1:
            ref_by = text.split(" ")[1]

        # Check if user exists in Supabase
        res = supabase.table("users").select("*").eq("uid", uid).execute()
        
        if not res.data:
            # New User Registration
            supabase.table("users").insert({
                "uid": uid, 
                "bal": 0.0, 
                "referrals_count": 0, 
                "referred_by": ref_by
            }).execute()
            
            # If referred by someone, update the referrer's stats
            if ref_by and ref_by != uid:
                r = supabase.table("users").select("bal", "referrals_count").eq("uid", ref_by).execute()
                if r.data:
                    new_ref_bal = r.data[0]['bal'] + 0.001 # Bonus for referring
                    new_ref_count = r.data[0]['referrals_count'] + 1
                    supabase.table("users").update({
                        "bal": new_ref_bal, 
                        "referrals_count": new_ref_count
                    }).eq("uid", ref_by).execute()

        # Send Welcome Message with Mini App Button
        welcome_text = f"💎 *Welcome {first_name}!*\n\nEarn TON by watching ads and inviting friends.\n\n🚀 *Minimum Withdraw:* {MIN_WITHDRAW} TON"
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": uid,
            "text": welcome_text,
            "parse_mode": "Markdown",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "🚀 Open Mini App", "web_app": {"url": "https://pne1973.github.io/mini-app/"}}
                ]]
            }
        })
    return "OK", 200

# --- APP LOGIC ROUTES ---

@app.route('/check_eligibility')
def check_eligibility():
    uid = request.args.get('user_id')
    
    # 1. Check Channel Subscription
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id={CHANNEL_ID}&user_id={uid}"
    try:
        r = requests.get(url).json()
        status = r.get("result", {}).get("status")
        is_subbed = status in ['member', 'administrator', 'creator']
    except:
        is_subbed = False
        
    # 2. Get User Data from DB
    u = supabase.table("users").select("*").eq("uid", uid).execute().data
    bal = u[0]['bal'] if u else 0.0
    refs = u[0]['referrals_count'] if u else 0
    
    # Eligibility = Subscribed AND at least 3 referrals
    eligible = (is_subbed and refs >= 3)
    
    return jsonify({
        "bal": bal, 
        "is_subbed": is_subbed, 
        "ref_count": refs, 
        "eligible": eligible
    })

@app.route('/reward')
def reward():
    uid = request.args.get('user_id')
    u = supabase.table("users").select("bal").eq("uid", uid).execute().data
    if not u: return jsonify({"error": "User not found"}), 404
    
    # Ad Reward Amount
    new_bal = u[0]['bal'] + 0.0002
    supabase.table("users").update({"bal": new_bal}).eq("uid", uid).execute()
    return jsonify({"new_bal": new_bal})

@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.get_json()
    uid = str(data.get('user_id'))
    addr = data.get('address')
    
    u = supabase.table("users").select("bal").eq("uid", uid).execute().data
    if not u or u[0]['bal'] < MIN_WITHDRAW:
        return jsonify({"error": f"Minimum {MIN_WITHDRAW} TON required"}), 400
    
    amount = u[0]['bal']
    
    # 1. Add to Withdrawals Table
    supabase.table("withdrawals").insert({
        "uid": uid, 
        "address": addr, 
        "amount": amount, 
        "status": "Pending"
    }).execute()
    
    # 2. Reset User Balance to 0
    supabase.table("users").update({"bal": 0.0}).eq("uid", uid).execute()
    
    # 3. Notify Admin (You)
    admin_msg = f"💰 *NEW WITHDRAWAL REQUEST*\n\n👤 User: `{uid}`\n💎 Amount: {amount:.4f} TON\n🏦 Address: `{addr}`"
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": ADMIN_ID,
        "text": admin_msg,
        "parse_mode": "Markdown"
    })
    
    return jsonify({"status": "ok"})

@app.route('/history')
def history():
    uid = request.args.get('user_id')
    res = supabase.table("withdrawals").select("*").eq("uid", uid).order("created_at", desc=True).execute().data
    return jsonify(res)

@app.route('/leaderboard')
def leaderboard():
    # Get top 10 users by balance
    res = supabase.table("users").select("uid", "bal").order("bal", desc=True).limit(10).execute().data
    formatted = []
    for u in res:
        # Hide middle of UID for privacy (e.g., 540***00)
        mask_uid = str(u['uid'])[:3] + "***" + str(u['uid'])[-2:]
        formatted.append({"name": mask_uid, "bal": u['bal']})
    return jsonify(formatted)

@app.route('/broadcast', methods=['POST'])
def broadcast():
    data = request.get_json()
    if str(data.get("admin_id")) != ADMIN_ID:
        return jsonify({"error": "Unauthorized"}), 403
    
    msg = data.get("message")
    users = supabase.table("users").select("uid").execute().data
    
    count = 0
    for u in users:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": u['uid'],
                "text": f"📢 *ANNOUNCEMENT*\n\n{msg}",
                "parse_mode": "Markdown"
            })
            count += 1
            time.sleep(0.05) # Prevent Telegram flood limits
        except:
            continue
            
    return jsonify({"total": count})

if __name__ == "__main__":
    # Render uses port 10000 by default
    app.run(host="0.0.0.0", port=10000)