import os, telebot, time
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from threading import Thread

TOKEN = os.environ.get("BOT_TOKEN")
S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_ID = "5401881400"

bot = telebot.TeleBot(TOKEN)
supabase = create_client(S_URL, S_KEY)
app = Flask(__name__)
CORS(app)

@app.route('/check_eligibility')
def check():
    uid = str(request.args.get('user_id'))
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data:
        data = {"uid": uid, "balance": 0.0, "energy": 10, "xp": 0, "level": 1, "last_regen": int(time.time())}
        supabase.table("users").insert(data).execute()
        return jsonify(data)
    
    u = res.data[0]
    now = int(time.time())
    diff = now - u.get('last_regen', now)
    points = diff // 1800
    if points > 0:
        new_nrg = min(10, u['energy'] + points)
        supabase.table("users").update({"energy": new_nrg, "last_regen": now}).eq("uid", uid).execute()
        u['energy'] = new_nrg
    return jsonify(u)

@app.route('/reward_spin', methods=['POST'])
def reward():
    uid = str(request.json.get('user_id'))
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    if u['energy'] <= 0: return jsonify({"error": "No Energy"}), 400
    
    new_xp = u['xp'] + 10
    new_lvl = u['level']
    if new_xp >= 100: # Sobe de nível a cada 100 XP
        new_xp = 0
        new_lvl += 1
        
    new_bal = round(u['balance'] + 0.0002, 6)
    supabase.table("users").update({"balance": new_bal, "energy": u['energy']-1, "xp": new_xp, "level": new_lvl}).eq("uid", uid).execute()
    return jsonify({"balance": new_bal, "energy": u['energy']-1, "xp": new_xp, "level": new_lvl})

@app.route('/get_leaderboard')
def leaderboard():
    res = supabase.table("users").select("uid, balance").order("balance", desc=True).limit(5).execute()
    return jsonify(res.data)

@app.route('/admin_stats')
def admin():
    if str(request.args.get('user_id')) != ADMIN_ID: return "No", 403
    users = supabase.table("users").select("balance").execute()
    return jsonify({"total_users": len(users.data), "debt": sum(u['balance'] for u in users.data)})

@app.route('/request_withdraw', methods=['POST'])
def withdraw():
    uid = str(request.json.get('user_id'))
    u = supabase.table("users").select("balance").eq("uid", uid).execute().data[0]
    if u['balance'] < 0.5: return jsonify({"error": "Mínimo 0.5 TON"}), 400
    return jsonify({"success": "Pedido em análise!"})

if __name__ == "__main__":
    Thread(target=lambda: bot.infinity_polling()).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
