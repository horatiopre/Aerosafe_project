from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.security import create_token, get_current_user, verify_password
from app.users import FAKE_USERS

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = FAKE_USERS.get(form.username)
    if user is None or not verify_password(form.password, user["hashed_password"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiant ou mot de passe incorrect")
    token = create_token(user["username"], user["role"])
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user