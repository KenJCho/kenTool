"""Single-degree-of-freedom vibration analysis for structural/vibration engineering.

Provides displacement, velocity, and acceleration responses under four force cases:
  1. Periodic force via Fourier series (sawtooth waveform)
  2. Irregular periodic force from (t, F) table via FFT
  3. Non-periodic transient force via closed-form Duhamel integrals
     (step, rectangular pulse, triangular blast pulse)
  4. Response spectrum (base excitation and shock pulses)

All inputs and outputs use SI units (kg, N, m, s).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# System definition
# ---------------------------------------------------------------------------

@dataclass
class SDOFSystem:
    """Single-degree-of-freedom system defined by mass, stiffness, and damping ratio.

    Args:
        m: Mass, kg. Must be positive.
        k: Stiffness, N/m. Must be positive.
        zeta: Damping ratio, dimensionless. Must satisfy 0 <= zeta < 1.

    Raises:
        ValueError: If any parameter is non-physical.
    """

    m: float
    k: float
    zeta: float
    omega_n: float = field(init=False)
    omega_d: float = field(init=False)
    c: float = field(init=False)
    T_n: float = field(init=False)

    def __post_init__(self) -> None:
        if self.m <= 0:
            raise ValueError(f"Mass must be positive, got {self.m}")
        if self.k <= 0:
            raise ValueError(f"Stiffness must be positive, got {self.k}")
        if not (0.0 <= self.zeta < 1.0):
            raise ValueError(f"Damping ratio must satisfy 0 <= zeta < 1, got {self.zeta}")
        self.omega_n = math.sqrt(self.k / self.m)
        self.omega_d = self.omega_n * math.sqrt(1.0 - self.zeta ** 2)
        self.c = 2.0 * self.m * self.omega_n * self.zeta
        self.T_n = 2.0 * math.pi / self.omega_n


def make_system(m: float, k: float, zeta: float) -> SDOFSystem:
    """Create an SDOFSystem with validated parameters.

    Args:
        m: Mass, kg.
        k: Stiffness, N/m.
        zeta: Damping ratio.

    Returns:
        Configured SDOFSystem with derived quantities pre-computed.
    """
    return SDOFSystem(m=m, k=k, zeta=zeta)


# ---------------------------------------------------------------------------
# Core mathematical primitives
# ---------------------------------------------------------------------------

def _compute_H(system: SDOFSystem, omega: np.ndarray) -> np.ndarray:
    """Complex frequency response function H(ω) = 1 / (k - m·ω² + j·c·ω).

    Args:
        system: SDOFSystem instance.
        omega: Angular frequencies, rad/s.

    Returns:
        Complex FRF array, m/N, same shape as omega.
    """
    return 1.0 / (system.k - system.m * omega ** 2 + 1j * system.c * omega)


def _unit_impulse_response(system: SDOFSystem, t: np.ndarray) -> np.ndarray:
    """Unit impulse response h(t) = exp(-ζωₙt)·sin(ωdt) / (m·ωd).

    Args:
        system: SDOFSystem instance.
        t: Time array, s (must be >= 0).

    Returns:
        Impulse response array, m/(N·s).
    """
    return (
        np.exp(-system.zeta * system.omega_n * t)
        * np.sin(system.omega_d * t)
        / (system.m * system.omega_d)
    )


# ---------------------------------------------------------------------------
# Issue 02 — Newmark-β average-acceleration integrator
# ---------------------------------------------------------------------------

def _newmark_beta_integrate(
    m: float,
    k: float,
    c: float,
    force: np.ndarray,
    dt: float,
    x0: float = 0.0,
    v0: float = 0.0,
    beta: float = 0.25,
    gamma: float = 0.5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Newmark average-acceleration time integrator (unconditionally stable).

    Args:
        m: Mass, kg.
        k: Stiffness, N/m.
        c: Damping coefficient, N·s/m.
        force: Applied force time series, N. Length n defines number of steps.
        dt: Time step, s.
        x0: Initial displacement, m.
        v0: Initial velocity, m/s.
        beta: Newmark beta parameter (0.25 = average acceleration).
        gamma: Newmark gamma parameter (0.5 = average acceleration).

    Returns:
        Tuple (x, v, a) — displacement, velocity, absolute acceleration arrays of length n.
    """
    n = len(force)
    x = np.zeros(n)
    v = np.zeros(n)
    a = np.zeros(n)

    x[0] = x0
    v[0] = v0
    a[0] = (force[0] - c * v0 - k * x0) / m

    # Effective stiffness: denominator of a_{n+1} solve
    k_eff = m + gamma * c * dt + beta * k * dt ** 2

    for i in range(n - 1):
        # Predictors
        x_pred = x[i] + dt * v[i] + dt ** 2 * (0.5 - beta) * a[i]
        v_pred = v[i] + dt * (1.0 - gamma) * a[i]

        # Solve for a_{n+1}: EOM gives m*a + c*v_pred + k*x_pred + (c*γ*dt + k*β*dt²)*a = F_{n+1}
        a[i + 1] = (force[i + 1] - c * v_pred - k * x_pred) / k_eff

        # Correctors
        x[i + 1] = x_pred + beta * dt ** 2 * a[i + 1]
        v[i + 1] = v_pred + gamma * dt * a[i + 1]

    return x, v, a


# ---------------------------------------------------------------------------
# Issue 03 — Case 3: Closed-form Duhamel integral solutions
# ---------------------------------------------------------------------------

def _step_displacement(system: SDOFSystem, t: np.ndarray, F0: float) -> np.ndarray:
    """Closed-form displacement for step force F0·u(t).

    x(t) = (F0/k)·[1 - exp(-ζωₙt)·(cos(ωdt) + (ζ/√(1-ζ²))·sin(ωdt))]
    """
    static = F0 / system.k
    damp_ratio = system.zeta / math.sqrt(1.0 - system.zeta ** 2)
    envelope = np.exp(-system.zeta * system.omega_n * t)
    return static * (1.0 - envelope * (np.cos(system.omega_d * t) + damp_ratio * np.sin(system.omega_d * t)))


def _rect_pulse_displacement(system: SDOFSystem, t: np.ndarray, F0: float, t_d: float) -> np.ndarray:
    """Closed-form displacement for rectangular pulse via superposition of two steps."""
    x = _step_displacement(system, t, F0)
    mask = t >= t_d
    if mask.any():
        x[mask] -= _step_displacement(system, t[mask] - t_d, F0)
    return x


def _triangular_pulse_displacement(system: SDOFSystem, t: np.ndarray, F0: float, t_d: float) -> np.ndarray:
    """Closed-form displacement for triangular blast pulse F(t) = F0·(1 - t/t_d) for t < t_d.

    Derived via Duhamel convolution: x(t) = (F0/t_d)*[(t_d - t)*I1(t) + I2(t)]
    where I1 and I2 are the convolution integrals of h(τ) and τ·h(τ). Chopra §4.3.
    """
    zeta = system.zeta
    omega_n = system.omega_n
    omega_d = system.omega_d
    k = system.k
    m = system.m
    damp_ratio = zeta / math.sqrt(1.0 - zeta ** 2) if zeta > 0 else 0.0

    def _phase1(tau: np.ndarray) -> np.ndarray:
        """Phase 1 closed-form for any time array — no branching, no recursion."""
        e = np.exp(-zeta * omega_n * tau)
        cos_t = np.cos(omega_d * tau)
        sin_t = np.sin(omega_d * tau)

        # I1(τ) = (1/k)*[1 - e*(cosωdτ + (ζ/√(1-ζ²))·sinωdτ)]
        I1 = (1.0 / k) * (1.0 - e * (cos_t + damp_ratio * sin_t))

        # I2(τ) derived by integration by parts of ∫τ·h(τ)dτ (Chopra §4.3):
        # numerator = -τ·e·(ωd·cos + ζωₙ·sin) + e·(-(2ζωd/ωₙ)·cos + (1-2ζ²)·sin) + 2ζωd/ωₙ
        num = (
            -tau * e * (omega_d * cos_t + zeta * omega_n * sin_t)
            + e * (-(2.0 * zeta * omega_d / omega_n) * cos_t + (1.0 - 2.0 * zeta ** 2) * sin_t)
            + 2.0 * zeta * omega_d / omega_n
        )
        I2 = num / (m * omega_d * omega_n ** 2)

        return (F0 / t_d) * ((t_d - tau) * I1 + I2)

    x = np.zeros_like(t, dtype=float)

    # Phase 1: 0 <= t < t_d
    mask1 = t < t_d
    if mask1.any():
        x[mask1] = _phase1(t[mask1])

    # Phase 2: t >= t_d — free vibration from (x_td, v_td)
    mask2 = t >= t_d
    if mask2.any():
        x_td = float(_phase1(np.array([t_d]))[0])
        eps = min(1e-6, t_d * 1e-4)
        # Centered difference gives O(eps²) error — phase1 is valid for any real τ
        v_td = (float(_phase1(np.array([t_d + eps]))[0]) - float(_phase1(np.array([t_d - eps]))[0])) / (2.0 * eps)

        tau2 = t[mask2] - t_d
        A = x_td
        B = (v_td + zeta * omega_n * x_td) / omega_d
        x[mask2] = np.exp(-zeta * omega_n * tau2) * (
            A * np.cos(omega_d * tau2) + B * np.sin(omega_d * tau2)
        )

    return x


def _differentiate(x: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
    """Compute velocity and acceleration from displacement via central differences.

    Args:
        x: Displacement array, m.
        dt: Time step, s.

    Returns:
        Tuple (v, a) — velocity (m/s) and acceleration (m/s²) arrays.
    """
    v = np.gradient(x, dt)
    a = np.gradient(v, dt)
    return v, a


def step_response(
    system: SDOFSystem,
    F0: float,
    t_end: float,
    dt: float,
    plot: bool = False,
) -> dict[str, np.ndarray]:
    """Exact closed-form response to a step force F0·u(t).

    Args:
        system: SDOFSystem instance.
        F0: Step force magnitude, N.
        t_end: Total analysis duration, s.
        dt: Time step, s.
        plot: If True, display a time-history plot.

    Returns:
        Dict with keys "t", "x", "v", "a" as numpy arrays.
    """
    t = np.arange(0.0, t_end, dt)
    x = _step_displacement(system, t, F0)
    v, a = _differentiate(x, dt)
    result = {"t": t, "x": x, "v": v, "a": a}
    if plot:
        from sdof_plots import _plot_case3_step
        _plot_case3_step(t, x, v, a, system, F0)
    return result


def rectangular_pulse_response(
    system: SDOFSystem,
    F0: float,
    t_d: float,
    t_end: float,
    dt: float,
    plot: bool = False,
) -> dict[str, np.ndarray]:
    """Exact closed-form response to a rectangular pulse of duration t_d.

    Args:
        system: SDOFSystem instance.
        F0: Pulse force magnitude, N.
        t_d: Pulse duration, s.
        t_end: Total analysis duration, s.
        dt: Time step, s.
        plot: If True, display a time-history plot.

    Returns:
        Dict with keys "t", "x", "v", "a" as numpy arrays.
    """
    t = np.arange(0.0, t_end, dt)
    x = _rect_pulse_displacement(system, t, F0, t_d)
    v, a = _differentiate(x, dt)
    result = {"t": t, "x": x, "v": v, "a": a}
    if plot:
        from sdof_plots import _plot_case3_rect
        _plot_case3_rect(t, x, v, a, system, F0, t_d)
    return result


def triangular_pulse_response(
    system: SDOFSystem,
    F0: float,
    t_d: float,
    t_end: float,
    dt: float,
    plot: bool = False,
) -> dict[str, np.ndarray]:
    """Exact closed-form response to a triangular (blast) pulse: F(t) = F0·(1 - t/t_d).

    Args:
        system: SDOFSystem instance.
        F0: Peak force at t=0, N.
        t_d: Duration of the triangular pulse (force is zero at t_d), s.
        t_end: Total analysis duration, s.
        dt: Time step, s.
        plot: If True, display a time-history plot.

    Returns:
        Dict with keys "t", "x", "v", "a" as numpy arrays.
    """
    t = np.arange(0.0, t_end, dt)
    x = _triangular_pulse_displacement(system, t, F0, t_d)
    v, a = _differentiate(x, dt)
    result = {"t": t, "x": x, "v": v, "a": a}
    if plot:
        from sdof_plots import _plot_case3_tri
        _plot_case3_tri(t, x, v, a, system, F0, t_d)
    return result


# ---------------------------------------------------------------------------
# Issue 04 — Case 1: Fourier series for periodic force
# ---------------------------------------------------------------------------

def _sawtooth_fourier_coefficients(
    F0: float,
    T_period: float,
    n_harmonics: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Fourier sine series coefficients for a sawtooth wave.

    Sawtooth definition: F(t) = F0·(1 - 2·frac(t/T)) with peak +F0.
    Coefficients: bₙ = -2·F0/(n·π)·(-1)ⁿ for n = 1 … n_harmonics.

    Args:
        F0: Amplitude, N.
        T_period: Period, s.
        n_harmonics: Number of harmonics to include.

    Returns:
        Tuple (omega_harmonics, b_coefficients) — angular frequencies (rad/s) and
        real Fourier sine amplitudes (N).
    """
    n = np.arange(1, n_harmonics + 1, dtype=float)
    omega0 = 2.0 * math.pi / T_period
    omega_harmonics = n * omega0
    b_n = -2.0 * F0 / (n * math.pi) * (-1.0) ** n
    return omega_harmonics, b_n


def _superpose_harmonics(
    system: SDOFSystem,
    t: np.ndarray,
    omega_harmonics: np.ndarray,
    b_coefficients: np.ndarray,
) -> np.ndarray:
    """Superpose steady-state harmonic responses.

    For each harmonic n: x_n(t) = bₙ · Re[H(ωₙ) · exp(j·ωₙ·t)]

    Args:
        system: SDOFSystem instance.
        t: Time array, s.
        omega_harmonics: Angular frequencies of harmonics, rad/s.
        b_coefficients: Fourier sine amplitudes, N.

    Returns:
        Total displacement array, m.
    """
    H = _compute_H(system, omega_harmonics)  # complex, shape (n_harmonics,)
    x = np.zeros(len(t))
    for bn, hn, wn in zip(b_coefficients, H, omega_harmonics):
        # Forcing is bₙ·sin(ωₙt) → complex amplitude = -j·bₙ (sine forcing convention)
        x += np.real(-1j * bn * hn * np.exp(1j * wn * t))
    return x


def periodic_sawtooth_response(
    system: SDOFSystem,
    F0: float,
    T_period: float,
    n_harmonics: int,
    t_end: float,
    dt: float,
    plot: bool = False,
) -> dict[str, np.ndarray]:
    """Steady-state response to a sawtooth periodic force via Fourier series.

    Args:
        system: SDOFSystem instance.
        F0: Sawtooth amplitude, N.
        T_period: Forcing period, s.
        n_harmonics: Number of Fourier harmonics to include.
        t_end: Total time, s.
        dt: Time step, s.
        plot: If True, display a time-history plot.

    Returns:
        Dict with keys "t", "F", "x", "v", "a".
    """
    t = np.arange(0.0, t_end, dt)
    omega_harmonics, b_n = _sawtooth_fourier_coefficients(F0, T_period, n_harmonics)
    x = _superpose_harmonics(system, t, omega_harmonics, b_n)
    v, a = _differentiate(x, dt)

    # Reconstruct the forcing function from harmonics
    F = np.zeros(len(t))
    omega0 = 2.0 * math.pi / T_period
    for i, bn in enumerate(b_n, start=1):
        F += bn * np.sin(i * omega0 * t)

    result = {"t": t, "F": F, "x": x, "v": v, "a": a}
    if plot:
        from sdof_plots import _plot_case1
        _plot_case1(t, F, x, system, n_harmonics)
    return result


# ---------------------------------------------------------------------------
# Issue 05 — Case 2: FFT for irregular periodic force
# ---------------------------------------------------------------------------

def _fft_extract_harmonics(
    t_input: np.ndarray,
    F_input: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract complex amplitudes from one period of force data via rfft.

    Args:
        t_input: Uniformly-spaced time points covering exactly one period, s.
        F_input: Force values at each time point, N.

    Returns:
        Tuple (omega_bins, C_bins) — positive angular frequencies (rad/s) and
        complex amplitudes (N), normalised by N.

    Raises:
        ValueError: If t_input is not uniformly spaced.
    """
    N = len(t_input)
    if N < 2:
        raise ValueError("t_input must have at least 2 points.")
    dt_vals = np.diff(t_input)
    if not np.allclose(dt_vals, dt_vals[0], rtol=1e-5):
        raise ValueError("t_input must be uniformly spaced.")

    dt = float(dt_vals[0])
    C = np.fft.rfft(F_input)  # raw DFT (no 1/N); standard LTI: X = H·F, x = irfft(X)
    freqs = np.fft.rfftfreq(N, d=dt)  # Hz
    omega_bins = 2.0 * math.pi * freqs
    return omega_bins, C


def _ifft_reconstruct(
    H_vals: np.ndarray,
    C_input: np.ndarray,
    N: int,
) -> np.ndarray:
    """Reconstruct displacement time series from frequency-domain response.

    Args:
        H_vals: Complex FRF values at each frequency bin, m/N.
        C_input: Complex force amplitudes at each frequency bin, N.
        N: Original number of time points (for irfft length).

    Returns:
        Displacement array over one period, m.
    """
    X_bins = H_vals * C_input
    return np.fft.irfft(X_bins, n=N)


def irregular_periodic_response(
    system: SDOFSystem,
    t_input: np.ndarray,
    F_input: np.ndarray,
    t_end: float,
    plot: bool = False,
) -> dict[str, np.ndarray]:
    """Steady-state response to an arbitrary periodic force supplied as a (t, F) table.

    The input must cover exactly one period with uniform spacing.

    Args:
        system: SDOFSystem instance.
        t_input: Uniformly-spaced time vector for one period, s.
        F_input: Force values at each t_input point, N.
        t_end: Total analysis duration, s.
        plot: If True, display a diagnostic + response plot.

    Returns:
        Dict with keys "t", "F_input", "F_reconstructed", "x", "v", "a".

    Raises:
        ValueError: If t_input is not uniformly spaced.
    """
    N = len(t_input)
    dt = float(t_input[1] - t_input[0])
    T_period = dt * N

    omega_bins, C_bins = _fft_extract_harmonics(t_input, F_input)
    H_vals = _compute_H(system, omega_bins)
    x_one_period = _ifft_reconstruct(H_vals, C_bins, N)

    # Reconstruct force for diagnostic (irfft is inverse of rfft)
    F_recon_one = np.fft.irfft(C_bins, n=N)

    # Tile to t_end
    n_total = int(math.ceil(t_end / dt))
    n_reps = math.ceil(n_total / N)
    x_tiled = np.tile(x_one_period, n_reps)[:n_total]
    F_tiled = np.tile(F_input, n_reps)[:n_total]
    F_recon_tiled = np.tile(F_recon_one, n_reps)[:n_total]
    t = np.arange(n_total) * dt

    v, a = _differentiate(x_tiled, dt)
    result = {
        "t": t,
        "F_input": F_tiled,
        "F_reconstructed": F_recon_tiled,
        "x": x_tiled,
        "v": v,
        "a": a,
    }
    if plot:
        from sdof_plots import _plot_case2
        _plot_case2(t, F_tiled, F_recon_tiled, x_tiled, system)
    return result


# ---------------------------------------------------------------------------
# Issue 06 — Case 4: Response spectrum
# ---------------------------------------------------------------------------

def _build_pulse_accel(
    excitation_type: str,
    a0: float,
    t_d: float,
    dt: float,
    t_end: float,
) -> np.ndarray:
    """Build base acceleration time series for pulse-type excitations.

    Args:
        excitation_type: One of "half_sine", "triangular", "rectangular".
        a0: Peak acceleration, m/s².
        t_d: Pulse duration, s.
        dt: Time step, s.
        t_end: Total duration, s.

    Returns:
        Acceleration array, m/s².
    """
    n = int(math.ceil(t_end / dt))
    t = np.arange(n) * dt
    ag = np.zeros(n)
    mask = t < t_d
    if excitation_type == "half_sine":
        ag[mask] = a0 * np.sin(math.pi * t[mask] / t_d)
    elif excitation_type == "triangular":
        ag[mask] = a0 * (1.0 - t[mask] / t_d)
    elif excitation_type == "rectangular":
        ag[mask] = a0
    return ag


def _sweep_spectrum(
    zeta: float,
    T_range: np.ndarray,
    ag: np.ndarray,
    dt: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute response spectrum by sweeping over natural periods.

    Uses Newmark-β integration for each period. Internally enforces dt <= T/20
    by linear interpolation upsampling when needed.

    Args:
        zeta: Damping ratio.
        T_range: Array of natural periods to evaluate, s.
        ag: Base acceleration time series, m/s².
        dt: Time step of ag, s.

    Returns:
        Tuple (Sd, Sv_pseudo, Sa_pseudo) — spectral displacement, pseudo-velocity,
        and pseudo-acceleration arrays.
    """
    Sd = np.zeros(len(T_range))
    t_ag = np.arange(len(ag)) * dt

    for i, T_i in enumerate(T_range):
        omega_n_i = 2.0 * math.pi / T_i
        m_i = 1.0
        k_i = omega_n_i ** 2
        c_i = 2.0 * zeta * omega_n_i * m_i

        # Ensure time step is fine enough for accuracy
        dt_req = T_i / 20.0
        if dt > dt_req:
            n_new = int(math.ceil((len(ag) - 1) * dt / dt_req))
            t_new = np.linspace(0.0, (len(ag) - 1) * dt, n_new)
            ag_i = np.interp(t_new, t_ag, ag)
            dt_i = float(t_new[1] - t_new[0]) if len(t_new) > 1 else dt
        else:
            ag_i = ag
            dt_i = dt

        # EOM in relative coordinates: force_eff = -m * ag
        force_eff = -m_i * ag_i
        x_rel, _, _ = _newmark_beta_integrate(m_i, k_i, c_i, force_eff, dt_i)
        Sd[i] = float(np.max(np.abs(x_rel)))

    Sv = (2.0 * math.pi / T_range) * Sd
    Sa = (2.0 * math.pi / T_range) ** 2 * Sd
    return Sd, Sv, Sa


def response_spectrum(
    system: SDOFSystem,
    excitation_type: str,
    ag_t: np.ndarray | None = None,
    ag_a: np.ndarray | None = None,
    a0: float | None = None,
    t_d: float | None = None,
    T_min: float = 0.01,
    T_max: float = 4.0,
    n_periods: int = 200,
    plot: bool = False,
) -> dict[str, np.ndarray]:
    """Compute displacement response spectrum and system time history.

    Args:
        system: SDOFSystem instance (used for the time history output and zeta).
        excitation_type: "base_accel" | "half_sine" | "triangular" | "rectangular".
        ag_t: Time vector for base acceleration record (base_accel only), s.
        ag_a: Base acceleration record (base_accel only), m/s².
        a0: Peak pulse acceleration (pulse types only), m/s².
        t_d: Pulse duration (pulse types only), s.
        T_min: Minimum period for spectrum sweep, s.
        T_max: Maximum period for spectrum sweep, s.
        n_periods: Number of periods in the sweep (log-spaced).
        plot: If True, display a 2×2 spectrum + time history plot.

    Returns:
        Dict with keys:
            "T_range", "Sd", "Sv", "Sa" — spectrum arrays
            "t_hist", "x_hist", "a_hist" — time history for system.T_n

    Raises:
        ValueError: If excitation_type is unrecognised or required arguments are missing.
    """
    valid_types = {"base_accel", "half_sine", "triangular", "rectangular"}
    if excitation_type not in valid_types:
        raise ValueError(f"excitation_type must be one of {valid_types}, got {excitation_type!r}")

    # Build ground acceleration array
    if excitation_type == "base_accel":
        if ag_t is None or ag_a is None:
            raise ValueError("ag_t and ag_a required for excitation_type='base_accel'")
        ag = ag_a
        dt = float(ag_t[1] - ag_t[0])
    else:
        if a0 is None or t_d is None:
            raise ValueError("a0 and t_d required for pulse excitation types")
        dt = min(T_min / 20.0, t_d / 50.0)
        t_end = max(T_max * 10.0, t_d * 10.0)
        ag = _build_pulse_accel(excitation_type, a0, t_d, dt, t_end)

    T_range = np.logspace(math.log10(T_min), math.log10(T_max), n_periods)
    Sd, Sv, Sa = _sweep_spectrum(system.zeta, T_range, ag, dt)

    # Time history for the user's specific system
    omega_n_sys = system.omega_n
    k_sys = system.k
    c_sys = system.c
    m_sys = system.m
    force_sys = -m_sys * ag
    x_hist, v_hist, a_hist = _newmark_beta_integrate(m_sys, k_sys, c_sys, force_sys, dt)
    t_hist = np.arange(len(ag)) * dt

    result: dict[str, np.ndarray] = {
        "T_range": T_range,
        "Sd": Sd,
        "Sv": Sv,
        "Sa": Sa,
        "t_hist": t_hist,
        "x_hist": x_hist,
        "a_hist": a_hist,
    }
    if plot:
        from sdof_plots import _plot_case4
        _plot_case4(T_range, Sd, Sv, Sa, t_hist, x_hist, system, excitation_type)
    return result


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import numpy as np

    sys = make_system(m=1.0, k=100.0, zeta=0.05)
    print(f"System: omega_n={sys.omega_n:.3f} rad/s, T_n={sys.T_n:.4f} s")

    # Case 1 — sawtooth
    r1 = periodic_sawtooth_response(sys, F0=100.0, T_period=1.0, n_harmonics=20,
                                    t_end=5.0, dt=0.001, plot=False)
    print(f"Case 1: peak x = {float(np.max(np.abs(r1['x']))):.4f} m")

    # Case 3 — step
    r3 = step_response(sys, F0=50.0, t_end=3.0, dt=0.001, plot=False)
    print(f"Case 3 step: peak x = {float(np.max(r3['x'])):.4f} m (static = {50/100:.4f} m)")

    # Case 4 — response spectrum
    r4 = response_spectrum(sys, excitation_type="rectangular", a0=9.81, t_d=0.1,
                           T_min=0.05, T_max=2.0, n_periods=100, plot=False)
    print(f"Case 4: Sd at T_n = {float(np.interp(sys.T_n, r4['T_range'], r4['Sd'])):.4f} m")
