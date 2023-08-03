from .config import settings
from .log import logger
from .model import ClientModel, NocoTimetable

from threading import Lock, Thread
import time
from typing import Optional


class CacheNotInitializedError(Exception):
    pass


class DataCacheThread(Thread):
    def __init__(self):
        super().__init__()
        self.__sleep: int = settings.cache_persistance_duration
        self.__data: Optional[ClientModel] = None
        self.__do_quit: bool = False
    
    def run(self):
        while True:
            logger.info("pull new version of data")
            noco_data = NocoTimetable.from_nocodb()
            temp = ClientModel.from_noco_model(noco_data)
            logger.info("update data with new version")
            self.__data = temp
            slept: int = 0
            while slept < self.__sleep:
                time.sleep(1)
                slept += 1
                if self.__do_quit:
                    break
            if self.__do_quit:
                break

    def get(self) -> ClientModel:
        while not self.__data:
            logger.warn("data is not yet pulled will try again in 1s")
            time.sleep(1)
        rsl = self.__data
        return rsl

    def quit(self):
        self.__do_quit = True