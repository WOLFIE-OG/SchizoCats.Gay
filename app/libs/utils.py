import asyncio
import sys
import re
import json
import logging
from colorama import Fore, init
from fastapi import FastAPI


@staticmethod
async def process(command: str):
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout, stderr


@staticmethod
async def get_url(url: str):
    if not re.match(
        re.compile(
            r"^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$"
        ),
        url,
    ):
        return False, False

    data = await process(f"yt-dlp {url} --dump-json --cookies cookies.txt")

    if data[1]:
        data = json.loads(bytes(data[1]).decode("utf-8"))
    match data.get("webpage_url_domain"):
        case "tiktok.com":
            media_url = next(
                (
                    _format.get("url")
                    for _format in data.get("formats")
                    if _format.get("format_note") == "Direct video (API)"
                ),
                None,
            )

        case "youtube.com" | "youtu.be" | "twitter.com" | "x.com":
            media_url = await process(f"yt-dlp {url} --get-url -f b --cookies cookies.txt")
        
        case _:
            media_url = await process(
                f"yt-dlp {url} --get-url -f b --cookies cookies.txt"
            )

    headers = data.get("http_headers")
    return headers, bytes(media_url[1]).decode("utf-8") if media_url[1] else False


@staticmethod
async def get_random_video(db):
    cursor = await db.cursor()
    get_records = await cursor.execute("SELECT * FROM Media ORDER BY RANDOM() LIMIT 1;")
    records = await get_records.fetchall()
    await cursor.close()
    if not records:
        return False, False
    return records[0][1], records[0][3]


@staticmethod
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
