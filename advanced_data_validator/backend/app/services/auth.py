"""
Authentication service for JWT token management and user verification.
Uses bcrypt for secure password hashing.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Password hashing context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "nyx-data-validator-secret-key-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Security scheme
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# Pre-hashed passwords for the two users
# These are bcrypt hashes of the passwords
# admin123 -> hashed | valid123 -> hashed
def get_valid_users():
    """Get valid users from environment variables with bcrypt hashed passwords."""
    users = {}
    
    # User 1
    user1_username = os.getenv("AUTH_USER1_USERNAME", "admin")
    user1_password_hash = os.getenv("AUTH_USER1_PASSWORD_HASH")
    user1_password_plain = os.getenv("AUTH_USER1_PASSWORD", "admin123")
    
    if user1_username:
        # Use hash if available, otherwise verify against plain (for backward compatibility)
        users[user1_username] = {
            "hash": user1_password_hash,
            "plain": user1_password_plain if not user1_password_hash else None
        }
    
    # User 2
    user2_username = os.getenv("AUTH_USER2_USERNAME", "validator")
    user2_password_hash = os.getenv("AUTH_USER2_PASSWORD_HASH")
    user2_password_plain = os.getenv("AUTH_USER2_PASSWORD", "valid123")
    
    if user2_username:
        users[user2_username] = {
            "hash": user2_password_hash,
            "plain": user2_password_plain if not user2_password_hash else None
        }
    
    return users


def verify_credentials(username: str, password: str) -> bool:
    """Verify username and password using bcrypt hashing."""
    valid_users = get_valid_users()
    
    if username not in valid_users:
        return False
    
    user_data = valid_users[username]
    
    # If hash is available, use secure bcrypt verification
    if user_data["hash"]:
        return verify_password(password, user_data["hash"])
    
    # Fallback to plain text comparison (for backward compatibility)
    # This should only be used during migration
    if user_data["plain"]:
        return user_data["plain"] == password
    
    return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify a JWT token and return the payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            return None
        
        return payload
    except JWTError:
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependency to get the current authenticated user from the JWT token.
    Raises HTTPException if token is invalid.
    """
    token = credentials.credentials
    
    # Import here to avoid circular imports
    from .session_db import get_session
    
    # Check if session exists in database
    session = get_session(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify the token
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {"username": payload.get("sub"), "token": token}


# Utility function to generate password hashes (run once to get hashes for .env)
def generate_password_hashes():
    """Generate bcrypt hashes for the default passwords."""
    passwords = {
        "admin123": hash_password("admin123"),
        "valid123": hash_password("valid123")
    }
    print("=== BCRYPT PASSWORD HASHES ===")
    print("Add these to your .env file for secure password storage:")
    print(f"AUTH_USER1_PASSWORD_HASH={passwords['admin123']}")
    print(f"AUTH_USER2_PASSWORD_HASH={passwords['valid123']}")
    return passwords


if __name__ == "__main__":
    generate_password_hashes()
