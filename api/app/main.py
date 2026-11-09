from fastapi import FastAPI

app = FastAPI(title="AeroSafe API")

@app.get("/health")
def health():
    return {"status": "ok"}

