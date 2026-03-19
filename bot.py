import os, datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
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
        supabase.table("users").insert({
            "uid": uid, "energy": 10, "referred_by": ref_id if ref_id != uid else None
        }).execute()
        u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
        if u['referred_by']:
            try: supabase.rpc('increment_ref', {'row_id': u['referred_by']}).execute()
            except: pass
    else:
        u = res.data[0]

    now = datetime.datetime.now(datetime.timezone.utc)
    last_reset = datetime.datetime.fromisoformat(u['last_energy_reset'].replace('Z', '+00:00'))
    mins = int((now - last_reset).total_seconds() / 60)
    new_energy = min(10, u['energy'] + (mins // 30))
    
    return jsonify({"bal": u['bal'], "energy": new_energy, "tickets": u['tickets'], "xp": u['xp'], "level": u['level'], "is_vip": u['is_vip']})

@app.route('/reward_spin', methods=['POST'])
def reward_spin():
    data = request.get_json()
    uid = str(data.get('user_id'))
    use_ticket = data.get('use_ticket', False)
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]

    if not use_ticket and u['energy'] <= 0: return jsonify({"error": "No energy"}), 403
    if use_ticket and u['tickets'] <= 0: return jsonify({"error": "No tickets"}), 403
    
    base = 0.0001
    bonus = (2.0 if u['is_vip'] else 1.0) * (1 + (u['level'] * 0.01))
    if use_ticket: bonus *= 5
    win = base * bonus

    if u['referred_by']:
        p_id = u['referred_by']
        p_data = supabase.table("users").select("bal").eq("uid", p_id).execute().data
        if p_data:
            supabase.table("users").update({"bal": p_data[0]['bal'] + (win * 0.1)}).eq("uid", p_id).execute()

    new_xp = u['xp'] + 10
    upd = {"bal": u['bal'] + win, "xp": new_xp, "level": (new_xp // 100) + 1}
    if use_ticket: upd["tickets"] = u['tickets'] - 1
    else: upd["energy"] = u['energy'] - 1
    
    supabase.table("users").update(upd).eq("uid", uid).execute()
    return jsonify({"win": win, "new_bal": u['bal'] + win})

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
    return jsonify({"users": len(users), "debt": round(sum(u['bal'] for u in users), 4), "vips": len([u for u in users if u['is_vip']])})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
