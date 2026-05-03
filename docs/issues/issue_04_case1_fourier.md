## Title
SDOF Case 1: Fourier series response to sawtooth periodic force

## Type
AFK

## Blocked by
- Blocked by issue 01 (SDOFSystem + core helpers)

## User stories covered
3, 4, 16, 17

---

## What to build

Implement `periodic_sawtooth_response` — the public function for Case 1 — plus its private Fourier helpers. The function decomposes the sawtooth waveform into `n_harmonics` Fourier sine terms, multiplies each by the complex FRF `H(nω₀)`, and superposes the real-part steady-state responses in the time domain.

The analytical sawtooth Fourier series is:
```
F(t) = Σ bₙ·sin(nω₀t),   bₙ = −2F0/(nπ)·(−1)ⁿ,   ω₀ = 2π/T_period
```
Each steady-state displacement harmonic:
```
x_n(t) = bₙ · Re[H(nω₀) · exp(j·nω₀·t)]
```

## Acceptance criteria

- [ ] `periodic_sawtooth_response(system, F0, T_period, n_harmonics, t_end, dt, plot=False) -> dict` implemented; returns `"t"`, `"F"`, `"x"`, `"v"`, `"a"`
- [ ] `_sawtooth_fourier_coefficients(F0, T_period, n_harmonics)` returns `(omega_harmonics, b_coefficients)` arrays
- [ ] `_superpose_harmonics(system, t, omega_harmonics, C_harmonics)` returns displacement array by summing `Re[Cₙ·H(ωₙ)·e^(jωₙt)]` for all harmonics
- [ ] `test_sawtooth_fundamental_amplitude`: with `n_harmonics=1`, peak `x` matches `|b₁|·|H(ω₀)|` to within `1e-6`
- [ ] `test_sawtooth_convergence`: RMS error of `x(t)` decreases as `n_harmonics` increases from 5 → 20 → 50
- [ ] Function does not assume `t_end` is a multiple of `T_period` — handles arbitrary `t_end`
