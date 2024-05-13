from enum import StrEnum


class States(StrEnum):
    DATA_UPDATE = "Data update"
    OPTIMIZATION = "Optimization"
    EVOLUTION_STEP = "Evolution step"
