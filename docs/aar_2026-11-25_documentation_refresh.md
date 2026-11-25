# Documentation refresh AAR

November 25, 2026. Baseline 8f4c98832505450d71cb760645e57fd2affb2a22 (merged #386). Documentation-only change.

## Audit and changes

The root README was mostly a rule summary and did not explain how to start the current game or find the analytics portal. Quickstart and GUI guides pointed at removed desktop launchers. Feature and architecture guides described retired React/Streamlit workflows, the disconnected recruiting site or an old fast simulator. Analytics and coaching references predated the current engine and career systems. Writer references reversed Delta cost and confused the bonus recipient, start and cancellation rules. The catalog inventory listed only nine defensive packages.

Rebuilt the current guides and linked them in docs/README.md. Retained the existing tested playing-rule sections and penalty table. Updated the live school list, package inventory from actual packages.json, coaching pathways, current rating scale, high-school feeder, browser routes, storage and setup, analytics estimands and support, scoring and defender-credit accounting from #386. Corrected writer-facing terminology and distinguished observed statistics from research models. Updated the consolidated queue against PR and CI evidence. Marked superseded design/specification documents historical, leaving dated AAR results intact.

## Verification

Compared against live repository source and current merged PRs. README penalty rows are unchanged (11 rows matched by the test's pattern); the original rulebook's generated penalty catalog and rule values are preserved. No gameplay, interface, or model code changed. Local full repository tests were not run in this environment. The package inventory is a catalog snapshot; use python -m engine.playbook_catalog for generated computed family strengths. Current deployment and national analytics acceptance are not verified. Existing interface regression failures remain recorded in the queue; documentation does not fix them.

The index is the entry point for future documentation maintenance. Do not retrospectively rewrite historical experiment results to describe current behavior.
