## Title
SDOF Case 4: Response spectrum — base excitation and shock pulses

## Type
AFK

## Blocked by
- Blocked by issue 02 (Newmark-β integrator)

## User stories covered
11, 12, 13, 14, 15

---

## What to build

Implement `response_spectrum` — the public function for Case 4 — plus its private sweep and pulse-builder helpers.

The function sweeps over a range of natural periods `T_min..T_max`, solves a unit-mass SDOF at each period using Newmark-β, records the peak relative displacement, and assembles `Sd`, `Sv = ωₙ·Sd`, `Sa = ωₙ²·Sd` arrays. It also returns the full time history for the user's own system.

Four excitation sub-cases:
- `"base_accel"` — arbitrary acceleration record `(ag_t, ag_a)` supplied by user; EOM in relative coords: `ẍ_rel + 2ζωₙẋ_rel + ωₙ²x_rel = −ag(t)`
- `"half_sine"` — `ag(t) = a0·sin(πt/t_d)` for `0 ≤ t ≤ t_d`, zero after
- `"triangular"` — `ag(t) = a0·(1 − t/t_d)` for `0 ≤ t ≤ t_d`, zero after
- `"rectangular"` — `ag(t) = a0` for `0 ≤ t ≤ t_d`, zero after

Private helpers:
- `_build_pulse_accel(excitation_type, a0, t_d, dt, t_end)` — constructs `ag` array for pulse types
- `_sweep_spectrum(zeta, T_range, ag, dt)` — inner loop; enforces `dt_inner ≤ Tᵢ/20` with linear interpolation upsampling when needed

## Acceptance criteria

- [ ] `response_spectrum(system, excitation_type, ag_t, ag_a, a0, t_d, T_min, T_max, n_periods, plot=False) -> dict` implemented
- [ ] Returns `"T_range"`, `"Sd"`, `"Sv"`, `"Sa"`, `"t_hist"`, `"x_hist"`, `"a_hist"`
- [ ] All four `excitation_type` values handled; `ValueError` raised for unknown type
- [ ] `_sweep_spectrum` enforces `dt_inner ≤ T_i/20` for every period in the sweep
- [ ] `test_spectrum_pseudo_relations`: `Sv[i] == omega_n_i * Sd[i]` and `Sa[i] == omega_n_i**2 * Sd[i]` for all `i`, within `1e-8`
- [ ] `test_spectrum_sd_rectangular_static`: for `t_d >> T` (quasi-static), `Sd ≈ 2·a0/ωₙ²` (twice the static displacement)
- [ ] `"t_hist"` and `"x_hist"` correspond to the user's `system.T_n`, not unit-mass system
- [ ] `n_periods` points are log-spaced between `T_min` and `T_max`
