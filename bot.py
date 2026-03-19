import os, datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# --- CONFIG ---
SUPABASE_URL = "https://your-project.supabase.co" 
SUPABASE_KEY = "your-service-key"
supabase: Client = create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())

@app.route('/check_eligibility')
def check_eligibility():
    uid = str(request.args.get('user_id'))
    ref_id = request.args.get('ref')
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    
    if not res.data:
        # NEW USER: 10 Energy + 0 Tickets + Referral Link
        supabase.table("users").insert({
            "uid": uid, "energy": 10, "tickets": 0, "bal": 0.0, "xp": 0, "level": 1, "referred_by": ref_id
        }).execute()
        u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
        if ref_id: # 10% Passive logic starts here
            supabase.rpc('increment_ref', {'row_id': ref_id}).execute()
    else:
        u = res.data[0]

    # ENERGY REGEN (1 per 30m)
    now = datetime.datetime.now(datetime.timezone.utc)
    last_reset = datetime.datetime.fromisoformat(u['last_energy_reset'].replace('Z', '+00:00'))
    new_energy = min(10, u['energy'] + int((now - last_reset).total_seconds() // 1800))
    
    return jsonify({"bal": u['bal'], "energy": new_energy, "tickets": u['tickets'], "xp": u['xp'], "level": u['level'], "is_vip": u['is_vip']})

@app.route('/reward_spin', methods=['POST'])
def reward_spin():
    data = request.get_json()
    uid = str(data.get('user_id'))
    use_ticket = data.get('use_ticket', False)
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]

    # ANTI-CHEAT & ENERGY CHECK
    if not use_ticket and u['energy'] <= 0: return jsonify({"error": "No energy"}), 403
    
    # REWARD LOGIC (Level Bonus + VIP 2x)
    win = 0.0001 * (2.0 if u['is_vip'] else 1.0) * (1 + (u['level'] * 0.01))
    if use_ticket: win *= 5 # Golden Tickets give 5x reward
    
    # 10% PASSIVE COMMISSION
    if u['referred_by']:
        p_id = u['referred_by']
        p_res = supabase.table("users").select("bal").eq("uid", p_id).execute()
        if p_res.data:
            supabase.table("users").update({"bal": p_res.data[0]['bal'] + (win * 0.1)}).eq("uid", p_id).execute()

    # UPDATE USER
    upd = {"bal": u['bal'] + win, "xp": u['xp'] + 10, "level": (u['xp'] + 10 // 100) + 1}
    if use_ticket: upd["tickets"] = u['tickets'] - 1
    else: upd["energy"] = u['energy'] - 1
    
    supabase.table("users").update(upd).eq("uid", uid).execute()
    return jsonify({"win": win, "new_bal": u['bal'] + win})

@app.route('/shoutbox', methods=['GET', 'POST'])
def shoutbox():
    if request.method == 'POST':
        data = request.get_json()
        supabase.table("shoutbox").insert({"uid": data['user_id'], "msg": data['msg']}).execute()
    res = supabase.table("shoutbox").select("*").order("created_at", desc=True).limit(5).execute()
    return jsonify(res.data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
