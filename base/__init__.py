from server.routes.ui.auth import router as auth_router
from server.routes.ui.user_pages import router as user_router
from server.routes.ui.welcome import router as dashboard_router

__all__ = ["auth_router", "user_router", "dashboard_router"]
