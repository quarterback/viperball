# Playbook Cookbook implementation AAR

## What shipped

The stats site now has a Playbook Cookbook at /stats/playbooks. A player can start from an offensive or defensive school, assemble up to four compatible packages, choose a preferred package, and save the result. The editor shows the source school, situation, roster requirements, and tradeoff. Books can be downloaded as versioned JSON and imported into a draft.

College and Dynasty setup accept separate custom books. Each team keeps the version chosen at setup. The coordinator uses the normal situational and roster checks and gives the preferred package first choice when it is eligible and a package is called. The base school supplies the ordinary calls. The box score shows eligible, selected, and executed package counts and links to the relevant snaps.

## Stack and decisions

FastAPI and Jinja serve the editor, plain JavaScript connects the controls to the field, and SQLite stores the library. Phaser 3.90.0 renders the animated field. The cloud browser rejected the hosted script certificate, so the app serves the verified npm release locally with its upstream MIT license. The static field works when the animation library is unavailable.

The field illustrates the intent of an existing package. This release supports assembling books and selecting an eligible preference. New route behavior, new defensive effects, and linked calls across snaps would need additional engine support.

## Verification

The full tests directory finished with 337 passing tests. A scheduled week exercised both custom books and showed their calls on the box score. Tests also verified the college archive snapshot, dynasty creation and reload, the assignment on the new dynasty season, and retention through a coordinator change.

Chromium exercised the Phaser animation, book save and export, import review, both team setup selectors, file import at mobile width, and the static fallback. The first simulated week test used a narrow late clock trigger that could produce zero calls. It now uses a roster with known fit and packages with broader opportunities so the test checks the complete flow reliably.
