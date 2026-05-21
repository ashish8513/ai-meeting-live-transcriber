from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.config import get_settings
from api.database import get_db
from api.deps import get_current_user
from api.models import User, UserRole
from api.schemas import TokenResponse, UserLogin, UserOut, UserRegister
from api.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=TokenResponse)
def register(body: UserRegister, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    role = UserRole.user
    if settings.admin_email and email == settings.admin_email:
        role = UserRole.admin
    elif db.query(User).count() == 0:
        role = UserRole.admin

    user = User(
        email=email,
        full_name=body.full_name.strip(),
        hashed_password=hash_password(body.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.email, user.role.value, user.id)
    return TokenResponse(
        access_token=token,
        role=user.role.value,
        email=user.email,
        full_name=user.full_name,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.email, user.role.value, user.id)
    return TokenResponse(
        access_token=token,
        role=user.role.value,
        email=user.email,
        full_name=user.full_name,
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        created_at=user.created_at,
    )
