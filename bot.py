import os
import telebot
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from threading import Thread

# --- 1. CONFIGURAÇÃO DE SEGURANÇA (RENDER) ---
# Vai buscar o Token que colocaste nas Environment Variables do Render
TOKEN = os.environ.get("BOT_TOKEN")

# Verifica se o token existe e é válido antes de iniciar
if not TOKEN or ":" not in TOKEN:
    print("❌ ERRO CRÍTICO: BOT_TOKEN não configurado corretamente no Render!")
    bot = None
else:
    bot = telebot.TeleBot(TOKEN)
    print("✅ Bot configurado com sucesso!")

# --- 2. CONFIGURAÇÃO DO SUPABASE ---
S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(S_URL, S_KEY)

# Teu ID de Administrador
ADMIN_ID = "5401881400"

# --- 3. CONFIGURAÇÃO DO SERVIDOR API (FLASK) ---
app = Flask(__name__)
CORS(app) # Permite que o GitHub Pages aceda a estes dados

@app.route('/')
def health_check():
    return "Servidor TON EMPIRE Online 🚀", 200

# Rota para carregar os dados do utilizador no jogo
@app.route('/check_eligibility', methods=['GET'])
def check():
    uid = str(request.args.get('user_id'))
    try:
        res = supabase.table("users").select("*").eq("uid", uid).execute()
        if not res.data:
            user_data = {"uid": uid, "balance": 0.0, "energy": 10, "xp": 0, "level": 1}
            supabase.table("users").insert(user_data).execute()
            return jsonify(user_data)
        return jsonify(res.data[0])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Rota para dar a recompensa do Spin
@app.route('/reward_spin', methods=['POST'])
def reward():
    data = request.get_json()
    uid = str(data.get('user_id'))
    try:
        u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
        if u['energy'] <= 0:
            return jsonify({"error": "Sem energia"}), 400
        
        novo_saldo = round(u['balance'] + 0.0002, 6)
        nova_energia = u['energy'] - 1
        
        supabase.table("users").update({"balance": novo_saldo, "energy": nova_energia}).eq("uid", uid).execute()
        return jsonify({"win": 0.0002, "new_balance": novo_saldo})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Rota para o Painel de Admin (Cálculo de Dívida e Users)
@app.route('/admin_stats')
def admin_stats():
    uid = request.args.get('user_id')
    if uid != ADMIN_ID:
        return jsonify({"error": "Não autorizado"}), 403
    
    try:
        users = supabase.table("users").select("balance").execute()
        total_users = len(users.data)
        total_debt = sum(x['balance'] for x in users.data)
        return jsonify({"total_users": total_users, "debt": round(total_debt, 4)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 4. LÓGICA DO TELEGRAM (MENU INICIAL) ---
if bot:
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        # Link do teu frontend no GitHub Pages
        web_app_url = "https://pne1973.github.io/mini-app/"
        
        markup = telebot.types.InlineKeyboardMarkup()
        btn = telebot.types.InlineKeyboardButton("🎮 JOGAR AGORA", web_app=telebot.types.WebAppInfo(url=web_app_url))
        markup.add(btn)
        
        texto = (
            "💎 **BEM-VINDO AO TON EMPIRE 2026**\n\n"
            "Ganhe TON real assistindo anúncios e subindo de nível!\n\n"
            "👇 Clique no botão abaixo para abrir o jogo:"
        )
        bot.send_message(message.chat.id, texto, parse_mode="Markdown", reply_markup=markup)

# --- 5. EXECUÇÃO SIMULTÂNEA (BOT + API) ---
def run_bot():
    if bot:
        bot.infinity_polling()

if __name__ == "__main__":
    # Inicia o bot numa linha separada (Thread)
    Thread(target=run_bot).start()
    
    # Inicia o servidor na porta que o Render exige
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
