import logging

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("uvicorn.access")
logger.disabled = True


app = Starlette()


@app.route("/", methods=["POST"])
async def jsonprint(request: Request) -> Response:
    bytes = await request.body()
    print(bytes.decode(), flush=True)
    return JSONResponse({"message": "Thank you", "bytes": len(bytes)})


if __name__ == "__main__":
    config = uvicorn.Config(app, port=8001, access_log=False)
    server = uvicorn.Server(config)
    server.run()
