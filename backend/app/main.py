from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.services.cpm_engine import CycleDetectedError
from app.db.session import engine
from app.db.base import Base

# Ensure all tables are created
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EventPath Scheduling Engine API",
    description=(
        "An Explainable AI Framework for Intelligent Event Scheduling and Dynamic Risk "
        "Optimization. Exposes a Critical Path Method (CPM) and Program Evaluation and "
        "Review Technique (PERT) computational scheduling engine, plus an XAI explanation "
        "layer that narrates bottlenecks, merge-path bias, crashing trade-offs and vendor "
        "constraint conflicts with the evidence behind every claim."
    ),
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Allow requests from React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
         "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "message": (
            "Welcome to the EventPath Scheduling Engine API. "
            "An Explainable AI Framework for Intelligent Event Scheduling and Dynamic Risk Optimization. "
            "Visit /docs for API documentation."
        )
    }
