"""Currency helpers.

Amounts are stored internally as integer paise (minor units). These helpers
convert to/from rupees and produce the Indian-format display strings used in
the statement, e.g. 829100 paise -> "8,291" -> "₹8,291/-".
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

RUPEE = "₹"


def rupees_to_paise(value: str | int | float | Decimal) -> int:
    """Convert a rupee value to integer paise, rounding half-up to the paisa."""
    dec = Decimal(str(value))
    paise = (dec * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(paise)


def paise_to_rupees(paise: int) -> Decimal:
    return (Decimal(paise) / 100).quantize(Decimal("0.01"))


def _group_indian(whole: str) -> str:
    """Group digits in the Indian numbering system (e.g. 1,23,456)."""
    if len(whole) <= 3:
        return whole
    last3 = whole[-3:]
    rest = whole[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ",".join(parts) + "," + last3


def format_amount(paise: int, with_suffix: bool = False, with_symbol: bool = True) -> str:
    """Format paise as an Indian-currency string.

    - whole rupees render without decimals (e.g. ₹8,291), matching the sample
      statement; fractional paise render with two decimals.
    - with_suffix adds the trailing "/-" used for totals in the statement.
    """
    negative = paise < 0
    rupees = paise_to_rupees(abs(paise))
    whole = int(rupees)
    frac = rupees - whole

    whole_str = _group_indian(str(whole))
    if frac == 0:
        body = whole_str
    else:
        body = f"{whole_str}.{str(frac * 100).split('.')[0].zfill(2)[:2]}"

    out = body
    if with_symbol:
        out = f"{RUPEE}{out}"
    if negative:
        out = f"-{out}"
    if with_suffix:
        out = f"{out}/-"
    return out
