@app.route('/verify_channel')
def verify_channel():
    uid = request.args.get('user_id')
    u = supabase.table("users").select("*").eq("uid", uid).execute().data[0]
    
    if u.get('joined_channel'):
        return jsonify({"error": "Already claimed!"}), 400

    # Telegram API Check
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id={CHANNEL_ID}&user_id={uid}"
    try:
        r = requests.get(url).json()
        status = r.get("result", {}).get("status")
        # 'member', 'administrator', or 'creator' means they are in
        if status in ['member', 'administrator', 'creator']:
            new_bal = u['bal'] + 0.005
            supabase.table("users").update({"bal": new_bal, "joined_channel": True}).eq("uid", uid).execute()
            return jsonify({"new_bal": new_bal, "msg": "Success! +0.005 TON added."})
        else:
            return jsonify({"error": "You haven't joined yet!"}), 400
    except:
        return jsonify({"error": "Verification failed. Try later."}), 500
