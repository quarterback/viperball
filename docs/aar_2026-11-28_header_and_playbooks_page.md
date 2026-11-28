# AAR: header and Playbooks page after the playbook merges

November 28, 2026

## What was asked

Ron said the latest agent's merges were good but broke the site's design and looked like
the old design was back. He asked me to rebase to main, find what broke, and fix it.

## What broke

1. The merge added Playbooks to the main nav and exempted it from the rule that hides nav
   labels between tablet and wide desktop. The nav no longer fit on one line at 1280 pixels,
   so the header grew to three rows with My Team and the Theme button on their own lines.
2. The Playbooks page had no breadcrumb, no tool tabs and its own heading style, so it did
   not match the rest of the site.
3. The book name field had no input type, so the site's input styling skipped it and it
   rendered as a bare browser box.
4. Game Sim carried a loose "Playbook Cookbook" link under its subtitle, outside the tabs.

## What changed

1. Playbooks left the main nav. It is now a tab under Tools, next to Game Sim, Compare Runs
   and Export, and the Tools nav item stays lit on that page. The new season, new dynasty
   and My Team pages still link to it.
2. The header nav rule is back to what it was, and the header is one row again.
3. The Playbooks page has the breadcrumb, the tool tabs and the standard subtitle. Its title
   is "Playbooks".
4. The book name field is a text input, so it picks up the site styling.

## Checks

Rendered the home, season, game and Playbooks pages at 1280, 1024 and 390 pixels. The
playbook tests, the UI tests and the NiceGUI freeze test pass. The NiceGUI app was not
touched by the merges.
