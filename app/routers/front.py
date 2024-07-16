from fastapi import Request
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from ..libs import get_random_video, get_video_by_id, update_view_count

front_router = InferringRouter()


@cbv(front_router)
class Front:
    """_summary_

    Returns:
        _type_: _description_
    """

    @front_router.get("/")
    @front_router.get("/{c_id}")
    async def home(self, request: Request, c_id: str = None):
        """_summary_

        Args:
            request (Request): _description_

        Returns:
            _type_: _description_
        """
        if not c_id:
            file_id, ext, views = await get_random_video(request.app.database)
        else:
            file_id, ext, views = await get_video_by_id(request.app.database, c_id)
            if not file_id:
                file_id, ext, views = await get_random_video(request.app.database)
        views = await update_view_count(request.app.database, file_id)
        return request.app.templates.TemplateResponse(
            "home.jinja2",
            {
                "request": request,
                "base_url": "https://schizocats.wolfieog.xyz",
                "random_file": f"{file_id}.{ext}",
                "file_id": file_id,
                "view_count": views,
            },
        )
