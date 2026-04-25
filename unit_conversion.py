"""Simple SI/imperial unit conversions for structural engineering units."""

from __future__ import annotations

from typing import Any


_UNIT_ALIASES = {
    "ft": "ft",
    "feet": "ft",
    "foot": "ft",
    "m": "m",
    "meter": "m",
    "meters": "m",
    "in": "in",
    "inch": "in",
    "inches": "in",
    "mm": "mm",
    "millimeter": "mm",
    "millimeters": "mm",
    "in^2": "in^2",
    "in2": "in^2",
    "sqin": "in^2",
    "squareinch": "in^2",
    "mm^2": "mm^2",
    "mm2": "mm^2",
    "sqmm": "mm^2",
    "squaremillimeter": "mm^2",
    "in^4": "in^4",
    "in4": "in^4",
    "mm^4": "mm^4",
    "mm4": "mm^4",
    "psf": "psf",
    "lb/ft^2": "psf",
    "lb/ft2": "psf",
    "poundforcepersquarefoot": "psf",
    "kN/m^2": "kN/m^2",
    "kn/m^2": "kN/m^2",
    "kn/m2": "kN/m^2",
    "kilonewtonspersquaremeter": "kN/m^2",
    "plf": "plf",
    "lb/ft": "plf",
    "lb/ft1": "plf",
    "poundforceperfoot": "plf",
    "kN/m": "kN/m",
    "kn/m": "kN/m",
    "kilonewtonspermeter": "kN/m",
    "lb": "lb",
    "lbf": "lb",
    "pound": "lb",
    "pounds": "lb",
    "n": "N",
    "newton": "N",
    "newtons": "N",
    "kip": "kip",
    "kips": "kip",
    "kn": "kN",
    "kilonewton": "kN",
    "kilonewtons": "kN",
    "ksi": "ksi",
    "ksi": "ksi",
    "mpa": "MPa",
    "megapascal": "MPa",
    "megapascals": "MPa",
    "pcf": "pcf",
    "lb/ft^3": "pcf",
    "lb/ft3": "pcf",
    "poundpercubicfoot": "pcf",
    "kg/m^3": "kg/m^3",
    "kg/m3": "kg/m^3",
    "kilogrampermetercubed": "kg/m^3",
    "in/s": "in/s",
    "inps": "in/s",
    "ips": "in/s",
    "inchpersecond": "in/s",
    "mm/s": "mm/s",
    "mmps": "mm/s",
    "mmpers": "mm/s",
    "millimeterpersecond": "mm/s",
    "in/s^2": "in/s^2",
    "in/s2": "in/s^2",
    "ips2": "in/s^2",
    "inchpersecond^2": "in/s^2",
    "m/s^2": "m/s^2",
    "m/s2": "m/s^2",
    "mps2": "m/s^2",
    "meterpersecond^2": "m/s^2",
}

_UNIT_DEFINITIONS = {
    "length": {
        "ft": 0.3048,
        "m": 1.0,
        "in": 0.0254,
        "mm": 0.001,
    },
    "area": {
        "in^2": 0.00064516,
        "mm^2": 1e-6,
    },
    "inertia": {
        "in^4": 4.1623199199999996e-7,
        "mm^4": 1e-12,
    },
    "area_load": {
        "psf": 0.047880258988,
        "kN/m^2": 1.0,
    },
    "line_load": {
        "plf": 0.014593903007,
        "kN/m": 1.0,
    },
    "force": {
        "lb": 4.4482216152605,
        "N": 1.0,
        "kip": 4448.2216152605,
        "kN": 1000.0,
    },
    "modulus": {
        "ksi": 6.894757293168361,
        "MPa": 1.0,
    },
    "density": {
        "pcf": 16.0184633739602,
        "kg/m^3": 1.0,
    },
    "velocity": {
        "in/s": 0.0254,
        "mm/s": 0.001,
    },
    "acceleration": {
        "in/s^2": 0.0254,
        "m/s^2": 1.0,
    },
}


def _normalize_unit(unit: str) -> str:
    if not isinstance(unit, str):
        raise TypeError("Unit names must be strings.")

    key = unit.strip().lower().replace(" ", "").replace("^", "^")
    return _UNIT_ALIASES.get(key, key)


def _find_unit_category(unit: str) -> str:
    for category, units in _UNIT_DEFINITIONS.items():
        if unit in units:
            return category
    raise ValueError(f"Unsupported unit: '{unit}'")


def convert_unit(value: Any, from_unit: str, to_unit: str) -> float:
    """Convert a numeric value between supported SI and imperial units.

    Args:
        value: Numeric value to convert.
        from_unit: Source unit string.
        to_unit: Destination unit string.

    Returns:
        Converted float value.

    Raises:
        ValueError: If units are not supported or categories do not match.
        TypeError: If the value is not numeric.
    """
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError("Value must be a number.") from exc

    from_normalized = _normalize_unit(from_unit)
    to_normalized = _normalize_unit(to_unit)

    if from_normalized == to_normalized:
        return numeric_value

    from_category = _find_unit_category(from_normalized)
    to_category = _find_unit_category(to_normalized)

    if from_category != to_category:
        raise ValueError(
            f"Cannot convert between units of different categories: '{from_unit}' ({from_category}) -> '{to_unit}' ({to_category})."
        )

    from_factor = _UNIT_DEFINITIONS[from_category][from_normalized]
    to_factor = _UNIT_DEFINITIONS[to_category][to_normalized]
    return numeric_value * from_factor / to_factor


if __name__ == "__main__":
    examples = [
        (1, "ft", "m"),
        (12, "in", "mm"),
        (1, "in^2", "mm^2"),
        (1, "in^4", "mm^4"),
        (1, "psf", "kN/m^2"),
        (1, "plf", "kN/m"),
        (1, "lb", "N"),
        (1, "kip", "kN"),
        (1, "ksi", "MPa"),
        (1, "pcf", "kg/m^3"),
        (1, "in/s", "mm/s"),
        (1, "in/s^2", "m/s^2"),
    ]

    for value, src, dst in examples:
        print(f"{value} {src} = {convert_unit(value, src, dst):.8g} {dst}")
