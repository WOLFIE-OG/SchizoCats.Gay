import asyncio
import re
import json

class Utils:
    
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
        if not re.match(re.compile(r"^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$"), url):
            return False, False
        
        data = await Utils.process(f"yt-dlp {url} --dump-json --cookies cookies.txt")
        
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
            
            case "twitter.com" | "x.com":
                media_url = await Utils.process(f"yt-dlp {url} --get-url --cookies cookies.txt")
            
            case "youtube.com" | "youtu.be":
                media_url = await Utils.process(f"yt-dlp {url} --get-url -f b --cookies cookies.txt")
        
        headers = data.get("http_headers")
        
        return headers, bytes(media_url[1]).decode("utf-8") if media_url[1] else False

