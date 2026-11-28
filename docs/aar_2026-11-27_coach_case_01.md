# COACH-CASE-01 after action record

November 27, 2026. Audited the eight casebook decisions and ten case scenarios against `main` at `ad32c9e`. Checked the coaching specification, development plans, existing selectors and tests, merged Cookbook #396, closed #397 and the local Cookbook branch at `6952d66` with its working changes. The public pull request list showed zero open pull requests at review. The audit includes one policy contract and an ownership map for the implementation packages. [Casebook](https://github.com/quarterback/viperball/blob/ad32c9e/docs/football_coaching_casebook_2026-11-27.md) · [Audit](COACH_CASE_01_POLICY_AUDIT.md) · [Pull request list](https://github.com/quarterback/viperball/pulls)

## Verification

Exported `ad32c9e` with `git archive` to a temporary directory and ran these tests with the existing environment's Python. The first command passed 128 tests. The second passed 12.

```sh
/workspace/viperball/venv/bin/python -m pytest -q \
  tests/test_coach_tactics.py tests/test_coach_tactics_gameplay.py \
  tests/test_coach_tactics_defense.py tests/test_coaching_identity.py \
  tests/test_defensive_package_preferences.py tests/test_defensive_tactics.py \
  tests/test_offensive_package_execution.py tests/test_playbook_catalog.py \
  tests/test_team_installation.py tests/test_custom_playbooks.py \
  tests/test_coach_learning.py tests/test_coach_career.py \
  tests/test_coaching_career_continuity.py
/workspace/viperball/venv/bin/python -m pytest -q \
  tests/test_snap_participation.py tests/test_box_score_ledger.py
```

The local Cookbook and offensive package checks passed 31 tests. The web integration tests emitted FastAPI, Starlette and AnyIO deprecation warnings.

```sh
venv/bin/python -m pytest -q tests/test_offensive_concepts.py \
  tests/test_offensive_package_execution.py tests/test_custom_playbooks.py \
  tests/test_team_installation.py
```

Existing test seeds were used as written. This work produced documentation only. The test counts cover current behavior, and the proposed scenario comparisons and multi season calibration remain acceptance work for the implementation packages. CASE-02 should establish the shared practice allocation and installation format before later packages consume it.
