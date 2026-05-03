## Title
SDOF: Plotting module (sdof_plots.py) — all four cases

## Type
AFK

## Blocked by
- Blocked by issue 03 (Case 3 Duhamel)
- Blocked by issue 04 (Case 1 Fourier)
- Blocked by issue 05 (Case 2 FFT)
- Blocked by issue 06 (Case 4 spectrum)

## User stories covered
3, 5, 7, 8, 9, 11, 12, 13, 14, 15, 16

---

## What to build

Create `sdof_plots.py` containing one private rendering function per analysis case. Wire each function into the corresponding analysis function in `sdof_analysis.py` via the `if plot:` guard that is already in the function signatures.

No public API. No tests (output is visual). Each function receives pre-computed numpy arrays and system metadata; it does not call any analysis functions.

**Plot layouts:**

| Function | Panels |
|---|---|
| `_plot_case1(t, F, x, system, n_harmonics)` | 2-panel: forcing waveform (top), displacement response (bottom) |
| `_plot_case2(t, F_input, F_reconstructed, x, system)` | 3-panel: original force (top), FFT-reconstructed force (middle), displacement (bottom) |
| `_plot_case3_step(t, x, v, a, system, F0)` | 3-panel: x(t) with F0/k dashed, v(t), a(t) |
| `_plot_case3_rect(t, x, v, a, system, F0, t_d)` | Same as step + vertical dashed line at t=t_d |
| `_plot_case3_tri(t, x, v, a, system, F0, t_d)` | Same as rect |
| `_plot_case4(T_range, Sd, Sv, Sa, t_hist, x_hist, system, excitation_type)` | 2×2: Sd, Sv, Sa spectra + time history; system Tₙ marked on each spectrum axis |

## Acceptance criteria

- [ ] `sdof_plots.py` created; imports only `matplotlib.pyplot`; no numpy imports (arrays passed in)
- [ ] Each private plot function listed above is implemented
- [ ] Each analysis function in `sdof_analysis.py` calls its corresponding plot function when `plot=True`
- [ ] All axes labelled with quantity name and SI units (e.g. "Displacement x [m]", "Period T [s]")
- [ ] Grid lines enabled on all subplots
- [ ] Figure titles include system parameters (m, k, ζ, Tₙ)
- [ ] Static deflection dashed line `F0/k` on Case 3 displacement panels
- [ ] System Tₙ marked as vertical dashed line on all three spectrum subplots in Case 4
- [ ] `plt.show()` called at the end of each function; no figure handles returned
