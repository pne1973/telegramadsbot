import os
import telebot
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from threading import Thread

# --- CONFIGURAÇÕES DO RENDER (Environment Variables) ---
TOKEN = os.environ.get("BOT_TOKEN")
S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_ID = "5401881400"

bot = telebot.TeleBot(TOKEN)
supabase = create_client(S_URL, S_KEY)
app = Flask(__name__)
CORS(app)

# --- BOT NO TELEGRAM ---
@bot.message_handler(commands=['start'])
def welcome(message):
    args = message.text.split()
    uid = str(message.from_user.id)
    
    # Lógica de Referência (Convite)
    if len(args) > 1 and args[1].startswith('ref_'):
        ref_by = args[1].replace('ref_', '')
        if ref_by != uid:
            # Verifica se o user já existe, se não, pode dar bónus ao ref_by aqui
            pass

    markup = telebot.types.InlineKeyboardMarkup()
    # O SEU LINK DO GITHUB PAGES
    webapp = telebot.types.WebAppInfo(url="https://pne1973.github.io/mini-app/")
    btn = telebot.types.InlineKeyboardButton("🚀 ENTRAR NO IMPÉRIO", web_app=webapp)
    markup.add(btn)
    
    bot.send_message(message.chat.id, 
        "💎 **BEM-VINDO AO TON EMPIRE**\n\n"
        "• Ganhe TON real assistindo anúncios\n"
        "• Suba no Ranking Global\n"
        "• Convide amigos e ganhe bónus!", 
        parse_mode="Markdown", reply_markup=markup)

# --- API DO JOGO ---

@app.route('/check_eligibility')
def check():
    uid = str(request.args.get('user_id'))
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    
    if not res.data:
        data = {"uid": uid, "balance": 0.0, "energy": 10, "xp": 0, "level": 1, "last_regen": int(time.time())}
        supabase.table("users").insert(data).execute()
        return jsonify(data)
    
    user_data = res.data[0]
    
    # Lógica de Recuperação Automática de Energia (1 ponto a cada 30 min)
    now = int(time.time())
    diff = now - user_data.get('last_regen', now)
    points_to_add = diff // 1800 # 1800 segundos = 30 min
    
    if points_to_add > 0:
        new_nrg = min(10, user_data['energy'] + points_to_add)
        supabase.table("users").update({"energy": new_nrg, "last_regen": now}).eq("uid", uid).execute()
        user_data['energy'] = new_nrg
        
    return jsonify(user_data)

@app.route('/reward_spin', methods=['POST'])
def reward():
    uid = str(request.json.get('user_id'))
    res = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    if res['energy'] <= 0:
        return jsonify({"error": "Sem energia"}), 400
    
    new_bal = round(res['balance'] + 0.0002, 6)
    new_nrg = res['energy'] - 1
    
    supabase.table("users").update({
        "balance": new_bal, 
        "energy": new_nrg,
        "xp": res['xp'] + 10
    }).eq("uid", uid).execute()
    
    return jsonify({"balance": new_bal, "energy": new_nrg, "level": res['level']})

@app.route('/get_leaderboard')
def leaderboard():
    res = supabase.table("users").select("uid, balance").order("balance", desc=True).limit(5).execute()
    return jsonify(res.data)

@app.route('/get_invite_link')
def invite():
    uid = request.args.get('user_id')
    return jsonify({"link": f"https://t.me/CryptoEarnerBot?start=ref_{uid}"})

@app.route('/admin_stats')
def admin():
    if str(request.args.get('user_id')) != ADMIN_ID: return "Forbidden", 403
    users = supabase.table("users").select("balance").execute()
    return jsonify({"total_users": len(users.data), "debt": sum(u['balance'] for u in users.data)})

# --- START ---
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
