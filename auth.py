from datetime import datetime, timedelta, timezone  
from typing import Annotated

from jose import jwt, JWTError
from passlib.context import CryptContext

from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer

from database import get_connection

SECRET_KEY = "your_64_character_random_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

pwd_context = CryptContext(schemes=['bcrypt'])

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):

    payload = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload.update({
        'exp': expire
    })

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get('sub')
        user_id = payload.get('user_id')

        if not username or not user_id:
            raise credentials_exception


    except JWTError:
        raise credentials_exception

    return {
        'username': username,
        'user_id': user_id
    }


