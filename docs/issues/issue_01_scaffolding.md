## Title
SDOF: Project scaffolding — SDOFSystem, core helpers, requirements.txt

## Type
AFK

## Blocked by
None — can start immediately

## User stories covered
1, 2, 18

---

## What to build

Create `requirements.txt` and the foundational layer of `sdof_analysis.py`: the `SDOFSystem` dataclass, the `make_system` constructor, and the two core mathematical primitives (`_compute_H`, `_unit_impulse_response`) that all four analysis cases depend on.

This slice delivers nothing to the end user on its own, but it is the prerequisite for every subsequent slice and can be tested in full isolation.

## Acceptance criteria

- [ ] `requirements.txt` exists at the repo root declaring `numpy >= 1.24` and `matplotlib >= 3.7`
- [ ] `SDOFSystem` dataclass accepts `m`, `k`, `zeta` and computes `omega_n`, `omega_d`, `c`, `T_n` in `__post_init__`
- [ ] `make_system(m, k, zeta)` is a thin public alias returning an `SDOFSystem`
- [ ] `ValueError` raised (with informative message) for `m <= 0`, `k <= 0`, or `zeta >= 1`
- [ ] `_compute_H(system, omega)` returns the correct complex FRF array: `1 / (k − m·ω² + j·c·ω)`
- [ ] `_unit_impulse_response(system, t)` returns `exp(−ζωₙt)·sin(ωdt) / (m·ωd)`
- [ ] `test_sdof_analysis.py` exists with `test_make_system_derived_quantities` and `test_make_system_invalid_inputs` passing
- [ ] Module follows the same code style as `unit_conversion.py` (Google docstrings, type hints, snake_case, private `_` prefix)
