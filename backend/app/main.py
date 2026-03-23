from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import contextlib

from app.core.warnings import silence_llama_index_pydantic_warning
# Silence the Pydantic validation warnings emitted by third-party packages early before they are imported
silence_llama_index_pydantic_warning()

from app.core.config import config
from app.api.admin_router import router as admin_router
from app.api.agent_router import router as agent_router
from app.core.scheduler import start_scheduler, stop_scheduler


from app.storage.vector_db import init_qdrant_collections

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 0: Initialize Qdrant Collections
    try:
        init_qdrant_collections()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to initialize Qdrant: {e}")

    # Phase 5: Initialize the APScheduler here
    start_scheduler()
    yield
    # Shutdown the scheduler here
    stop_scheduler()

def create_app() -> FastAPI:
    app = FastAPI(
        title=config.api_title,
        version=config.api_version,
        lifespan=lifespan
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(admin_router)
    app.include_router(agent_router)
    
    @app.get("/health/ready", tags=["Health"])
    async def ready():
        return {"status": "ok", "app": config.api_title}
        
    @app.get("/", include_in_schema=False)
    async def root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/docs")
        
    return app

app = create_app()
