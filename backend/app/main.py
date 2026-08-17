from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.api.v1 import api_router
from app.services.cpm_engine import CycleDetectedError

app = FastAPI(
    title="EventPath Scheduling Engine API",
    description=(
        "A Critical Path Method (CPM) and Program Evaluation and Review Technique (PERT) "
        "computational scheduling engine backend designed for event planning projects."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global Exception Handler for CycleDetectedError
@app.exception_handler(CycleDetectedError)
async def cycle_detected_exception_handler(request: Request, exc: CycleDetectedError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": str(exc),
            "cycle_ids": exc.cycle_ids,
            "cycle_names": exc.cycle_names
        }
    )

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the EventPath Scheduling Engine API. Visit /docs for API documentation."
    }
