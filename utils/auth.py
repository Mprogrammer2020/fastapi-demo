import os  # Standard library for interacting with operating system
from bson import ObjectId  # Library for working with MongoDB ObjectId
from typing import Annotated  # Library for type annotations
from dotenv import load_dotenv  # Library for loading environment variables from a .env file
import jwt  # Library for handling JWT encoding and decoding
from datetime import datetime, timedelta  # Libraries for handling date and time
from passlib.context import CryptContext  # Library for hashing passwords
from fastapi.security import OAuth2PasswordBearer  # Security utility for handling OAuth2 password flow
from fastapi import Depends, HTTPException, status  # FastAPI utilities for dependency injection and error handling
from schemas.schema import find_one_schema, insert_one_schema  # Importing utility functions for database operations

# Load environment variables
load_dotenv(override=True)

# Set up JWT and password hashing contexts
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """
    Dependency function to retrieve the current user based on the provided JWT token.
    
    Parameters:
    - token (str): The JWT token extracted from the Authorization header.
    
    Raises:
    - HTTPException: If the token is invalid or cannot be validated.
    
    Returns:
    - dict: The user's data if the token is valid; otherwise, raises an HTTP exception.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials"
    )
    
    try:
        payload = jwt.decode(token, key=SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("id")
        
        if user_id is None:
            raise credentials_exception
        
        # Use the common `find_one_schema` function to fetch user data
        user_data = find_one_schema({"_id": ObjectId(user_id)}, "users")
        
        if not user_data["status"]:
            raise credentials_exception
        
        return user_data["data"]
    
    except jwt.exceptions.InvalidTokenError:
        raise credentials_exception


def signup_user(username: str, email: str, password: str):
    """
    Function to create a new user account with a unique username and email, hashing the password.
    
    Parameters:
    - username (str): The username for the new account.
    - email (str): The email for the new account.
    - password (str): The password for the new account.
    
    Raises:
    - HTTPException: If the username or email already exists.
    
    Returns:
    - dict: Success message upon successful account creation.
    """
    # Check if a user with the given username or email already exists
    if find_one_schema({"$or": [{"username": username}, {"email": email}]}, "users")["status"]:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Hash the password and prepare the user data
    hashed_password = pwd_context.hash(password)
    user_data = {"username": username, "email": email, "password": hashed_password, "total_credits": 1000}
    
    # Insert user data into the database
    result = insert_one_schema(user_data, "users")
    if not result["status"]:
        raise HTTPException(status_code=500, detail="Failed to create user account")
    
    return {"status": "success", "detail": "User created successfully"}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Parameters:
    - plain_password (str): The plain text password to verify.
    - hashed_password (str): The hashed password stored in the database.
    
    Returns:
    - bool: True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a JWT access token with optional expiration.
    
    Parameters:
    - data (dict): Data to include in the JWT payload.
    - expires_delta (timedelta): Optional; the time duration for the token's validity.
    
    Returns:
    - str: The generated JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        to_encode.update({"exp": datetime.utcnow() + expires_delta})
    else:
        to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)})
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def login_user(username: str, password: str):
    """
    Function to authenticate an existing user and return a JWT token.
    
    Parameters:
    - username (str): The username of the user trying to log in.
    - password (str): The password of the user trying to log in.
    
    Raises:
    - HTTPException: If the username or password is invalid.
    
    Returns:
    - dict: Contains JWT token and token type upon successful authentication.
    """
    # Use the common `find_one_schema` function to fetch user by username
    user = find_one_schema({"username": username}, "users")
    
    if not user["status"] or not verify_password(password, user["data"]["password"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    
    # Generate JWT token with user ID as payload
    access_token = create_access_token(data={"id": str(user["data"]["_id"])})
    
    return {
        "status": "success",
        "detail": "User logged in successfully",
        "access_token": access_token,
        "token_type": "bearer"
    }
