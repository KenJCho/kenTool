## Problem Statement

As a vibration and structural engineer, I need to analyse the dynamic response of single-degree-of-freedom (SDOF) systems under a variety of realistic forcing conditions — periodic machine vibrations, measured irregular loads, transient shock and blast pulses, and seismic or shock base excitations. Currently kenTool only converts units; there is no tool for computing or visualising dynamic structural response. I must either reach for heavyweight FEA packages or write one-off scripts from scratch each time.

## Solution

Add `sdof_analysis.py` to kenTool: a focused Python module that models an underdamped SDOF system (defined by mass, stiffness, and damping ratio) and computes its response under four force categories, each using the most analytically appropriate method. A companion `sdof_plots.py` module renders time-history and spectrum plots via matplotlib. All inputs and outputs are in SI units.

## User Stories

1. As a vibration engineer, I want to define an SDOF system with mass, stiffness, and damping ratio so that all derived quantities (ωₙ, ωd, c, Tₙ) are computed automatically.
2. As a vibration engineer, I want to receive a `ValueError` with a clear message if I provide non-physical parameters (m ≤ 0, k ≤ 0, ζ ≥ 1) so that I catch input mistakes early.
3. As a vibration engineer, I want to compute the steady-state response to a sawtooth forcing function using a Fourier series so that I can see how each harmonic contributes to the total response.
4. As a vibration engineer, I want to control the number of Fourier harmonics included so that I can observe convergence as I add more terms.
5. As a vibration engineer, I want to provide an arbitrary periodic force as a (t, F) table and get the displacement time history via FFT so that I can analyse measured or numerically generated waveforms.
6. As a vibration engineer, I want the FFT reconstruction of the input force plotted alongside the original tabular data so that I can verify the harmonic fidelity before trusting the response.
7. As a vibration engineer, I want the exact closed-form Duhamel integral response to a step force so that I can verify the dynamic amplification factor and static settlement.
8. As a vibration engineer, I want the exact closed-form response to a rectangular pulse load so that I can characterise the shock amplification for a given pulse duration relative to the natural period.
9. As a vibration engineer, I want the exact closed-form response to a triangular (blast) pulse so that I can evaluate peak displacement and post-pulse free vibration for blast loading scenarios.
10. As a vibration engineer, I want to see displacement, velocity, and acceleration time histories for all Case 3 sub-cases so that I can assess all demand quantities.
11. As a vibration engineer, I want to generate a displacement response spectrum (Sd vs T) for base excitation so that I can characterise the frequency-dependent demand of a ground motion record.
12. As a vibration engineer, I want pseudo-velocity (Sv) and pseudo-acceleration (Sa) spectra in addition to Sd so that I have the full tripartite spectrum for code comparison.
13. As a vibration engineer, I want to generate response spectra for shock pulses (half-sine, triangular, rectangular) so that I can design equipment isolation for shock environments.
14. As a vibration engineer, I want the full time history of my specific SDOF system returned alongside the spectrum sweep so that I can cross-check my system's peak response against the spectrum ordinate.
15. As a vibration engineer, I want my system's natural period marked on the spectrum plot so that I can immediately read off the design demand.
16. As a vibration engineer, I want to call each analysis function with `plot=False` by default so that I can use the module in scripts without opening windows unexpectedly.
17. As a vibration engineer, I want all analysis functions to return a `dict` of numpy arrays so that I can post-process results directly without parsing special return objects.
18. As a vibration engineer, I want the module to work with only numpy and matplotlib as dependencies so that it installs cleanly in any standard scientific Python environment.

## Implementation Decisions

### Modules built

- **`sdof_analysis.py`** — all analysis logic; public API only (no side effects at import time)
- **`sdof_plots.py`** — all matplotlib rendering; called only from within `sdof_analysis.py` via `if plot:` guards; no independent public API
- **`test_sdof_analysis.py`** — plain-assert test suite matching the style of `test_unit_conversion.py`
- **`requirements.txt`** — declares `numpy >= 1.24` and `matplotlib >= 3.7`; no scipy

### `SDOFSystem` dataclass

Inputs: `m` (kg), `k` (N/m), `zeta` (dimensionless).  
Derived in `__post_init__`: `omega_n = sqrt(k/m)`, `omega_d = omega_n*sqrt(1-zeta²)`, `c = 2*m*omega_n*zeta`, `T_n = 2π/omega_n`.  
Validation raises `ValueError` for non-physical inputs.

### Case 1 — Fourier series (periodic sawtooth)

Sawtooth coefficients `bₙ = -2F0/(nπ)·(-1)ⁿ` are computed analytically.  
Each harmonic `bₙ·sin(nω₀t)` is multiplied by the complex FRF `H(nω₀) = 1/(k − m·(nω₀)² + j·c·nω₀)`.  
Responses are superposed in the time domain.

### Case 2 — FFT (irregular periodic table)

Input must be one complete period of uniformly-sampled (t, F) pairs.  
`numpy.fft.rfft` extracts complex amplitudes; each bin is multiplied by `H(ωₖ)`; `irfft` reconstructs `x(t)`.  
Result is tiled to fill `t_end`.

### Case 3 — Closed-form Duhamel integrals

Three sub-cases, all exact for underdamped systems:
- **Step**: `x(t) = (F0/k)·[1 − e^(−ζωₙt)·(cos(ωdt) + (ζ/√(1−ζ²))·sin(ωdt))]`
- **Rectangular pulse**: superposition of two shifted step responses (exact, no numerical integration)
- **Triangular blast pulse**: ramp-load Duhamel convolution during `[0, t_d]` (coefficients from Chopra §4.3), free-vibration formula after `t_d`

Velocity and acceleration derived by central-difference of the displacement array.

### Case 4 — Response spectrum

Period sweep from `T_min` to `T_max` with `n_periods` log-spaced points.  
For each period: unit-mass SDOF solved via Newmark-β (average-acceleration, β=0.25, γ=0.5).  
Pulse shapes built analytically; base-acceleration record accepted as a (t, a) array.  
Pseudo-spectra: `Sv = ωₙ·Sd`, `Sa = ωₙ²·Sd`.  
User's own system time history returned under keys `"t_hist"`, `"x_hist"`, `"a_hist"`.

### Return value convention

All analysis functions return `dict[str, np.ndarray]`. Core keys: `"t"`, `"x"`, `"v"`, `"a"`. Case 4 adds: `"T_range"`, `"Sd"`, `"Sv"`, `"Sa"`, `"t_hist"`, `"x_hist"`, `"a_hist"`.

## Testing Decisions

A good test checks externally observable behaviour against a known analytical result; it does not test internal array sizes, intermediate variable names, or plotting side effects.

**Modules tested:** `sdof_analysis.py` only. `sdof_plots.py` is not unit-tested (rendering is visual).

**Prior art:** `test_unit_conversion.py` — plain `assert` statements, `approx_equal(a, b, tol)` helper, `if __name__ == "__main__"` runner. `test_sdof_analysis.py` follows the same conventions.

**Key tests:**

| Test | What it verifies |
|---|---|
| `test_make_system_derived_quantities` | ωₙ, ωd, c, Tₙ computed correctly |
| `test_make_system_invalid_inputs` | ValueError for m≤0, k≤0, ζ≥1 |
| `test_step_response_static_limit` | High-ζ step response settles to F0/k |
| `test_step_response_daf` | Near-undamped step max ≈ 2·F0/k |
| `test_rectangular_pulse_short` | Short pulse ≈ impulse: x_max ≈ F0·t_d/(m·ωd) |
| `test_rectangular_pulse_long` | Long pulse ≈ step: x_max ≈ 2·F0/k |
| `test_triangular_pulse_free_vibration` | Post-t_d array matches free-vibration formula |
| `test_sawtooth_fundamental_amplitude` | n=1 result matches \|H(ω₀)\|·\|b₁\| analytically |
| `test_fft_case2_roundtrip` | Sine-wave table → FFT path matches Case 1 harmonic |
| `test_newmark_free_vibration` | x₀≠0, F=0 → Newmark matches analytical free vibration |
| `test_spectrum_pseudo_relations` | Sv = ωₙ·Sd and Sa = ωₙ²·Sd at every sweep point |

Tolerances: `1e-8` for algebraic identities; `1e-4` for time-integration comparisons.

## Out of Scope

- Multiple-degree-of-freedom (MDOF) systems
- Non-linear stiffness or damping
- Overdamped (ζ ≥ 1) or critically damped (ζ = 1) systems
- Imperial unit input (users convert via `unit_conversion.py` before calling)
- GUI or command-line interface
- File I/O (CSV/Excel import of force tables)
- Frequency-domain output (transfer functions, Bode plots)
- scipy dependency

## Further Notes

- The triangular pulse closed-form coefficients follow Chopra, "Dynamics of Structures", 5th ed., §4.3. The implementation should name intermediate variables to match that derivation for auditability.
- For the response spectrum sweep, `_sweep_spectrum` should internally enforce `dt_inner ≤ Tᵢ/20` and upsample the acceleration record via linear interpolation when the user-supplied `dt` is too coarse for small-period systems.
- On Windows, matplotlib defaults to a non-interactive backend in some environments. The module relies on the user's environment configuration and does not call `matplotlib.use()` itself.
