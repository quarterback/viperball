# AAR: choosing playbooks for a dynasty program

November 28, 2026

## What was asked

Ron could not pick the new playbooks when he set up a dynasty program and asked for them to
be available now.

## What was wrong

1. The New dynasty page showed the playbook selects only when the library already held a
   saved book for that side. With no saved books there was nothing on the page at all.
2. A dynasty program could take a book only at creation. The Start season form on the
   dynasty hub let the coach pick an offense, defense and special teams school but not a
   playbook, so books saved later could never be used.

## What changed

1. The playbook selects always show on the New season and New dynasty pages. When the
   library has no book for a side, the select says so and links to the Playbooks page.
2. The Start season form on the dynasty hub has offense and defense playbook selects. They
   list every saved book and preselect the books the program already uses. Picking a book
   replaces the program's book for that side; picking "Use the school above" drops it.
3. The start season request takes an optional `playbooks` field. Left out, the program keeps
   its current books.

## Checks

Saved a Ground Control offense book with a clinic concept and a Delta package, created a
dynasty, and started its season from the hub with that book. The program's assignment and
its season offense school both came through. The playbook and UI tests pass.
