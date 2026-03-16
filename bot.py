import os, asyncio, aiosqlite, logging, time
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiohttp import web

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5401881400")) # Your Telegram ID
REWARD_PER_AD = 0.001  # Keep it at this level for 50% profit margins
MIN_WITHDRAW = 5.0    # Users must earn 5 TON to cash out

bot = Bot(token=TOKEN)
dp = Dispatcher()

class WithdrawState(StatesGroup):
    waiting_for_address = State()

# 1. Database Setup
async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, 
            total_ads INTEGER DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
            amount REAL, wallet TEXT, status TEXT DEFAULT 'PENDING')""")
        await db.commit()

# 2. Reward API (Where you earn from visitors)
async def handle_reward(request):
    uid = int(request.query.get("user_id"))
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET balance = balance + ?, total_ads = total_ads + 1 WHERE user_id = ?", (REWARD_PER_AD, uid))
        await db.commit()
    return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})

# 3. Admin View (Where you see your earnings)
@dp.message(Command("admin_stats"), F.from_user.id == ADMIN_ID)
async def cmd_admin(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT COUNT(*), SUM(total_ads), SUM(balance) FROM users") as cur:
            users, ads, owed = await cur.fetchone()
    
    # Calculation: 1000 ads = ~$3.00 revenue. Owed = what you pay out.
    est_revenue = (ads or 0) * 0.003 
    text = (f"📈 **OWNER'S DASHBOARD**\n\n"
            f"👥 Total Users: `{users}`\n"
            f"📺 Total Ads Served: `{ads or 0}`\n"
            f"💰 Est. Gross Revenue: `${est_revenue:.2f}`\n"
            f"💸 Total Owed to Users: `{owed or 0:.3f} TON`\n\n"
            f"✅ **Net Profit:** `${est_revenue - ((owed or 0)*1.34):.2f}`")
    await message.answer(text, parse_mode="Markdown")

# 4. Withdrawal Logic
@dp.message(F.text == "🏦 WITHDRAW")
async def start_withdraw(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) as cur:
            row = await cur.fetchone()
            bal = row[0] if row else 0
            if bal < MIN_WITHDRAW:
                return await message.answer(f"❌ Minimum withdrawal is {MIN_WITHDRAW} TON.\nYour balance: {bal:.3f} TON")
            
            await message.answer("🏦 Enter your **TON Wallet Address** for payment:")
            await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def process_withdraw(message: types.Message, state: FSMContext):
    wallet, uid = message.text, message.from_user.id
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (uid,)) as cur:
            bal = (await cur.fetchone())[0]
            await db.execute("INSERT INTO withdrawals (user_id, amount, wallet) VALUES (?, ?, ?)", (uid, bal, wallet))
            await db.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (uid,))
            await db.commit()
    
    await bot.send_message(ADMIN_ID, f"🔔 **PAYOUT REQUEST**\nUser: `{uid}`\nAmount: `{bal:.3f} TON`\nWallet: `{wallet}`")
    await message.answer("✅ Request sent! Admin will pay you within 24 hours."); await state.clear()

# --- STARTUP ---
async def main():
    await init_db()
    app = web.Application()
    app.router.add_get('/reward', handle_reward)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", "10000"))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
