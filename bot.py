import os, asyncio, aiosqlite, logging, time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5401881400")) 
REWARD = 0.001 
DAILY = 0.05
MIN_WITHDRAW = 5.0

bot = Bot(token=TOKEN)
dp = Dispatcher()

class WithdrawState(StatesGroup):
    waiting_for_address = State()

async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, total_ads INTEGER DEFAULT 0, last_bonus TIMESTAMP DEFAULT NULL)")
        await db.execute("CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, wallet TEXT)")
        await db.commit()

async def handle_reward(request):
    uid = int(request.query.get("user_id"))
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET balance = balance + ?, total_ads = total_ads + 1 WHERE user_id = ?", (REWARD, uid))
        await db.commit()
    return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})

async def handle_daily(request):
    uid = int(request.query.get("user_id"))
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT last_bonus FROM users WHERE user_id = ?", (uid,)) as cur:
            row = await cur.fetchone()
            now = datetime.now()
            if row and row[0] and datetime.fromisoformat(row[0]) > now - timedelta(days=1):
                return web.Response(text="Error", status=403)
            await db.execute("UPDATE users SET balance = balance + ?, last_bonus = ? WHERE user_id = ?", (DAILY, now.isoformat(), uid))
            await db.commit()
    return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})

@dp.message(CommandStart())
async def start(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
        await db.commit()
   kb = [[types.KeyboardButton(text="💰 EARN", web_app=types.WebAppInfo(url="https://pne1973.github.io/mini-app/"))],
          [types.KeyboardButton(text="💳 BALANCE"), types.KeyboardButton(text="🏦 WITHDRAW")]]
    await message.answer("🚀 **Crypto Earner Bot**\nClick EARN to start.", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.text == "💳 BALANCE")
async def balance(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance, total_ads FROM users WHERE user_id = ?", (message.from_user.id,)) as cur:
            bal, ads = await cur.fetchone()
            await message.answer(f"💳 **Balance:** `{bal:.3f} TON`\n📺 **Ads:** `{ads}`")

@dp.message(F.text == "🏦 WITHDRAW")
async def withdraw_start(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) as cur:
            bal = (await cur.fetchone())[0]
            if bal < MIN_WITHDRAW: return await message.answer(f"❌ Min payout: {MIN_WITHDRAW} TON")
            await message.answer("🏦 Send TON Wallet Address:"); await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def withdraw_done(message: types.Message, state: FSMContext):
    wallet, uid = message.text, message.from_user.id
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (uid,)) as cur:
            bal = (await cur.fetchone())[0]
            await db.execute("INSERT INTO withdrawals (user_id, amount, wallet) VALUES (?, ?, ?)", (uid, bal, wallet))
            await db.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (uid,))
            await db.commit()
    await bot.send_message(ADMIN_ID, f"🔔 **PAYOUT:** {bal} TON to `{wallet}`")
    await message.answer("✅ Sent! Admin will pay you soon."); await state.clear()

@dp.message(Command("admin_stats"), F.from_user.id == ADMIN_ID)
async def admin(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT COUNT(*), SUM(total_ads) FROM users") as cur:
            u, a = await cur.fetchone()
            await message.answer(f"📊 **Stats**\nUsers: {u}\nTotal Ads: {a}")

async def main():
    await init_db()
    app = web.Application()
    app.router.add_get('/reward', handle_reward); app.router.add_get('/daily', handle_daily)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", "10000"))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
