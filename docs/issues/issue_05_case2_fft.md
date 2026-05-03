## Title
SDOF Case 2: FFT response to arbitrary periodic force from input table

## Type
AFK

## Blocked by
- Blocked by issue 01 (SDOFSystem + core helpers)
- Blocked by issue 04 (Case 1 Fourier, needed for roundtrip validation)

## User stories covered
5, 6, 16, 17

---

## What to build

Implement `irregular_periodic_response` — the public function for Case 2 — plus its private FFT helpers. The function accepts one complete period of uniformly-sampled `(t_input, F_input)` data, extracts complex amplitudes via `numpy.fft.rfft`, multiplies each frequency bin by `H(ωₖ)`, and reconstructs `x(t)` via `irfft`. The result is tiled to fill `t_end`.

Pipeline:
```
C = rfft(F_input) / N                  # complex amplitudes, positive freqs
omega_bins = 2π · rfftfreq(N, d=dt)   # rad/s
X_bins = C · H(omega_bins)             # response in frequency domain
x(t) = irfft(X_bins, n=N)             # one period of displacement
```

## Acceptance criteria

- [ ] `irregular_periodic_response(system, t_input, F_input, t_end, plot=False) -> dict` implemented; returns `"t"`, `"F_input"`, `"F_reconstructed"`, `"x"`, `"v"`, `"a"`
- [ ] `_fft_extract_harmonics(t_input, F_input)` returns `(omega_bins, C_bins)` via `rfft`; normalises by `N`
- [ ] `_ifft_reconstruct(H_vals, C_input, N)` returns displacement array via `irfft`
- [ ] `"F_reconstructed"` key holds the IFFT-back-to-time version of the input force (for plot verification fidelity check)
- [ ] Input validation: raises `ValueError` if `t_input` is not uniformly spaced
- [ ] `test_fft_case2_roundtrip`: pure sine-wave input table produces displacement that matches the equivalent `periodic_sawtooth_response` called with `n_harmonics=1` to within `1e-4`
- [ ] Result is tiled correctly when `t_end` exceeds one input period
