import os
import hashlib
import hmac
import json
import unittest
from types import SimpleNamespace

os.environ["JWT_SECRET_KEY"] = "test-only-secret-with-more-than-thirty-two-characters"
os.environ["RAZORPAY_KEY_ID"] = "rzp_test_key"
os.environ["RAZORPAY_KEY_SECRET"] = "test-only-provider-secret"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
import routers.payments as payments
from database import Base, get_db
from models import Credit_Transaction


class FakeRazorpayClient:
    def __init__(self):
        self.order_number = 0
        self.payment_data = {}
        self.order = SimpleNamespace(create=self.create_order)
        self.utility = SimpleNamespace(verify_payment_signature=lambda _data: True)
        self.payment = SimpleNamespace(fetch=lambda _payment_id: self.payment_data)

    def create_order(self, _data):
        self.order_number += 1
        return {"id": f"order_test_{self.order_number}"}


class AuthAndPaymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestSession = sessionmaker(bind=cls.engine)

        def override_db():
            db = cls.TestSession()
            try:
                yield db
            finally:
                db.close()

        main.app.dependency_overrides[get_db] = override_db
        cls.client = TestClient(main.app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        main.app.dependency_overrides.clear()
        cls.engine.dispose()

    def setUp(self):
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.provider = FakeRazorpayClient()
        payments._razorpay_client = lambda: self.provider
        response = self.client.post(
            "/users/",
            json={"username": "payer", "email": "payer@example.com", "password": "strong-pass-123"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.auth = response.json()
        self.headers = {"Authorization": f"Bearer {self.auth['access_token']}"}

    def test_authentication_scopes_profile_and_credits(self):
        self.assertEqual(self.client.get("/credits/me").status_code, 401)
        self.assertEqual(self.client.post("/route/", json={"request": "hello"}).status_code, 401)
        self.assertEqual(
            self.client.post(
                "/users/",
                json={"username": "   ", "email": "blank@example.com", "password": "strong-pass-789"},
            ).status_code,
            422,
        )
        self.assertEqual(self.client.get("/users/me", headers=self.headers).json()["id"], self.auth["user"]["id"])
        self.assertEqual(self.client.get("/credits/me", headers=self.headers).json()["balance"], 100)
        self.assertEqual(
            self.client.post("/users/login", json={"email": "payer@example.com", "password": "wrong-pass-123"}).status_code,
            401,
        )

    def test_paid_credits_are_granted_once(self):
        order_response = self.client.post(
            "/payments/orders",
            json={"package_id": "credits_50"},
            headers=self.headers,
        )
        self.assertEqual(order_response.status_code, 200, order_response.text)
        self.provider.payment_data = {
            "order_id": "order_test_1",
            "status": "captured",
            "amount": 5000,
        }
        payment = {
            "razorpay_order_id": "order_test_1",
            "razorpay_payment_id": "payment_test_1",
            "razorpay_signature": "verified-by-test-double",
        }
        other_user = self.client.post(
            "/users/",
            json={"username": "other", "email": "other@example.com", "password": "strong-pass-456"},
        ).json()
        other_headers = {"Authorization": f"Bearer {other_user['access_token']}"}
        self.assertEqual(self.client.post("/payments/verify", json=payment, headers=other_headers).status_code, 404)

        for _ in range(2):
            response = self.client.post("/payments/verify", json=payment, headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text)

        self.assertEqual(self.client.get("/credits/me", headers=self.headers).json()["balance"], 150)
        with self.TestSession() as db:
            self.assertEqual(db.query(Credit_Transaction).filter_by(transaction_type="payment").count(), 1)

    def test_captured_payment_webhook_requires_valid_signature(self):
        os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test-webhook-secret"
        self.client.post("/payments/orders", json={"package_id": "credits_50"}, headers=self.headers)
        body = json.dumps({
            "event": "payment.captured",
            "payload": {"payment": {"entity": {
                "id": "payment_webhook_1",
                "order_id": "order_test_1",
                "amount": 5000,
            }}},
        }).encode()
        signature = hmac.new(b"test-webhook-secret", body, hashlib.sha256).hexdigest()
        response = self.client.post(
            "/payments/webhook",
            content=body,
            headers={"X-Razorpay-Signature": signature, "Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get("/credits/me", headers=self.headers).json()["balance"], 150)

    def test_uncaptured_or_wrong_amount_payment_does_not_add_credits(self):
        self.client.post("/payments/orders", json={"package_id": "credits_50"}, headers=self.headers)
        self.provider.payment_data = {
            "order_id": "order_test_1",
            "status": "captured",
            "amount": 1,
        }
        response = self.client.post(
            "/payments/verify",
            json={
                "razorpay_order_id": "order_test_1",
                "razorpay_payment_id": "payment_test_1",
                "razorpay_signature": "verified-by-test-double",
            },
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/credits/me", headers=self.headers).json()["balance"], 100)

    def test_free_recharge_endpoint_is_gone(self):
        response = self.client.post("/credits/1/recharge?amount=500", headers=self.headers)
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()