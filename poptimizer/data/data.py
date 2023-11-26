from pydantic import BaseModel, ConfigDict


class Row(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
