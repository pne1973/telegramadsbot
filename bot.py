import os, asyncio, aiosqlite, logging
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

bot = Bot(token=TOKEN)
dp = Dispatcher()

class WithdrawState(StatesGroup):
    waiting_for_address = State()

# 1. Database Initialization
async def init_db():
    async with aiosqlite.connect("users.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, full_name TEXT, balance REAL DEFAULT 0, referred_by INTEGER DEFAULT NULL)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, wallet TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        await db.commit()

# 2. Reward API (Frontend calls this)
async def handle_reward(request):
    user_id = int(request.query.get("user_id"))
    async with aiosqlite.connect("users.db") as db:
        await db.execute("UPDATE users SET balance = balance + 0.01 WHERE user_id = ?", (user_id,))
        async with db.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row and row[0]: # Pay 10% referral bonus
                await db.execute("UPDATE users SET balance = balance + 0.001 WHERE user_id = ?", (row[0],))
        await db.commit()
    try: await bot.send_message(user_id, "💰 +0.01 TON Added!")
    except: pass
    return web.Response(text="OK", headers={"Access-Control-Allow-Origin": "*"})

# 3. Bot Commands
@dp.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject):
    user_id, name = message.from_user.id, message.from_user.full_name
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cur:
            if not await cur.fetchone():
                ref = int(command.args) if command.args and command.args.isdigit() and int(command.args) != user_id else None
                await db.execute("INSERT INTO users (user_id, full_name, balance, referred_by) VALUES (?, ?, 0, ?)", (user_id, name, ref))
                if ref: await bot.send_message(ref, f"🎁 {name} joined your team!")
            else:
                await db.execute("UPDATE users SET full_name = ? WHERE user_id = ?", (name, user_id))
        await db.commit()
    await message.answer(f"👋 Welcome {name}!\n\n🚀 /refer - Get invite link\n📊 /balance - Check TON\n🏆 /leaderboard - Top users\n📜 /history - Payouts")

@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) as cur:
            row = await cur.fetchone()
            await message.answer(f"💎 **Balance:** {row[1] if row else 0:.2f} TON")

@dp.message(Command("refer"))
async def cmd_refer(message: types.Message):
    link = await create_start_link(bot, str(message.from_user.id), encode=False)
    await message.answer(f"🤝 **Invite Friends**\nEarn 10% of their ad revenue forever!\n\nLink: `{link}`")

@dp.message(Command("leaderboard"))
async def cmd_leaderboard(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        query = "SELECT u.full_name, COUNT(r.user_id) FROM users r JOIN users u ON r.referred_by = u.user_id GROUP BY r.referred_by ORDER BY COUNT(r.user_id) DESC LIMIT 5"
        async with db.execute(query) as cur:
            rows = await cur.fetchall()
            text = "🏆 **TOP REFERRERS**\n\n" + "\n".join([f"👤 {r[0]} — {r[1]} invites" for r in rows]) if rows else "No referrers yet!"
            await message.answer(text)

@dp.message(Command("history"))
async def cmd_history(message: types.Message):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT amount, date FROM withdrawals WHERE user_id = ? ORDER BY date DESC LIMIT 5", (message.from_user.id,)) as cur:
            rows = await cur.fetchall()
            text = "📜 **HISTORY**\n\n" + "\n".join([f"💰 {r[0]} TON ({r[1].split(' ')[0]})" for r in rows]) if rows else "No history."
            await message.answer(text)

@dp.message(Command("withdraw"))
async def cmd_withdraw(message: types.Message, state: FSMContext):
    async with aiosqlite.connect("users.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) as cur:
            bal = (await cur.fetchone())[0]
            if bal < MIN_WITHDRAW: return await message.answer(f"❌ Need {MIN_WITHDRAW} TON.")
            await message.answer("🏦 Send your TON Wallet Address:")
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
    await bot.send_message(ADMIN_ID, f"🔔 **PAYOUT:** {bal} TON to `{wallet}`")
    await message.answer("✅ Request Sent!"); await state.clear()

# 4. Startup logic
async def main():
    await init_db()
    app = web.Application()
    app.router.add_get('/reward', handle_reward)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", "10000"))).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO); asyncio.run(main())
