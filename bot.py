import os
import telebot
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from telebot import types
from threading import Thread

# --- CONFIGURAÇÕES ---
TOKEN = "8609038498:AAFzTSVCg2XzwAFsfc8xiA20jEIiPMIxmzc" 

S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_ID = "5401881400"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
# CORS TOTAL para permitir que o GitHub Pages aceda aos dados
CORS(app, resources={r"/*": {"origins": "*"}}) 

# LIGAÇÃO AO SUPABASE
supabase = None
if S_URL and S_KEY:
    supabase = create_client(S_URL, S_KEY)

# --- COMANDO /START (MENU INICIAL) ---
@bot.message_handler(commands=['start'])
def welcome(message):
    web_app_url = "https://pne1973.github.io/mini-app/"
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🎮 PLAY & EARN TON", web_app=types.WebAppInfo(url=web_app_url))
    markup.add(btn)
    
    texto = (
        "💎 **WELCOME TO TON EMPIRE 2026**\n\n"
        "O teu bot está oficialmente online! Assiste a anúncios e ganha TON real.\n\n"
        "👇 Clica no botão abaixo para abrir o jogo:"
    )
    bot.send_message(message.chat.id, texto, parse_mode="Markdown", reply_markup=markup)

# --- API PARA O JOGO ---
@app.route('/check_eligibility', methods=['GET'])
def check():
    uid = str(request.args.get('user_id'))
    if not supabase: return jsonify({"error": "Supabase offline"}), 500
    
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
    
    if u['energy'] <= 0: return jsonify({"error": "No energy"}), 400
    
    win = 0.00015 * (1 + (u['level'] * 0.01))
    upd = {"balance": round(u['balance'] + win, 6), "energy": u['energy'] - 1}
    supabase.table("users").update(upd).eq("uid", uid).execute()
    return jsonify({"win": win})

@app.route('/')
def home(): return "Bot Server Online"

# --- INICIAR SERVIDOR ---
def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("✅ Bot está a correr no Telegram!")
    bot.infinity_polling()
