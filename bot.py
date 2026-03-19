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
        data = {"uid": uid, "balance": 0.0, "energy": 10, "xp": 0, "level": 1, "last_regen": int(time.time()), "last_daily": 0}
        supabase.table("users").insert(data).execute()
        return jsonify(data)
    
    u = res.data[0]
    now = int(time.time())
    # Regen Energia: 1pt/30min
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
    if u['energy'] <= 0: return jsonify({"error": "Sem Energia"}), 400
    
    new_xp = u['xp'] + 10
    new_lvl = u['level']
    if new_xp >= 100:
        new_xp = 0
        new_lvl += 1
        
    new_bal = round(u['balance'] + 0.0002, 6)
    supabase.table("users").update({"balance": new_bal, "energy": u['energy']-1, "xp": new_xp, "level": new_lvl}).eq("uid", uid).execute()
    return jsonify({"balance": new_bal, "energy": u['energy']-1, "xp": new_xp, "level": new_lvl})

@app.route('/claim_daily', methods=['POST'])
def daily():
    uid = str(request.json.get('user_id'))
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    now = int(time.time())
    
    if now - u.get('last_daily', 0) < 86400:
        return jsonify({"error": "Volte amanhã!"}), 400
        
    new_bal = round(u['balance'] + 0.001, 6) # Bónus diário maior
    supabase.table("users").update({"balance": new_bal, "last_daily": now}).eq("uid", uid).execute()
    return jsonify({"balance": new_bal, "success": "Bónus de 0.001 TON resgatado!"})

# ... (restantes rotas de admin e leaderboard mantêm-se iguais)
