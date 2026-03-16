import os, asyncio, aiosqlite, logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiohttp import web

# --- CONFIGURATION ---
# Set these in your Render Dashboard -> Environment
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5401881400"))
MIN_WITHDRAW = 5.0  # Minimum TON to request withdrawal

bot = Bot(token=TOKEN)
dp = Dispatcher()

# States for the Withdrawal Flow
class WithdrawState(StatesGroup):
    waiting_for_address = State()

# 1. Database Setup
async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, 
                balance REAL DEFAULT 0
            )
        """)
        await db.commit()

# 2. Reward Endpoint (Called by Mini App after RichAds)
async def handle_reward(request):
    user_id = request.query.get("user_id")
    if not user_id: return web.Response(status=400)
    
    async with aiosqlite.connect("users.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
        await db.execute("UPDATE users SET balance = balance + 0.01 WHERE user_id = ?", (user_id,))
        await db.commit()

    try:
        await bot.send_message(user_id, "✅ Ad Complete! 0.01 TON added to your balance.")
    except Exception as e:
        logging.error(f"Notify error: {e}")
    
    return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})

# 3. Bot Handlers
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("💰 Welcome! Watch ads in the Mini App to earn TON.\n\n"
                         "Commands:\n/balance - Check earnings\n/withdraw - Claim your TON")

@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 0
            await message.answer(f"💰 Current Balance: {balance:.2f} TON")

# --- WITHDRAWAL SYSTEM ---
@dp.message(Command("withdraw"))
async def cmd_withdraw(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 0

    if balance < MIN_WITHDRAW:
        await message.answer(f"❌ Minimum withdrawal is {MIN_WITHDRAW} TON.\nYour balance: {balance:.2f} TON")
    else:
        await message.answer("🏦 Please send your **TON Wallet Address** now.")
        await state.set_state(WithdrawState.waiting_for_address)

@dp.message(WithdrawState.waiting_for_address)
async def process_withdraw(message: types.Message, state: FSMContext):
    wallet_address = message.text
    user_id = message.from_user.id

    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 0

    if balance >= MIN_WITHDRAW:
        # Notify Admin (You)
        await bot.send_message(ADMIN_ID, 
            f"🔔 **Withdrawal Request!**\nUser: `{user_id}`\nAmount: {balance:.2f} TON\nWallet: `{wallet_address}`")
        
        # Reset balance
        async with aiosqlite.connect("users.db") as db:
            await db.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
            await db.commit()
            
        await message.answer("✅ Request sent! The admin will verify and send your TON soon.")
    else:
        await message.answer("❌ Error: Balance updated recently. Try /balance.")
    
    await state.clear()

# 4. Startup
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
