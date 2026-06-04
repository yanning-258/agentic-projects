import threading
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import engine, get_db
from models import Base, Task
from src.planning_agent import planner_agent, executor_agent_step

from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="templates")

class AnalyseRequest(BaseModel):
    ticker: str
    question: str

def run_analysis(task_id: str, ticker: str, question: str):
    from database import SessionLocal
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        task.status = "in_progress"
        db.commit()

        steps = planner_agent(question, ticker)
        task.steps = [{"step": s if isinstance(s, str) else str(s), "status": "pending"} for s in steps]
        db.commit()

        history = []
        for i, step in enumerate(steps):
            task.steps[i]["status"] = "in_progress"
            db.commit()

            result = executor_agent_step(step, ticker, question, history)
            history.append(result)

            task.steps[i]["status"] = "done"
            db.commit()

        task.result = history[-1]
        task.status = "done"
        db.commit()

    except Exception as e:
        task.status = "failed"
        task.result = str(e)
        db.commit()
    finally:
        db.close()

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/analyse")
def analyse(request: AnalyseRequest, db: Session = Depends(get_db)):
    task_id = str(uuid.uuid4())
    task = Task(id=task_id, status="pending", steps=[], result=None)
    db.add(task)
    db.commit()

    thread = threading.Thread(target=run_analysis, args=(task_id, request.ticker, request.question))
    #request already parsed and validated by pydantic
    thread.start()

    return {"task_id": task_id}

@app.get("/task_progress/{task_id}")
def task_progress(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": task.status, "steps": task.steps}

@app.get("/task_status/{task_id}")
def task_status(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": task.status, "result": task.result}

@app.get("/ui")
def ui(request: Request):
    return templates.TemplateResponse(request, "index.html")
