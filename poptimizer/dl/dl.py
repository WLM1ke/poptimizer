from enum import Enum, auto, unique

import torch

from poptimizer.domain import consts


class DLError(consts.POError): ...


@unique
class FeatTypes(Enum):
    LABEL1P = auto()
    RETURNS = auto()
    NUMERICAL = auto()


Batch = dict[FeatTypes, torch.Tensor]
