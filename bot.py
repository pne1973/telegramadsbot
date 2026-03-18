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
REF_REQUIRED = 3  # <--- RESTORED REQUIREMENT

@app.route('/check_eligibility')
def check_eligibility():
    uid = request.args.get('user_id')
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    # Check if energy needs reset (24h)
    now = datetime.now()
    last_reset = datetime.fromisoformat(u['last_energy_reset'].replace('Z', '+00:00'))
    energy = u['energy']
    if now - last_reset > timedelta(hours=24):
        energy = 10
        supabase.table("users").update({"energy": 10, "last_energy_reset": now.isoformat()}).eq("uid", uid).execute()

    return jsonify({
        "bal": u['bal'],
        "energy": energy,
        "is_vip": u.get('is_vip', False),
        "ref_count": u.get('referrals_count', 0),
        "joined_channel": u.get('joined_channel', False),
        "streak": u.get('streak_days', 0)
    })

@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.get_json()
    uid, addr = str(data.get('user_id')), data.get('address')
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    # SECURITY CHECKS
    if u['referrals_count'] < REF_REQUIRED:
        return jsonify({"error": f"Locked! You need {REF_REQUIRED} referrals to withdraw."}), 403
    if u['bal'] < MIN_WITHDRAW:
        return jsonify({"error": f"Min {MIN_WITHDRAW} TON required."}), 400
    
    supabase.table("withdrawals").insert({"uid": uid, "address": addr, "amount": u['bal'], "status": "Pending"}).execute()
    supabase.table("users").update({"bal": 0.0}).eq("uid", uid).execute()
    return jsonify({"status": "ok"})

# ... (Keep existing /reward_spin, /daily_claim, and /verify_channel from previous steps)
