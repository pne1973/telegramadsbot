from aiohttp import web
import sqlite3 # Or whatever database you are currently using
import os, asyncio, aiosqlite, hashlib
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiohttp import web

# --- CONFIG (Use Environment Variables on Render) ---
TOKEN = os.getenv("8609038498:AAFzTSVCg2XzwAFsfc8xiA20jEIiPMIxmzc")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5401881400"))
SECRET = os.getenv("AD_SECRET", "verde") # For hashing rewards

bot = Bot(token=TOKEN)
dp = Dispatcher()

# 1. Database Setup
async def init_db():
    async with aiosqlite.connect("database.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0)")
        await db.commit()

# 2. Reward Endpoint (The link you'll put in your index.html)
async def handle_reward(request):
    user_id = request.query.get("user_id")
    if not user_id: return web.Response(status=400)
    
    async with aiosqlite.connect("database.db") as db:
        await db.execute("UPDATE users SET balance = balance + 0.01 WHERE id = ?", (user_id,))
        await db.commit()
    return web.Response(text="OK")

# 3. Simple Health Check (To keep the bot awake)
async def health_check(request):
    return web.Response(text="I am alive!")

# 4. Bot Handlers
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("💰 Welcome! Use the Web App to earn TON.")

# --- STARTUP LOGIC ---
async def handle_reward(request):
    user_id = request.query.get("user_id")
    if not user_id:
        return web.Response(text="No User ID", status=400)

    # --- YOUR CUSTOM DATABASE CODE GOES HERE ---
    # Example: If you use SQLite, update the balance
    # conn = sqlite3.connect("your_database.db")
    # cursor = conn.cursor()
    # cursor.execute("UPDATE users SET balance = balance + 0.01 WHERE id = ?", (user_id,))
    # conn.commit()
    # ------------------------------------------

    # Send a message to the user confirming payment
    try:
        await bot.send_message(user_id, "✅ Ad Complete! 0.01 TON added to your balance.")
    except Exception as e:
        print(f"Error sending message: {e}")

    return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})
async def main():
    await init_db()
    
    # Setup Web Server
    app = web.Application()
    app.router.add_get('/reward', handle_reward)
    app.router.add_get('/', health_check) # Health check at root
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render provides a 'PORT' environment variable
    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # Start Bot Polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
