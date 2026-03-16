import os
import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# --- CONFIGURATION ---
# We use the variable name "BOT_TOKEN". 
# You will set the actual value inside the Render Dashboard.
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

# 1. Database Initialization
async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, 
                balance REAL DEFAULT 0
            )
        """)
        await db.commit()

# 2. Reward Webhook (Called by your Mini App)
async def handle_reward(request):
    user_id_str = request.query.get("user_id")
    if not user_id_str:
        return web.Response(text="Missing user_id", status=400)
    
    try:
        user_id = int(user_id_str)
        async with aiosqlite.connect("users.db") as db:
            # Add 0.01 TON to user (create user if they don't exist)
            await db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
            await db.execute("UPDATE users SET balance = balance + 0.01 WHERE user_id = ?", (user_id,))
            await db.commit()

        # Notify the user via the bot
        await bot.send_message(user_id, "✅ Ad Verified! 0.01 TON has been added to your balance.")
        return web.Response(text="Success", headers={"Access-Control-Allow-Origin": "*"})
    
    except Exception as e:
        logging.error(f"Reward error: {e}")
        return web.Response(text="Error", status=500)

# 3. Health Check (Keeps Render happy)
async def health_check(request):
    return web.Response(text="Bot is running!")

# 4. Bot Command Handlers
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Welcome to Crypto Earner!\n\n"
        "Click the button below to watch ads and earn TON. "
        "Use /balance to check your current earnings."
    )

@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) as cursor:
            row = await cursor.fetchone()
            balance = row[0] if row else 0
            await message.answer(f"💰 Your Current Balance: {balance:.2f} TON")

# 5. Main Startup Function
async def main():
    await init_db()
    
    # Setup the Web Server for the Mini App to talk to
    app = web.Application()
    app.router.add_get('/reward', handle_reward)
    app.router.add_get('/', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render uses the 'PORT' environment variable automatically
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logging.info(f"Web server started on port {port}")
    
    # Start bot polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
