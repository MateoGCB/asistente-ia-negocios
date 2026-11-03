# schemas/user_schemas.py
from pydantic import BaseModel, EmailStr, field_validator

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72  # bcrypt only uses the first 72 BYTES: longer passwords would be silently cut


def strip_email(value):
    # Before EmailStr: spaces around the address are not an error, just noise
    return value.strip() if isinstance(value, str) else value


def lowercase_email(email: str) -> str:
    # EmailStr only lowercases the domain; the whole address is stored and compared in lowercase
    return email.lower()


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

    _strip_email = field_validator("email", mode="before")(strip_email)
    _lowercase_email = field_validator("email")(lowercase_email)

    @field_validator("password")
    @classmethod
    def password_rules(cls, password: str) -> str:
        # Only on register. Login never checks these rules (it always answers the same generic 401)
        if len(password) < PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must have at least {PASSWORD_MIN_LENGTH} characters")
        if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
            # Bytes, not characters: "ñ" or "á" take 2 bytes each
            raise ValueError(f"Password must be at most {PASSWORD_MAX_BYTES} bytes long")
        if not any(char.isalpha() for char in password):
            raise ValueError("Password must contain at least one letter")
        if not any(char.isdigit() for char in password):
            raise ValueError("Password must contain at least one number")
        return password


class User(BaseModel):
    id: int
    name: str
    email: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str  # no rules here on purpose

    _strip_email = field_validator("email", mode="before")(strip_email)
    _lowercase_email = field_validator("email")(lowercase_email)
