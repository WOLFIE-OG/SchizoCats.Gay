import signal
import aiosqlite
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .libs import setup_logging, signal_handler
from .routers import api_router, front_router

middleware = [
    Middleware(SessionMiddleware, secret_key="f43543h625346g4536bh534", max_age=None)
]

app = FastAPI(debug=False, middleware=middleware, log_config=None)
app.mount("/web", StaticFiles(directory="web"), name="web")
templates = Jinja2Templates(directory="web/templates")
setattr(app, "templates", Jinja2Templates(directory="web/templates"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def start_up():
    setup_logging(app)
    signal.signal(signal.SIGINT, signal_handler)
    db_con = await aiosqlite.connect("CatDB.schizo")
    await db_con.execute(
        "CREATE TABLE IF NOT EXISTS Media (ID INTEGER PRIMARY KEY AUTOINCREMENT, FileID, FileHash, Extension, OriginalFileName, Size, ContentType, UploadDate, IP, Origin)"
    )
    app.__setattr__("database", db_con)


@app.middleware("http")
async def log_request(request: Request, call_next):
    """_summary_

    Args:
        request (Request): _description_
        call_next (_type_): _description_

    Returns:
        _type_: _description_
    """
    response: Request = await call_next(request)
    response.headers["server"] = "Cats"
    return response


app.include_router(api_router)
app.include_router(front_router)
