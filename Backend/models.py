from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String(255), nullable=True)
    credit_balance = Column(Integer, default=100)  # Default credits for new users

    transactions = relationship("Credit_Transaction", back_populates="user")
    payment_orders = relationship("PaymentOrder", back_populates="user")

class Credit_Transaction(Base):
    __tablename__ = "credit_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer)  # Positive for recharge, negative for usage
    transaction_type = Column(String)  # e.g., "recharge", "chat", "video"
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    
    user = relationship("User", back_populates="transactions")

class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    razorpay_order_id = Column(String, unique=True, nullable=False, index=True)
    razorpay_payment_id = Column(String, unique=True, nullable=True)
    amount_paise = Column(Integer, nullable=False)
    credits = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending")
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    user = relationship("User", back_populates="payment_orders")
