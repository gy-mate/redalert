"""Download and parse the OVSZ blood-stock page.

The page at https://www.ovsz.hu/veradas renders one block per blood type that
looks like this::

    <div class="keszletszint-col">
        <div class="ab-p">
            <img name="ab-p" src=".../keszletszint-5.png"/>
            <b>AB+</b>
            <span id="ab-p-text">5 vagy több napra elegendő</span>
        </div>
    </div>

The ``name``/``id`` codes encode the blood type: a ``0/a/b/ab`` group prefix and
a ``p`` (pozitív, ``+``) or ``m`` (negatív, ``-``) suffix. The span text starts
with the number of days the current stock is expected to last.
"""

import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

DEFAULT_URL = "https://www.ovsz.hu/veradas"

# Pretend to be a normal browser; the site returns 403 for some bare clients.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Map the HTML group prefix to the human-readable blood group, and back.
_GROUP_TO_LABEL = {"0": "0", "a": "A", "b": "B", "ab": "AB"}
_SIGN_TO_LABEL = {"p": "+", "m": "-"}

_CODE_RE = re.compile(r"^(0|a|b|ab)-(p|m)$")
_FIRST_INT_RE = re.compile(r"\d+")


@dataclass(frozen=True)
class StockLevel:
    """Stock reading for a single blood type."""

    code: str  # e.g. "ab-p"
    blood_type: str  # e.g. "AB+"
    days: int  # number parsed from the span text, e.g. 5
    text: str  # raw Hungarian text, e.g. "5 vagy több napra elegendő"


def code_to_blood_type(code: str) -> str:
    """Turn an HTML code such as ``ab-p`` into a label such as ``AB+``."""
    match = _CODE_RE.match(code)
    if not match:
        raise ValueError(f"Unrecognised blood-type code: {code!r}")
    group, sign = match.groups()
    return _GROUP_TO_LABEL[group] + _SIGN_TO_LABEL[sign]


def blood_type_to_code(blood_type: str) -> str:
    """Turn a label such as ``AB+`` (or ``ab+``, ``O+``) into a code ``ab-p``.

    Accepts the letter ``O`` as an alias for the Hungarian ``0`` (zero).
    """
    normalised = blood_type.strip().upper().replace("O", "0")
    match = re.match(r"^(0|A|B|AB)\s*([+-])$", normalised)
    if not match:
        raise ValueError(
            f"Unrecognised blood type: {blood_type!r} "
            "(expected one of 0+ A+ B+ AB+ 0- A- B- AB-)"
        )
    group, sign = match.groups()
    return f"{group.lower()}-{'p' if sign == '+' else 'm'}"


def fetch_html(url: str = DEFAULT_URL, timeout: float = 30.0) -> str:
    """Download the page and return its raw HTML."""
    response = requests.get(url, headers=_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_levels(html: str) -> dict[str, StockLevel]:
    """Parse all blood-type stock levels, keyed by code (e.g. ``ab-p``)."""
    soup = BeautifulSoup(html, "html.parser")
    levels: dict[str, StockLevel] = {}

    for span in soup.find_all("span", id=re.compile(r"^(0|a|b|ab)-(p|m)-text$")):
        span_id = span.get("id")
        if not isinstance(span_id, str):
            continue
        code = span_id.removesuffix("-text")
        text = span.get_text(strip=True)
        number_match = _FIRST_INT_RE.search(text)
        if not number_match:
            # No leading number in the text — skip rather than crash.
            continue
        levels[code] = StockLevel(
            code=code,
            blood_type=code_to_blood_type(code),
            days=int(number_match.group()),
            text=text,
        )

    return levels
