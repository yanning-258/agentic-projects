# ========== standard libraries ==========
import threading
import uuid
from contextlib import asynccontextmanager

# ========== fastapi ==========
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request

# ========== Database ==========
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import engine, get_db
from models import Base, Task

# ========== own project modules ==========
from single_ticker.planning_agent import planner_agent, executor_agent_step
from portfolio_agent.dashboard import get_dashboard_data, TICKERS


# 01: Create app, with starting and exit execution manager
#Q: Why context manager: 
# we need some code to be run once at startup and once at shutdown
# this is exactly the shape of contextmanager: __enter__, __exit__
# code before yield is code to be run at start up, after yield = code at shutdown
# fastapi -> lifespan parameter -> expext this shape

#Q: why async
# fastapi's whole request-handling lidfecyle runs on an async event loop,
# so the lifespan hook has to be an async def to fit into that same loop
#replaces old @app.on_event("startup") / @app.on_event("shutdown") decorators 
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

#02: Define Web template
templates = Jinja2Templates(directory="templates")
templates.env.filters["commas"] = lambda v: f"{v:,}" if isinstance(v, (int, float)) else v

#03: Create Pydantic Schema - defined the exact shape of the JSON body the other API expects to receive
class AnalyseRequest(BaseModel):
    ticker: str
    question: str

def run_analysis(task_id: str, ticker: str, question: str):
    from database import SessionLocal
    db = SessionLocal()
    try:
        #Step 1: Open a new task, register it in db, commit
        task = db.query(Task).filter(Task.id == task_id).first()
        task.status = "in_progress"
        db.commit()
        #Step 2: plan steps, register steps in db
        steps = planner_agent(question, ticker)
        task.steps = [{"step": s if isinstance(s, str) else str(s), "status": "pending"} for s in steps]
        db.commit()

        # Step 3: iterate to execute steps, change status to complete when finish
        history = []
        for i, step in enumerate(steps):
            task.steps[i]["status"] = "in_progress"
            db.commit()

            result = executor_agent_step(step, ticker, question, history)
            history.append(result)

            task.steps[i]["status"] = "done"
            db.commit()

        #Step 4: store task result history and update state, commit to db
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

@app.get("/dashboard")
def dashboard():
    return get_dashboard_data(TICKERS)

@app.get("/dashboard/view")
def dashboard_view(request: Request):
    data = get_dashboard_data(TICKERS)
    for d in data:
        if isinstance(d["News"], str):  # news_tool returns a plain string when there's no news
            d["News"] = []
    return templates.TemplateResponse(request, "dashboard.html", {"dashboards": data})