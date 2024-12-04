from pydantic import BaseModel


class Result(BaseModel):
    alfas: list[float]
    llh: list[float]
    mean: list[list[float]]
    cov: list[list[float]]
    risk_tolerance: float
