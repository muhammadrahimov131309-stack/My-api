import os
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

# Настройки подключения
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:%40plushwallet20132008Mm$@db.dzpxmhzdousaureiedul.supabase.co:5432/postgres"
)
# Укажи свой Telegram ID здесь, чтобы видеть кнопку Админки!
ADMIN_IDS = [7127705775] 

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(BigInteger, unique=True, index=True)
    nickname = Column(String, default="Игрок")
    balance = Column(BigInteger, default=1000)
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    gang = Column(String, default="SHADOW")
    income_per_hour = Column(Integer, default=100)
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

SHOP_ITEMS = [
    {"id": 1, "name": "Кепка новичка", "type": "Accessory", "price": 1000, "income": 50, "icon": "🧢"},
    {"id": 2, "name": "Белая футболка", "type": "Skin", "price": 2500, "income": 150, "icon": "👕"},
    {"id": 3, "name": "Тренч SHADOW", "type": "Skin", "price": 50000, "income": 3500, "icon": "🧥"},
    {"id": 4, "name": "Спортивная тачка", "type": "Car", "price": 500000, "income": 40000, "icon": "🏎️"},
    {"id": 5, "name": "Пентхаус в Сити", "type": "Real Estate", "price": 2500000, "income": 250000, "icon": "🏙️"},
]

class BetRequest(BaseModel):
    tg_id: int
    amount: int
    multiplier: float = 2.0
    choice: str = ""

class BuyRequest(BaseModel):
    tg_id: int
    item_id: int

class AdminAction(BaseModel):
    admin_id: int
    target_tg_id: int
    amount: int

class TapRequest(BaseModel):
    tg_id: int
    nickname: str = "Боец"

@app.get("/")
def root():
    return {"status": "TSTCOIN API ONLINE"}

@app.post("/api/auth")
def auth_user(req: TapRequest):
    db = SessionLocal()
    user = db.query(User).filter(User.tg_id == req.tg_id).first()
    if not user:
        user = User(tg_id=req.tg_id, nickname=req.nickname, balance=5000, inventory=[])
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
    
    reward = 10 * user.level
    user.balance += reward
    user.xp += 10
    if user.xp >= user.level * 100:
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
        raise HTTPException(status_code=404, detail="Ошибка покупки")
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
    db.commit()
    
    res = {"balance": user.balance, "income_per_hour": user.income_per_hour, "inventory": user.inventory}
    db.close()
    return res

@app.post("/api/casino/upgrader")
def casino_upgrader(req: BetRequest):
    db = SessionLocal()
    user = db.query(User).filter(User.tg_id == req.tg_id).first()
    if not user:
        db.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if req.amount <= 0 or req.amount > user.balance:
        db.close()
        raise HTTPException(status_code=400, detail="Неверная сумма ставки")
    
    chance = min(85.0, (1.0 / req.multiplier) * 90.0)
    win = random.uniform(0, 100) <= chance
    
    if win:
        payout = int(req.amount * req.multiplier) - req.amount
        user.balance += payout
    else:
        payout = 0
        user.balance -= req.amount
        
    db.commit()
    new_bal = user.balance
    db.close()
    return {"win": win, "payout": int(req.amount * req.multiplier) if win else 0, "new_balance": new_bal}

@app.post("/api/casino/dice")
def casino_dice(req: BetRequest):
    db = SessionLocal()
    user = db.query(User).filter(User.tg_id == req.tg_id).first()
    if not user or req.amount <= 0 or req.amount > user.balance:
        db.close()
        raise HTTPException(status_code=400, detail="Недостаточно средств")
        
    roll = random.randint(1, 100)
    win = (req.choice == "under" and roll < 48) or (req.choice == "over" and roll > 52)
    
    if win:
        user.balance += req.amount
    else:
        user.balance -= req.amount
        
    db.commit()
    new_bal = user.balance
    db.close()
    return {"win": win, "roll": roll, "new_balance": new_bal}

# === АДМИН-ПАНЕЛЬ ===
@app.get("/api/admin/users")
def admin_get_users(admin_id: int):
    if admin_id not in ADMIN_IDS:
        raise HTTPException(status_code=403, detail="Нет доступа")
    db = SessionLocal()
    users = db.query(User).order_by(User.balance.desc()).limit(20).all()
    res = [{"tg_id": u.tg_id, "nickname": u.nickname, "balance": u.balance, "level": u.level} for u in users]
    db.close()
    return {"users": res}

@app.post("/api/admin/give")
def admin_give_money(req: AdminAction):
    if req.admin_id not in ADMIN_IDS:
        raise HTTPException(status_code=403, detail="Нет доступа")
    db = SessionLocal()
    target = db.query(User).filter(User.tg_id == req.target_tg_id).first()
    if not target:
        db.close()
        raise HTTPException(status_code=404, detail="Игрок с таким ID не найден")
    target.balance += req.amount
    if target.balance < 0:
        target.balance = 0
    db.commit()
    new_bal = target.balance
    db.close()
    return {"status": "ok", "new_balance": new_bal}

