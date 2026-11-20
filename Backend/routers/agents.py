from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Credit_Transaction
from pydantic import BaseModel, Field
from typing import Literal
from agents.master_agent import get_master_agent, get_agent_instance
from security import get_current_user

router = APIRouter(prefix="/route", tags=["agents"])

class RouteRequest(BaseModel):
    request: str = Field(min_length=1)
    destination: Literal["code", "pdf", "ppt", "image", "video", "chat"] | None = None

@router.post("/")
def route_request(
    req: RouteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if req.destination:
        destination = req.destination
    else:
        try:
            destination = get_master_agent()(req.request)
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Could not route the request") from exc
    
    # 2. Get Agent Instance and Cost
    agent = get_agent_instance(destination)
    cost = agent.cost
    
    # 3. Check Credits
    if user.credit_balance < cost:
        raise HTTPException(status_code=402, detail="Insufficient credits")
        
    # 4. Execute Agent and Deduct Credits
    try:
        response = agent.run(req.request)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The selected AI agent failed to process the request") from exc
    
    user.credit_balance -= cost
    transaction = Credit_Transaction(
        user_id=user.id,
        amount=-cost,
        transaction_type=destination
    )
    db.add(transaction)
    db.commit()
    
    return {
        "request": req.request,
        "destination": destination,
        "response": response,
        "credits_deducted": cost,
        "remaining_credits": user.credit_balance
    }
