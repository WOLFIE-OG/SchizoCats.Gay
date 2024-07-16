import asyncio
import sys
import re
import json
import logging
import aiohttp
from aiosqlite import Connection
from colorama import Fore, init
from pypika import Table, Query
from fastapi import FastAPI


@staticmethod
async def process(command: str) -> tuple[int | None, bytes, bytes]:
    """_summary_

    Args:
        command (str): _description_

    Returns:
        tuple[int | None, bytes, bytes]: _description_
    """
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout, stderr


@staticmethod
async def check_content_length(url: str):
    async with aiohttp.ClientSession(
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
        }
    ) as session:
        async with session.head(url) as response:
            content_length = int(response.headers.get("Content-Length"))
            if content_length > (50 * 1024 * 1024):
                return False
            else:
                return True


@staticmethod
async def get_url(url: str) -> tuple[bool, bool] | tuple[bool, str | None]:
    """_summary_

    Args:
        url (str): _description_

    Returns:
        _type_: _description_
    """
    if not re.match(
        re.compile(
            r"^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$"
        ),
        url,
    ):
        return False, False

    data = await process(f'yt-dlp "{url}" --dump-json')
    if data[1]:
        data = json.loads(bytes(data[1]).decode("utf-8"))
        headers = data.get("http_headers")
        match data.get("webpage_url_domain"):
            case "tiktok.com":
                source = next(
                    (
                        _format
                        for _format in data.get("formats")
                        if _format.get("format_id") == "download"
                    ),
                    next(
                        (
                            _format
                            for _format in data.get("formats")
                            if _format.get("format_id") == data.get("format_id")
                        ),
                        None,
                    ),
                )
                cookies = []
                for i in source["cookies"].split(";"):
                    c = i.split("=", 1)
                    if c[0].strip() in ["ttwid", "tt_csrf_token", "tt_chain_token"]:
                        key = c[0]
                        value = c[1].replace('"', "")
                        cookies.append(f"{key}={value};")
                headers["Cookie"] = "".join(cookies)
                media_url = [0, str(source.get("url")).encode("utf-8")]

            case "youtube.com" | "youtu.be" | "twitter.com" | "x.com":
                media_url = await process(
                    f'yt-dlp "{url}" --get-url -f b --cookies cookies.txt'
                )

            case _:
                media_url = await process(
                    f'yt-dlp "{url}" --get-url -f b --cookies cookies.txt'
                )
    else:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
        }
        media_url = [0, url.encode("utf-8"), 0]
    return headers, media_url[1].decode("utf-8")


@staticmethod
async def update_view_count(db: Connection, c_id: str) -> int:
    """_summary_

    Args:
        db (Connection): _description_
        c_id (str): _description_

    Returns:
        int: _description_
    """
    cursor = await db.cursor()
    table = Table("Content")
    query = (
        Query.update(table)
        .set(table.ViewCount, table.ViewCount + 1)
        .where(table.FileID == c_id)
    )
    await cursor.execute(str(query))
    await db.commit()

    select_query = (
        Query.from_(table).select(table.ViewCount).where(table.FileID == c_id)
    )
    await cursor.execute(str(select_query))
    result = await cursor.fetchone()
    await cursor.close()

    if result:
        return result[0]
    else:
        return 0


@staticmethod
async def get_random_video(db: Connection) -> tuple[bool, bool, bool] | tuple:
    """_summary_

    Args:
        db (Connection): _description_

    Returns:
        _type_: _description_
    """
    cursor = await db.cursor()
    get_record = await cursor.execute(
        "SELECT FileID, Extension, ViewCount FROM Content ORDER BY RANDOM() LIMIT 1;"
    )
    record = await get_record.fetchone()
    await cursor.close()
    if not record:
        return False, False, False
    return record[0], record[1], record[2]


@staticmethod
async def get_video_by_id(db: Connection, c_id: str) -> tuple[bool, bool, bool] | tuple:
    """_summary_

    Args:
        db (Connection): _description_

    Returns:
        _type_: _description_
    """
    cursor = await db.cursor()
    table = Table("Content")
    select_query = (
        Query.from_(table)
        .select(table.FileID, table.Extension, table.ViewCount)
        .where(table.FileID == c_id)
    )
    get_record = await cursor.execute(str(select_query))
    record = await get_record.fetchone()
    await cursor.close()
    if not record:
        return False, False, False
    return record[0], record[1], record[2]


@staticmethod
def setup_logging(app_instance: FastAPI) -> None:
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
        if log.handlers:
            log.handlers.clear()
        log.propagate = False
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(formatting))
        log.addHandler(handler)
        setattr(app_instance, f"logger.{logger}", log)


@staticmethod
def signal_handler(sigint: int, *args, **kwargs):
    """_summary_

    Args:
        signalNumber (int): _description_
    """
    print(f"Received: {sigint}")
    sys.exit()
