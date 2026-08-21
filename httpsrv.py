import logging

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

logger = logging.getLogger("uvicorn.access")
logger.disabled = True


async def jsonprint(request: Request) -> Response:
    bytes = await request.body()
    print(bytes.decode(), flush=True)
    return JSONResponse({"message": "Thank you", "bytes": len(bytes)})


app = Starlette(routes=[Route("/", jsonprint, methods=["POST"])])


if __name__ == "__main__":
    config = uvicorn.Config(app, port=8001, access_log=False)
    server = uvicorn.Server(config)
    server.run()
