from .config import settings
from .log import logger
from .model import ClientModel, NocoTimetable

import asyncio
from typing import Optional


class DataCache:
    """Caches the data of NocoDB."""
    def __init__(self):
        self.__sleep: int = settings.cache_persistance_duration
        self.__lock: asyncio.Lock = asyncio.Lock()
        self.__data: Optional[ClientModel] = None
    
    async def run(self):
        while True:
            logger.debug("pull new version of data")
            noco_data = NocoTimetable.from_nocodb()
            temp = ClientModel.from_noco_model(noco_data)
            async with self.__lock:
                logger.debug("update data with new version")
                self.__data = temp
            await asyncio.sleep(self.__sleep)

    async def get(self) -> ClientModel:
        while not self.__data:
            logger.warn("data is not yet pulled will try again in 5s")
            await asyncio.sleep(5)
        async with self.__lock:
            rsl = self.__data
        return rsl