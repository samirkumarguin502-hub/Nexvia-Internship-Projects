from pathlib import Path
p = Path("backend/app/schemas.py")
s = p.read_text(encoding="utf-8")

if "class LoginIn(" in s:
    print("AUTH SCHEMAS ALREADY PRESENT")
    raise SystemExit(0)

s += '''

class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class UserCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
    role: Literal["admin", "analyst"]


class TokenOut(_Out):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(_Out):
    id: int
    username: str
    role: str
    is_active: bool
'''
p.write_text(s, encoding="utf-8")
print("AUTH SCHEMAS ADDED")
