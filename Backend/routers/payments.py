import json
import os

import razorpay
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Credit_Transaction, PaymentOrder, User
from security import get_current_user

router = APIRouter(prefix="/payments", tags=["payments"])
PACKAGES = {"credits_50": {"amount_paise": 5000, "credits": 50}}


class CreateOrderRequest(BaseModel):
    package_id: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def _razorpay_client():
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        raise HTTPException(status_code=503, detail="Razorpay is not configured")
    return razorpay.Client(auth=(key_id, key_secret))


def _settle_order(db: Session, order_id: str, payment_id: str) -> PaymentOrder:
    order = (
        db.query(PaymentOrder)
        .filter(PaymentOrder.razorpay_order_id == order_id)
        .with_for_update()
        .first()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Payment order not found")
    if order.status == "paid":
        if order.razorpay_payment_id != payment_id:
            raise HTTPException(status_code=409, detail="Order was paid with a different payment")
        return order

    user = db.query(User).filter(User.id == order.user_id).with_for_update().first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    order.status = "paid"
    order.razorpay_payment_id = payment_id
    user.credit_balance += order.credits
    db.add(Credit_Transaction(
        user_id=user.id,
        amount=order.credits,
        transaction_type="payment",
    ))
    db.commit()
    db.refresh(order)
    return order


@router.post("/orders")
def create_order(
    order_data: CreateOrderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    package = PACKAGES.get(order_data.package_id)
    if package is None:
        raise HTTPException(status_code=400, detail="Invalid credit package")

    client = _razorpay_client()
    try:
        provider_order = client.order.create({
            "amount": package["amount_paise"],
            "currency": "INR",
            "receipt": f"credits-{user.id}-{os.urandom(8).hex()}",
            "notes": {"user_id": str(user.id), "credits": str(package["credits"])},
        })
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not create payment order") from exc

    db.add(PaymentOrder(
        user_id=user.id,
        razorpay_order_id=provider_order["id"],
        amount_paise=package["amount_paise"],
        credits=package["credits"],
        status="pending",
    ))
    db.commit()
    return {
        "key_id": os.environ["RAZORPAY_KEY_ID"],
        "order_id": provider_order["id"],
        "amount_paise": package["amount_paise"],
        "currency": "INR",
        "credits": package["credits"],
    }


@router.post("/verify")
def verify_payment(
    payment_data: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = db.query(PaymentOrder).filter(
        PaymentOrder.razorpay_order_id == payment_data.razorpay_order_id,
        PaymentOrder.user_id == user.id,
    ).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Payment order not found")
    if order.status == "paid":
        if order.razorpay_payment_id != payment_data.razorpay_payment_id:
            raise HTTPException(status_code=409, detail="Order was paid with a different payment")
        return {"status": "paid", "credits": user.credit_balance}

    client = _razorpay_client()
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": payment_data.razorpay_order_id,
            "razorpay_payment_id": payment_data.razorpay_payment_id,
            "razorpay_signature": payment_data.razorpay_signature,
        })
        provider_payment = client.payment.fetch(payment_data.razorpay_payment_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Payment verification failed") from exc

    if (
        provider_payment.get("order_id") != order.razorpay_order_id
        or provider_payment.get("status") != "captured"
        or provider_payment.get("amount") != order.amount_paise
    ):
        raise HTTPException(status_code=400, detail="Payment is not captured for this order")

    settled_order = _settle_order(db, order.razorpay_order_id, payment_data.razorpay_payment_id)
    return {
        "status": settled_order.status,
        "credits_added": settled_order.credits,
        "balance": db.query(User.credit_balance).filter(User.id == user.id).scalar(),
    }


@router.post("/webhook")
async def payment_webhook(request: Request, db: Session = Depends(get_db)):
    webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Razorpay webhook is not configured")

    body = await request.body()
    import hashlib
    import hmac

    expected = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        event = json.loads(body)
        payment = event["payload"]["payment"]["entity"]
        if event.get("event") != "payment.captured":
            return {"status": "ignored"}
        order = db.query(PaymentOrder).filter(
            PaymentOrder.razorpay_order_id == payment["order_id"]
        ).first()
        if order is None or payment.get("amount") != order.amount_paise:
            raise HTTPException(status_code=400, detail="Payment does not match an order")
        _settle_order(db, order.razorpay_order_id, payment["id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid payment webhook payload") from exc

    return {"status": "ok"}