from inspect import getcallargs
from pydantic_core.core_schema import timedelta_schema
from .config import settings
from typing import Any, Optional, Union

from datetime import date, datetime

from nocodb.nocodb import APIToken, NocoDBProject, WhereFilter
from nocodb.infra.requests_client import NocoDBRequestsClient
from pydantic import BaseModel, ConfigDict, Field, FieldValidationInfo, model_validator, RootModel


def get_nocodb_client() -> NocoDBRequestsClient:
    return NocoDBRequestsClient(
        APIToken(settings.nocodb_api_key),
        settings.nocodb_url,
    )


def get_nocodb_project() -> NocoDBProject:
    return NocoDBProject(
        settings.nocodb_org_name,
        settings.project_name,
    )

def get_nocodb_data(table_name: str, filter_obj: Optional[WhereFilter] = None) -> Any:
    client = get_nocodb_client()
    return client.table_row_list(
        get_nocodb_project(),
        table_name,
        filter_obj=filter_obj,
    )

class NocoLocation(BaseModel):
    noco_id: int = Field(alias="Id")
    created_at: datetime = Field(alias="CreatedAt")
    updated_at: datetime = Field(alias="UpdatedAt")
    name: str = Field(alias=settings.column_location_name)


class NocoLocations(RootModel[list[NocoLocation]]):
    root: list[NocoLocation] 


class NocoEntry(BaseModel):
    noco_id: int = Field(alias="Id")
    created_at: datetime = Field(alias="CreatedAt")
    updated_at: datetime = Field(alias="UpdatedAt")
    artist_name: Optional[str] = Field(alias=settings.column_entries_artist_name)
    artist_cv: Optional[str] = Field(alias=settings.column_entries_artist_cv)
    title: Optional[str] = Field(alias=settings.column_entries_title)
    genre: Optional[str] = Field(alias=settings.column_entries_genre)
    description: Optional[str] = Field(alias=settings.column_entries_description)
    location: str = ""
    # location: Optional[NocoLocations] = None

    # @model_validator(mode="after")
    # def load_linked_location(self):
    #     client = get_nocodb_client()
    #     raw = client.table_row_nested_relations_list(
    #         get_nocodb_project(),
    #         settings.table_location,
    #         "mm",
    #         self.noco_id,
    #         settings.column_entries_location
    #     )
    #     self.linked_locations = NocoLocations.model_validate(raw["list"])
    #     return self


class NocoTimeSlot(BaseModel):
    noco_id: int = Field(alias="Id")
    created_at: datetime = Field(alias="CreatedAt")
    updated_at: datetime = Field(alias="UpdatedAt")
    when: datetime = Field(alias=settings.column_timetable_when)
    linked_entry: Optional[NocoEntry] = None

    @model_validator(mode="after")
    def load_linked_entry(self):
        client = get_nocodb_client()
        raw = client.table_row_nested_relations_list(
            get_nocodb_project(),
            settings.table_timetable,
            "hm",
            self.noco_id,
            "entry",
        )
        print(raw)
        self.linked_entry = NocoEntry.model_validate(raw["list"][0])
        return self


class NocoTimetable(RootModel[list[NocoTimeSlot]]):
    root: list[NocoTimeSlot]

    @classmethod
    def from_nocodb(cls):
        raw = get_nocodb_data(settings.table_timetable)
        print(raw)
        return cls.model_validate(raw["list"], strict=False)


class NocoPerson(BaseModel):
    noco_id: int = Field(alias="Id")
    created_at: datetime = Field(alias="CreatedAt")
    updated_at: datetime = Field(alias="UpdatedAt")
    name: str = Field(alias="Name")
    age: int = Field(alias="Age")


class NocoPersons(RootModel[list[NocoPerson]]):
    root: list[NocoPerson]

    @classmethod
    def from_nocodb(cls):
        raw = get_nocodb_data("Person")
        return cls.model_validate(raw["list"])


class NocoCourse(BaseModel):
    noco_id: int = Field(alias="Id")
    created_at: datetime = Field(alias="CreatedAt")
    updated_at: datetime = Field(alias="UpdatedAt")
    name: str = Field(alias="Name")
    students: Optional[NocoPersons] = None

    @model_validator(mode="after")
    def load_linked_students(self):
        client = get_nocodb_client()
        raw = client.table_row_nested_relations_list(
            get_nocodb_project(),
            "Course",
            "mm",
            self.noco_id,
            "Students"
        )
        self.students = NocoPersons.model_validate(raw["list"])
        return self


class NocoCourses(RootModel[list[NocoCourse]]):
    root: list[NocoCourse]

    @classmethod
    def from_nocodb(cls):
        raw = get_nocodb_data("Course")
        return cls.model_validate(raw["list"], strict=False)


class ClientEntry(BaseModel):
    item_id: int
    when: datetime
    title: Optional[str]
    lead: Optional[str]
    description: Optional[str]
    genres: list[str] = []
    artist_name: Optional[str]
    artist_cv: Optional[str]
    location: Optional[str]

    @classmethod
    def from_noco_model(cls, slot: NocoTimeSlot):
        if not slot.linked_entry:
            raise ValueError(f"TimeSlot with id {slot.noco_id} has no linked entry")
        lead = "TODO"
        genres = ["TODO"]
        return cls(
            item_id = slot.noco_id,
            when = slot.when,
            title = slot.linked_entry.title,
            lead = lead,
            description = slot.linked_entry.description,
            genres = genres,
            artist_name = slot.linked_entry.artist_name,
            artist_cv = slot.linked_entry.artist_cv,
            location = slot.linked_entry.location,
        )



class ClientSchedule(RootModel[list[ClientEntry]]):
    root: list[ClientEntry]

    @classmethod
    def from_noco_model(cls, timetable: NocoTimetable):
        rsl: list[ClientEntry] = []
        for slot in timetable.root:
            rsl.append(ClientEntry.from_noco_model(slot))
        return cls(root=rsl)


class ClientModel(BaseModel):
    description: str
    dates: list[date]
    schedule: ClientSchedule

    @classmethod
    def from_noco_model(cls, timetable: NocoTimetable):
        schedule = ClientSchedule.from_noco_model(timetable)
        dates = []
        for entry in schedule.root:
            if entry.when.date() not in dates:
                dates.append(entry.when.date())
        return cls(
            description = settings.description,
            dates = sorted(dates),
            schedule = schedule
        )