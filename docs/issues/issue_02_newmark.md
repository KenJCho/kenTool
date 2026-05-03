## Title
SDOF: Newmark-β average-acceleration time integrator

## Type
AFK

## Blocked by
- Blocked by issue 01 (SDOFSystem + core helpers)

## User stories covered
12, 13, 14 (underpins Case 4 response spectrum)

---

## What to build

Implement `_newmark_beta_integrate(m, k, c, force, dt)` — a private average-acceleration Newmark-β solver (β=0.25, γ=0.5) that steps through an arbitrary discrete force vector and returns `(x, v, a)` time histories.

This is the numerical engine for Case 4 (response spectrum sweep). It must also be validated against the known analytical free-vibration solution so that accuracy is confirmed before the sweep logic is built on top of it.

## Acceptance criteria

- [ ] `_newmark_beta_integrate(m, k, c, force, dt)` implemented with β=0.25, γ=0.5 (unconditionally stable, second-order accurate)
- [ ] Predictor–corrector update equations match the average-acceleration formulation:
  - `a_(n+1) = (F_(n+1) − c·v_pred − k·x_pred) / (m + γ·dt·c + β·dt²·k)`
  - `x_(n+1) = x_pred + β·dt²·a_(n+1)`
  - `v_(n+1) = v_pred + γ·dt·a_(n+1)`
- [ ] Returns `(x, v, a)` as three numpy arrays of length `len(force)`
- [ ] `test_newmark_free_vibration`: with non-zero initial displacement `x₀`, zero force, Newmark result matches analytical free-vibration `x(t) = x₀·e^(−ζωₙt)·cos(ωdt)` to within tolerance `1e-4`
