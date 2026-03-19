import os
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client

app = Flask(__name__)
CORS(app)

# --- CONFIGURAÇÃO (Variáveis de Ambiente no Render) ---
S_URL = os.environ.get("SUPABASE_URL")
S_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(S_URL, S_KEY)
ADMIN_ID = "5401881400"

@app.route('/check_eligibility', methods=['GET'])
def check():
    uid = str(request.args.get('user_id'))
    ref = request.args.get('ref') # ID de quem convidou
    
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data:
        user_data = {
            "uid": uid, 
            "referred_by": ref if ref != uid else None, 
            "energy": 10, 
            "balance": 0,
            "xp": 0,
            "level": 1
        }
        supabase.table("users").insert(user_data).execute()
        if ref and ref != uid:
            # Chama a função SQL que criaste para dar tickets
            supabase.rpc("increment_ref", {"mestre_id": ref}).execute()
        return jsonify(user_data)
    
    return jsonify(res.data[0])

@app.route('/reward_spin', methods=['POST'])
def reward():
    data = request.get_json()
    uid = str(data.get('user_id'))
    use_ticket = data.get('use_ticket', False)
    
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    if u['energy'] <= 0 and not use_ticket:
        return jsonify({"error": "No energy! Wait or use Ticket."}), 400

    # LÓGICA DE LUCRO (TON @ 1.253 / CPM @ 1.429)
    base_win = 0.00015
    # Bónus de Nível: +1% por nível
    multiplier = (1 + (u['level'] * 0.01))
    if use_ticket: multiplier *= 5 # Golden Ticket dá 5x mais
    
    total_win = base_win * multiplier
    new_xp = u['xp'] + 20
    new_lvl = (new_xp // 100) + 1
    
    # Atualização do Utilizador
    upd = {
        "balance": round(u['balance'] + total_win, 6),
        "xp": new_xp,
        "level": new_lvl,
        "energy": u['energy'] - 1 if not use_ticket else u['energy']
    }
    if use_ticket: upd["tickets"] = u['tickets'] - 1
    
    supabase.table("users").update(upd).eq("uid", uid).execute()

    # 10% Referral Commission (Rendimento Passivo)
    if u['referred_by']:
        p = supabase.table("users").select("balance").eq("uid", u['referred_by']).execute().data
        if p:
            new_p_bal = round(p[0]['balance'] + (total_win * 0.1), 6)
            supabase.table("users").update({"balance": new_p_bal}).eq("uid", u['referred_by']).execute()

    return jsonify({"win": total_win, "new_balance": upd["balance"]})

@app.route('/daily_checkin', methods=['POST'])
def daily():
    uid = str(request.get_json().get('user_id'))
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    now = datetime.datetime.now(datetime.timezone.utc)
    last_check = u.get('last_checkin')
    
    if last_check:
        last_dt = datetime.datetime.fromisoformat(last_check.replace('Z', '+00:00'))
        if (now - last_dt).total_seconds() < 86400:
            return jsonify({"success": False, "msg": "Try again tomorrow!"}), 400

    supabase.table("users").update({
        "xp": u['xp'] + 50,
        "energy": 10,
        "last_checkin": now.isoformat()
    }).eq("uid", uid).execute()
    
    return jsonify({"success": True, "msg": "Daily Bonus: +50 XP & Energy Refilled!"})

@app.route('/admin_stats')
def admin():
    if request.args.get('user_id') != ADMIN_ID: return "Forbidden", 403
    users = supabase.table("users").select("balance", count="exact").execute()
    total_debt = sum(x['balance'] for x in users.data)
    return jsonify({"total_users": users.count, "debt": round(total_debt, 4)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
