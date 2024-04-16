from app.server import app
from asyncio import get_event_loop_policy
from uvicorn import Config, Server

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
