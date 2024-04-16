import pathlib
import uuid
import datetime
from typing import List
import hashlib
from aiohttp import ClientSession
from pypika import Table, Query
from fastapi import Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from ..libs import get_url, get_random_video

api_router = InferringRouter()


@cbv(api_router)
class API:
    @api_router.get("/api/upload/external")
    async def upload_external_site(self, request: Request, url: str):
        """_summary_

        Args:
            request (Request): _description_
            url (str): _description_

        Returns:
            _type_: _description_
        """

        headers, url = await get_url(url)
        async with ClientSession(headers=headers) as session:
            if url:
                async with session.get(
                    url,
                ) as req:
                    file = await req.read()
                    if req.content_type not in [
                        "video/mp4",
                        "video/mpeg",
                        "video/webm",
                        "video/x-msvideo",
                        "video/ogg",
                        "video/quicktime",
                    ]:
                        return JSONResponse(
                            content={
                                "upload_type": "external",
                                "msg": "Something went wrong...",
                            },
                            status_code=403,
                        )
                    file_id = f"CAT_{str(uuid.uuid4())}"
                    hash = hashlib.sha256(file).hexdigest()
                    cursor = await request.app.database.cursor()
                    res = await cursor.execute(
                        f"SELECT COUNT(*) FROM Media WHERE FileHash='{hash}'"
                    )
                    res = await res.fetchone()
                    if res[0]:
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
                    await request.app.database.commit()
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

    @api_router.post("/api/upload")
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
            cursor = await request.app.database.cursor()
            res = await cursor.execute(
                f"SELECT COUNT(*) FROM Media WHERE FileHash='{hash}'"
            )
            res = await res.fetchone()
            if res[0]:
                continue

            with open(pathlib.Path(f"web/content/{file_id}.{ext}"), "wb") as _file:
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
            await request.app.database.commit()
            await cursor.close()
            successfull += 1

        return JSONResponse(
            content={"upload_type": "file", "successfull": successfull, "total": total},
            status_code=200,
        )

    @api_router.get("/api/get_cat")
    async def fetch_cat(self, request: Request):
        """_summary_

        Args:
            request (Request): _description_

        Returns:
            _type_: _description_
        """
        file_id, ext = await get_random_video(request.app.database)
        return JSONResponse(content={"file_id": file_id, "ext": ext}, status_code=200)

    @api_router.get("/api/get_count")
    async def fetch_count(self, request: Request):
        cursor = await request.app.database.cursor()
        res = await cursor.execute(f"SELECT COUNT(*) FROM Media")
        res = await res.fetchone()
        return JSONResponse(content={"count": res[0]}, status_code=200)
