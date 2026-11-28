# AAR: ready made playbooks for every school

November 28, 2026

## What was asked

Ron is playing a dynasty. When he picks his school and goes to choose playbooks, the new
concepts (Cape Cod and the others) are not there to choose. He also wants computer coaches to
use every option across the offensive and defensive books.

## What was wrong

* The playbook lists in the dynasty and season forms only held books Ron had saved himself.
  With none saved, the list was empty, so no package could be chosen there.
* Computer coaches pick packages from their own preferences, and those preferences cluster.
  In one league setup 9 of 61 packages were never installed by any team (among them Viper
  Trail, Pindown Chase, three clinic concepts and two defensive packages), and Cape Cod's
  defensive trap went to one team.
* Computer teams only took books when the dynasty was created, and only from saved books.

## What changed

1. `engine/custom_playbooks.py`: `house_books()` builds ready made books for every school.
   Each school gets a base book and one book per concept set it carries (Cape Cod, cross
   code, clinic, Delta), four packages each, split into more books when a set has more than
   four. Concept books lead with their set and fill with the school's base packages. The 120
   books hold all 61 packages. IDs start with `house:` and resolve like saved books.
2. The playbook selects list your saved books, then the ready made books grouped by school.
3. Computer assignment: each team takes the fitting book its school has used least so far, so
   books spread before any repeats.
4. "Let computer teams use playbooks" is checked by default on season and dynasty setup, and
   is now also on the dynasty season start form. There it gives a book to computer programs
   that have none and leaves the rest alone, so an existing dynasty picks them up next season.
5. README Playbook Cookbook section updated.

## Result

Same league setup with the box checked: 39 of 39 offensive packages and 22 of 22 defensive
packages installed by at least one team (was 32 and 20). Cape Cod's hook went to 8 teams and
its trap to 2.

## Checks

`tests/test_house_playbooks.py` (new) and `tests/test_custom_playbooks.py` pass. One check in
the custom playbook test assumed the computer pool held only the saved book; it now checks
that a computer team ran a package from whatever book it was given.
