import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client

app = Flask(__name__)
CORS(app)

# --- CONFIG ---
SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def home():
    return "Server is Running"

@app.route('/check_eligibility')
def check_eligibility():
    uid = str(request.args.get('user_id'))
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data:
        supabase.table("users").insert({"uid": uid}).execute()
        user_data = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    else:
        user_data = res.data[0]
    return jsonify(user_data)

@app.route('/reward_spin', methods=['POST'])
def reward_spin():
    data = request.get_json()
    uid = str(data.get('user_id'))
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data: return jsonify({"error": "User not found"}), 404
    
    u = res.data[0]
    if u['energy'] <= 0: return jsonify({"error": "No energy"}), 403

    # Logic: VIPs get 2x. Base win is 0.0001
    mult = 2.0 if u['is_vip'] else 1.0
    win = 0.0001 * mult
    
    new_bal = u['bal'] + win
    new_xp = u['xp'] + 10
    new_lvl = (new_xp // 100) + 1

    supabase.table("users").update({
        "bal": new_bal, 
        "energy": u['energy'] - 1,
        "xp": new_xp,
        "level": new_lvl
    }).eq("uid", uid).execute()

    return jsonify({"win": win, "new_bal": new_bal})

if __name__ == '__main__':
    # FIX FOR RENDER: Use the port provided by the environment
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
