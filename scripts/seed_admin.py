"""Create default admin account. Run: python scripts/seed_admin.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.database import SessionLocal, init_db
from api.models import User, UserRole
from api.security import hash_password

ADMIN_EMAIL = "admin@meetscribe.com"
ADMIN_PASSWORD = "Admin@123"
ADMIN_NAME = "MeetScribe Admin"


def main():
    init_db()
    db = SessionLocal()
    try:
        email = ADMIN_EMAIL.strip().lower()
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.role = UserRole.admin
            user.hashed_password = hash_password(ADMIN_PASSWORD)
            user.full_name = ADMIN_NAME
            db.commit()
            print(f"Updated existing user to admin: {email}")
        else:
            user = User(
                email=email,
                full_name=ADMIN_NAME,
                hashed_password=hash_password(ADMIN_PASSWORD),
                role=UserRole.admin,
            )
            db.add(user)
            db.commit()
            print(f"Created admin user: {email}")
        print(f"Password: {ADMIN_PASSWORD}")
        print("Login at http://localhost:3000/login")
    finally:
        db.close()


if __name__ == "__main__":
    main()
