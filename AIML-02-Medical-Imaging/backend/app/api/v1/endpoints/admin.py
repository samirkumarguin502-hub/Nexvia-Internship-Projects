from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.v1.endpoints.auth import require_admin
from app.core.security import list_users, update_user_active
router = APIRouter()
class ActiveBody(BaseModel): active: bool
@router.get('/users')
def users(_admin=Depends(require_admin)):
    return list_users()
@router.patch('/users/{user_id}/status')
def set_user_status(user_id: int, body: ActiveBody, admin=Depends(require_admin)):
    if user_id == admin['id'] and not body.active:
        raise HTTPException(400, 'You cannot deactivate your own administrator account')
    if not update_user_active(user_id, body.active):
        raise HTTPException(404, 'User not found')
    return {'user_id': user_id, 'active': body.active}
