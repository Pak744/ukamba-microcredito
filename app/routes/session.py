from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["Sessão"])

@router.get("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("access_token")
    resp.delete_cookie("Authorization")
    return resp
