from fastapi import APIRouter, Depends
from models import User
from security import get_current_user

router = APIRouter(prefix="/credits", tags=["credits"])

@router.get("/me")
def get_credits(user: User = Depends(get_current_user)):
    return {"user_id": user.id, "balance": user.credit_balance}
