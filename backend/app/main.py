from fastapi import FastAPI
from app.api.authentication import authentication_router
from app.api.classifier import classifier_router
from app.db.init_db import init_db

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    await init_db()

app.include_router(authentication_router)
app.include_router(classifier_router)