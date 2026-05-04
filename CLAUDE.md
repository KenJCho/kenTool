# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run unit conversion examples
python unit_conversion.py

# Run unit conversion tests
python test_unit_conversion.py

# Run SDOF analysis examples (all four cases)
python sdof_analysis.py

# Run SDOF analysis tests
python test_sdof_analysis.py

# Launch the SDOF GUI
python sdof_gui.py

# Run a single test (pytest)
pytest test_unit_conversion.py::test_length_ft_to_m -v
pytest test_sdof_analysis.py::test_step_response_daf -v
```

## Architecture

**kenTool** is a Python utility for structural engineering. It provides unit conversions and SDOF vibration analysis. All modules are flat (no packages), SI-only internally.

### Unit conversion: [unit_conversion.py](unit_conversion.py)

Single public function: `convert_unit(value, from_unit, to_unit) -> float`

The conversion pipeline:
1. **Alias normalization** — maps variants like `"feet"`, `"foot"` → `"ft"` via the `UNIT_ALIASES` dict
2. **Category detection** — each canonical unit belongs to a category (length, force, etc.); mismatched categories raise `ValueError`
3. **Factor lookup** — `CONVERSION_FACTORS` stores each unit's multiplier to its SI base; conversion is `value × (from_factor / to_factor)`

Supported categories: length, area, inertia, area_load, line_load, force, modulus, density, velocity, acceleration.

### SDOF vibration analysis: [sdof_analysis.py](sdof_analysis.py)

Entry point: `make_system(m, k, zeta) -> SDOFSystem` — derives ωₙ, ωd, c, Tₙ in `__post_init__`.

Four public analysis functions, each returning `dict[str, np.ndarray]` with keys `"t"`, `"x"`, `"v"`, `"a"` (and spectrum keys for Case 4):

| Function | Case | Method |
|---|---|---|
| `periodic_sawtooth_response` | Periodic force (sawtooth) | Fourier series → H(ω) per harmonic → superpose |
| `irregular_periodic_response` | Arbitrary periodic (table) | FFT → H(ω) × F(ω) → IFFT |
| `step_response`, `rectangular_pulse_response`, `triangular_pulse_response` | Non-periodic transient | Closed-form Duhamel integral (Chopra §4.3) |
| `response_spectrum` | Response spectrum | Newmark-β sweep over T_range; returns Sd/Sv/Sa + time history |

All functions accept `plot=False`; passing `plot=True` delegates to [sdof_plots.py](sdof_plots.py), which contains one private rendering function per case (not independently importable).

Key private helpers: `_compute_H` (complex FRF), `_newmark_beta_integrate` (average-acceleration, β=0.25, γ=0.5), `_triangular_pulse_displacement` (Duhamel closed-form with local `_phase1` sub-function to avoid recursion).

### Tests: [test_unit_conversion.py](test_unit_conversion.py), [test_sdof_analysis.py](test_sdof_analysis.py)

Both use `approx_equal()` (tolerance `1e-8` for algebraic checks, `1e-4` for time-integration), plain `assert` statements, and `if __name__ == "__main__"` runners — no external test framework required.

### GUI: [sdof_gui.py](sdof_gui.py)

Three-column Qt desktop app (`python sdof_gui.py`). Requires PyQt5 (or PySide6).

Layout: **left** system params + case selector + case parameters + Calculate button | **center** force/excitation diagram | **right** response (3-panel x/v/a time history, or 2×2 Sd/Sv/Sa spectrum).

Design tokens follow `Agents_Skills/GUI_design_description.md` (FINSUL palette: `#F8F9FA` background, `#7BAAD4` primary, `#CC3344` accent). Qt shim at top of file supports both PyQt5 and PySide6.

### Agents_Skills/

Contains Claude skill definitions and a [GUI design specification](Agents_Skills/GUI_design_description.md) for potential future GUI tooling. Not part of the runtime module.
