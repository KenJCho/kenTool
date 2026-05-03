## Title
SDOF: Update CLAUDE.md with new module commands and architecture

## Type
AFK

## Blocked by
- Blocked by issue 07 (all implementation complete)

## User stories covered
18 (developer experience)

---

## What to build

Update `CLAUDE.md` to document the new `sdof_analysis.py` module: how to run it, how to run its tests, and a brief architectural description that lets a future Claude instance understand the SDOF module as quickly as it understands the existing unit conversion module.

## Acceptance criteria

- [ ] `CLAUDE.md` Commands section includes:
  - `python sdof_analysis.py` — runs built-in example for each case
  - `python test_sdof_analysis.py` — runs the SDOF test suite
  - `pytest test_sdof_analysis.py::test_step_response_daf -v` — example single-test invocation
  - `pip install -r requirements.txt` — install numpy + matplotlib
- [ ] Architecture section describes `sdof_analysis.py` public API at the same level of detail as the existing `unit_conversion.py` entry
- [ ] `sdof_plots.py` is noted as the rendering companion, called only via `plot=True` — not a standalone module
- [ ] No information duplicated from the existing CLAUDE.md content
