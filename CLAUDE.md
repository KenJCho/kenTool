# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the module directly (executes example conversions)
python unit_conversion.py

# Run the test suite
python test_unit_conversion.py

# Run a single test (pytest)
pytest test_unit_conversion.py::test_length_ft_to_m -v
```

## Architecture

**kenTool** is a Python utility for structural engineering unit conversions. The project is minimal and focused.

### Core module: [unit_conversion.py](unit_conversion.py)

Single public function: `convert_unit(value, from_unit, to_unit) -> float`

The conversion pipeline:
1. **Alias normalization** — maps variants like `"feet"`, `"foot"` → `"ft"` via the `UNIT_ALIASES` dict
2. **Category detection** — each canonical unit belongs to a category (length, force, etc.); mismatched categories raise `ValueError`
3. **Factor lookup** — `CONVERSION_FACTORS` stores each unit's multiplier to its SI base; conversion is `value × (from_factor / to_factor)`

Supported categories: length, area, inertia, area_load, line_load, force, modulus, density, velocity, acceleration.

### Tests: [test_unit_conversion.py](test_unit_conversion.py)

Uses `approx_equal()` (tolerance `1e-8`) for floating-point comparisons. Each test covers a round-trip or specific conversion path. Cross-category conversion is also tested for the expected `ValueError`.

### Agents_Skills/

Contains Claude skill definitions and a [GUI design specification](Agents_Skills/GUI_design_description.md) for potential future GUI tooling. Not part of the runtime module.
