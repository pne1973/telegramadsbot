import os, random, requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --- CONFIG ---
SUPABASE_URL = "https://your-project.supabase.co" # ⚠️ Update this
SUPABASE_KEY = "your-service-key"              # ⚠️ Update this
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def home(): return "MyEarn Master Backend Online 🚀"

@app.route('/check_eligibility')
def check_eligibility():
    uid = str(request.args.get('user_id'))
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    
    if not res.data:
        ref = request.args.get('ref')
        supabase.table("users").insert({"uid": uid, "referred_by": ref, "energy": 10}).execute()
        u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    else:
        u = res.data[0]

    # Energy Regen (1 per 30 mins)
    now = datetime.now()
    last_reset = datetime.fromisoformat(u['last_energy_reset'].replace('Z', '+00:00'))
    mins_passed = int((now - last_reset).total_seconds() / 60)
    energy_to_add = mins_passed // 30
    new_energy = min(10, u['energy'] + energy_to_add)

    return jsonify({
        "bal": u['bal'], "energy": new_energy, "xp": u['xp'], 
        "level": u['level'], "is_vip": u['is_vip']
    })

@app.route('/reward_spin', methods=['POST'])
def reward_spin():
    data = request.get_json()
    uid = str(data.get('user_id'))
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    if u['energy'] <= 0: return jsonify({"error": "No energy"}), 403

    # XP & Level Logic (RPG Feature)
    new_xp = u['xp'] + 10
    new_level = (new_xp // 100) + 1
    
    # Multiplier (VIP 2x + Level Bonus 1% per level)
    mult = (1 + (new_level * 0.01)) * (2.0 if u['is_vip'] else 1.0)
    win = 0.0001 * mult

    # 10% Referral Commission (Passive Income Feature)
    if u['referred_by']:
        ref_id = u['referred_by']
        comm = win * 0.10
        ref_user = supabase.table("users").select("bal").eq("uid", ref_id).execute().data
        if ref_user:
            supabase.table("users").update({"bal": ref_user[0]['bal'] + comm}).eq("uid", ref_id).execute()

    # Update User
    supabase.table("users").update({
        "bal": u['bal'] + win, "xp": new_xp, "level": new_level, "energy": u['energy'] - 1
    }).eq("uid", uid).execute()

    return jsonify({"win": win, "new_bal": u['bal'] + win, "leveled_up": new_level > u['level']})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
