import os, telebot, time
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client
from threading import Thread

TOKEN = os.environ.get("BOT_TOKEN")
S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_ID = "5401881400" 

bot = telebot.TeleBot(TOKEN)
supabase = create_client(S_URL, S_KEY)
app = Flask(__name__)
CORS(app)

@app.route('/check_eligibility')
def check():
    uid = str(request.args.get('user_id'))
    ref_by = request.args.get('ref_by', "None")
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    
    if not res.data:
        data = {"uid": uid, "balance": 0.0, "energy": 10, "xp": 0, "level": 1, "last_regen": int(time.time()), "referred_by": ref_by}
        supabase.table("users").insert(data).execute()
        return jsonify(data)
    
    u = res.data[0]
    # BOOSTER DE ENERGIA: Nível 1-9 (10), 10-19 (15), 20+ (20)
    max_nrg = 10
    if u['level'] >= 20: max_nrg = 20
    elif u['level'] >= 10: max_nrg = 15
    
    now = int(time.time())
    diff = now - u.get('last_regen', now)
    points = diff // 1800 
    if points > 0:
        new_nrg = min(max_nrg, u['energy'] + points)
        supabase.table("users").update({"energy": new_nrg, "last_regen": now}).eq("uid", uid).execute()
        u['energy'] = new_nrg
    u['max_energy'] = max_nrg
    return jsonify(u)

@app.route('/reward_spin', methods=['POST'])
def reward():
    uid = str(request.json.get('user_id'))
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    if u['energy'] <= 0: return jsonify({"error": "Sem energia!"}), 400
    
    # BOOSTER DE PRÉMIO: Nível 20+ ganha 0.00025
    reward_val = 0.00025 if u['level'] >= 20 else 0.0002
    
    new_xp = u['xp'] + 10
    new_lvl = u['level']
    if new_xp >= 100:
        new_xp = 0
        new_lvl += 1
    
    new_bal = round(u['balance'] + reward_val, 6)
    supabase.table("users").update({"balance": new_bal, "energy": u['energy'] - 1, "xp": new_xp, "level": new_lvl, "last_regen": int(time.time())}).eq("uid", uid).execute()

    # SISTEMA DE REFERRAL: 10% de comissão para o Padrinho
    if u.get('referred_by') and u['referred_by'] != "None":
        padrinho = supabase.table("users").select("balance").eq("uid", u['referred_by']).execute()
        if padrinho.data:
            bonus = round(reward_val * 0.1, 7)
            novo_bal_pad = round(padrinho.data[0]['balance'] + bonus, 6)
            supabase.table("users").update({"balance": novo_bal_pad}).eq("uid", u['referred_by']).execute()

    return jsonify({"balance": new_bal, "energy": u['energy']-1, "xp": new_xp, "level": new_lvl})

@app.route('/request_withdraw', methods=['POST'])
def withdraw():
    uid = str(request.json.get('user_id'))
    u = supabase.table("users").select("balance").eq("uid", uid).execute().data[0]
    # TRAVA DE 3 AMIGOS
    friends = supabase.table("users").select("uid").eq("referred_by", uid).execute()
    if len(friends.data) < 3:
        return jsonify({"error": f"Bloqueio: Precisas de 3 convites. Tens: {len(friends.data)}/3"}), 403
    if u['balance'] < 0.5: return jsonify({"error": "Mínimo 0.5 TON."}), 400
    return jsonify({"success": "Pedido enviado!"})

if __name__ == "__main__":
    Thread(target=lambda: bot.infinity_polling()).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
