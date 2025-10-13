import re
from typing import List, Dict, Optional

UNIT_SYNONYMS = {
    "k": "kg",
    "kg": "kg",
    "kilo": "kg",
    "kilos": "kg",
    "u": "unit",
    "uni": "unit",
    "unidad": "unit",
    "unidades": "unit",
    "unit": "unit",
    "gr": "g",
    "g": "g",
}

ZERO_WIDTH = "\u200B\u200C\u200D\u2060\uFEFF"
BULLETS = "\u2022\u2023\u25E6\u2043\u2219•-*"


def _clean_line(text: str) -> str:
    if not text:
        return ""
    for ch in ZERO_WIDTH:
        text = text.replace(ch, "")
    text = text.strip()
    text = re.sub(rf"^[{re.escape(BULLETS)}\s]+", "", text)
    return text.strip()


def _extract_paren_notes(text: str) -> (str, str):
    m = re.search(r"\(([^)]*)\)", text)
    if not m:
        return text.strip(), ""
    note = m.group(1).strip()
    cleaned = (text[: m.start()] + text[m.end():]).strip()
    return cleaned, note


def _norm_unit(unit: Optional[str]) -> str:
    if not unit:
        return "kg"
    u = unit.strip().lower().rstrip('.')
    return UNIT_SYNONYMS.get(u, u)


def _to_float(s: str) -> float:
    try:
        return float(s.replace(",", "."))
    except Exception:
        return 1.0


def _parse_line(line: str) -> Dict:
    original = line
    line = _clean_line(line)
    if not line:
        return {}

    without_paren, paren_notes = _extract_paren_notes(line)

    unit_group = r"(?P<u>(?:k|kg|kilo|kilos|u|uni|unidad|unidades|unit|gr|g)\.? )?"
    unit_group_end = r"(?P<uend>(?:k|kg|kilo|kilos|u|uni|unidad|unidades|unit|gr|g)\.? )?"

    # 1) Cantidad + unidad al inicio (incluye "2k"/"2 uni."/opcional 'de')
    m = re.match(rf"^(?P<qty>[0-9]+(?:[\.,][0-9]+)?)\s*(?P<u1>(?:k|kg|kilo|kilos|u|uni|unidad|unidades|unit|gr|g)\.?)?\b\s*(?:de\s+)?(?P<rest>.+)$", without_paren, re.IGNORECASE)
    if m:
        qty = _to_float(m.group("qty"))
        unit = _norm_unit(m.group("u1") or "unit")
        product = m.group("rest").strip()
        return {"product": product, "qty": qty, "unit": unit, "notes": paren_notes, "_raw": original}

    # 2) Cantidad + unidad al final (opcional 'de')
    m = re.match(rf"^(?P<p>.+?)\s+(?:de\s+)?(?P<qty>[0-9]+(?:[\.,][0-9]+)?)\s*(?P<u3>(?:k|kg|kilo|kilos|u|uni|unidad|unidades|unit|gr|g)\.?)\b\s*$", without_paren, re.IGNORECASE)
    if m:
        product = m.group("p").strip()
        qty = _to_float(m.group("qty"))
        unit = _norm_unit(m.group("u3"))
        return {"product": product, "qty": qty, "unit": unit, "notes": paren_notes, "_raw": original}

    # 2b) Producto + cantidad (sin unidad) => unidad por defecto 'unit'
    m = re.match(r"^(?P<p>.+?)\s+(?P<qty>[0-9]+(?:[\.,][0-9]+)?)\s*$", without_paren)
    if m:
        product = m.group("p").strip()
        qty = _to_float(m.group("qty"))
        return {"product": product, "qty": qty, "unit": "unit", "notes": paren_notes, "_raw": original}

    # 3) Solo cantidad al inicio -> unidad por defecto unit
    m = re.match(r"^(?P<qty>[0-9]+(?:[\.,][0-9]+)?)\s+(?P<rest>.+)$", without_paren)
    if m:
        qty = _to_float(m.group("qty"))
        product = m.group("rest").strip()
        return {"product": product, "qty": qty, "unit": "unit", "notes": paren_notes, "_raw": original}

    # 4) Palabras clave
    if re.search(r"\b(paquete|bandeja)\b", without_paren, re.IGNORECASE):
        return {"product": without_paren, "qty": 1.0, "unit": "unit", "notes": paren_notes, "_raw": original}

    return {"product": without_paren, "qty": 1.0, "unit": "unit", "notes": paren_notes, "_raw": original}


def parse_orders_text(text: str) -> List[Dict]:
    items: List[Dict] = []
    current_customer: Optional[str] = None

    for idx, raw_line in enumerate(text.splitlines()):
        line = _clean_line(raw_line)
        if not line:
            continue
        mb = re.match(r"^pedido\s+(.+)$", line, re.IGNORECASE)
        if mb:
            current_customer = mb.group(1).strip()
            continue

        parsed = _parse_line(line)
        if not parsed:
            continue
        parsed["customer"] = current_customer or (parsed.get("customer") or "")
        parsed["line_index"] = idx
        items.append(parsed)

    return items
