from pydantic import BaseModel, EmailStr, Field, ValidationInfo, field_validator

# Passwords that are rejected outright (compared case-insensitively).
COMMON_PASSWORDS = frozenset({
    "password", "password1", "password12", "password123", "passw0rd", "p@ssword",
    "12345678", "123456789", "1234567890", "qwertyuiop", "qwerty123", "iloveyou",
    "admin123", "administrator", "letmein123", "welcome123", "changeme", "changeme123",
    "abc12345", "11111111", "00000000", "scanhive", "scanhive123",
})


def validate_password_policy(password: str, email: str | None = None) -> str:
    # bcrypt only reads the first 72 bytes; anything longer would be silently
    # ignored, so reject it instead of pretending it counts.
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Your password is too long. Use at most 72 characters (fewer if it contains accents or symbols).")
    if not password.strip():
        raise ValueError("Your password can't be blank or only spaces.")
    if password.lower() in COMMON_PASSWORDS:
        raise ValueError("That password is too common and easy to guess. Try a longer passphrase, e.g. three or four unrelated words.")
    if email:
        local = email.split("@", 1)[0].lower()
        if password.lower() == email.lower() or (len(local) >= 4 and local in password.lower()):
            raise ValueError("Your password can't contain your email address or the part before the @. Choose something unrelated to it.")
    return password


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(default="", max_length=100)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("organization_name", "first_name", "last_name")
    @classmethod
    def strip_and_reject_markup(cls, value: str) -> str:
        value = value.strip()
        if any(ch in value for ch in "<>"):
            raise ValueError("Must not contain < or >")
        return value

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str, info: ValidationInfo) -> str:
        # `email` is declared earlier, so it's already validated here (and
        # absent if it was invalid, in which case that error is reported).
        email = info.data.get("email")
        return validate_password_policy(value, str(email) if email else None)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class InvitationPreviewResponse(BaseModel):
    organization_name: str
    email: EmailStr


class AcceptInvitationRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(default="", max_length=100)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_and_reject_markup(cls, value: str) -> str:
        value = value.strip()
        if any(ch in value for ch in "<>"):
            raise ValueError("Must not contain < or >")
        return value

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return validate_password_policy(value)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return validate_password_policy(value)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str
