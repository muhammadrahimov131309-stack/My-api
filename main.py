import os
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

# Подключение к базе данных Supabase
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:%40plushwallet20132008Mm$@db.dzpxmhzdousaureiedul.supabase.co:5432/postgres"
)
# Укажи здесь свой Telegram ID, чтобы получить доступ к админ-панели
ADMIN_IDS = [7127705775] 

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(BigInteger, unique=True, index=True)
    nickname = Column(String, default="Боец")
    balance = Column(BigInteger, default=10000)
    level = Column(Integer, default=1)
    xp = Column(Integer, default=380)
    gang = Column(String, default="SHADOW")
    income_per_hour = Column(Integer, default=1200)
    inventory = Column(JSON, default=list)

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Каталог товаров магазина активов
SHOP_ITEMS = [
    {"id": 1, "name": "Кепка «Новичок»", "type": "Accessory", "price": 2000, "income": 100, "icon": "🧢"},
    {"id": 2, "name": "Кожаная куртка", "type": "Skin", "price": 15000, "income": 450, "icon": "🧥"},
    {"id": 3, "name": "Лада «Стартовая»", "type": "Car", "price": 25000, "income": 800, "icon": "🚗"},
    {"id": 4, "name": "Крипто-Ферма RTX", "type": "Business", "price": 75000, "income": 2500, "icon": "💻"},
    {"id": 5, "name": "Скин «Легенда»", "type": "Skin", "price": 500000, "income": 15000, "icon": "👑"},
]

class AuthRequest(BaseModel):
    tg_id: int
    nickname: str = "Боец"

class TapRequest(BaseModel):
    tg_id: int

class BetRequest(BaseModel):
    tg_id: int
    amount: int
    multiplier: float = 2.0
    choice: str = "red"

class BuyRequest(BaseModel):
    tg_id: int
    item_id: int

class AdminAction(BaseModel):
    admin_id: int
    target_tg_id: int
    amount: int

@app.get("/")
def root():
    return {"status": "UNIVERSE API ONLINE"}

@app.post("/api/auth")
def auth_user(req: AuthRequest):
    db = SessionLocal()
    user = db.query(User).filter(User.tg_id == req.tg_id).first()
    if not user:
        user = User(tg_id=req.tg_id, nickname=req.nickname, balance=10000, inventory=[])
        db.add(user)
        db.commit()
        db.refresh(user)
    elif req.nickname and req.nickname != "Боец" and user.nickname != req.nickname:
        user.nickname = req.nickname
        db.commit()
    
    res = {
        "tg_id": user.tg_id,
        "nickname": user.nickname,
        "balance": user.balance,
        "level": user.level,
        "xp": user.xp,
        "gang": user.gang,
        "income_per_hour": user.income_per_hour,
        "inventory": user.inventory or [],
        "is_admin": user.tg_id in ADMIN_IDS
    }
    db.close()
    return res

@app.post("/api/tap")
def tap_earn(req: TapRequest):
    db = SessionLocal()
    user = db.query(User).filter(User.tg_id == req.tg_id).first()
    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="Юзер не найден")
    
    reward = 100 * user.level
    user.balance += reward
    user.xp += 25
    
    next_xp_target = user.level * 1000
    if user.xp >= next_xp_target:
        user.xp = 0
        user.level += 1
        
    db.commit()
    bal, lvl, xp = user.balance, user.level, user.xp
    db.close()
    return {"balance": bal, "level": lvl, "xp": xp, "reward": reward}

@app.get("/api/shop")
def get_shop():
    return {"items": SHOP_ITEMS}

@app.post("/api/shop/buy")
def buy_item(req: BuyRequest):
    db = SessionLocal()
    user = db.query(User).filter(User.tg_id == req.tg_id).first()
    item = next((i for i in SHOP_ITEMS if i["id"] == req.item_id), None)
    
    if not user or not item:
        db.close()
        raise HTTPException(status_code=404, detail="Товар не найден")
    if user.balance < item["price"]:
        db.close()
        raise HTTPException(status_code=400, detail="Недостаточно монет!")
    
    inv = list(user.inventory or [])
    if item["id"] in inv:
        db.close()
        raise HTTPException(status_code=400, detail="Уже куплено!")
        
    user.balance -= item["price"]
    user.income_per_hour += item["income"]
    inv.append(item["id"])
    user.inventory = inv
    user.xp += 100
    
    db.commit()
    res = {
        "balance": user.balance, 
        "income_per_hour": user.income_per_hour, 
        "inventory": user.inventory,
        "level": user.level,
        "xp": user.xp
    }
    db.close()
    return res

# Казино: Краш
@app.post("/api/casino/crash")
def casino_crash(req: BetRequest):
    db = SessionLocal()
    user = db.query(User).filter(User.tg_id == req.tg_id).first()
    if not user or req.amount <= 0 or req.amount > user.balance:
        db.close()
        raise HTTPException(status_code=400, detail="Неверная ставка")
    
    crash_point = round(random.uniform(1.01, max(1.1, req.multiplier)), 2)
    win = req.multiplier <= crash_point
    
    if win:
        payout = int(req.amount * req.multiplier)
        user.balance += (payout - req.amount)
    else:
        user.balance -= req.amount
        
    db.commit()
    new_bal = user.balance
    db.close()
    return {"win": win, "crash_point": crash_point, "new_balance": new_bal}

# Админка: выдача баланса
@app.post("/api/admin/give")
def admin_give(req: AdminAction):
    if req.admin_id not in ADMIN_IDS:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    db = SessionLocal()
    target = db.query(User).filter(User.tg_id == req.target_tg_id).first()
    if not target:
        db.close()
        raise HTTPException(status_code=404, detail="Игрок не найден")
    target.balance += req.amount
    db.commit()
    new_bal = target.balance
    db.close()
    return {"status": "ok", "new_balance": new_bal}


