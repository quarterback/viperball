# AAR: Cape Cod and the cross code concepts get their own groups on the Playbooks page

November 28, 2026

## What was asked

Ron could not find Cape Cod and the other new concepts on the Playbooks page.

## What was wrong

They were there, but only for the schools that carry them, and the page sorted every
package that was not Clinic or Delta into "Base packages". Cape Cod sat in that list
between Restart Go-To and Vertical Shot with nothing to mark it. Cape Cod offense comes with
Lateral Spread, Chain Gang, Slick 'n Slide and Stampede; Cape Cod defense with Swarm, Shadow
and Chaos.

## What changed

`stats_site/static/playbook_cookbook.js` now groups the list as Cape Cod, Cross code
concepts (Viper Trail, Far Side Coil, Third Strike, Bonus Guard, Pindown Chase), Base
packages, Clinic concepts and Delta. A group shows only when the chosen school has members.

## Checks

Checked in Chromium: Lateral Spread offense and Swarm defense both open with a Cape Cod
group at the top, and its preview loads.
