from fastapi import FastAPI

from . import assessments, auth, health, questions, tracks


def register_routes(app: FastAPI) -> None:
    """Attach all API routers to the FastAPI application."""
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(tracks.router)
    app.include_router(questions.router)
    app.include_router(assessments.router)
