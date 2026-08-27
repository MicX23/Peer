from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/get")

@router.get("/user")
async def get_user(request: Request):
    node = request.app.state.node

    if not node.user_loaded.is_set():
        raise HTTPException(status_code=404, detail="User not found")
    return {'name':node.get_user()}