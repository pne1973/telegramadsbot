<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>MyEarn TON Pro</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
    <style>
        :root { --bg: #0b0f14; --card: #1c222b; --blue: #0088cc; --green: #28a745; --text-dim: #818d99; --gold: #ffaa00; } [cite: 12, 13]
        * { box-sizing: border-box; margin: 0; padding: 0; } [cite: 14]
        body { background: var(--bg); color: #fff; font-family: sans-serif; display: flex; justify-content: center; min-height: 100vh; padding: 20px 16px; } [cite: 15, 16]
        .app-container { width: 100%; max-width: 420px; display: flex; flex-direction: column; align-items: center; } [cite: 17]
        .glass-card { background: var(--card); padding: 24px; border-radius: 24px; margin-bottom: 16px; width: 100%; text-align: center; } [cite: 18, 19]
        .tabs { display: flex; gap: 8px; margin-bottom: 20px; background: rgba(0,0,0,0.3); padding: 5px; border-radius: 16px; width: 100%; } [cite: 20, 21]
        .tab { flex: 1; padding: 12px; border-radius: 12px; background: transparent; border: none; color: var(--text-dim); font-weight: bold; cursor: pointer; } [cite: 22, 23]
        .tab.active { background: var(--blue); color: #fff; } [cite: 24]
        .btn { display: block; width: 100%; padding: 18px; border-radius: 16px; font-weight: bold; border: none; cursor: pointer; color: #fff; text-align: center; margin-bottom: 10px; } [cite: 25, 26]
        .btn-blue { background: var(--blue); } [cite: 27]
        .btn-green { background: var(--green); } [cite: 28]
        .tab-content { display: none; width: 100%; } [cite: 30]
        .tab-content.active { display: block; } [cite: 31]
    </style>
</head>
<body>
<div class="app-container">
    <div class="tabs">
        <button class="tab active" onclick="showTab('earn')">Earn</button>
        <button class="tab" onclick="showTab('wallet')">Wallet</button>
    </div>

    <div id="earn" class="tab-content active">
        <div class="glass-card">
            <h2 id="balance" style="color: var(--gold)">0.0000 TON</h2>
            <p style="color: var(--text-dim)">Ready to claim</p>
        </div>
        <button class="btn btn-blue" onclick="handleClaim()">Claim Rewards</button>
        
        <div class="glass-card" style="margin-top: 20px;">
            <h3>Refer & Earn</h3>
            <p style="color: var(--text-dim); font-size: 13px;">Get 0.005 TON for every active friend.</p>
            <button class="btn btn-green" onclick="shareReferral()">Invite Friend</button>
        </div>
    </div>

    <div id="wallet" class="tab-content">
        <div class="glass-card">
            <p>Withdrawal Minimum: 1.0 TON</p>
        </div>
        <button class="btn btn-green">Connect Wallet</button>
    </div>
</div>

<script>
    const tg = window.Telegram.WebApp;
    tg.expand(); [cite: 33]
    const API_URL = "https://your-render-url.onrender.com"; // REPLACE THIS
    const userId = tg.initDataUnsafe?.user?.id;

    async function loadData() {
        const startParam = tg.initDataUnsafe?.start_param;
        const res = await fetch(`${API_URL}/get_user_info?user_id=${userId}&ref_by=${startParam || ''}`);
        const data = await res.json();
        document.getElementById('balance').innerText = `${data.bal} TON`;
    }

    async function handleClaim() {
        const res = await fetch(`${API_URL}/reward?user_id=${userId}`);
        const data = await res.json();
        if (data.status === "ok") {
            document.getElementById('balance').innerText = `${data.new_bal} TON`;
            confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } }); [cite: 37]
        } else {
            tg.showAlert("Daily limit reached!");
        }
    }

    function shareReferral() {
        const botLink = `https://t.me/MyEarnTonBot?start=${userId}`;
        tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(botLink)}&text=Earn%20TON%20with%20me!`);
    }

    function showTab(tabId) {
        document.querySelectorAll('.tab, .tab-content').forEach(el => el.classList.remove('active')); [cite: 34]
        event.currentTarget.classList.add('active');
        document.getElementById(tabId).classList.add('active'); [cite: 35]
        if (tg.HapticFeedback) tg.HapticFeedback.impactOccurred('light'); [cite: 36]
    }

    loadData();
</script>
</body>
</html>
