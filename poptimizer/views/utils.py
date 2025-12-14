def format_float(number: float, decimals: int | None = None) -> str:
    match decimals:
        case None if number % 1:
            rez = f"{number:_}"
        case None:
            rez = f"{int(number):_}"
        case _:
            rez = f"{number:_.{decimals}f}"

    return rez.replace("_", " ").replace(".", ",")


def format_percent(number: float) -> str:
    return f"{format_float(number * 100, 1)} %"
