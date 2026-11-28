# AAR: field previews for the cross code calls

November 28, 2026

## What was asked

Ron asked for the item left open in the cross code books run: the Playbooks page previews
were the generic drawing for each play family, not one for each new call.

## What changed

`stats_site/static/playbook_cookbook.js`:
* Each of the 15 offensive calls has its own drawing. The calls with more than one branch
  have a choice for each branch of the read, for example Switchback's missed switch and
  clean switch, or Up Back Across's up and back, up back and across, and held. Handoff Punish
  has one drawing.
* Each of the 8 defensive answers shows which real defenders move and where: the two
  defenders trading men on Exchange, the three depths of Stagger, the box defender held on
  the weak edge by Edge Anchor, the help slide of Slide and Replace, the rushers and the
  wide side defender of Channel Press, the nearest tacklers and the deep recovery of
  Transition Net, the two crossing rushers of Cross Rush and the step up of Set Breaker.
* A new color marks movement without the ball (decoys, crossers, a lineman releasing). The
  animated ball skips those steps and follows only the ball's path.

`stats_site/templates/playbooks.html` adds the new color to the key. `stats_site/router.py`
passes the cross code defensive postures to the page, so each answer's drawing starts from
its own front.

## Checks

All 39 drawings, every branch included, rendered in Chrome with no script errors. A new test
checks that every call has its own drawing and that every call with more than one branch
lets the viewer pick it. Cross code, catalog and custom playbook tests pass. The full suite
was not run locally, at Ron's request.
