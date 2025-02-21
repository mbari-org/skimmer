from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class Error(Model):
    """
    Error response.
    """

    message: str


class HealthStatus(Model):
    """
    Service health status.
    """

    jdk_version: str
    available_processors: int
    free_memory: int
    max_memory: int
    total_memory: int
    application: str
    version: str
    description: str
