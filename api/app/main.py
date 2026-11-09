from fastapi import FastAPI

from app.routers import alerts, auth

app = FastAPI(title="AeroSafe API")
app.include_router(auth.router)
app.include_router(alerts.router)


@app.get("/health")
def health():
    return {"status": "ok"}