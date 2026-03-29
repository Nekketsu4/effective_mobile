from fastapi import FastAPI
from app.api.v1 import auth, mock_resources


app = FastAPI(title="Effective")


app.include_router(auth.router)
app.include_router(mock_resources.router)
