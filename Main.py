import os
import asyncio
import logging
import random
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7127705775"))
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://your-app.pages.dev")

# База данных в памяти для старта
users_db = {}
SHOP_ITEMS = [
    {"id": 1, "name": "Кепка новичка", "type": "accessory", "rarity": "common", "price": 1000},
    {"id": 2, "name": "Белая футболка", "type": "skin", "rarity": "common", "price": 2500},
    {"id": 3, "name": "Тренч SHADOW", "type": "skin", "rarity": "epic", "price": 50000},
    {"id": 4, "name": "Спортивная тачка", "type": "car", "rarity": "legendary", "price": 500000},
]

def get_or_create_user(tg_id: int, username: str = "Боец"):
    if tg_id not in users_db:
        users_db[tg_id] = {
            "id": len(users_db) + 1,
            "tg_id": tg_id,
            "nickname": username,
            "balance": 10000,
            "level": 1,
            "xp": 450,
            "max_xp": 1000,
            "gang": "SHADOW",
            "rank": len(users_db) + 1,
            "daily_claimed": False,
            "inventory": [SHOP_ITEMS[0], SHOP_ITEMS[1]],
            "businesses": [
                {"biz_id": 1, "name": "Палатка с хот-догами", "level": 1, "income_per_hour": 500, "accumulated": 1200}
            ],
            "force_win": None,
            "is_banned": False
        }
    return users_db[tg_id]

# Инициализация бота
bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher()

if bot:
    @dp.message(CommandStart())
    async def cmd_start(message: types.Message):
        user = get_or_create_user(message.from_user.id, message.from_user.first_name)
        if user["is_banned"]:
            return await message.answer("🚫 Аккаунт заблокирован.")

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Открыть TSTCOIN", web_app=WebAppInfo(url=MINI_APP_URL))]
        ])
        await message.answer(
            f"👋 Привет, <b>{user['nickname']}</b>!\n\n"
            f"💰 Баланс: <b>{user['balance']:,}</b> монет\n"
            f"🏴 Банда: <b>{user['gang']}</b>",
            reply_markup=kb,
            parse_mode="HTML"
        )

# Жизненный цикл приложения (FastAPI + фоновый опрос Telegram)
@asynccontextmanager
async def lifespan(app: FastAPI):
    polling_task = None
    if bot:
        polling_task = asyncio.create_task(dp.start_polling(bot))
        logger.info("🤖 Telegram бот запущен в фоне!")
    yield
    if polling_task:
        polling_task.cancel()
        if bot:
            await bot.session.close()

app = FastAPI(title="TSTCOIN API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Эндпоинты
@app.get("/")
async def health_check():
    return {"status": "ok", "game": "TSTCOIN", "active_users": len(users_db)}

@app.get("/api/profile/{tg_id}")
async def get_profile(tg_id: int):
    return get_or_create_user(tg_id)

@app.get("/api/магазин")
async def get_shop():
    return {"items": SHOP_ITEMS}

@app.get("/api/инвентарь/{tg_id}")
async def get_inventory(tg_id: int):
    user = get_or_create_user(tg_id)
    return {"inventory": user["inventory"]}
