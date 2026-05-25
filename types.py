#!/usr/bin/env python3
"""
  types.py
  ========

  Description:           Defines API request/response structure
  Author:                Michael De Pasquale
  Creation Date:         2025-02-13
  Modification Date:     2026-05-25

"""

from datetime import datetime, timedelta, timezone
import json
from typing import Optional, Union

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

# TODO: forbid 'extra' in config, prevents silently dropping incorrect keyword arguments
# see https://docs.pydantic.dev/latest/concepts/config/#configuration-with-dataclass-from-the-standard-library-or-typeddict


class StatusResponse(BaseModel):
    """Response returned by /status."""

    lastSchemaUpdate: datetime
    lastMarketUpdate: dict[str, datetime]

    # See backend matcher.types.MatchStats for format
    stats: Optional[dict[str, dict]] = None

    @field_serializer("lastSchemaUpdate")
    @classmethod
    def serialiseLastSchemaUpdate(cls, ts: datetime, _info) -> str:
        """Serialise last schema update timestamp."""
        return ts.isoformat()

    @field_validator("lastSchemaUpdate", mode="before")
    @classmethod
    def deserialiseLastSchemaUpdate(cls, ts: Union[str, datetime]) -> datetime:
        """Parse last schema update timestamp."""
        if isinstance(ts, str):
            return datetime.fromisoformat(ts)

        return ts

    @field_serializer("lastMarketUpdate")
    @classmethod
    def serialiseLastMarketUpdate(
        cls, lm: dict[str, datetime], _info
    ) -> dict[str, str]:
        """Serialise last market update timestamps."""
        return {k: v.isoformat() for k, v in lm.items()}

    @field_validator("lastMarketUpdate", mode="before")
    @classmethod
    def deserialiseLastMarketUpdate(
        cls, lm: dict[str, Union[str, datetime]]
    ) -> datetime:
        """Parse last market update timestamps."""
        for agency, timestamp in lm.items():
            if isinstance(timestamp, str):
                lm[agency] = datetime.fromisoformat(timestamp)

        return lm


class EvaluateRequest(BaseModel):
    """Request to perform evaluation."""

    sport: Union[str, None] = None
    competition: Union[str, None] = None

    # Subset of agencies to consider when evaluating
    considerAgencies: Union[list[str], None] = None

    # One or more agencies that must be included in every result
    includeAgencies: Union[list[str], None] = None

    resultCount: Union[int, None] = None

    # Must start before this number of days from now
    startInDays: Union[int, None] = None

    @model_validator(mode="after")
    def ensureValid(self) -> "EvaluateRequest":
        """Perform model-level validation."""
        # Keys must not be empty, must not start/end with space
        assert all(
            map(
                lambda s: s.strip() == s and s.strip() != "",
                filter(
                    lambda x: x,
                    [self.sport, self.competition]
                    + (self.considerAgencies or [])
                    + (self.includeAgencies or []),
                ),
            )
        )

        assert self.resultCount is None or self.resultCount > 0
        assert self.startInDays is None or self.startInDays > 0

        return self

    def getBeforeDate(self) -> Union[datetime, None]:
        """If startInDays is provided, convert it to a UTC datetime from the current time,
        otherwise return None."""
        if not self.startInDays:
            return None

        return datetime.now(tz=timezone.utc) + timedelta(days=self.startInDays)


# FIXME: These are duplicated from namedtuples in evaluator.Evaluator..
class EvaluatorPricedOutcome(BaseModel):
    """An outcome associated with a result."""

    agency: str
    outcome: str
    price: float


class EvaluatorResult(BaseModel):
    """An evaluator result for a given market."""

    sport: str
    competition: str
    start: datetime
    participant1: str
    participant2: str
    # FIXME: str for now. Probably better to move MarketType here?
    marketType: str
    outcomes: list[EvaluatorPricedOutcome] = Field(default_factory=list)
    returnFactor: float

    @field_serializer("start")
    @classmethod
    def serialiseStart(cls, start: datetime, _info) -> str:
        """Serialise start time."""
        return start.isoformat()

    @field_validator("start", mode="before")
    @classmethod
    def deserialiseStart(cls, start: Union[str, datetime]) -> datetime:
        """Parse start time."""
        if isinstance(start, str):
            return datetime.fromisoformat(start)

        return start


class EvaluateResponse(BaseModel):
    """Response returned by /evaluate."""

    results: list[EvaluatorResult]


class EvaluateKeysRequest(BaseModel):
    # If provided, response includes competitions for this sport key
    sport: Union[str, None] = None


class EvaluateKeysResponse(BaseModel):
    """Response returned by /evaluate/keys"""

    agencies: list[str]
    sports: list[str]
    competitions: Union[list[str], None] = None


# FIXME: duplicate of api.tasks.models.Task
class TaskInfo(BaseModel):
    """Basic info for a Task"""

    id: int
    uuid: str
    name: str
    args: list[str]
    kwargs: dict
    started: bool
    success: Union[bool, None]
    errorInfo: Union[str, None] = None

    addedTime: datetime
    startedTime: Union[datetime, None] = None
    finishedTime: Union[datetime, None] = None

    @classmethod
    def fromModel(cls, model: object) -> "TaskInfo":
        """Create from an api.tasks.models.Task instance"""
        # NOTE: Expects TaskInfo attributes to match Task
        kwargs = {k: getattr(model, k) for k in cls.model_fields.keys()}

        # Need to deserialise args/kwargs
        kwargs["args"] = json.loads(kwargs["args"])
        kwargs["kwargs"] = json.loads(kwargs["kwargs"])

        return cls(**kwargs)

    @field_serializer("addedTime")
    @field_serializer("startedTime")
    @field_serializer("finishedTime")
    @classmethod
    def serialiseDt(cls, dt: datetime, _info) -> str:
        """Serialise timestamp."""
        return dt.isoformat()


class TaskExtendedInfoResponse(TaskInfo):
    """Full details for a task"""

    # NOTE: These can be in the megabytes if logging level is set to DEBUG
    stdout: Union[str, None]
    stderr: Union[str, None]


class TaskRunResponse(TaskInfo):
    """Synonym for TaskInfo"""


class TaskListResponse(BaseModel):
    """Response for getting the list of tasks."""

    tasks: list[TaskInfo]


class ScraperListResponse(BaseModel):
    scrapers: list[str]
