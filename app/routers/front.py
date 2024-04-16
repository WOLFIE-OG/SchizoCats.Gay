from fastapi import Request
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from ..libs import get_random_video

front_router = InferringRouter()


@cbv(front_router)
class Front:
    @front_router.get("/")
    async def home(self, request: Request):
        """_summary_

        Args:
            request (Request): _description_

        Returns:
            _type_: _description_
        """
        file_id, ext = await get_random_video(request.app.database)
        return request.app.templates.TemplateResponse(
            "home.jinja2",
            {
                "request": request,
                "random_file": f"{file_id}.{ext}",
            },
        )
