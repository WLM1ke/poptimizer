from collections.abc import Iterable
from typing import cast

from lxml import etree, html

type Element = etree._Element  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]


def xpath_elements(page: str, path: str) -> list[Element]:
    tree = html.document_fromstring(page)  # pyright: ignore[reportUnknownMemberType]
    return cast("list[Element]", tree.xpath(path))


def element_text(element: Element) -> str:
    return "".join(cast("Iterable[str]", element.itertext()))


def element_html(element: Element) -> str:
    return etree.tostring(element, encoding="unicode", method="html")
