from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from pydantic import BaseModel

from poptimizer.domain import domain


class Edit(BaseModel):
    msg_id: int = 0
    acc_value: float = 0
    account: domain.AccName = domain.AccName("")
    ticker: domain.Ticker = domain.Ticker("")
    quantity: int = 0
    value: float = 0

    async def update_state(self, fsm_ctx: FSMContext, state: State) -> None:
        await fsm_ctx.set_data(self.model_dump())
        await fsm_ctx.set_state(state)


async def edit(state: FSMContext) -> Edit:
    data = await state.get_data()

    return Edit.model_validate(data)
