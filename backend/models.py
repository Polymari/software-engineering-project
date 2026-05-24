from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    dietary_restrictions = Column(String, default="[]")  # JSON string of restrictions
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    items = relationship("InventoryItem", back_populates="owner", cascade="all, delete-orphan")
    shared_rooms = relationship("SharedRoom", back_populates="user", cascade="all, delete-orphan")

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    quantity = Column(Float, default=1.0)
    unit = Column(String, default="pcs")
    category = Column(String, default="Others")
    added_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    owner = relationship("User", back_populates="items")

class SharedRoom(Base):
    __tablename__ = "shared_rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="shared_rooms")
