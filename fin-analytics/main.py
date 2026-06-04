from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import engine
from models import Base

@asynccontextmanager #turns the lifespan function into a context manager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    #code before yield is run on startup, code after yield is run on shutdown

app = FastAPI(lifespan=lifespan)
#this is to tell FastAPI to use this function for startup/shutdown


@app.get("/")
def health_check():
    return {"status": "ok"}
