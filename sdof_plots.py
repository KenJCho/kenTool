"""Plotting utilities for sdof_analysis.py — one private function per analysis case.

Not part of the public API. Called only from sdof_analysis.py via plot=True guards.
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np


def _system_label(system: object) -> str:
    return (
        f"m={system.m:.3g} kg, k={system.k:.3g} N/m, "  # type: ignore[attr-defined]
        f"ζ={system.zeta:.4g}, Tₙ={system.T_n:.4g} s"   # type: ignore[attr-defined]
    )


def _plot_case1(
    t: np.ndarray,
    F: np.ndarray,
    x: np.ndarray,
    system: object,
    n_harmonics: int,
) -> None:
    """2-panel plot: sawtooth forcing (top) and displacement response (bottom)."""
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    fig.suptitle(f"Case 1 — Sawtooth Fourier Response ({n_harmonics} harmonics)\n{_system_label(system)}")

    axes[0].plot(t, F, color="steelblue")
    axes[0].set_ylabel("Force F [N]")
    axes[0].grid(True)

    axes[1].plot(t, x, color="darkorange")
    axes[1].set_ylabel("Displacement x [m]")
    axes[1].set_xlabel("Time t [s]")
    axes[1].grid(True)

    plt.tight_layout()
    plt.show()


def _plot_case2(
    t: np.ndarray,
    F_input: np.ndarray,
    F_reconstructed: np.ndarray,
    x: np.ndarray,
    system: object,
) -> None:
    """3-panel plot: original force, FFT-reconstructed force, displacement."""
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    fig.suptitle(f"Case 2 — Irregular Periodic FFT Response\n{_system_label(system)}")

    axes[0].plot(t, F_input, color="steelblue", label="Input table")
    axes[0].set_ylabel("Force F [N]")
    axes[0].legend()
    axes[0].grid(True)

    axes[1].plot(t, F_reconstructed, color="mediumseagreen", linestyle="--", label="FFT reconstructed")
    axes[1].set_ylabel("Force F [N]")
    axes[1].legend()
    axes[1].grid(True)

    axes[2].plot(t, x, color="darkorange")
    axes[2].set_ylabel("Displacement x [m]")
    axes[2].set_xlabel("Time t [s]")
    axes[2].grid(True)

    plt.tight_layout()
    plt.show()


def _plot_case3_step(
    t: np.ndarray,
    x: np.ndarray,
    v: np.ndarray,
    a: np.ndarray,
    system: object,
    F0: float,
) -> None:
    """3-panel time-history: displacement (with static line), velocity, acceleration."""
    static = F0 / system.k  # type: ignore[attr-defined]
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    fig.suptitle(f"Case 3a — Step Response\n{_system_label(system)}")

    axes[0].plot(t, x, color="darkorange", label="x(t)")
    axes[0].axhline(static, color="gray", linestyle="--", label=f"Static = {static:.4g} m")
    axes[0].set_ylabel("Displacement x [m]")
    axes[0].legend()
    axes[0].grid(True)

    axes[1].plot(t, v, color="steelblue")
    axes[1].set_ylabel("Velocity v [m/s]")
    axes[1].grid(True)

    axes[2].plot(t, a, color="crimson")
    axes[2].set_ylabel("Acceleration a [m/s²]")
    axes[2].set_xlabel("Time t [s]")
    axes[2].grid(True)

    plt.tight_layout()
    plt.show()


def _plot_case3_rect(
    t: np.ndarray,
    x: np.ndarray,
    v: np.ndarray,
    a: np.ndarray,
    system: object,
    F0: float,
    t_d: float,
) -> None:
    """3-panel time-history with pulse-end marker at t_d."""
    static = F0 / system.k  # type: ignore[attr-defined]
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    fig.suptitle(f"Case 3b — Rectangular Pulse Response (t_d={t_d:.4g} s)\n{_system_label(system)}")

    for ax in axes:
        ax.axvline(t_d, color="gray", linestyle=":", linewidth=1.0, label="_nolegend_")

    axes[0].plot(t, x, color="darkorange")
    axes[0].axhline(static, color="gray", linestyle="--", label=f"Static = {static:.4g} m")
    axes[0].set_ylabel("Displacement x [m]")
    axes[0].legend()
    axes[0].grid(True)

    axes[1].plot(t, v, color="steelblue")
    axes[1].set_ylabel("Velocity v [m/s]")
    axes[1].grid(True)

    axes[2].plot(t, a, color="crimson")
    axes[2].set_ylabel("Acceleration a [m/s²]")
    axes[2].set_xlabel("Time t [s]")
    axes[2].grid(True)

    plt.tight_layout()
    plt.show()


def _plot_case3_tri(
    t: np.ndarray,
    x: np.ndarray,
    v: np.ndarray,
    a: np.ndarray,
    system: object,
    F0: float,
    t_d: float,
) -> None:
    """3-panel time-history for triangular blast pulse with t_d marker."""
    static = F0 / system.k  # type: ignore[attr-defined]
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    fig.suptitle(f"Case 3c — Triangular Blast Pulse Response (t_d={t_d:.4g} s)\n{_system_label(system)}")

    for ax in axes:
        ax.axvline(t_d, color="gray", linestyle=":", linewidth=1.0)

    axes[0].plot(t, x, color="darkorange")
    axes[0].axhline(static, color="gray", linestyle="--", label=f"Static = {static:.4g} m")
    axes[0].set_ylabel("Displacement x [m]")
    axes[0].legend()
    axes[0].grid(True)

    axes[1].plot(t, v, color="steelblue")
    axes[1].set_ylabel("Velocity v [m/s]")
    axes[1].grid(True)

    axes[2].plot(t, a, color="crimson")
    axes[2].set_ylabel("Acceleration a [m/s²]")
    axes[2].set_xlabel("Time t [s]")
    axes[2].grid(True)

    plt.tight_layout()
    plt.show()


def _plot_case4(
    T_range: np.ndarray,
    Sd: np.ndarray,
    Sv: np.ndarray,
    Sa: np.ndarray,
    t_hist: np.ndarray,
    x_hist: np.ndarray,
    system: object,
    excitation_type: str,
) -> None:
    """2×2 figure: Sd, Sv, Sa spectra + system time history. System Tₙ marked on each spectrum."""
    T_n = system.T_n  # type: ignore[attr-defined]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(f"Case 4 — Response Spectrum [{excitation_type}]\n{_system_label(system)}")

    for ax, y, ylabel in zip(
        [axes[0, 0], axes[0, 1], axes[1, 0]],
        [Sd, Sv, Sa],
        ["Sd [m]", "Sv (pseudo) [m/s]", "Sa (pseudo) [m/s²]"],
    ):
        ax.plot(T_range, y, color="steelblue")
        ax.axvline(T_n, color="darkorange", linestyle="--", label=f"Tₙ = {T_n:.4g} s")
        ax.set_xlabel("Period T [s]")
        ax.set_ylabel(ylabel)
        ax.legend(fontsize=8)
        ax.grid(True)

    axes[1, 1].plot(t_hist, x_hist, color="darkorange")
    axes[1, 1].set_xlabel("Time t [s]")
    axes[1, 1].set_ylabel("Relative displacement x [m]")
    axes[1, 1].set_title(f"Time history at Tₙ = {T_n:.4g} s")
    axes[1, 1].grid(True)

    plt.tight_layout()
    plt.show()
