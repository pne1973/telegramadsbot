import os, datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client

app = Flask(__name__)
CORS(app)

# --- CONFIG (Pega do Render Environment) ---
S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(S_URL, S_KEY)
ADMIN_ID = "5401881400"

@app.route('/check_eligibility', methods=['GET'])
def check():
    uid = str(request.args.get('user_id'))
    ref = request.args.get('ref')
    
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data:
        user_data = {"uid": uid, "referred_by": ref if ref != uid else None, "energy": 10, "balance": 0, "xp": 0, "level": 1}
        supabase.table("users").insert(user_data).execute()
        if ref and ref != uid:
            supabase.rpc("increment_ref", {"mestre_id": ref}).execute()
        return jsonify(user_data)
    return jsonify(res.data[0])

@app.route('/reward_spin', methods=['POST'])
def reward():
    data = request.get_json()
    uid = str(data.get('user_id'))
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    if u['energy'] <= 0: return jsonify({"error": "No energy!"}), 400

    win = 0.00015 * (1 + (u['level'] * 0.01))
    new_xp = u['xp'] + 20
    
    upd = {"balance": round(u['balance'] + win, 6), "xp": new_xp, "level": (new_xp // 100) + 1, "energy": u['energy'] - 1}
    supabase.table("users").update(upd).eq("uid", uid).execute()
    return jsonify({"win": win, "new_balance": upd["balance"]})

@app.route('/admin_stats')
def admin_stats():
    uid = request.args.get('user_id')
    if uid != ADMIN_ID: return jsonify({"error": "Unauthorized"}), 403
    
    users = supabase.table("users").select("balance", count="exact").execute()
    total_debt = sum(x['balance'] for x in users.data)
    return jsonify({"total_users": users.count, "debt": round(total_debt, 4)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
