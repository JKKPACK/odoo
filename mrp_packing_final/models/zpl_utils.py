import re


def zpl_safe(value):
    """Return a ZPL-safe, single-line value for ^FD fields."""
    if value in (None, False):
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ")
    # ^ and ~ can start ZPL commands inside field data.
    text = text.replace("^", " ").replace("~", " ")
    return re.sub(r"\s+", " ", text).strip()


def qty_text(value, decimals=2):
    value = float(value or 0.0)
    text = f"{value:.{decimals}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text
