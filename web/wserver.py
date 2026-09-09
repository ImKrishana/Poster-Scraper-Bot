# ruff: noqa: E402
from uvloop import install

install()

from logging import INFO, WARNING, FileHandler, StreamHandler, basicConfig, getLogger

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

getLogger("httpx").setLevel(WARNING)
getLogger("aiohttp").setLevel(WARNING)

app = FastAPI()

templates = Jinja2Templates(directory="web/templates/")

basicConfig(
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%d-%b-%y %I:%M:%S %p",
    handlers=[FileHandler("log.txt"), StreamHandler()],
    level=INFO,
)


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse(request, "landing.html")

@app.exception_handler(Exception)
async def page_not_found(_, exc):
    return HTMLResponse(
        f"<h1>404: Task not found! Mostly wrong input. <br><br>Error: {exc}</h1>",
        status_code=404,
    )
