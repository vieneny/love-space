from datetime import date as Date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


Visibility = Literal["private", "shared"]
Scope = Literal["personal", "shared"]
Kind = Literal["travel", "milestone", "daily"]


class DevLogin(Input):
    identity: str = Field(min_length=1, max_length=100)
    nickname: str | None = Field(default=None, min_length=1, max_length=80)


class WechatLogin(Input):
    code: str = Field(min_length=1, max_length=512)


class AdminLogin(Input):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    id: str
    nickname: str
    space_id: str | None


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class SpaceWrite(Input):
    title: str = Field(min_length=1, max_length=120)
    start_date: Date | None = None


class SpacePatch(Input):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    start_date: Date | None = None


class SpaceOut(BaseModel):
    id: str
    title: str
    start_date: Date | None
    members: list[UserOut]


class Join(Input):
    code: str = Field(min_length=1, max_length=100)


class Place(Input):
    name: str = Field(default="", max_length=200)
    country_code: str = Field(default="", max_length=3)
    country_name: str = Field(default="", max_length=100)
    city: str = Field(default="", max_length=160)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    coordinate_system: Literal["wgs84", "gcj02"] = "wgs84"
    timezone: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def coordinates_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together")
        self.country_code = self.country_code.upper()
        if self.timezone:
            try:
                ZoneInfo(self.timezone)
            except ZoneInfoNotFoundError:
                raise ValueError("Unknown timezone")
        return self


class MemoryWrite(Input):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(default="", max_length=20000)
    occurred_on: Date
    kind: Kind = "daily"
    visibility: Visibility = "private"
    trip_id: str | None = None
    place: Place | None = None
    photo_ids: list[str] = Field(default_factory=list, max_length=30)


class MemoryPatch(Input):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    content: str | None = Field(default=None, max_length=20000)
    occurred_on: Date | None = None
    kind: Kind | None = None
    visibility: Visibility | None = None
    trip_id: str | None = None
    place: Place | None = None
    photo_ids: list[str] | None = Field(default=None, max_length=30)


class PhotoOut(BaseModel):
    id: str
    url: str


class MemoryOut(BaseModel):
    id: str
    title: str
    content: str
    occurred_on: Date
    kind: Kind
    visibility: Visibility
    trip_id: str | None
    place: Place | None
    photos: list[PhotoOut]
    author_id: str
    author_name: str
    created_at: datetime


class MemoryList(BaseModel):
    items: list[MemoryOut]
    total: int


class TripWrite(Input):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=10000)
    start_date: Date | None = None
    end_date: Date | None = None
    visibility: Visibility = "private"

    @model_validator(mode="after")
    def date_order(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must not precede start date")
        return self


class TripPatch(Input):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=10000)
    start_date: Date | None = None
    end_date: Date | None = None
    visibility: Visibility | None = None


class TripOut(TripWrite):
    id: str
    author_id: str
    memory_count: int


class TripList(BaseModel):
    items: list[TripOut]
    total: int


class AnniversaryWrite(Input):
    title: str = Field(min_length=1, max_length=160)
    date: Date
    repeat_yearly: bool = True


class AnniversaryPatch(Input):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    date: Date | None = None
    repeat_yearly: bool | None = None


class WishWrite(Input):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=10000)
    completed: bool = False


class WishPatch(Input):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=10000)
    completed: bool | None = None


class AnswerWrite(Input):
    question_id: str
    answer: str = Field(min_length=1, max_length=5000)


class MoodWrite(Input):
    mood: str = Field(min_length=1, max_length=32)
    note: str = Field(default="", max_length=3000)
    visibility: Visibility = "private"


class HabitWrite(Input):
    title: str = Field(min_length=1, max_length=160)


class CheckinWrite(Input):
    day: Date | None = None


class FeedbackWrite(Input):
    content: str = Field(min_length=1, max_length=5000)


class QuestionWrite(Input):
    text: str = Field(min_length=1, max_length=1000)
    active: bool = True


class QuestionPatch(Input):
    text: str | None = Field(default=None, min_length=1, max_length=1000)
    active: bool | None = None
