import os
import telebot
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from threading import Thread

# --- CONFIGURAÇÕES DO RENDER (ENVIRONMENT) ---
TOKEN = os.environ.get("BOT_TOKEN") # O nome da chave no Render deve ser BOT_TOKEN
S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_ID = "5401881400"

bot = telebot.TeleBot(TOKEN)
supabase = create_client(S_URL, S_KEY)
app = Flask(__name__)
CORS(app)

# --- BOT TELEGRAM ---
@bot.message_handler(commands=['start'])
def welcome(message):
    markup = telebot.types.InlineKeyboardMarkup()
    # Link do seu GitHub Pages
    web_app_url = "https://pne1973.github.io/mini-app/"
    btn = telebot.types.InlineKeyboardButton("🚀 OPEN TON EMPIRE", web_app=telebot.types.WebAppInfo(url=web_app_url))
    markup.add(btn)
    bot.send_message(message.chat.id, "💎 **TON EMPIRE 2026**\n\nPrepare-se para minerar TON e subir de nível!", parse_mode="Markdown", reply_markup=markup)

# --- API PARA O JOGO ---
@app.route('/check_eligibility')
def check():
    uid = str(request.args.get('user_id'))
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data:
        data = {"uid": uid, "balance": 0.0, "energy": 10, "xp": 0, "level": 1}
        supabase.table("users").insert(data).execute()
        return jsonify(data)
    return jsonify(res.data[0])

@app.route('/reward_spin', methods=['POST'])
def reward():
    uid = str(request.json.get('user_id'))
    res = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    if res['energy'] <= 0: return jsonify({"error": "Sem energia"}), 400
    
    new_bal = round(res['balance'] + 0.0002, 6)
    supabase.table("users").update({"balance": new_bal, "energy": res['energy'] - 1}).eq("uid", uid).execute()
    return jsonify({"balance": new_bal, "energy": res['energy'] - 1})

@app.route('/admin_stats')
def admin():
    if str(request.args.get('user_id')) != ADMIN_ID: return "Acesso Negado", 403
    users = supabase.table("users").select("balance").execute()
    total_debt = sum(u['balance'] for u in users.data)
    return jsonify({"total_users": len(users.data), "debt": total_debt})

# --- EXECUÇÃO DUPLA ---
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
