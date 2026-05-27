from fastapi import APIRouter, Depends

from app.dependencies.authz import Principal, get_current_principal
from app.schemas.rbac import MeResponse, MeUserOut

router = APIRouter()


@router.get("/me", response_model=MeResponse)
def get_me(principal: Principal = Depends(get_current_principal)):
    return MeResponse(
        user=MeUserOut.model_validate(principal.db_user),
        roles=principal.roles,
        permissions=sorted(principal.permissions),
    )
