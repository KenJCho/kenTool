"""Tests for sdof_analysis.py — plain-assert style matching test_unit_conversion.py."""

from __future__ import annotations

import math
import numpy as np

from sdof_analysis import (
    SDOFSystem,
    make_system,
    step_response,
    rectangular_pulse_response,
    triangular_pulse_response,
    periodic_sawtooth_response,
    irregular_periodic_response,
    response_spectrum,
)


def approx_equal(a: float, b: float, tol: float = 1e-8) -> bool:
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# Issue 01 — SDOFSystem construction
# ---------------------------------------------------------------------------

def test_make_system_derived_quantities() -> None:
    sys = make_system(m=1.0, k=100.0, zeta=0.05)
    assert approx_equal(sys.omega_n, 10.0)
    assert approx_equal(sys.omega_d, 10.0 * math.sqrt(1.0 - 0.05**2))
    assert approx_equal(sys.c, 2.0 * 1.0 * 10.0 * 0.05)
    assert approx_equal(sys.T_n, 2.0 * math.pi / 10.0)


def test_make_system_invalid_inputs() -> None:
    for bad_m in (0.0, -1.0):
        try:
            make_system(m=bad_m, k=100.0, zeta=0.05)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for m={bad_m}")

    for bad_k in (0.0, -1.0):
        try:
            make_system(m=1.0, k=bad_k, zeta=0.05)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for k={bad_k}")

    for bad_z in (1.0, 1.5):
        try:
            make_system(m=1.0, k=100.0, zeta=bad_z)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for zeta={bad_z}")


# ---------------------------------------------------------------------------
# Issue 02 — Newmark-β free-vibration validation
# ---------------------------------------------------------------------------

def test_newmark_free_vibration() -> None:
    """x₀≠0, zero force → Newmark matches analytical free vibration."""
    from sdof_analysis import _newmark_beta_integrate

    sys = make_system(m=1.0, k=100.0, zeta=0.05)
    dt = sys.T_n / 100
    t_end = 5.0 * sys.T_n
    n = int(t_end / dt)
    force = np.zeros(n)
    x0, v0 = 0.01, 0.0

    x, v, a = _newmark_beta_integrate(sys.m, sys.k, sys.c, force, dt, x0=x0, v0=v0)

    t = np.arange(n) * dt
    x_analytical = (
        x0 * np.exp(-sys.zeta * sys.omega_n * t)
        * (
            np.cos(sys.omega_d * t)
            + (sys.zeta / math.sqrt(1.0 - sys.zeta**2)) * np.sin(sys.omega_d * t)
        )
    )
    max_err = float(np.max(np.abs(x - x_analytical)))
    assert max_err < 1e-4, f"Newmark free-vib error {max_err:.2e} exceeds 1e-4"


# ---------------------------------------------------------------------------
# Issue 03 — Case 3: Closed-form Duhamel
# ---------------------------------------------------------------------------

def test_step_response_static_limit() -> None:
    """High-damping step response settles to F0/k."""
    sys = make_system(m=1.0, k=100.0, zeta=0.99)
    F0 = 50.0
    res = step_response(sys, F0=F0, t_end=20.0, dt=0.001)
    x_final = float(res["x"][-1])
    assert approx_equal(x_final, F0 / sys.k, tol=1e-3), f"Static limit failed: {x_final} vs {F0/sys.k}"


def test_step_response_daf() -> None:
    """Near-undamped step: peak displacement ≈ 2·F0/k (exact DAF = 1 + exp(-ζπ/√(1-ζ²)))."""
    sys = make_system(m=1.0, k=100.0, zeta=0.001)
    F0 = 50.0
    res = step_response(sys, F0=F0, t_end=5.0, dt=0.0005)
    x_max = float(np.max(res["x"]))
    expected = 2.0 * F0 / sys.k
    assert abs(x_max - expected) / expected < 0.01, f"DAF test failed: x_max={x_max:.4f}, expected~{expected:.4f}"


def test_rectangular_pulse_short() -> None:
    """Short pulse (t_d << T_n, ζ≈0) → x_max ≈ F0·t_d / (m·ωd) within 5%."""
    sys = make_system(m=1.0, k=100.0, zeta=0.001)  # near-undamped so envelope ≈ 1
    F0 = 100.0
    t_d = sys.T_n / 20.0
    res = rectangular_pulse_response(sys, F0=F0, t_d=t_d, t_end=3.0 * sys.T_n, dt=t_d / 50)
    x_max = float(np.max(np.abs(res["x"])))
    expected = F0 * t_d / (sys.m * sys.omega_d)
    assert abs(x_max - expected) / expected < 0.05, f"Short pulse: x_max={x_max:.5f}, expected≈{expected:.5f}"


def test_rectangular_pulse_long() -> None:
    """Long pulse (t_d >> T_n, ζ≈0) → x_max ≈ 2·F0/k within 1%."""
    sys = make_system(m=1.0, k=100.0, zeta=0.001)
    F0 = 50.0
    t_d = 20.0 * sys.T_n
    res = rectangular_pulse_response(sys, F0=F0, t_d=t_d, t_end=t_d + 2.0 * sys.T_n, dt=sys.T_n / 100)
    x_max = float(np.max(res["x"]))
    expected = 2.0 * F0 / sys.k
    assert abs(x_max - expected) / expected < 0.01, f"Long pulse: x_max={x_max:.4f}, expected~{expected:.4f}"


def test_triangular_pulse_free_vibration() -> None:
    """After t_d, displacement matches analytical free-vibration from (x(t_d), v(t_d))."""
    sys = make_system(m=1.0, k=100.0, zeta=0.05)
    F0 = 100.0
    t_d = sys.T_n * 0.5
    dt = sys.T_n / 500
    t_end = t_d + 3.0 * sys.T_n
    res = triangular_pulse_response(sys, F0=F0, t_d=t_d, t_end=t_end, dt=dt)

    t = res["t"]
    x = res["x"]
    v = res["v"]

    # Find index just after t_d
    i_td = int(round(t_d / dt))
    x0 = float(x[i_td])
    v0 = float(v[i_td])

    # Analytical free vibration after t_d
    tau = t[i_td:] - t[i_td]
    A = x0
    B = (v0 + sys.zeta * sys.omega_n * x0) / sys.omega_d
    x_free = np.exp(-sys.zeta * sys.omega_n * tau) * (A * np.cos(sys.omega_d * tau) + B * np.sin(sys.omega_d * tau))

    max_err = float(np.max(np.abs(x[i_td:] - x_free)))
    assert max_err < 1e-4, f"Free-vib after t_d error {max_err:.2e}"


# ---------------------------------------------------------------------------
# Issue 04 — Case 1: Fourier series
# ---------------------------------------------------------------------------

def test_sawtooth_fundamental_amplitude() -> None:
    """n_harmonics=1: peak x matches |b1|·|H(ω0)| analytically."""
    from sdof_analysis import _compute_H

    sys = make_system(m=2.0, k=200.0, zeta=0.05)
    F0 = 100.0
    T_period = 0.5
    omega0 = 2.0 * math.pi / T_period
    b1 = -2.0 * F0 / math.pi * (-1.0) ** 1

    H_val = _compute_H(sys, np.array([omega0]))[0]
    expected_amp = abs(b1) * abs(H_val)

    res = periodic_sawtooth_response(sys, F0=F0, T_period=T_period, n_harmonics=1,
                                     t_end=10.0 * T_period, dt=T_period / 500)
    x_max = float(np.max(np.abs(res["x"][int(len(res["x"]) * 0.5):])))  # steady-state half
    assert abs(x_max - expected_amp) / expected_amp < 1e-4, \
        f"Fundamental amplitude: got {x_max:.6f}, expected {expected_amp:.6f}"


def test_sawtooth_convergence() -> None:
    """RMS error decreases as n_harmonics increases: 5 → 20 → 50."""
    sys = make_system(m=1.0, k=400.0, zeta=0.1)
    F0 = 50.0
    T_period = 0.3
    t_end = 20.0 * T_period
    dt = T_period / 500

    def rms_diff(n1: int, n2: int) -> float:
        r1 = periodic_sawtooth_response(sys, F0=F0, T_period=T_period, n_harmonics=n1,
                                        t_end=t_end, dt=dt)
        r2 = periodic_sawtooth_response(sys, F0=F0, T_period=T_period, n_harmonics=n2,
                                        t_end=t_end, dt=dt)
        return float(np.sqrt(np.mean((r1["x"] - r2["x"]) ** 2)))

    err_5_20 = rms_diff(5, 50)
    err_20_50 = rms_diff(20, 100)
    assert err_5_20 > err_20_50, "Convergence failed: error should decrease with more harmonics"


# ---------------------------------------------------------------------------
# Issue 05 — Case 2: FFT roundtrip
# ---------------------------------------------------------------------------

def test_fft_case2_roundtrip() -> None:
    """Pure sine input table → FFT path ≈ Case 1 with n_harmonics=1."""
    sys = make_system(m=2.0, k=200.0, zeta=0.05)
    F0 = 100.0
    T_period = 0.5
    omega0 = 2.0 * math.pi / T_period

    # Build one period of a pure sine (= first harmonic of sawtooth with b1 sign)
    N = 500
    t_input = np.linspace(0, T_period, N, endpoint=False)
    b1 = -2.0 * F0 / math.pi * (-1.0) ** 1
    F_input = b1 * np.sin(omega0 * t_input)

    t_end = 10.0 * T_period
    res_fft = irregular_periodic_response(sys, t_input=t_input, F_input=F_input, t_end=t_end)
    res_fourier = periodic_sawtooth_response(sys, F0=F0, T_period=T_period, n_harmonics=1,
                                             t_end=t_end, dt=T_period / N)

    # Compare steady-state (second half)
    half = len(res_fft["x"]) // 2
    rms_err = float(np.sqrt(np.mean((res_fft["x"][half:] - res_fourier["x"][half:half + len(res_fft["x"][half:])]) ** 2)))
    x_scale = float(np.sqrt(np.mean(res_fourier["x"][half:] ** 2))) + 1e-12
    assert rms_err / x_scale < 0.02, f"FFT roundtrip RMS error {rms_err/x_scale:.4f} > 2%"


# ---------------------------------------------------------------------------
# Issue 06 — Case 4: Response spectrum
# ---------------------------------------------------------------------------

def test_spectrum_pseudo_relations() -> None:
    """Sv = ωₙ·Sd and Sa = ωₙ²·Sd at every sweep point."""
    sys = make_system(m=1.0, k=100.0, zeta=0.05)
    res = response_spectrum(sys, excitation_type="rectangular", a0=9.81, t_d=0.1,
                            T_min=0.05, T_max=2.0, n_periods=50)
    T_range = res["T_range"]
    omega_n_arr = 2.0 * math.pi / T_range
    sv_expected = omega_n_arr * res["Sd"]
    sa_expected = omega_n_arr ** 2 * res["Sd"]
    assert np.allclose(res["Sv"], sv_expected, rtol=1e-6), "Sv ≠ ωₙ·Sd"
    assert np.allclose(res["Sa"], sa_expected, rtol=1e-6), "Sa ≠ ωₙ²·Sd"


def test_spectrum_time_history_returned() -> None:
    """response_spectrum returns t_hist, x_hist, a_hist for the system's own T_n."""
    sys = make_system(m=1.0, k=100.0, zeta=0.05)
    res = response_spectrum(sys, excitation_type="half_sine", a0=9.81, t_d=0.05,
                            T_min=0.05, T_max=2.0, n_periods=30)
    assert "t_hist" in res and len(res["t_hist"]) > 0
    assert "x_hist" in res and len(res["x_hist"]) > 0
    assert "a_hist" in res and len(res["a_hist"]) > 0


if __name__ == "__main__":
    test_make_system_derived_quantities()
    test_make_system_invalid_inputs()
    test_newmark_free_vibration()
    test_step_response_static_limit()
    test_step_response_daf()
    test_rectangular_pulse_short()
    test_rectangular_pulse_long()
    test_triangular_pulse_free_vibration()
    test_sawtooth_fundamental_amplitude()
    test_sawtooth_convergence()
    test_fft_case2_roundtrip()
    test_spectrum_pseudo_relations()
    test_spectrum_time_history_returned()
    print("All tests passed.")
