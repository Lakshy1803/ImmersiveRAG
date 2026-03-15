from __future__ import annotations

import warnings

from pydantic.warnings import UnsupportedFieldAttributeWarning


def silence_llama_index_pydantic_warning() -> None:
    warnings.filterwarnings(
        "ignore",
        message=r"The 'validate_default' attribute with value True was provided to the `Field\(\)` function.*",
        category=UnsupportedFieldAttributeWarning,
    )
