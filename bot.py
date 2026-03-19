import os, datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# --- CONFIG ---
SUPABASE_URL = "https://your-project.supabase.co" 
SUPABASE_KEY = "your-service-role-key"
ADMIN_ID = "5401881400" 

supabase: Client = create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())

@app.route('/check_eligibility')
def check_eligibility():
    uid = str(request.args.get('user_id'))
    ref_id = request.args.get('ref')
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    
    if not res.data:
        # New User Initialization
        supabase.table("users").insert({
            "uid": uid, "energy": 10, "referred_by": ref_id if ref_id != uid else None
        }).execute()
        u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
        # Trigger referral logic if they joined via link
        if u['referred_by']:
            try: supabase.rpc('increment_ref', {'row_id': u['referred_by']}).execute()
            except: pass
    else:
        u = res.data[0]

    # LOW DIFFICULTY: Energy recovers 1 per 10 minutes
    now = datetime.datetime.now(datetime.timezone.utc)
    last_reset = datetime.datetime.fromisoformat(u['last_energy_reset'].replace('Z', '+00:00'))
    mins_passed = int((now - last_reset).total_seconds() / 60)
    new_energy = min(10, u['energy'] + (mins_passed // 10))
    
    return jsonify({
        "bal": u['bal'], "energy": new_energy, "tickets": u['tickets'], 
        "xp": u['xp'], "level": u['level'], "refs": u['ref_count']
    })

@app.route('/reward_spin', methods=['POST'])
def reward_spin():
    data = request.get_json()
    uid, use_ticket = str(data.get('user_id')), data.get('use_ticket', False)
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    if not use_ticket and u['energy'] <= 0: return jsonify({"error": "No energy"}), 403
    if use_ticket and u['tickets'] <= 0: return jsonify({"error": "No tickets"}), 403
    
    # Reward Logic (Base + Level Bonus)
    base = 0.00015 
    bonus = (1 + (u['level'] * 0.01))
    if use_ticket: bonus *= 5 # 5x Golden Ticket Boost
    win = base * bonus

    # 10% Passive Referral Commission
    if u['referred_by']:
        p_id = u['referred_by']
        p_data = supabase.table("users").select("bal").eq("uid", p_id).execute().data
        if p_data:
            supabase.table("users").update({"bal": p_data[0]['bal'] + (win * 0.1)}).eq("uid", p_id).execute()

    # Low Difficulty: +20 XP per action
    new_xp = u['xp'] + 20
    upd = {
        "bal": u['bal'] + win, 
        "xp": new_xp, 
        "level": (new_xp // 100) + 1,
        "last_energy_reset": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    if use_ticket: upd["tickets"] = u['tickets'] - 1
    else: upd["energy"] = u['energy'] - 1
    
    supabase.table("users").update(upd).eq("uid", uid).execute()
    return jsonify({"win": win, "new_bal": u['bal'] + win})

@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.get_json()
    uid, amount, addr = str(data['user_id']), float(data['amount']), data['address']
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    # VIRAL LOCK: Must have 3 referrals to withdraw
    if u['ref_count'] < 3:
        return jsonify({"error": f"You need 3 referrals to unlock withdrawals. Current: {u['ref_count']}/3"}), 403
        
    if u['bal'] < amount or amount < 0.1: 
        return jsonify({"error": "Minimum withdrawal is 0.1 TON"}), 400
    
    # Deduct and log request
    supabase.table("users").update({"bal": u['bal'] - amount}).eq("uid", uid).execute()
    supabase.table("withdrawals").insert({"uid": uid, "amount": amount, "address": addr}).execute()
    return jsonify({"success": True})

@app.route('/shoutbox', methods=['GET', 'POST'])
def shoutbox():
    if request.method == 'POST':
        d = request.get_json()
        supabase.table("shoutbox").insert({"uid": d['user_id'], "msg": d['msg']}).execute()
    return jsonify(supabase.table("shoutbox").select("*").order("created_at", desc=True).limit(5).execute().data)

@app.route('/admin_stats')
def admin_stats():
    if str(request.args.get('user_id')) != ADMIN_ID: return jsonify({"error": "Forbidden"}), 403
    users = supabase.table("users").select("*").execute().data
    return jsonify({"users": len(users), "debt": round(sum(u['bal'] for u in users), 4)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
