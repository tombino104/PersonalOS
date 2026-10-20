from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ActivityName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Weight = Annotated[int, Field(ge=1, le=3)]


class ActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area: str
    name: ActivityName
    weight: Weight


class ActivityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area: str | None = None
    name: ActivityName | None = None
    weight: Weight | None = None
    archived: bool | None = None


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=1024)]


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: Annotated[str, StringConstraints(min_length=1, max_length=1024)]
    new_password: Annotated[str, StringConstraints(max_length=2048)]


class ReportOpen(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: date


class DoneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    done: bool


class ReflectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: Annotated[str, StringConstraints(max_length=5000)] | None


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timezone: str | None = None
    day_cutoff: Annotated[str, StringConstraints(pattern=r"^\d{2}:\d{2}$")] | None = None
