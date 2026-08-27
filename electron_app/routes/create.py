from fastapi import APIRouter, Request,HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/create")

class CreateUserRequest(BaseModel):
    name: str

@router.post("/user", status_code=201)
async def create_user(body: CreateUserRequest, request: Request):
    node = request.app.state.node

    if node.user_loaded.is_set():
        raise HTTPException(status_code=404, detail="User not found") 
    
    node.create_user(body.name)
    return {"status": "ok", 'name':node.get_user()}


@router.post("/test")
async def test(body: CreateUserRequest):
    return body