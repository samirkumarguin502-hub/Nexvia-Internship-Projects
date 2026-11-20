import sqlite3

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.core.security import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    verify_password,
    issue_token,
    decode_token,
)
from app.core.rate_limit import (
    check_login_limit,
    record_failed_login,
    reset_login_limit,
)


router = APIRouter()
bearer = HTTPBearer(auto_error=False)


class RegisterBody(BaseModel):
    email: str = Field(
        min_length=5,
        max_length=254,
        pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$',
    )
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=10, max_length=128)


class LoginBody(BaseModel):
    email: str = Field(
        min_length=5,
        max_length=254,
        pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$',
    )
    password: str = Field(min_length=1, max_length=128)
    portal: str = Field(default='user', pattern='^(user|admin)$')


@router.post('/register', status_code=201)
def register(body: RegisterBody):
    if get_user_by_email(body.email):
        raise HTTPException(
            409,
            'An account with this email already exists',
        )

    try:
        user = create_user(
            body.email,
            body.full_name,
            body.password,
            'user',
        )

    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            409,
            'An account with this email already exists',
        ) from exc

    return {
        'access_token': issue_token(user),
        'token_type': 'bearer',
        'user': user,
    }


@router.post('/login')
def login(body: LoginBody, request: Request):
    rate_limit_key = check_login_limit(body.email, request)

    user = get_user_by_email(body.email)

    if (
        not user
        or not user['active']
        or not verify_password(body.password, user['password_hash'])
    ):
        record_failed_login(rate_limit_key)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid email or password',
        )

    if body.portal == 'admin' and user['role'] != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='This account does not have administrator access',
        )

    if body.portal == 'user' and user['role'] != 'user':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Use the administrator login for this account',
        )

    reset_login_limit(rate_limit_key)

    public_user = {
        key: user[key]
        for key in ('id', 'email', 'full_name', 'role', 'active')
    }

    return {
        'access_token': issue_token(public_user),
        'token_type': 'bearer',
        'user': public_user,
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    if not credentials:
        raise HTTPException(
            401,
            'Authentication required',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    try:
        claims = decode_token(credentials.credentials)

    except ValueError:
        raise HTTPException(
            401,
            'Invalid or expired session',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    user = get_user_by_id(int(claims['sub']))

    if not user or not user['active']:
        raise HTTPException(401, 'Account unavailable')

    return user


def require_admin(user=Depends(get_current_user)):
    if user['role'] != 'admin':
        raise HTTPException(
            403,
            'Administrator permission required',
        )

    return user


@router.get('/me')
def me(user=Depends(get_current_user)):
    return {
        key: user[key]
        for key in ('id', 'email', 'full_name', 'role', 'active')
    }