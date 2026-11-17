import os
import asyncio
import logging
import random
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7127705775"))
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://your-frontend.vercel.app")
DATABASE_URL = os.getenv("DATABASE_URL", "") # Ссылка подключения из Supabase (начинается с postgresql://...)

# Функция для подключения к PostgreSQL (Supabase)
def get_db_connection():
    if not DATABASE_URL:
        return None
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

# Магазин по умолчанию
SHOP_ITEMS = [
    {"id": 1, "name": "Кепка новичка", "type": "accessory", "rarity": "common", "price": 1000},
    {"id": 2, "name": "Белая футболка", "type": "skin", "rarity": "common", "price": 2500},
    {"id": 3, "name": "Тренч SHADOW", "type": "skin", "rarity": "epic", "price": 50000},
    {"id": 4, "name": "Спортивная тачка", "type": "car", "rarity": "legendary", "price": 500000},
]

def get_or_create_user_db(tg_id: int, nickname: str = "Боец"):
    conn = get_db_connection()
    if not conn:
        # Если база еще не подключена, возвращаем фейк для теста
        return {"tg_id": tg_id, "nickname": nickname, "balance": 10000, "level": 1, "gang": "SHADOW"}
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE tg_id = %s;", (tg_id,))
            user = cursor.fetchone()
            if not user:
                cursor.execute(
                    "INSERT INTO users (tg_id, nickname, balance, level, xp, max_xp, gang) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *;",
                    (tg_id, nickname, 10000, 1, 450, 1000, "SHADOW")
                )
                user = cursor.fetchone()
                conn.commit()
            return dict(user)
    finally:
        conn.close()

# Инициализация бота
bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher()

if bot:
    @dp.message(CommandStart())
    async def cmd_start(message: types.Message):
        user = get_or_create_user_db(message.from_user.id, message.from_user.first_name)
        if user.get("is_banned"):
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
    return {"status": "ok", "game": "TSTCOIN", "database": "connected" if DATABASE_URL else "memory_only"}

@app.get("/api/profile/{tg_id}")
async def get_profile(tg_id: int):
    user = get_or_create_user_db(tg_id)
    return user

@app.get("/api/магазин")
async def get_shop():
    return {"items": SHOP_ITEMS}
