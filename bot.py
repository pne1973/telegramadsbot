import os, asyncio, aiosqlite, logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiohttp import web

# --- CONFIG ---
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5401881400")) # Your ID
MIN_WITHDRAW = 5.0 

bot = Bot(token=TOKEN)
dp = Dispatcher()

class WithdrawState(StatesGroup):
    waiting_for_address = State()

# 1. Database
async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)")
        await db.commit()

# 2. Reward API
async def handle_reward(request):
    user_id = request.query.get("user_id")
    if not user_id: return web.Response(status=400)
    
    async with aiosqlite.connect("users.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
        await db.execute("UPDATE users SET balance = balance + 0.01 WHERE user_id = ?", (user_id,))
        await db.commit()

    try:
        await bot.send_message(user_id, "💰 +0.01 TON Received! Keep watching to earn more.")
    except: pass
    
    return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})

# 3. Handlers
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🚀 **Crypto Earner Bot**\n\nEarn TON by watching ads in our Mini App.\n\n"
                         "📊 /balance - See your earnings\n"
                         "🏦 /withdraw - Claim your TON")

@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 0
            await message.answer(f"💳 **Your Balance:** {balance:.2f} TON")

@dp.message(Command("withdraw"))
async def cmd_withdraw(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 0

    if balance < MIN_WITHDRAW:
        await message.answer(f"⚠️ Minimum withdrawal is {MIN_WITHDRAW} TON.\nEarn more to unlock!")
    else:
        await message.answer("🏦 Send your **TON Wallet Address** below:")
        await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def process_withdraw(message: types.Message, state: FSMContext):
    wallet = message.text
    user_id = message.from_user.id
    
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 0

    if balance >= MIN_WITHDRAW:
        # Reset balance first (security)
        async with aiosqlite.connect("users.db") as db:
            await db.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
            await db.commit()
        
        # Notify Admin
        await bot.send_message(ADMIN_ID, f"🔔 **Withdrawal Request!**\nUser: `{user_id}`\nAmount: {balance:.2f} TON\nWallet: `{wallet}`")
        await message.answer("✅ Withdrawal request submitted! Admin will process it shortly.")
    else:
        await message.answer("❌ Error: Insufficient balance.")
    await state.clear()

# 4. Main
async def main():
    await init_db()
    app = web.Application()
    app.router.add_get('/reward', handle_reward)
    app.router.add_get('/', lambda r: web.Response(text="Bot is Live"))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", "10000")))
    await site.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
