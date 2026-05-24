import os
import json
import hashlib
import secrets
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import jwt
from dotenv import load_dotenv

# Load environment variables from .env file at startup
load_dotenv()

from . import database, models, schemas
from .gemini_service import analyze_fridge_image

# JWT Token configuration
SECRET_KEY = "KULKAS_PINTAR_SECRET_KEY_2026_MVP"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Password Hashing Utilities
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    db_val = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${db_val}"

def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, db_val = hashed.split("$")
        check_val = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return secrets.compare_digest(db_val, check_val)
    except Exception:
        return False

# Database lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=database.engine)
    yield

app = FastAPI(
    title="KulkasPintar AI Web API",
    description="Backend services for KulkasPintar AI Web MVP",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth dependency
def get_current_user(token: Optional[str] = None, db: Session = Depends(database.get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

# User Auth Routes
@app.post("/api/v1/auth/register", response_model=schemas.UserOut)
def register(user_in: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    hashed_pwd = hash_password(user_in.password)
    new_user = models.User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        dietary_restrictions="[]"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Parse restrictions
    restrictions = json.loads(new_user.dietary_restrictions)
    return schemas.UserOut(
        id=new_user.id,
        email=new_user.email,
        dietary_restrictions=restrictions,
        created_at=new_user.created_at
    )

@app.post("/api/v1/auth/login")
def login(user_in: schemas.UserLogin, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    token_data = {"user_id": user.id}
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/v1/auth/me", response_model=schemas.UserOut)
def get_me(token: str, db: Session = Depends(database.get_db)):
    user = get_current_user(token, db)
    restrictions = json.loads(user.dietary_restrictions)
    return schemas.UserOut(
        id=user.id,
        email=user.email,
        dietary_restrictions=restrictions,
        created_at=user.created_at
    )

@app.put("/api/v1/auth/profile", response_model=schemas.UserOut)
def update_profile(
    token: str,
    profile_update: schemas.UserUpdateRestrictions,
    db: Session = Depends(database.get_db)
):
    user = get_current_user(token, db)
    user.dietary_restrictions = json.dumps(profile_update.dietary_restrictions)
    db.commit()
    db.refresh(user)
    
    restrictions = json.loads(user.dietary_restrictions)
    return schemas.UserOut(
        id=user.id,
        email=user.email,
        dietary_restrictions=restrictions,
        created_at=user.created_at
    )

# Room Collaboration Routes
@app.post("/api/v1/rooms/join", response_model=schemas.SharedRoomOut)
def join_room(
    token: str,
    room_join: schemas.SharedRoomJoin,
    db: Session = Depends(database.get_db)
):
    user = get_current_user(token, db)
    # Check if already joined this room
    existing = db.query(models.SharedRoom).filter(
        models.SharedRoom.user_id == user.id,
        models.SharedRoom.room_id == room_join.room_id
    ).first()
    
    if existing:
        return existing
        
    # Remove user from any other rooms first (user can only be in one active room at a time for MVP)
    db.query(models.SharedRoom).filter(models.SharedRoom.user_id == user.id).delete()
    
    new_room_link = models.SharedRoom(
        room_id=room_join.room_id,
        user_id=user.id
    )
    db.add(new_room_link)
    db.commit()
    db.refresh(new_room_link)
    return new_room_link

@app.post("/api/v1/rooms/leave")
def leave_room(token: str, db: Session = Depends(database.get_db)):
    user = get_current_user(token, db)
    db.query(models.SharedRoom).filter(models.SharedRoom.user_id == user.id).delete()
    db.commit()
    return {"message": "Successfully left the room"}

@app.get("/api/v1/rooms/active")
def get_active_room(token: str, db: Session = Depends(database.get_db)):
    user = get_current_user(token, db)
    active_room = db.query(models.SharedRoom).filter(models.SharedRoom.user_id == user.id).first()
    if not active_room:
        return {"in_room": False, "room_id": None, "members": []}
    
    # Query all users in this room
    members_links = db.query(models.SharedRoom).filter(
        models.SharedRoom.room_id == active_room.room_id
    ).all()
    
    members = []
    for m in members_links:
        members.append({
            "user_id": m.user.id,
            "email": m.user.email
        })
        
    return {
        "in_room": True,
        "room_id": active_room.room_id,
        "members": members
    }

# Helper to fetch merged inventory items
def fetch_user_inventory(user: models.User, db: Session) -> List[models.InventoryItem]:
    # Check if user is in an active room
    active_room = db.query(models.SharedRoom).filter(models.SharedRoom.user_id == user.id).first()
    if active_room:
        # Get all users in this room
        members = db.query(models.SharedRoom).filter(
            models.SharedRoom.room_id == active_room.room_id
        ).all()
        user_ids = [m.user_id for m in members]
        return db.query(models.InventoryItem).filter(models.InventoryItem.user_id.in_(user_ids)).all()
    else:
        return db.query(models.InventoryItem).filter(models.InventoryItem.user_id == user.id).all()

# Inventory CRUD Routes
@app.get("/api/v1/inventory", response_model=List[schemas.InventoryItemOut])
def get_inventory(token: str, db: Session = Depends(database.get_db)):
    user = get_current_user(token, db)
    return fetch_user_inventory(user, db)

@app.post("/api/v1/inventory", response_model=schemas.InventoryItemOut)
def create_inventory_item(
    token: str,
    item_in: schemas.InventoryItemCreate,
    db: Session = Depends(database.get_db)
):
    user = get_current_user(token, db)
    # Check if we already have an item with the same name in the current room/user inventory
    # to avoid duplicates and update quantity instead
    active_room = db.query(models.SharedRoom).filter(models.SharedRoom.user_id == user.id).first()
    
    existing = None
    if active_room:
        members = db.query(models.SharedRoom).filter(models.SharedRoom.room_id == active_room.room_id).all()
        user_ids = [m.user_id for m in members]
        existing = db.query(models.InventoryItem).filter(
            models.InventoryItem.name.ilike(item_in.name),
            models.InventoryItem.user_id.in_(user_ids)
        ).first()
    else:
        existing = db.query(models.InventoryItem).filter(
            models.InventoryItem.name.ilike(item_in.name),
            models.InventoryItem.user_id == user.id
        ).first()

    if existing:
        existing.quantity += item_in.quantity
        db.commit()
        db.refresh(existing)
        return existing

    new_item = models.InventoryItem(
        user_id=user.id,
        name=item_in.name,
        quantity=item_in.quantity,
        unit=item_in.unit,
        category=item_in.category,
        expires_at=item_in.expires_at
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.put("/api/v1/inventory/{item_id}", response_model=schemas.InventoryItemOut)
def update_inventory_item(
    item_id: int,
    token: str,
    item_update: schemas.InventoryItemUpdate,
    db: Session = Depends(database.get_db)
):
    user = get_current_user(token, db)
    db_item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Check if user has permission (owns the item, or is in the same room as the owner)
    owner_id = db_item.user_id
    if owner_id != user.id:
        active_room = db.query(models.SharedRoom).filter(models.SharedRoom.user_id == user.id).first()
        if not active_room:
            raise HTTPException(status_code=403, detail="Not authorized to edit this item")
        
        # Verify if owner is in the same room
        is_in_same_room = db.query(models.SharedRoom).filter(
            models.SharedRoom.room_id == active_room.room_id,
            models.SharedRoom.user_id == owner_id
        ).first()
        if not is_in_same_room:
            raise HTTPException(status_code=403, detail="Not authorized to edit this item")

    # Perform updates
    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_item, key, value)
        
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/v1/inventory/{item_id}")
def delete_inventory_item(
    item_id: int,
    token: str,
    db: Session = Depends(database.get_db)
):
    user = get_current_user(token, db)
    db_item = db.query(models.InventoryItem).filter(models.InventoryItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    # Check permissions
    owner_id = db_item.user_id
    if owner_id != user.id:
        active_room = db.query(models.SharedRoom).filter(models.SharedRoom.user_id == user.id).first()
        if not active_room:
            raise HTTPException(status_code=403, detail="Not authorized to delete this item")
        
        is_in_same_room = db.query(models.SharedRoom).filter(
            models.SharedRoom.room_id == active_room.room_id,
            models.SharedRoom.user_id == owner_id
        ).first()
        if not is_in_same_room:
            raise HTTPException(status_code=403, detail="Not authorized to delete this item")

    db.delete(db_item)
    db.commit()
    return {"message": "Item deleted successfully"}

# Multimodal Recipe Generation Route
@app.post("/api/v1/analyze-fridge", response_model=schemas.AnalyzeResponse)
async def analyze_fridge(
    token: str = Form(...),
    strict_match: bool = Form(False),
    save_the_food: bool = Form(False),
    image: UploadFile = File(...),
    db: Session = Depends(database.get_db)
):
    user = get_current_user(token, db)
    dietary_restrictions = json.loads(user.dietary_restrictions)
    
    # Read inventory context
    inventory_items = fetch_user_inventory(user, db)
    inventory_data = [
        {
            "name": item.name,
            "quantity": item.quantity,
            "unit": item.unit,
            "category": item.category,
            "added_at": item.added_at.isoformat() if item.added_at else ""
        }
        for item in inventory_items
    ]
    
    image_bytes = await image.read()
    
    try:
        result = await analyze_fridge_image(
            image_bytes=image_bytes,
            dietary_restrictions=dietary_restrictions,
            inventory_items=inventory_data,
            strict_match=strict_match,
            save_the_food=save_the_food
        )
        return result
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(val_err)
        )


# Router mechanism for shared rooms URL serving
@app.get("/room/{room_id}")
async def serve_room(room_id: str):
    static_file_path = os.path.join("backend", "static", "index.html")
    if os.path.exists(static_file_path):
        return FileResponse(static_file_path)
    raise HTTPException(status_code=404, detail="Frontend file not found")

# Serve the static frontend SPA
static_dir = os.path.join("backend", "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

# Mount the static files
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
