from poptimizer.domain.settings import Settings, Theme
from poptimizer.use_cases import handler


class GetTheme(handler.DTO): ...


class UpdateTheme(handler.DTO):
    theme: Theme


class ThemeResponse(handler.DTO):
    theme: Theme


class Handler:
    async def get_theme(self, ctx: handler.Ctx, msg: GetTheme) -> ThemeResponse:  # noqa: ARG002
        settings = await ctx.get(Settings)

        return ThemeResponse(theme=settings.theme)

    async def update_theme(self, ctx: handler.Ctx, msg: UpdateTheme) -> ThemeResponse:
        settings = await ctx.get_for_update(Settings)

        settings.update_theme(msg.theme)

        return ThemeResponse(theme=settings.theme)
