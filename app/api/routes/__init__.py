from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.user import router as user_router

__all__ = ["admin_router", "auth_router", "user_router"]
