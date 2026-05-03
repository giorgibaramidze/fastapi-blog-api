from fastapi import FastAPI
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter
from app.modules.auth.routes import auth_router
from app.core.exceptions.handlers import (
    register_exception_handlers,
)
 
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    register_exception_handlers(app)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_router = APIRouter(prefix="/api/v1")

    api_router.include_router(auth_router)

    app.include_router(api_router)

    return app


app = create_app()
 