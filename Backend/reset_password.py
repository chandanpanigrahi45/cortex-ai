import getpass
import sys

from database import SessionLocal
from models import User
from security import password_hash


def main() -> int:
    email = input("Account email: ").strip().lower()
    password = getpass.getpass("New password (8+ characters): ")
    if len(password) < 8 or len(password) > 128:
        print("Password must be between 8 and 128 characters.")
        return 1

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print("No account found for that email.")
            return 1
        user.password_hash = password_hash.hash(password)
        db.commit()
        print("Password updated.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())