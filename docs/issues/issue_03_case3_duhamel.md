## Title
SDOF Case 3: Closed-form Duhamel responses — step, rectangular pulse, triangular blast

## Type
AFK

## Blocked by
- Blocked by issue 01 (SDOFSystem + core helpers)

## User stories covered
7, 8, 9, 10

---

## What to build

Implement three public analysis functions that return exact closed-form Duhamel integral solutions for non-periodic transient loads. Each function returns a `dict` with keys `"t"`, `"x"`, `"v"`, `"a"`. Velocity and acceleration are derived from displacement by central-difference (`_differentiate`).

This slice is completely independent of the Newmark integrator and can be verified against known analytical limits.

**Formulas to implement:**

**Step (Case 3a):**
```
x(t) = (F0/k) · [1 − e^(−ζωₙt) · (cos(ωdt) + (ζ/√(1−ζ²))·sin(ωdt))]
```

**Rectangular pulse (Case 3b) — superposition of two steps:**
```
x(t) = x_step(t)                       for 0 ≤ t < t_d
x(t) = x_step(t) − x_step(t − t_d)    for t ≥ t_d
```

**Triangular blast pulse (Case 3c) — Chopra §4.3:**
- Phase 1 `[0, t_d]`: ramp-load Duhamel convolution (named A, B coefficients from Chopra)
- Phase 2 `[t_d, t_end]`: free vibration from `(x(t_d), v(t_d))`

## Acceptance criteria

- [ ] `step_response(system, F0, t_end, dt, plot=False) -> dict` implemented and returns `"t"`, `"x"`, `"v"`, `"a"`
- [ ] `rectangular_pulse_response(system, F0, t_d, t_end, dt, plot=False) -> dict` implemented
- [ ] `triangular_pulse_response(system, F0, t_d, t_end, dt, plot=False) -> dict` implemented; free-vibration phase uses initial conditions from the during-pulse solution
- [ ] Private helpers `_step_displacement`, `_rect_pulse_displacement`, `_triangular_pulse_displacement`, `_differentiate` all present
- [ ] `test_step_response_static_limit`: high-ζ (e.g. 0.99) step response settles to `F0/k` within `1e-4`
- [ ] `test_step_response_daf`: near-undamped (ζ=0.01) step response max ≈ `2·F0/k` within `1e-3`
- [ ] `test_rectangular_pulse_short`: `t_d << T_n` → `x_max ≈ F0·t_d/(m·ωd)` within `5%`
- [ ] `test_rectangular_pulse_long`: `t_d >> T_n` → `x_max ≈ 2·F0/k` within `1e-3`
- [ ] `test_triangular_pulse_free_vibration`: post-`t_d` array matches analytical free-vibration formula within `1e-6`
- [ ] Triangular pulse intermediate variables follow Chopra §4.3 naming for auditability
