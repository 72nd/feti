from .config import settings
from typing import Any, Optional

from datetime import date, datetime

from nocodb.nocodb import APIToken, NocoDBProject, WhereFilter
from nocodb.infra.requests_client import NocoDBRequestsClient
from pydantic import BaseModel, Field, model_validator, RootModel


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

def get_nocodb_data(
    table_name: str,
    filter_obj: Optional[WhereFilter] = None,
    params: Optional[dict[str, Any]] = None,
) -> Any:
    client = get_nocodb_client()
    return client.table_row_list(
        get_nocodb_project(),
        table_name,
        filter_obj=filter_obj,
        params=params
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


class NocoTimeSlot(BaseModel):
    noco_id: int = Field(alias="Id")
    created_at: datetime = Field(alias="CreatedAt")
    updated_at: datetime = Field(alias="UpdatedAt")
    when: Optional[datetime] = Field(alias=settings.column_timetable_when)
    linked_entry: Optional[NocoEntry] = None
    linked_location: Optional[NocoLocation] = None

    @model_validator(mode="after")
    def load_linked_entry(self):
        client = get_nocodb_client()
        raw_entry = client.table_row_nested_relations_list(
            get_nocodb_project(),
            settings.table_timetable,
            "hm",
            self.noco_id,
            settings.column_timetable_entry,
        )
        self.linked_entry = NocoEntry.model_validate(raw_entry["list"][0])
        raw_location = client.table_row_nested_relations_list(
            get_nocodb_project(),
            settings.table_timetable,
            "mm",
            self.noco_id,
            settings.column_timetable_location,
        )
        self.linked_location = NocoLocation.model_validate(raw_location["list"][0])
        return self


class NocoTimetable(RootModel[list[NocoTimeSlot]]):
    root: list[NocoTimeSlot]

    @classmethod
    def from_nocodb(cls):
        raw = get_nocodb_data(
            settings.table_timetable,
            params={"limit": 1000},
        )
        return cls.model_validate(raw["list"], strict=False)


class ClientEntry(BaseModel):
    item_id: int
    when: Optional[datetime]
    title: Optional[str]
    lead: str
    description: Optional[str]
    genre: Optional[str]
    artist_name: Optional[str]
    artist_cv: Optional[str]
    location: Optional[str]

    @classmethod
    def from_noco_model(cls, slot: NocoTimeSlot):
        if not slot.linked_entry:
            raise ValueError(f"TimeSlot with id {slot.noco_id} has no linked entry")
        if not slot.linked_location:
            raise ValueError(f"TimeSlot with id {slot.noco_id} has no linked location")
        return cls(
            item_id = slot.noco_id,
            when = slot.when,
            title = slot.linked_entry.title,
            lead = cls.generate_lead(slot.linked_entry.description),
            description = slot.linked_entry.description,
            genre = slot.linked_entry.genre,
            artist_name = slot.linked_entry.artist_name,
            artist_cv = slot.linked_entry.artist_cv,
            location = slot.linked_location.name,
        )
    
    @staticmethod
    def generate_lead(description: Optional[str]) -> str:
        if not description:
            return "n.n."
        if len(description) <= settings.max_lead_length:
            return description
        parts = description.split(".")
        rsl = ""
        for part in parts:
            if len(rsl+part) > settings.max_lead_length:
                break
            if rsl == "":
                rsl = part
            else:
                rsl = f"{rsl}.{part}"
        return f"{rsl}..."




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
            if entry.when and entry.when.date() not in dates:
                dates.append(entry.when.date())
        return cls(
            description = settings.description,
            dates = sorted(dates),
            schedule = schedule
        )