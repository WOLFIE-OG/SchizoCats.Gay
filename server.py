import pathlib
import uuid
import asyncio
import datetime
from typing import List
import hashlib
import json
import signal
import sys
import logging
import re
from asyncio import get_event_loop_policy
from aiohttp import ClientSession
import aiosqlite
from colorama import Fore, init
from pypika import Table, Query
from fastapi import FastAPI, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from uvicorn import Config, Server
from libs.utils import Utils

BASE_URL = "https://schizocats.gay"
WEB_URL = f"{BASE_URL}/web"
API_URL = f"{BASE_URL}/api"


def setup_logging(app_instance: FastAPI):
    """_summary_

    Args:
        app_instance (FastAPI): _description_
    """
    init(autoreset=True)
    spacer = f"{Fore.WHITE}-{Fore.RESET}"
    formatting = [
        f"{Fore.LIGHTMAGENTA_EX}CatServer{Fore.RESET}",
        f"{Fore.LIGHTBLACK_EX}%(asctime)s{Fore.RESET}",
        f"{Fore.LIGHTMAGENTA_EX}%(name)s{Fore.RESET}",
        f"{Fore.YELLOW}%(levelname)s{Fore.RESET}",
        f"{Fore.WHITE}%(message)s{Fore.RESET}",
    ]
    formatting = f" | {spacer} | ".join(formatting)
    for logger in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        log = logging.getLogger(logger)
        if len(log.handlers) != 0:
            log.removeHandler(log.handlers[0])
        log.propagate = False
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(formatting))
        log.addHandler(handler)
        setattr(app_instance, f"logger.{logger}", log)
    


base_router = InferringRouter()
front_end = InferringRouter()

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


def receive_signal(signalNumber: int, *args, **kwargs):
    """_summary_

    Args:
        signalNumber (int): _description_
    """
    print(f"Received: {signalNumber}")
    sys.exit()


async def get_random_video():
    cursor = await app.database.cursor()
    get_records = await cursor.execute("SELECT * FROM Media ORDER BY RANDOM() LIMIT 1;")
    records = await get_records.fetchall()
    return records[0][1], records[0][3]


@app.on_event("startup")
async def start_up():
    setup_logging(app)
    signal.signal(signal.SIGINT, receive_signal)
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


@cbv(front_end)
class FrontEnd:
    @front_end.get("/")
    async def home(self, request: Request):
        """_summary_

        Args:
            request (Request): _description_

        Returns:
            _type_: _description_
        """
        file_id, ext = await get_random_video()
        return templates.TemplateResponse(
            "home.jinja2",
            {
                "request": request,
                "random_file": f"{file_id}.{ext}",
            },
        )


@cbv(base_router)
class BaseCat:
    @base_router.get("/api/upload/external")
    async def upload_external_site(self, request: Request, url: str):
        """_summary_

        Args:
            request (Request): _description_
            url (str): _description_

        Returns:
            _type_: _description_
        """
        
        async with ClientSession() as session:
            headers, url = await Utils.get_url(url)
            if url:
                async with session.get(
                    url,
                    headers=headers,
                ) as req:
                    file = await req.read()
                    file_id = f"CAT_{str(uuid.uuid4())}"
                    hash = hashlib.sha256(file).hexdigest()
                    cursor = await app.database.cursor()
                    res = await cursor.execute(
                        f"SELECT FileHash FROM Media WHERE FileHash='{hash}'"
                    )
                    if len(await res.fetchall()) > 0:
                        return JSONResponse(
                            content={
                                "upload_type": "EXTERNAL_VIDEO",
                                "msg": "File is already uploaded.",
                            },
                            status_code=403,
                        )

                    with open(
                        pathlib.Path(f"web/content/{file_id}.mp4"),
                        "wb",
                    ) as _file:
                        _file.write(file)

                    ip = request.headers.get("cf-connecting-ip")
                    origin = request.headers.get("cf-ipcountry")
                    
                    query = (
                        Query.into(Table("Media"))
                        .columns(
                            "FileID",
                            "FileHash",
                            "Extension",
                            "OriginalFileName",
                            "Size",
                            "ContentType",
                            "UploadDate",
                            "IP",
                            "Origin",
                        )
                        .insert(
                            file_id,
                            hash,
                            "mp4",
                            "EXTERNAL_DOWNLOAD",
                            len(file),
                            "video/mp4",
                            int(datetime.datetime.now().timestamp()),
                            ip,
                            origin,
                        )
                    )

                    await cursor.execute(str(query))
                    await app.database.commit()
                    await cursor.close()
                    return JSONResponse(
                        content={
                            "upload_type": "external",
                            "msg": "Uploaded video from external site.",
                        },
                        status_code=200,
                    )
            else:
                return JSONResponse(
                    content={
                        "upload_type": "external",
                        "msg": "Couldn't find raw URL or the url is invalid.",
                    },
                    status_code=403,
                )
    @base_router.post("/api/upload")
    async def upload_file(self, request: Request, files: List[UploadFile]):
        """_summary_

        Args:
            request (Request): _description_
            files (List[UploadFile]): _description_

        Returns:
            _type_: _description_
        """
        total = len(files)
        successfull = 0
        for media in files:
            file_id = f"CAT_{str(uuid.uuid4())}"
            raw = await media.read()
            match media.content_type:
                case "video/mp4":
                    ext = "mp4"

                case "video/mpeg":
                    ext = "mpeg"

                case "video/webm":
                    ext = "webm"

                case "video/x-msvideo":
                    ext = "avi"

                case "video/ogg":
                    ext = "ogg"

                case "video/quicktime":
                    ext = "mov"

                case _:
                    continue

            hash = hashlib.sha256(raw).hexdigest()
            cursor = await app.database.cursor()
            res = await cursor.execute(
                f"SELECT FileHash FROM Media WHERE FileHash='{hash}'"
            )
            if len(await res.fetchall()) > 0:
                continue

            with open(
                pathlib.Path(f"web/content/{file_id}.{ext}"), "wb"
            ) as _file:
                _file.write(raw)

            ip = request.headers.get("cf-connecting-ip")
            origin = request.headers.get("cf-ipcountry")
            query = (
                Query.into(Table("Media"))
                .columns(
                    "FileID",
                    "FileHash",
                    "Extension",
                    "OriginalFileName",
                    "Size",
                    "ContentType",
                    "UploadDate",
                    "IP",
                    "Origin",
                )
                .insert(
                    file_id,
                    hash,
                    ext,
                    media.filename,
                    len(raw),
                    media.content_type,
                    int(datetime.datetime.now().timestamp()),
                    ip,
                    origin,
                )
            )

            await cursor.execute(str(query))
            await app.database.commit()
            await cursor.close()
            successfull += 1

        return JSONResponse(
            content={"upload_type": "file", "successfull": successfull, "total": total},
            status_code=200,
        )

    @base_router.get("/api/get_cat")
    async def fetch_cat(self, request: Request):
        """_summary_

        Args:
            request (Request): _description_

        Returns:
            _type_: _description_
        """
        file_id, ext = await get_random_video()  #
        return JSONResponse(content={"file_id": file_id, "ext": ext}, status_code=200)


app.include_router(base_router)
app.include_router(front_end)

if __name__ == "__main__":
    event = get_event_loop_policy().get_event_loop()
    server = Server(
        config=Config(
            app=app,
            host="0.0.0.0",
            port=2095,
        )
    )
    event.create_task(server.serve())
    event.run_forever()
