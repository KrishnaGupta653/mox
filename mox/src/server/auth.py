"""
Authentication Manager with JWT, Rate Limiting, and Security
"""

import os
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from collections import defaultdict
import threading


class AuthManager:
    def __init__(self, pin: str):
        self.pin = self._hash_pin(pin)
        self.secret_key = secrets.token_urlsafe(32)
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 1440  # 24 hours
        
        # Rate limiting
        self.failed_attempts = defaultdict(list)
        self.rate_limit_lock = threading.Lock()
        self.max_attempts = 5
        self.lockout_duration = 300  # 5 minutes
    
    def _hash_pin(self, pin: str) -> str:
        """Hash PIN for secure storage"""
        return hashlib.sha256(pin.encode()).hexdigest()
    
    def authenticate(self, pin: str) -> Optional[str]:
        """Authenticate user and return JWT token"""
        hashed_pin = self._hash_pin(pin)
        
        if hashed_pin != self.pin:
            return None
        
        # Generate JWT token
        expires_delta = timedelta(minutes=self.access_token_expire_minutes)
        expire = datetime.utcnow() + expires_delta
        
        to_encode = {
            "sub": "mox_user",
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    def check_rate_limit(self, client_ip: str) -> bool:
        """Check if IP is rate limited"""
        with self.rate_limit_lock:
            now = time.time()
            
            # Clean old attempts
            self.failed_attempts[client_ip] = [
                attempt for attempt in self.failed_attempts[client_ip]
                if now - attempt < self.lockout_duration
            ]
            
            # Check if locked out
            if len(self.failed_attempts[client_ip]) >= self.max_attempts:
                return False
            
            return True
    
    def record_failed_attempt(self, client_ip: str):
        """Record failed authentication attempt"""
        with self.rate_limit_lock:
            self.failed_attempts[client_ip].append(time.time())
    
    def clear_failed_attempts(self, client_ip: str):
        """Clear failed attempts after successful login"""
        with self.rate_limit_lock:
            self.failed_attempts[client_ip] = []


# Dependency for FastAPI routes
async def get_current_user(authorization: str = None) -> dict:
    """Get current authenticated user from JWT token"""
    if not authorization:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Extract token from "Bearer <token>"
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    
    auth_manager = AuthManager(os.environ.get('MOX_PIN', '000000'))
    payload = auth_manager.verify_token(token)
    
    if not payload:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload
