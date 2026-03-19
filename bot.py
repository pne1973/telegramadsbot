import os
import telebot
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from telebot import types

# --- CONFIGURAÇÕES ---
TOKEN = "TEU_TOKEN_DO_BOTFATHER" # Substitui pelo teu Token real
S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_ID = "5401881400"

bot = telebot.TeleBot(TOKEN)
supabase = create_client(S_URL, S_KEY)
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) # Permite conexão do GitHub Pages

# --- LÓGICA DO TELEGRAM (Menu Inicial) ---
@bot.message_handler(commands=['start'])
def welcome(message):
    web_app_url = "https://pne1973.github.io/mini-app/"
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🎮 PLAY & EARN TON", web_app=types.WebAppInfo(url=web_app_url))
    markup.add(btn)
    
    texto = "💎 **WELCOME TO TON EMPIRE 2026**\n\nGanhe TON real assistindo anúncios!"
    bot.send_message(message.chat.id, texto, parse_mode="Markdown", reply_markup=markup)

# --- ROTAS DA API (Para o index.html consultar) ---
@app.route('/check_eligibility', methods=['GET'])
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
    if u['energy'] <= 0: return jsonify({"error": "No energy"}), 400
    
    win = 0.00015 * (1 + (u['level'] * 0.01))
    upd = {"balance": round(u['balance'] + win, 6), "energy": u['energy'] - 1, "xp": u['xp'] + 20}
    supabase.table("users").update(upd).eq("uid", uid).execute()
    return jsonify({"win": win})

# Rota para o Render não dar erro de porta
@app.route('/')
def home(): return "Bot Server is Online!"

if __name__ == "__main__":
    # Inicia o Flask em background e o Bot em foreground
    from threading import Thread
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))).start()
    bot.infinity_polling()
