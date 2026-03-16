import os, asyncio, aiosqlite, logging, time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.deep_linking import create_start_link
from aiohttp import web

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5401881400"))
MIN_WITHDRAW = 5.0 
WEBAPP_URL = "https://pne1973.github.io"

bot = Bot(token=TOKEN)
dp = Dispatcher()

class BotStates(StatesGroup):
    waiting_for_address = State()
    waiting_for_broadcast = State()

# 1. Database Setup
async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, full_name TEXT, balance REAL DEFAULT 0, 
            referred_by INTEGER DEFAULT NULL, total_ads INTEGER DEFAULT 0,
            last_bonus TIMESTAMP DEFAULT NULL)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, wallet TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        await db.commit()

# 2. Keyboard Helper
def main_menu():
    kb = [
        [types.KeyboardButton(text="💰 OPEN APP", web_app=types.WebAppInfo(url=WEBAPP_URL)), types.KeyboardButton(text="💳 BALANCE")],
        [types.KeyboardButton(text="🚀 REFER"), types.KeyboardButton(text="🏆 TOP 10")],
        [types.KeyboardButton(text="📜 HISTORY")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# 3. Reward APIs
async def handle_reward(request):
    user_id, verify = int(request.query.get("user_id")), request.query.get("verify")
    if not verify or abs(int(verify) - int(time.time())) > 60:
        return web.Response(text="Invalid", status=403)
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET balance = balance + 0.01, total_ads = total_ads + 1 WHERE user_id = ?", (user_id,))
        async with db.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row and row[0]: await db.execute("UPDATE users SET balance = balance + 0.001 WHERE user_id = ?", (row[0],))
        await db.commit()
    return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})

async def handle_daily(request):
    uid = int(request.query.get("user_id"))
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT last_bonus FROM users WHERE user_id = ?", (uid,)) as cur:
            last = (await cur.fetchone())[0]
            now = datetime.now()
            if last and datetime.fromisoformat(last) > now - timedelta(days=1):
                return web.Response(text="Wait 24h", status=403)
            await db.execute("UPDATE users SET balance = balance + 0.05, last_bonus = ? WHERE user_id = ?", (now.isoformat(), uid))
            await db.commit()
    try: await bot.send_message(uid, "🎁 Daily Bonus Claimed: +0.05 TON!")
    except: pass
    return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})

# 4. Bot Handlers
@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    uid, name = message.from_user.id, message.from_user.full_name
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,)) as cur:
            if not await cur.fetchone():
                ref = int(command.args) if command.args and command.args.isdigit() and int(command.args) != uid else None
                await db.execute("INSERT INTO users (user_id, full_name, balance, referred_by) VALUES (?, ?, 0, ?)", (uid, name, ref))
                if ref: await bot.send_message(ref, f"🎉 New Referral: {name}")
        await db.commit()
    await message.answer(f"💎 **PRO DASHBOARD**\nEarn TON by watching ads!", reply_markup=main_menu())

@dp.message(F.text == "💳 BALANCE")
async def menu_balance(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance, total_ads FROM users WHERE user_id = ?", (message.from_user.id,)) as cur:
            row = await cur.fetchone()
            if row: await message.answer(f"💳 **WALLET**\n\nBalance: `{row[0]:.2f} TON`\nAds Watched: `{row[1]}`\n\nUse /withdraw to cash out.")

@dp.message(F.text == "🚀 REFER")
async def menu_refer(message: types.Message):
    link = await create_start_link(bot, str(message.from_user.id), encode=False)
    await message.answer(f"🤝 **REFERRAL**\nEarn 10% commission!\n\n`{link}`")

@dp.message(F.text == "🏆 TOP 10")
async def menu_leaderboard(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        query = "SELECT u.full_name, COUNT(r.user_id) FROM users r JOIN users u ON r.referred_by = u.user_id GROUP BY r.referred_by ORDER BY COUNT(r.user_id) DESC LIMIT 10"
        async with db.execute(query) as cur:
            rows = await cur.fetchall()
            text = "🏆 **TOP 10 REFERRERS**\n\n" + "\n".join([f"{i+1}. {r[0]} — {r[1]}" for i, r in enumerate(rows)])
            await message.answer(text if rows else "No referrers.")

@dp.message(F.text == "📜 HISTORY")
async def menu_history(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT amount, date FROM withdrawals WHERE user_id = ? ORDER BY date DESC LIMIT 5", (message.from_user.id,)) as cur:
            rows = await cur.fetchall()
            text = "📜 **HISTORY**\n\n" + "\n".join([f"💰 {r[0]} TON | {r[1].split(' ')[0]}" for r in rows])
            await message.answer(text if rows else "No history.")

@dp.message(Command("broadcast"), F.from_user.id == ADMIN_ID)
async def start_broadcast(message: types.Message, state: FSMContext):
    await message.answer("📢 Message to broadcast:"); await state.set_state(BotStates.waiting_for_broadcast)

@dp.message(BotStates.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            users = await cur.fetchall()
    count = 0
    for u in users:
        try: await bot.send_message(u[0], message.text); count += 1; await asyncio.sleep(0.05)
        except: continue
    await message.answer(f"✅ Sent to {count} users."); await state.clear()

@dp.message(Command("withdraw"))
async def cmd_withdraw(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) as cur:
            bal = (await cur.fetchone())[0]
            if bal < MIN_WITHDRAW: return await message.answer(f"❌ Min {MIN_WITHDRAW} TON.")
            await message.answer("🏦 Paste Wallet:"); await state.set_state(BotStates.waiting_for_address)

@dp.message(BotStates.waiting_for_address)
async def finish_withdraw(message: types.Message, state: FSMContext):
    wallet, uid = message.text, message.from_user.id
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (uid,)) as cur:
            bal = (await cur.fetchone())[0]
            await db.execute("INSERT INTO withdrawals (user_id, amount, wallet) VALUES (?, ?, ?)", (uid, bal, wallet))
            await db.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (uid,))
            await db.commit()
    await bot.send_message(ADMIN_ID, f"🔔 **PAYOUT:** {bal} TON to `{wallet}`"); await message.answer("✅ Sent!"); await state.clear()

async def main():
    await init_db()
    app = web.Application()
    app.router.add_get('/reward', handle_reward)
    app.router.add_get('/daily', handle_daily)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", "10000"))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO); asyncio.run(main())
