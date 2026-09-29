from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt, JWTError
from fastapi import HTTPException
from app.database import User
from sqlalchemy import select

SECRET_KEY = os.getenv("VAULTX_JWT_SECRET", "supersecret-dev-key")
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    # bcrypt requires bytes
    salt = bcrypt.gensalt()
    pwd_bytes = password.encode('utf-8')
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except ValueError:
        return False

def create_access_token(user_id: str, role: str, expires_delta: timedelta = timedelta(hours=8)) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"user_id": user_id, "role": role, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        role: str = payload.get("role")
        if user_id is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return {"user_id": user_id, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

def seed_default_users(session):
    users = [
        {"id": "user-1", "email": "analyst@vault.local", "name": "Analyst User", "role": "Analyst", "password": "vaultx"},
        {"id": "user-2", "email": "senior@vault.local", "name": "Senior User", "role": "Senior Investigator", "password": "vaultx"},
        {"id": "user-3", "email": "supervisor@vault.local", "name": "Supervisor User", "role": "Supervisor", "password": "vaultx"},
        {"id": "user-4", "email": "auditor@vault.local", "name": "Auditor User", "role": "Auditor", "password": "vaultx"},
    ]
    
    for u in users:
        existing = session.scalars(select(User).where(User.email == u["email"])).first()
        if not existing:
            new_user = User(
                id=u["id"],
                email=u["email"],
                name=u["name"],
                role=u["role"],
                password_hash=hash_password(u["password"]),
                is_active=True
            )
            session.add(new_user)
    
    try:
        session.commit()
    except Exception as e:
        session.rollback()
