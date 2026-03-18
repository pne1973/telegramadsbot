import os, requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

# Env Vars (Ensure these are set in Render Dashboard)
supabase: Client = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))
BOT_TOKEN = "8609038498:AAFzTSVCg2XzwAFsfc8xiA20jEIiPMIxmzc"
CHANNEL_ID = "-1003836027199"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    if "message" in data:
        msg = data["message"]
        uid = str(msg["from"]["id"])
        text = msg.get("text", "")
        
        # Referral Detection
        ref_by = text.split(" ")[1] if text.startswith("/start ") and len(text.split(" ")) > 1 else None
        
        # Register User
        res = supabase.table("users").select("*").eq("uid", uid).execute()
        if not res.data:
            supabase.table("users").insert({"uid": uid, "bal": 0.0, "referred_by": ref_by}).execute()
            if ref_by and ref_by != uid:
                # Reward Referrer
                r = supabase.table("users").select("bal", "referrals_count").eq("uid", ref_by).execute()
                if r.data:
                    supabase.table("users").update({
                        "bal": r.data[0]['bal'] + 0.001, 
                        "referrals_count": r.data[0]['referrals_count'] + 1
                    }).eq("uid", ref_by).execute()

        # Welcome Msg
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": uid,
            "text": "🚀 *Welcome to MyEarn TON!*\nWatch ads, invite friends, and withdraw TON.",
            "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": [[{"text": "🚀 Open App", "web_app": {"url": "https://pne1973.github.io/mini-app/"}}]]}
        })
    return "OK", 200

@app.route('/check_eligibility')
def check_eligibility():
    uid = request.args.get('user_id')
    # Check Sub
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id={CHANNEL_ID}&user_id={uid}"
    is_subbed = False
    try:
        r = requests.get(url).json()
        is_subbed = r.get("result", {}).get("status") in ['member', 'administrator', 'creator']
    except: pass

    # Check Database
    u = supabase.table("users").select("*").eq("uid", uid).execute()
    bal = u.data[0]['bal'] if u.data else 0.0
    refs = u.data[0]['referrals_count'] if u.data else 0
    
    return jsonify({
        "bal": bal,
        "is_subbed": is_subbed,
        "ref_count": refs,
        "eligible": (is_subbed and refs >= 3)
    })

@app.route('/reward')
def reward():
    uid = request.args.get('user_id')
    u = supabase.table("users").select("bal").eq("uid", uid).execute()
    new_bal = u.data[0]['bal'] + 0.0002
    supabase.table("users").update({"bal": new_bal}).eq("uid", uid).execute()
    return jsonify({"status": "ok", "new_bal": new_bal})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
