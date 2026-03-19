import os
import telebot
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from threading import Thread

# --- CONFIGURAÇÕES ---
TOKEN = "TEU_TOKEN_DO_BOTFATHER" # Substitui pelo teu Token
bot = telebot.TeleBot(TOKEN)

S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(S_URL, S_KEY)

ADMIN_ID = "5401881400"
app = Flask(__name__)
CORS(app)

# --- LÓGICA DO BOT (TELEGRAM) ---
@bot.message_handler(commands=['start'])
def welcome(message):
    web_app_url = "https://pne1973.github.io/mini-app/"
    markup = telebot.types.InlineKeyboardMarkup()
    btn = telebot.types.InlineKeyboardButton("🎮 JOGAR AGORA", web_app=telebot.types.WebAppInfo(url=web_app_url))
    markup.add(btn)
    
    bot.send_message(message.chat.id, "💎 **BEM-VINDO AO TON EMPIRE!**\n\nGanhe TON real assistindo anúncios.", 
                     parse_mode="Markdown", reply_markup=markup)

# --- API PARA O JOGO ---
@app.route('/check_eligibility')
def check():
    uid = str(request.args.get('user_id'))
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data:
        user_data = {"uid": uid, "balance": 0.0, "energy": 10, "xp": 0, "level": 1}
        supabase.table("users").insert(user_data).execute()
        return jsonify(user_data)
    return jsonify(res.data[0])

@app.route('/reward_spin', methods=['POST'])
def reward():
    data = request.get_json()
    uid = str(data.get('user_id'))
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    if u['energy'] <= 0: return jsonify({"error": "Sem energia"}), 400
    
    win = 0.0002 # Valor fixo ou baseado no level
    supabase.table("users").update({"balance": u['balance'] + win, "energy": u['energy'] - 1}).eq("uid", uid).execute()
    return jsonify({"win": win})

@app.route('/admin_stats')
def admin():
    if request.args.get('user_id') != ADMIN_ID: return "Forbidden", 403
    users = supabase.table("users").select("balance").execute()
    total_debt = sum(x['balance'] for x in users.data)
    return jsonify({"total_users": len(users.data), "debt": total_debt})

# --- INICIALIZAÇÃO ---
def run_bot(): bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
