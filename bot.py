import os
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
# ⚠️ PASTE YOUR ACTUAL KEYS BETWEEN THE QUOTES BELOW
SUPABASE_URL = "https://your-project-id.supabase.co" 
SUPABASE_KEY = "your-service-role-key-goes-here"

# --- SAFETY INITIALIZATION ---
try:
    # We strip() the strings to remove any accidental spaces from copy-pasting
    supabase: Client = create_client(SUPABASE_URL.strip(), SUPABASE_KEY.strip())
    print("✅ Supabase Client Initialized Successfully")
except Exception as e:
    print(f"❌ DATABASE ERROR: {e}")
    supabase = None

@app.route('/')
def home():
    return "MyEarn Backend is Online 🚀"

@app.route('/check_eligibility')
def check_eligibility():
    if not supabase: return jsonify({"error": "Database not connected"}), 500
    
    uid = str(request.args.get('user_id'))
    try:
        res = supabase.table("users").select("*").eq("uid", uid).execute()
        if not res.data:
            supabase.table("users").insert({"uid": uid}).execute()
            user_data = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
        else:
            user_data = res.data[0]
        return jsonify(user_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/reward_spin', methods=['POST'])
def reward_spin():
    if not supabase: return jsonify({"error": "Database not connected"}), 500
    
    data = request.get_json()
    uid = str(data.get('user_id'))
    
    try:
        res = supabase.table("users").select("*").eq("uid", uid).execute()
        if not res.data: return jsonify({"error": "User not found"}), 404
        
        u = res.data[0]
        if u.get('energy', 0) <= 0: return jsonify({"error": "No energy"}), 403

        # Rewards logic
        mult = 2.0 if u.get('is_vip') else 1.0
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Fix for Render: Port must be dynamic
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
