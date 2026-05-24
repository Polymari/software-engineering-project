from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    dietary_restrictions: List[str]
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdateRestrictions(BaseModel):
    dietary_restrictions: List[str]

# Inventory Item Schemas
class InventoryItemCreate(BaseModel):
    name: str
    quantity: float = 1.0
    unit: str = "pcs"
    category: str = "Others"
    expires_at: Optional[datetime] = None

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    expires_at: Optional[datetime] = None

class InventoryItemOut(BaseModel):
    id: int
    user_id: int
    name: str
    quantity: float
    unit: str
    category: str
    added_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Shared Room Schemas
class SharedRoomJoin(BaseModel):
    room_id: str

class SharedRoomOut(BaseModel):
    id: int
    room_id: str
    user_id: int
    joined_at: datetime

    class Config:
        from_attributes = True

# AI Multimodal analysis schemas
class IngredientDetected(BaseModel):
    name: str
    quantity: float
    unit: str
    category: str
    days_to_expiration: int

class RecipeStep(BaseModel):
    name: str
    ingredients_used: List[str]
    instructions: List[str]
    prep_time: str

class AnalyzeResponse(BaseModel):
    ingredients: List[IngredientDetected]
    recipes: List[RecipeStep]

# Auth Token schema
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
