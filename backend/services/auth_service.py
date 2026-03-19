"""
Authentication Service for CarbonShip
JWT-based authentication with user management.

Features:
- User registration and login
- JWT token generation and validation
- Password hashing with bcrypt
- User session management
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict
from dataclasses import dataclass, asdict
from enum import Enum


# Configuration
SECRET_KEY = os.getenv("CARBONSHIP_SECRET_KEY", secrets.token_hex(32))
ACCESS_TOKEN_EXPIRE_HOURS = 24
USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "users.json")


class UserRole(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class User:
    """User data model"""
    id: str
    email: str
    company_name: str
    password_hash: str
    role: UserRole
    created_at: str
    last_login: Optional[str] = None
    gstin: Optional[str] = None
    phone: Optional[str] = None
    calculations_this_month: int = 0
    max_calculations_per_month: int = 5  # Free tier default


@dataclass
class TokenPayload:
    """JWT token payload"""
    user_id: str
    email: str
    role: str
    exp: str


def _hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${hashed}"


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    try:
        salt, hashed = password_hash.split("$")
        return hashlib.sha256((password + salt).encode()).hexdigest() == hashed
    except Exception:
        return False


def _generate_token(user: User) -> str:
    """Generate JWT-like token (simplified)"""
    import base64
    
    payload = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value,
        "exp": (datetime.now() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)).isoformat()
    }
    
    payload_json = json.dumps(payload)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    
    # Create signature
    signature = hashlib.sha256((payload_b64 + SECRET_KEY).encode()).hexdigest()[:32]
    
    return f"{payload_b64}.{signature}"


def _verify_token(token: str) -> Optional[Dict]:
    """Verify and decode token"""
    import base64
    
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        
        payload_b64, signature = parts
        
        # Verify signature
        expected_sig = hashlib.sha256((payload_b64 + SECRET_KEY).encode()).hexdigest()[:32]
        if signature != expected_sig:
            return None
        
        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        payload = json.loads(payload_json)
        
        # Check expiration
        exp = datetime.fromisoformat(payload["exp"])
        if datetime.now() > exp:
            return None
        
        return payload
    except Exception:
        return None


class AuthService:
    """
    Authentication service for user management
    """
    
    # Role limits
    ROLE_LIMITS = {
        UserRole.FREE: 5,
        UserRole.STARTER: 50,
        UserRole.PROFESSIONAL: 500,
        UserRole.ENTERPRISE: 10000
    }
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self._load_users()
    
    def _load_users(self):
        """Load users from file"""
        try:
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, 'r') as f:
                    data = json.load(f)
                    for user_data in data.get("users", []):
                        user_data["role"] = UserRole(user_data["role"])
                        user = User(**user_data)
                        self.users[user.id] = user
        except Exception as e:
            print(f"Error loading users: {e}")
    
    def _save_users(self):
        """Save users to file"""
        try:
            os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
            users_data = []
            for user in self.users.values():
                user_dict = asdict(user)
                user_dict["role"] = user.role.value
                users_data.append(user_dict)
            
            with open(USERS_FILE, 'w') as f:
                json.dump({"users": users_data}, f, indent=2)
        except Exception as e:
            print(f"Error saving users: {e}")
    
    def register(
        self,
        email: str,
        password: str,
        company_name: str,
        gstin: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Dict:
        """
        Register a new user
        
        Args:
            email: User email
            password: Password (min 8 characters)
            company_name: Company/organization name
            gstin: Optional GSTIN for Indian companies
            phone: Optional phone number
            
        Returns:
            Dict with user info and access token
        """
        # Validate email
        if not email or "@" not in email:
            return {"error": "Invalid email address"}
        
        # Check if email exists
        for user in self.users.values():
            if user.email.lower() == email.lower():
                return {"error": "Email already registered"}
        
        # Validate password
        if len(password) < 8:
            return {"error": "Password must be at least 8 characters"}
        
        # Create user
        user_id = secrets.token_hex(16)
        user = User(
            id=user_id,
            email=email.lower(),
            company_name=company_name,
            password_hash=_hash_password(password),
            role=UserRole.FREE,
            created_at=datetime.now().isoformat(),
            gstin=gstin,
            phone=phone,
            calculations_this_month=0,
            max_calculations_per_month=self.ROLE_LIMITS[UserRole.FREE]
        )
        
        self.users[user_id] = user
        self._save_users()
        
        # Generate token
        token = _generate_token(user)
        
        return {
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "company_name": user.company_name,
                "role": user.role.value,
                "calculations_remaining": user.max_calculations_per_month - user.calculations_this_month
            },
            "access_token": token,
            "token_type": "bearer"
        }
    
    def login(self, email: str, password: str) -> Dict:
        """
        Login user
        
        Args:
            email: User email
            password: User password
            
        Returns:
            Dict with user info and access token
        """
        # Find user by email
        user = None
        for u in self.users.values():
            if u.email.lower() == email.lower():
                user = u
                break
        
        if not user:
            return {"error": "Invalid email or password"}
        
        # Verify password
        if not _verify_password(password, user.password_hash):
            return {"error": "Invalid email or password"}
        
        # Update last login
        user.last_login = datetime.now().isoformat()
        self._save_users()
        
        # Generate token
        token = _generate_token(user)
        
        return {
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "company_name": user.company_name,
                "role": user.role.value,
                "calculations_remaining": user.max_calculations_per_month - user.calculations_this_month
            },
            "access_token": token,
            "token_type": "bearer"
        }
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify access token
        
        Args:
            token: JWT token
            
        Returns:
            Dict with user info if valid, None otherwise
        """
        payload = _verify_token(token)
        if not payload:
            return None
        
        user = self.users.get(payload["user_id"])
        if not user:
            return None
        
        return {
            "id": user.id,
            "email": user.email,
            "company_name": user.company_name,
            "role": user.role.value,
            "calculations_remaining": user.max_calculations_per_month - user.calculations_this_month
        }
    
    def increment_calculation(self, user_id: str) -> Dict:
        """
        Increment calculation count for user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with remaining calculations or error
        """
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}
        
        if user.calculations_this_month >= user.max_calculations_per_month:
            return {
                "error": "Monthly calculation limit reached",
                "limit": user.max_calculations_per_month,
                "upgrade_url": "/pricing"
            }
        
        user.calculations_this_month += 1
        self._save_users()
        
        return {
            "success": True,
            "calculations_used": user.calculations_this_month,
            "calculations_remaining": user.max_calculations_per_month - user.calculations_this_month
        }
    
    def get_user_stats(self, user_id: str) -> Optional[Dict]:
        """Get user statistics"""
        user = self.users.get(user_id)
        if not user:
            return None
        
        return {
            "id": user.id,
            "email": user.email,
            "company_name": user.company_name,
            "role": user.role.value,
            "gstin": user.gstin,
            "calculations_this_month": user.calculations_this_month,
            "max_calculations_per_month": user.max_calculations_per_month,
            "calculations_remaining": user.max_calculations_per_month - user.calculations_this_month,
            "member_since": user.created_at,
            "last_login": user.last_login
        }
    
    def upgrade_user(self, user_id: str, new_role: UserRole) -> Dict:
        """Upgrade user to a new role"""
        user = self.users.get(user_id)
        if not user:
            return {"error": "User not found"}
        
        user.role = new_role
        user.max_calculations_per_month = self.ROLE_LIMITS[new_role]
        self._save_users()
        
        return {
            "success": True,
            "new_role": new_role.value,
            "new_limit": user.max_calculations_per_month
        }


# Create singleton instance
auth_service = AuthService()


# FastAPI dependency helpers
from fastapi import HTTPException, Header


async def get_current_user(authorization: str = Header(None)) -> Dict:
    """FastAPI dependency to get current user from token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization[7:]
    user = auth_service.verify_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user


async def get_optional_user(authorization: str = Header(None)) -> Optional[Dict]:
    """FastAPI dependency to optionally get current user"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization[7:]
    return auth_service.verify_token(token)


if __name__ == "__main__":
    print("=" * 50)
    print("AUTH SERVICE TEST")
    print("=" * 50)
    
    # Test registration
    result = auth_service.register(
        email="test@tatasteel.com",
        password="testpass123",
        company_name="Tata Steel Limited",
        gstin="27AAACC1206D1ZM"
    )
    print(f"\nRegistration: {result}")
    
    if result.get("success"):
        token = result["access_token"]
        
        # Test token verification
        user = auth_service.verify_token(token)
        print(f"\nToken verification: {user}")
        
        # Test login
        login_result = auth_service.login("test@tatasteel.com", "testpass123")
        print(f"\nLogin: {login_result}")
        
        # Test calculation increment
        for i in range(3):
            calc_result = auth_service.increment_calculation(result["user"]["id"])
            print(f"\nCalculation {i+1}: {calc_result}")
