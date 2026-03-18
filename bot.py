import random
from datetime import datetime, timedelta

# --- NEW ADD-ONS ---

@app.route('/daily_claim')
def daily_claim():
    uid = request.args.get('user_id')
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    now = datetime.now()
    last = u.get('last_checkin')
    
    if last:
        last_dt = datetime.fromisoformat(last.replace('Z', '+00:00'))
        if now - last_dt < timedelta(hours=24):
            return jsonify({"error": "Come back tomorrow!"}), 400
        
        # Check if they missed a day (Reset streak)
        if now - last_dt > timedelta(hours=48):
            streak = 1
        else:
            streak = u['streak_days'] + 1
    else:
        streak = 1

    # Budget-Friendly Rewards (Scale with streak)
    reward = 0.0001 + (min(streak, 7) * 0.00005) 
    new_bal = u['bal'] + reward
    
    supabase.table("users").update({
        "bal": new_bal, 
        "last_checkin": now.isoformat(),
        "streak_days": streak
    }).eq("uid", uid).execute()

    return jsonify({"new_bal": new_bal, "streak": streak, "reward": reward})

@app.route('/lucky_spin')
def lucky_spin():
    uid = request.args.get('user_id')
    u = supabase.table("users").select("bal").eq("uid", uid).execute().data[0]
    
    # Randomizer Logic (House always wins)
    # 80% small, 15% medium, 5% Jackpot
    roll = random.random()
    if roll < 0.80:
        win = 0.0001
        msg = "Common Win!"
    elif roll < 0.95:
        win = 0.0005
        msg = "Rare Win! ⭐"
    else:
        win = 0.0025
        msg = "JACKPOT! 🔥"

    new_bal = u['bal'] + win
    supabase.table("users").update({"bal": new_bal}).eq("uid", uid).execute()
    
    return jsonify({"new_bal": new_bal, "win": win, "msg": msg})