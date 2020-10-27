"""Преобразования типов во время загрузки данных  из MongoDB."""
from typing import Any, Callable, Dict, Final, NamedTuple, Optional, Tuple

import pandas as pd

from poptimizer.data_di.ports import tables


class Desc(NamedTuple):
    """Описание кодирования и декодирования из документа MongoDB."""

    field_name: str
    doc_name: str
    factory_name: str
    encoder: Optional[Callable[[tables.TableAttrValues], Any]] = None  # type: ignore
    decoder: Optional[Callable[[Any], tables.TableAttrValues]] = None  # type: ignore


class Mapper:
    """Преобразует данные."""

    def __init__(self, desc_list: Tuple[Desc, ...]) -> None:  # type: ignore
        """Сохраняет описание кодировки."""
        self._to_doc = {desc.field_name: desc for desc in desc_list}
        self._from_doc = {desc.doc_name: desc for desc in desc_list}

    def encode(self, attr_dict: Dict[str, tables.TableAttrValues]) -> Dict[str, Any]:  # type: ignore
        """Кодирует данные в совместимый с MongoDB формат."""
        desc_dict = self._to_doc
        mongo_dict = {}
        for name, attr_value in attr_dict.items():
            desc = desc_dict[name]
            if desc.encoder:
                attr_value = desc.encoder(attr_value)
            mongo_dict[desc.doc_name] = attr_value
        return mongo_dict

    def decode(self, mongo_dict: Dict[str, Any]) -> Dict[str, tables.TableAttrValues]:  # type: ignore
        """Декодирует данные из формата MongoDB формат атрибутов модели."""
        desc_dict = self._from_doc
        attr_dict = {}
        for name, attr_value in mongo_dict.items():
            desc = desc_dict[name]
            if desc.decoder:
                attr_value = desc.decoder(attr_value)
            attr_dict[desc.factory_name] = attr_value
        return attr_dict


# Описание мэппинга данных в MongoDB
DATA_MAPPING: Final = (
    Desc(
        field_name="_df",
        doc_name="data",
        factory_name="df",
        encoder=lambda df: df.to_dict("split"),  # type: ignore
        decoder=lambda doc_df: pd.DataFrame(**doc_df),
    ),
    Desc(
        field_name="_timestamp",
        doc_name="timestamp",
        factory_name="timestamp",
    ),
)
