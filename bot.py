import os
import telebot
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from threading import Thread

# --- CONFIGURAÇÕES ---
TOKEN = os.environ.get("BOT_TOKEN")
S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_ID = "5401881400"

bot = telebot.TeleBot(TOKEN)
supabase = create_client(S_URL, S_KEY)
app = Flask(__name__)
CORS(app)

@bot.message_handler(commands=['start'])
def welcome(message):
    markup = telebot.types.InlineKeyboardMarkup()
    webapp = telebot.types.WebAppInfo(url="https://pne1973.github.io/mini-app/")
    btn = telebot.types.InlineKeyboardButton("🚀 ABRIR TON EMPIRE", web_app=webapp)
    markup.add(btn)
    bot.send_message(message.chat.id, "💎 **TON EMPIRE**\n\nMinere TON, suba no Ranking e ganhe prémios reais!", parse_mode="Markdown", reply_markup=markup)

# --- API ---
@app.route('/check_eligibility')
def check():
    uid = str(request.args.get('user_id'))
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data:
        data = {"uid": uid, "balance": 0.0, "energy": 10, "xp": 0, "level": 1, "last_regen": int(time.time())}
        supabase.table("users").insert(data).execute()
        return jsonify(data)
    
    user_data = res.data[0]
    # Regen: 1 ponto a cada 30 min (1800s)
    now = int(time.time())
    diff = now - user_data.get('last_regen', now)
    points = diff // 1800
    if points > 0:
        new_nrg = min(10, user_data['energy'] + points)
        supabase.table("users").update({"energy": new_nrg, "last_regen": now}).eq("uid", uid).execute()
        user_data['energy'] = new_nrg
    return jsonify(user_data)

@app.route('/reward_spin', methods=['POST'])
def reward():
    uid = str(request.json.get('user_id'))
    res = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    if res['energy'] <= 0: return jsonify({"error": "No Energy"}), 400
    new_bal = round(res['balance'] + 0.0002, 6)
    supabase.table("users").update({"balance": new_bal, "energy": res['energy']-1}).eq("uid", uid).execute()
    return jsonify({"balance": new_bal, "energy": res['energy']-1})

@app.route('/get_leaderboard')
def leaderboard():
    res = supabase.table("users").select("uid, balance").order("balance", desc=True).limit(5).execute()
    return jsonify(res.data)

@app.route('/admin_stats')
def admin():
    if str(request.args.get('user_id')) != ADMIN_ID: return "No", 403
    users = supabase.table("users").select("balance").execute()
    return jsonify({"total_users": len(users.data), "debt": sum(u['balance'] for u in users.data)})

if __name__ == "__main__":
    Thread(target=lambda: bot.infinity_polling()).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
