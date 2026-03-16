import os, asyncio, aiosqlite, logging, time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiohttp import web

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5401881400")) 
REWARD_PER_AD = 0.001  # Your profitable rate
DAILY_BONUS = 0.05    # Daily loyalty reward
MIN_WITHDRAW = 5.0    # Payout threshold

bot = Bot(token=TOKEN)
dp = Dispatcher()

class WithdrawState(StatesGroup):
    waiting_for_address = State()

# 1. Database Initialization
async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, 
            total_ads INTEGER DEFAULT 0, last_bonus TIMESTAMP DEFAULT NULL)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
            amount REAL, wallet TEXT, status TEXT DEFAULT 'PENDING')""")
        await db.commit()

# 2. Web API Endpoints (Syncs with index.html)
async def handle_reward(request):
    uid = int(request.query.get("user_id"))
    verify = request.query.get("verify")
    # Basic Anti-Cheat
    if not verify or abs(int(verify) - int(time.time())) > 120:
        return web.Response(text="Security fail", status=403)

    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET balance = balance + ?, total_ads = total_ads + 1 WHERE user_id = ?", (REWARD_PER_AD, uid))
        await db.commit()
    return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})

async def handle_daily(request):
    uid = int(request.query.get("user_id"))
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT last_bonus FROM users WHERE user_id = ?", (uid,)) as cur:
            row = await cur.fetchone()
            now = datetime.now()
            if row and row[0] and datetime.fromisoformat(row[0]) > now - timedelta(days=1):
                return web.Response(text="Wait 24h", status=403)
            
            await db.execute("UPDATE users SET balance = balance + ?, last_bonus = ? WHERE user_id = ?", (DAILY_BONUS, now.isoformat(), uid))
            await db.commit()
    return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})

# 3. Admin & User Handlers
@dp.message(Command("admin_stats"), F.from_user.id == ADMIN_ID)
async def cmd_admin(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT COUNT(*), SUM(total_ads), SUM(balance) FROM users") as cur:
            users, ads, owed = await cur.fetchone()
    text = (f"📈 **OWNER STATS**\n\nUsers: `{users}`\nAds Served: `{ads or 0}`\nTotal Liability: `{owed or 0:.3f} TON`\n\n"
            f"💰 Est. Revenue: `${(ads or 0) * 0.003:.2f}`")
    await message.answer(text)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,)) as cur:
            if not await cur.fetchone():
                await db.execute("INSERT INTO users (user_id, balance) VALUES (?, 0)", (uid,))
                await db.commit()
    kb = [[types.KeyboardButton(text="💰 EARN", web_app=types.WebAppInfo(url="https://pne1973.github.io"))],
          [types.KeyboardButton(text="💳 BALANCE"), types.KeyboardButton(text="🏦 WITHDRAW")]]
    await message.answer("💎 **TON Earner Pro**\nStart earning now!", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.text == "💳 BALANCE")
async def cmd_bal(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance, total_ads FROM users WHERE user_id = ?", (message.from_user.id,)) as cur:
            bal, ads = await cur.fetchone()
            await message.answer(f"💳 **Your Wallet**\n\nBalance: `{bal:.3f} TON`\nAds Watched: `{ads}`")

@dp.message(F.text == "🏦 WITHDRAW")
async def cmd_withdraw(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) as cur:
            bal = (await cur.fetchone())[0]
            if bal < MIN_WITHDRAW: return await message.answer(f"❌ Min payout: {MIN_WITHDRAW} TON")
            await message.answer("🏦 Send your **TON Wallet Address**:"); await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def process_payout(message: types.Message, state: FSMContext):
    wallet, uid = message.text, message.from_user.id
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (uid,)) as cur:
            bal = (await cur.fetchone())[0]
            await db.execute("INSERT INTO withdrawals (user_id, amount, wallet) VALUES (?, ?, ?)", (uid, bal, wallet))
            await db.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (uid,))
            await db.commit()
    await bot.send_message(ADMIN_ID, f"🔔 **PAYOUT REQUEST**\nUser: `{uid}`\nAmount: `{bal:.3f} TON`\nWallet: `{wallet}`")
    await message.answer("✅ Request Sent! Wait for admin approval."); await state.clear()

async def main():
    await init_db()
    app = web.Application()
    app.router.add_get('/reward', handle_reward); app.router.add_get('/daily', handle_daily)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", "10000"))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
