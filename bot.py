import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Database Structure
# {user_id: {"bal": 0.0, "daily_count": 0, "last_claim": "date", "refs": 0, "ad_total": 0, "ref_by": "id", "bonus_paid": False, "payouts": []}}
db = {}

ADMIN_PASSWORD = "sporting" # Change this to your own secret key

@app.route('/get_user_info')
def info():
    uid = request.args.get('user_id')
    ref_by = request.args.get('ref_by')
    today = datetime.now().strftime("%Y-%m-%d")
    
    if uid not in db:
        db[uid] = {
            "bal": 0.0, "daily_count": 0, "last_claim": today, 
            "refs": 0, "ad_total": 0, "ref_by": ref_by, 
            "bonus_paid": False, "payouts": []
        }
            
    if db[uid]["last_claim"] != today:
        db[uid]["daily_count"] = 0
        db[uid]["last_claim"] = today
            
    return jsonify({
        "bal": float(f"{db[uid]['bal']:.4f}"),
        "daily_count": db[uid]["daily_count"],
        "refs": db[uid]["refs"],
        "payouts": db[uid]["payouts"][-3:] # Last 3 transactions
    })

@app.route('/reward')
def reward():
    uid = request.args.get('user_id')
    if uid in db:
        if db[uid]["daily_count"] >= 15:
            return jsonify({"error": "Limit reached"}), 400
        
        db[uid]["bal"] += 0.0002
        db[uid]["daily_count"] += 1
        db[uid]["ad_total"] += 1
        
        # Anti-Fraud Referral Bonus (Pays out after friend watches 5 ads)
        ref_id = db[uid].get("ref_by")
        if ref_id and ref_id in db and db[uid]["ad_total"] == 5 and not db[uid]["bonus_paid"]:
            db[ref_id]["bal"] += 0.005
            db[ref_id]["refs"] += 1
            db[uid]["bonus_paid"] = True
            
        return jsonify({"status": "ok", "new_bal": f"{db[uid]['bal']:.4f}"})
    return jsonify({"error": "User not found"}), 404

@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    uid, wallet = data.get('user_id'), data.get('wallet')
    if uid in db and db[uid]["bal"] >= 1.0:
        amt = db[uid]["bal"]
        db[uid]["bal"] = 0 
        new_payout = {
            "amt": float(f"{amt:.4f}"),
            "status": "Pending",
            "date": datetime.now().strftime("%b %d")
        }
        db[uid]["payouts"].append(new_payout)
        print(f"💰 PAYOUT ALERT: User {uid} | Wallet {wallet} | Amt {amt} TON")
        return jsonify({"status": "success"})
    return jsonify({"error": "Minimum 1.0 TON required"}), 400

@app.route('/admin_pay')
def admin_pay():
    auth = request.args.get('pass')
    uid = request.args.get('user_id')
    if auth != ADMIN_PASSWORD:
        return "Unauthorized", 401
    if uid in db and db[uid]["payouts"]:
        for p in db[uid]["payouts"]:
            if p["status"] == "Pending":
                p["status"] = "Paid"
        return f"User {uid} payouts marked as Paid!"
    return "No pending payouts.", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
