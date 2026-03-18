import os, random
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --- CONFIG ---
# ⚠️ Paste your actual keys here
SUPABASE_URL = "https://your-project.supabase.co" 
SUPABASE_KEY = "your-service-key"
supabase: Client = create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())

@app.route('/')
def home(): return "MyEarn Master Engine Online 🚀"

@app.route('/check_eligibility')
def check_eligibility():
    uid = str(request.args.get('user_id'))
    ref_id = request.args.get('ref') # Captures referral from start_param
    
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    
    if not res.data:
        # NEW USER: Start with 10 Energy and record who referred them
        supabase.table("users").insert({
            "uid": uid, "energy": 10, "bal": 0.0, "xp": 0, "level": 1, "referred_by": ref_id
        }).execute()
        u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
        # Update referrer count
        if ref_id:
            supabase.rpc('increment_ref', {'row_id': ref_id}).execute()
    else:
        u = res.data[0]

    # ENERGY REGEN LOGIC (1 per 30 mins)
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

    # XP & LEVEL LOGIC (RPG Enhancement)
    new_xp = u['xp'] + 10
    new_level = (new_xp // 100) + 1
    
    # MULTIPLIER (VIP 2x + Level Bonus 1% per level)
    level_bonus = 1 + (new_level * 0.01)
    vip_mult = 2.0 if u['is_vip'] else 1.0
    win = 0.0001 * vip_mult * level_bonus

    # 10% REFERRAL COMMISSION (Passive Income for Parent)
    if u['referred_by']:
        parent_id = u['referred_by']
        comm = win * 0.10
        parent_res = supabase.table("users").select("bal").eq("uid", parent_id).execute()
        if parent_res.data:
            new_p_bal = parent_res.data[0]['bal'] + comm
            supabase.table("users").update({"bal": new_p_bal}).eq("uid", parent_id).execute()

    # UPDATE USER
    supabase.table("users").update({
        "bal": u['bal'] + win, "xp": new_xp, "level": new_level, "energy": u['energy'] - 1
    }).eq("uid", uid).execute()

    return jsonify({"win": win, "new_bal": u['bal'] + win, "leveled_up": new_level > u['level']})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
