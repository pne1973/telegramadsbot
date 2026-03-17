import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Database Structure: 
# {user_id: {"bal": 0.0, "daily_count": 0, "last_claim": "date", "payouts": [{"amt": 0.5, "status": "Pending", "date": "..."}]}}
db = {}

@app.route('/get_user_info')
def info():
    uid = request.args.get('user_id')
    today = datetime.now().strftime("%Y-%m-%d")
    
    if uid not in db:
        db[uid] = {
            "bal": 0.0, "daily_count": 0, "last_claim": today, 
            "refs": 0, "ad_total": 0, "ref_by": request.args.get('ref_by'), 
            "payouts": []
        }
            
    if db[uid]["last_claim"] != today:
        db[uid]["daily_count"] = 0
        db[uid]["last_claim"] = today
            
    return jsonify({
        "bal": float(f"{db[uid]['bal']:.4f}"),
        "daily_count": db[uid]["daily_count"],
        "refs": db[uid]["refs"],
        "payouts": db[uid]["payouts"][-3:] # Send last 3 payouts
    })

@app.route('/reward')
def reward():
    uid = request.args.get('user_id')
    if uid in db:
        if db[uid]["daily_count"] >= 15:
            return jsonify({"error": "Limit"}), 400
        db[uid]["bal"] += 0.0002
        db[uid]["daily_count"] += 1
        return jsonify({"status": "ok", "new_bal": f"{db[uid]['bal']:.4f}"})
    return jsonify({"error": "not_found"}), 404

@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    uid, wallet = data.get('user_id'), data.get('wallet')
    if uid in db and db[uid]["bal"] >= 1.0:
        amt = db[uid]["bal"]
        db[uid]["bal"] = 0 
        # Add to history
        new_payout = {
            "amt": float(f"{amt:.4f}"),
            "status": "Pending",
            "date": datetime.now().strftime("%b %d")
        }
        db[uid]["payouts"].append(new_payout)
        print(f"💰 PAYOUT REQUEST: {uid} | {amt} TON | {wallet}")
        return jsonify({"status": "success"})
    return jsonify({"error": "Min 1.0 TON"}), 400

if __name__ == "__main__":
    # This is only used for local testing; Gunicorn uses the 'app' object directly.
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
