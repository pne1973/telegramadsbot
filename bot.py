import os, telebot, time
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from threading import Thread

# Configurações do Ambiente
TOKEN = os.environ.get("BOT_TOKEN")
S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_ID = "5401881400" # O teu ID

bot = telebot.TeleBot(TOKEN)
supabase = create_client(S_URL, S_KEY)
app = Flask(__name__)
CORS(app)

@bot.message_handler(commands=['start'])
def welcome(message):
    markup = telebot.types.InlineKeyboardMarkup()
    webapp = telebot.types.WebAppInfo(url="https://pne1973.github.io/mini-app/")
    btn = telebot.types.InlineKeyboardButton("🚀 OPEN TON EMPIRE", web_app=webapp)
    markup.add(btn)
    bot.send_message(message.chat.id, "💎 **TON EMPIRE 2026**\nMinere TON, suba de nível e ganhe bónus diários!", parse_mode="Markdown", reply_markup=markup)

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
    # Regeneração: 1pt a cada 30min (1800s)
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
        return jsonify({"error": "Bónus disponível apenas a cada 24h!"}), 400
    
    new_bal = round(u['balance'] + 0.001, 6)
    supabase.table("users").update({"balance": new_bal, "last_daily": now}).eq("uid", uid).execute()
    return jsonify({"balance": new_bal, "success": "Recebeu 0.001 TON de bónus!"})

@app.route('/request_withdraw', methods=['POST'])
def withdraw():
    uid = str(request.json.get('user_id'))
    u = supabase.table("users").select("balance").eq("uid", uid).execute().data[0]
    if u['balance'] < 0.5:
        return jsonify({"error": "Mínimo para saque é 0.5 TON"}), 400
    return jsonify({"success": "Pedido de saque enviado para análise!"})

@app.route('/get_leaderboard')
def leaderboard():
    res = supabase.table("users").select("uid, balance").order("balance", desc=True).limit(5).execute()
    return jsonify(res.data)

@app.route('/admin_stats')
def admin():
    if str(request.args.get('user_id')) != ADMIN_ID: return "Forbidden", 403
    users = supabase.table("users").select("balance").execute()
    return jsonify({"total_users": len(users.data), "debt": sum(u['balance'] for u in users.data)})

if __name__ == "__main__":
    Thread(target=lambda: bot.infinity_polling()).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
