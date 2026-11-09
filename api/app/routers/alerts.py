from fastapi import APIRouter, Depends

from app.security import require_role

router = APIRouter(prefix="/alerts", tags=["Alertes"])


@router.get("")
def list_alerts(user: dict = Depends(require_role("superviseur"))):
    # Liste vide pour l'instant : les vraies alertes viendront du Lot 3.
    return []