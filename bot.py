import os, requests, urllib.parse
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
BOT_TOKEN = "8609038498:AAFzTSVCg2XzwAFsfc8xiA20jEIiPMIxmzc"

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json(force=True)
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        # Basic /start handler
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": chat_id,
            "text": "🚀 *Welcome back!* Click below to earn TON.",
            "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": [[{"text": "🚀 Open App", "web_app": {"url": "https://pne1973.github.io/mini-app/"}}]]}
        })
    return "OK", 200

@app.route('/get_user_info')
def info():
    uid = request.args.get('user_id')
    res = supabase.table("users").select("*").eq("uid", uid).execute()
    if not res.data:
        user = {"uid": uid, "bal": 0.0}
        supabase.table("users").insert(user).execute()
        return jsonify(user)
    return jsonify(res.data[0])

@app.route('/reward')
def reward():
    uid = request.args.get('user_id')
    res = supabase.table("users").select("bal").eq("uid", uid).execute()
    new_bal = res.data[0]['bal'] + 0.0002
    supabase.table("users").update({"bal": new_bal}).eq("uid", uid).execute()
    return jsonify({"status": "ok", "new_bal": new_bal})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
