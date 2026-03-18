import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# ================= CONFIGURATION =================
# These are pulled safely from your Render Environment Variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BOT_TOKEN = "8609038498:AAFzTSVCg2XzwAFsfc8xiA20jEIiPMIxmzc"
# =================================================

@app.route('/')
def home():
    # Render needs this to see the app is "Alive" and pass the health check
    return "MyEarn TON Server is Active", 200

@app.route('/get_user_info')
def info():
    uid = request.args.get('user_id')
    ref_by = request.args.get('ref_by')
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Check if user exists in Supabase
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    user = res.data[0] if res.data else None
    
    if not user:
        # Create new user in Supabase
        user_data = {
            "uid": uid, "bal": 0.0, "daily_count": 0, 
            "last_claim": today, "ref_by": ref_by, 
            "refs": 0, "ad_total": 0, "bonus_paid": 0
        }
        supabase.table("users").insert(user_data).execute()
        user = user_data
    
    # Reset daily limit if it's a new day
    if user.get('last_claim') != today:
        supabase.table("users").update({"daily_count": 0, "last_claim": today}).eq("uid", uid).execute()
        user['daily_count'] = 0

    return jsonify({
        "bal": round(user['bal'], 4),
        "daily_count": user['daily_count'],
        "refs": user['refs'],
        "can_daily": user.get('last_daily') != today
    })

@app.route('/reward')
def reward():
    uid = request.args.get('user_id')
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data: return jsonify({"error": "User not found"}), 404
    user = res.data[0]

    if user['daily_count'] >= 15:
        return jsonify({"error": "Limit reached"}), 400

    new_bal = user['bal'] + 0.0002
    new_ad_total = user['ad_total'] + 1
    
    # Update balance in Supabase
    supabase.table("users").update({
        "bal": new_bal, 
        "daily_count": user['daily_count'] + 1,
        "ad_total": new_ad_total
    }).eq("uid", uid).execute()

    # Referral Logic: Reward inviter once friend watches 5 ads
    if user['ref_by'] and new_ad_total == 5 and user.get('bonus_paid') == 0:
        inviter_res = supabase.table("users").select("bal, refs").eq("uid", user['ref_by']).execute()
        if inviter_res.data:
            inv_user = inviter_res.data[0]
            supabase.table("users").update({
                "bal": inv_user['bal'] + 0.005,
                "refs": inv_user['refs'] + 1
            }).eq("uid", user['ref_by']).execute()
            supabase.table("users").update({"bonus_paid": 1}).eq("uid", uid).execute()

    return jsonify({"status": "ok", "new_bal": round(new_bal, 4)})

@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    uid, wallet = data.get('user_id'), data.get('wallet')
    
    res = supabase.table("users").select("bal").eq("uid", uid).execute()
    if res.data and res.data[0]['bal'] >= 1.0:
        amt = res.data[0]['bal']
        # Set balance to 0 and log payout
        supabase.table("users").update({"bal": 0}).eq("uid", uid).execute()
        supabase.table("payouts").insert({"uid": uid, "amt": amt, "status": "Pending", "wallet": wallet}).execute()
        return jsonify({"status": "success"})
    return jsonify({"error": "Minimum 1.0 TON"}), 400

if __name__ == "__main__":
    # Locally we use port 10000 to match Render
    app.run(host="0.0.0.0", port=10000)
