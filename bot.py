import random, requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --- CONFIG ---
SUPABASE_URL = "YOUR_URL"
SUPABASE_KEY = "YOUR_KEY"
BOT_TOKEN = "YOUR_TOKEN"
ADMIN_ID = "YOUR_ID"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/check_eligibility')
def check_eligibility():
    uid = str(request.args.get('user_id'))
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    # Energy Regen Logic (1 every 30m)
    now = datetime.now()
    last_reset = datetime.fromisoformat(u['last_energy_reset'].replace('Z', '+00:00'))
    mins_passed = int((now - last_reset).total_seconds() / 60)
    energy_to_add = mins_passed // 30
    
    new_energy = min(10, u['energy'] + energy_to_add)
    sec_until_next = 1800 - ((now - last_reset).total_seconds() % 1800) if new_energy < 10 else 0

    return jsonify({
        "bal": u['bal'], "energy": new_energy, "xp": u['xp'], "level": u['level'],
        "tickets": u['tickets'], "next_energy_in": sec_until_next, "is_vip": u['is_vip']
    })

@app.route('/reward_spin', methods=['POST'])
def reward_spin():
    data = request.get_json()
    uid = str(data.get('user_id'))
    use_ticket = data.get('use_ticket', False)
    
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    if u['energy'] <= 0 and not use_ticket: return jsonify({"error": "No energy"}), 403

    # XP & Level Logic
    new_xp = u['xp'] + 10
    new_level = (new_xp // 100) + 1
    leveled_up = new_level > u['level']
    
    # Multiplier Logic
    mult = (1 + (new_level * 0.01)) * (2.0 if u['is_vip'] else 1.0)
    win = (0.0001 if random.random() < 0.8 else 0.0005) * mult
    if use_ticket: win = 0.001 

    # 10% Referral Commission
    if u['referred_by']:
        ref_id = u['referred_by']
        comm = win * 0.10
        ref_data = supabase.table("users").select("bal").eq("uid", ref_id).execute().data
        if ref_data:
            supabase.table("users").update({"bal": ref_data[0]['bal'] + comm}).eq("uid", ref_id).execute()

    # Update Database
    upd = {"bal": u['bal'] + win, "xp": new_xp, "level": new_level}
    if use_ticket: upd["tickets"] = u['tickets'] - 1
    else: upd["energy"] = u['energy'] - 1
    
    supabase.table("users").update(upd).eq("uid", uid).execute()
    return jsonify({"win": win, "level": new_level, "leveled_up": leveled_up})

@app.route('/admin_stats')
def admin_stats():
    if request.args.get('admin_id') != ADMIN_ID: return "No", 403
    users = supabase.table("users").select("uid", count="exact").execute().count
    paid = sum([x['amount'] for x in supabase.table("withdrawals").select("amount").eq("status", "Paid").execute().data])
    vips = supabase.table("users").select("uid").eq("is_vip", True).execute().count
    return jsonify({"users": users, "paid": paid, "profit": (vips * 0.5) - paid})

if __name__ == '__main__':
    app.run(port=5000)
