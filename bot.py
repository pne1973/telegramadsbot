import os
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
import telebot
from telebot import types

app = Flask(__name__)
CORS(app)

# --- CONFIGURAÇÃO ---
S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN") # Token do BotFather
WEBAPP_URL = os.environ.get("WEBAPP_URL") # Teu link do Render
ADMIN_ID = "5401881400"

supabase = create_client(S_URL, S_KEY)
bot = telebot.TeleBot(BOT_TOKEN)

# --- LÓGICA DO TELEGRAM (/START) ---
@bot.message_handler(commands=['start'])
def start(message):
    ref_id = message.text.split()[1] if len(message.text.split()) > 1 else ""
    markup = types.InlineKeyboardMarkup()
    # Passa o ref_id para a WebApp via URL
    url_com_ref = f"{WEBAPP_URL}?ref={ref_id}"
    web_app = types.WebAppInfo(url=url_com_ref)
    btn = types.InlineKeyboardButton("💎 ENTER EMPIRE (EARN TON)", web_app=web_app)
    markup.add(btn)
    
    msg_text = (
        "👑 *WELCOME TO TON EMPIRE 2026*\n\n"
        "🚀 Start earning real TON by watching ads!\n"
        "📈 Level up to multiply your rewards.\n"
        "🎁 Daily bonuses and 10% referral commission.\n\n"
        "👇 Click the button below to start!"
    )
    bot.send_message(message.chat.id, msg_text, parse_mode="Markdown", reply_markup=markup)

# --- API DA WEB APP ---
@app.route('/check_eligibility', methods=['GET'])
def check():
    uid = str(request.args.get('user_id'))
    ref = request.args.get('ref')
    
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data:
        user_data = {"uid": uid, "referred_by": ref if ref and ref != uid else None, "energy": 10, "balance": 0, "xp": 0, "level": 1}
        supabase.table("users").insert(user_data).execute()
        if ref and ref != uid:
            supabase.rpc("increment_ref", {"mestre_id": ref}).execute()
        return jsonify(user_data)
    return jsonify(res.data[0])

@app.route('/reward_spin', methods=['POST'])
def reward():
    data = request.get_json()
    uid = str(data.get('user_id'))
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    if u['energy'] <= 0: return jsonify({"error": "No energy"}), 400

    base = 0.00015
    mult = (1 + (u['level'] * 0.01))
    win = round(base * mult, 6)
    
    new_xp = u['xp'] + 20
    upd = {
        "balance": round(u['balance'] + win, 6),
        "xp": new_xp,
        "level": (new_xp // 100) + 1,
        "energy": u['energy'] - 1
    }
    supabase.table("users").update(upd).eq("uid", uid).execute()

    # 10% Comissão
    if u['referred_by']:
        p = supabase.table("users").select("balance").eq("uid", u['referred_by']).execute().data
        if p:
            supabase.table("users").update({"balance": round(p[0]['balance'] + (win * 0.1), 6)}).eq("uid", u['referred_by']).execute()

    return jsonify({"win": win, "new_balance": upd["balance"]})

@app.route('/admin_stats')
def admin():
    if str(request.args.get('user_id')) != ADMIN_ID: return "Forbidden", 403
    users = supabase.table("users").select("balance").execute()
    return jsonify({"total_users": len(users.data), "debt": sum(x['balance'] for x in users.data)})

# Rota para o Render não deixar o bot morrer
@app.route('/')
def home(): return "Bot Online", 200

if __name__ == '__main__':
    # Inicia o Polling do Bot numa thread separada ou usa webhooks
    import threading
    threading.Thread(target=bot.infinity_polling).start()
    app.run(host='0.0.0.0', port=5000)
