from .cache import DataCache
from .config import settings
from .log import logger
from .model import NocoCourses, NocoPersons, NocoTimetable

import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from nocodb.exceptions import NocoDBAPIError


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")


cache = DataCache()


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(cache.run())


@app.get("/")
async def root(request: Request):
    test = NocoTimetable.from_nocodb()
    print(test)
    data = {
        "title": settings.title,
        "description": settings.description,
        "request": request,
    }
    return templates.TemplateResponse("index.html.jinja2", data)


@app.get("/api/course")
async def get_courses():
    try:
        # data = NocoCourses.from_nocodb()
        data = {}
    except NocoDBAPIError as e:
        message = f"NocoDBAPIError. Message: {e}. Response Text: {e.response_text}"
        logger.error(message)
        raise HTTPException(status_code=500, detail=message)
    # return data.model_dump()
    return data



@app.get("/api/person")
async def get_persons():
    try:
        data = {}
    except NocoDBAPIError as e:
        message = f"NocoDBAPIError. Message: {e}. Response Text: {e.response_text}"
        logger.error(message)
        raise HTTPException(status_code=500, detail=message)
    return data