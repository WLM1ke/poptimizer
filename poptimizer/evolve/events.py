from poptimizer.core import fsm


class BaseModelNotEvaluated(fsm.Event): ...


class NewModelCreated(fsm.Event): ...


class ModelDeleted(fsm.Event): ...
