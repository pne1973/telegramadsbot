import os, telebot, time
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from threading import Thread

# --- CONFIGURAÇÕES ---
TOKEN = "TEU_TOKEN_AQUI" # Substituir pelo token do BotFather
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
    btn = telebot.types.InlineKeyboardButton("🚀 OPEN EMPIRE", web_app=telebot.types.WebAppInfo(url="https://pne1973.github.io/mini-app/"))
    markup.add(btn)
    bot.send_message(message.chat.id, "💎 **TON EMPIRE**\nClica abaixo para começar!", parse_mode="Markdown", reply_markup=markup)

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
    if res['energy'] <= 0: return jsonify({"error": "No energy"}), 400
    new_bal = round(res['balance'] + 0.0002, 6)
    supabase.table("users").update({"balance": new_bal, "energy": res['energy'] - 1}).eq("uid", uid).execute()
    return jsonify({"balance": new_bal, "energy": res['energy'] - 1})

@app.route('/admin_stats')
def admin():
    if str(request.args.get('user_id')) != ADMIN_ID: return "403", 403
    users = supabase.table("users").select("balance").execute()
    return jsonify({"total_users": len(users.data), "debt": sum(u['balance'] for u in users.data)})

def run_bot(): bot.infinity_polling()
if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
