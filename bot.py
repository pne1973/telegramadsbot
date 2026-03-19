import os
import telebot
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from datetime import datetime, timedelta
from threading import Thread
import time

# --- CONFIGURAÇÃO INICIAL ---
TOKEN = os.environ.get("BOT_TOKEN")
S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
CORS(app)
supabase = create_client(S_URL, S_KEY)

ADMIN_ID = "5401881400"
WEB_APP_URL = "https://pne1973.github.io/mini-app/"

# --- MOTOR DE MENSAGENS (TELEGRAM CHAT) ---

@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    username = message.from_user.first_name
    args = message.text.split()
    referrer_id = args[1] if len(args) > 1 else None

    # Verifica ou Cria Utilizador
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data:
        new_user = {
            "uid": uid, 
            "referred_by": referrer_id,
            "balance": 0.0,
            "last_spin": datetime.now().isoformat()
        }
        supabase.table("users").insert(new_user).execute()
        if referrer_id:
            supabase.rpc("increment_ref", {"mestre_id": referrer_id}).execute()
            try: bot.send_message(referrer_id, f"🎊 **Novo Recruta!** {username} juntou-se ao teu império.")
            except: pass

    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    btn_play = telebot.types.InlineKeyboardButton("🔱 ENTER THE EMPIRE", web_app=telebot.types.WebAppInfo(url=WEB_APP_URL))
    btn_news = telebot.types.InlineKeyboardButton("📢 News Channel", url="https://t.me/ton_empire_news")
    markup.add(btn_play, btn_news)

    welcome_text = (
        f"💎 **WELCOME TO TON EMPIRE 2026** 💎\n\n"
        f"Greetings, {username}!\n"
        "Your path to crypto dominance starts here.\n\n"
        "🚀 **Level Up** to multiply earnings\n"
        "🎰 **Spin** to earn real TON\n"
        "👥 **Invite** friends for Golden Tickets\n\n"
        "👇 *Enter the command center below:*"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup)

# --- API DO JOGO (ROTAS DO FRONTEND) ---

@app.route('/sync_data')
def sync():
    uid = str(request.args.get('user_id'))
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data: return jsonify({"error": "User not found"}), 404
    
    u = res.data[0]
    now = datetime.now()
    
    # 1. LÓGICA DE AUTO-FARMING (GANHO PASSIVO)
    # Ganha 0.00005 TON por hora offline, máximo de 3 horas.
    last_spin = datetime.fromisoformat(u['last_spin'].replace('Z', '+00:00'))
    hours_away = min(3, (now.replace(tzinfo=None) - last_spin.replace(tzinfo=None)).total_seconds() / 3600)
    passive_gain = round(hours_away * 0.00005 * u['level'], 6)
    
    if passive_gain > 0:
        new_bal = u['balance'] + passive_gain
        supabase.table("users").update({"balance": new_bal}).eq("uid", uid).execute()
        u['balance'] = new_bal

    return jsonify({
        "user": u,
        "passive_gain": passive_gain,
        "server_time": now.isoformat()
    })

@app.route('/reward_spin', methods=['POST'])
def reward():
    data = request.get_json()
    uid = str(data.get('user_id'))
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    if u['energy'] <= 0: return jsonify({"error": "Energy empty"}), 400
    
    # Cálculo Multiplicador (RPG + VIP)
    multiplier = 1 + (u['level'] * 0.01)
    if u.get('is_vip'): multiplier *= 1.5
    
    win_amount = round(0.00015 * multiplier, 6)
    new_xp = u['xp'] + 20
    new_lvl = (new_xp // 100) + 1
    
    upd = {
        "balance": round(u['balance'] + win_amount, 6),
        "energy": u['energy'] - 1,
        "xp": new_xp,
        "level": new_lvl,
        "last_spin": datetime.now().isoformat()
    }
    supabase.table("users").update(upd).eq("uid", uid).execute()
    return jsonify({"win": win_amount, "new_bal": upd['balance'], "lvl_up": new_lvl > u['level']})

@app.route('/daily_bonus', methods=['POST'])
def daily():
    uid = str(request.get_json().get('user_id'))
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    now = datetime.now()
    last = datetime.fromisoformat(u['last_checkin']) if u['last_checkin'] else datetime.min
    
    if (now - last.replace(tzinfo=None)) < timedelta(days=1):
        return jsonify({"error": "Already claimed today"}), 400
        
    supabase.table("users").update({"energy": 10, "last_checkin": now.isoformat()}).eq("uid", uid).execute()
    return jsonify({"success": True})

# --- PAINEL ADMIN AVANÇADO ---

@app.route('/admin_master_stats')
def admin_stats():
    uid = request.args.get('user_id')
    if uid != ADMIN_ID: return "Unauthorized", 403
    
    users = supabase.table("users").select("balance").execute()
    total_debt = sum(u['balance'] for u in users.data)
    
    return jsonify({
        "total_players": len(users.data),
        "total_debt": round(total_debt, 4),
        "server_status": "OPTIMIZED",
        "payouts_pending": 0 # Pode ser ligado a uma tabela de 'payouts'
    })

@app.route('/admin_broadcast', methods=['POST'])
def broadcast():
    data = request.get_json()
    if str(data.get('admin_id')) != ADMIN_ID: return "Forbidden", 403
    
    msg = data.get('message')
    users = supabase.table("users").select("uid").execute()
    
    count = 0
    for u in users.data:
        try:
            bot.send_message(u['uid'], f"📢 **EMPIRE NEWS:**\n\n{msg}", parse_mode="Markdown")
            count += 1
            time.sleep(0.05) # Evita spam block do Telegram
        except: pass
    return jsonify({"sent_to": count})

# --- INICIALIZAÇÃO ---
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    # Roda o Bot e o Flask juntos
    Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
