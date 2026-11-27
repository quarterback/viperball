# Viperball Playbook Cookbook

## Product decision

Let a player build an offense or defense from the existing catalog, then select either saved book when picking a team. A custom book starts from one existing school and adds the player's choices of packages and concepts. The normal week and season simulations run that book. The box score shows where the coach used it and what happened.

A school is the team's base identity. A package is a plan for a situation. A concept describes what the players try to do on a snap. A call sheet tells the coach when to choose one. Keep these distinctions visible in the editor. The team setup screen only needs to show the name of the resulting book, its base school and its fit for the roster.

## What other games and editors show

| Reference | Evidence | Implication for Viperball |
| --- | --- | --- |
| Sierra Front Page Sports Football Pro '98 on PC | Community file tooling documents separate user plays, gameplans that hold stock or custom plays, and offensive or defensive profiles containing situation rules. The PNFL community also maintains a categorized play pool. [Play files](https://github.com/jako479/fbpro98-play), [gameplans](https://github.com/jako479/fbpro98-gameplan), [coaching profiles](https://github.com/jako479/fbpro98-profile), [community play pool](https://github.com/jako479/pnfl-playpool) | Separate what a concept does, which book contains it, and when the coach uses it. The user should be able to copy a concept without bringing an entire coaching profile along. |
| Tecmo Super Bowl and NCAA Football community tools | The Tecmo ROM editor exposes team playbooks and CPU run/pass tendencies through the team interface. Morphy's NCAA editor documents custom playbook installation for College Football Revamped. These are community tools. [Tecmo editor](https://github.com/jayjonesvip/nes-football-rom-editor), [NCAA editor](https://github.com/TFCNYCFBR/Morphy-s-NCAA-Playbook-Editor) | Put book assignment on the team setup screen. Let the player carry the same book between teams. |
| NFL Head Coach 09 on Xbox 360 | A community project that documents the original game describes Play Creator inside a career, a weekly gameplan, and separate offense and defense playbooks in coach data. [Project documentation](https://github.com/tools81/nfl-head-coach-09-static-recomp) | Make a created book available to the career and give each side its own assignment. |
| Madden community tools | The custom book editor organizes formation, subformation, play, drawn play art and editable assignments. The team book editor documents copying a play or an entire formation between books, plus a separate field view and defensive play art. [Custom book editor](https://github.com/chrisjohnsdev/Madden-CustomPlaybook-Editor), [team book editor](https://github.com/chrisjohnsdev/Madden-TeamPlaybook-Editor) | Make it easy to borrow one concept or a set. Synchronize the field and the assignments. Selecting an arrow should reveal the relevant action, and changing the action should redraw it. |
| Football Manager | Community FM24 tactic files show a shareable format in use. The independent FM Player Analyzer displays how many roles a roster can fill and which roles lack a backup. The editor inside Football Manager still needs direct verification for this study. [Shared tactics](https://github.com/yiyuanlee/fm24-tactics), [roster fit screenshot](https://github.com/ElectroHugin/FM-Player-Analyzer/blob/main/docs/screenshots/en/tactic-explorer.png) | Use the pitch as a view of the system, with roles, instructions and roster fit. A saved book should travel as a coherent tactic. |
| EA Rugby 08 community projects | Rugby 08 Revival documents team and player customization and credits The Rugby Forum. Its documentation does not establish how set plays were shown or authored in the original game. [Revival](https://github.com/garfakk/rugby08-revival) | Follow the community to learn which set plays users could select, how they previewed them, and whether they could create their own. |
| Standalone diagram editors | Playmaker documents layered offensive and defensive formations and distinct route, block and motion lines. [Playmaker](https://github.com/yamat47/playmaker) | Give different actions distinct markings and display both sides when the matchup matters. |

The cloud proxy denied search engines, Operation Sports, Sports Interactive, The Rugby Forum, BigFooty, Matrix Games, Internet Archive and GameFAQs. Direct historical UI evidence remains incomplete. These are the next comparisons to verify in manuals, screenshots and community discussion:

| Games to check | What to establish |
| --- | --- |
| Football Manager 2024 and a newer release | How pitch, roles and team instructions fit together, what travels in an exported tactic, and how role fit or familiarity is shown. |
| Rugby 08 and Rugby League Live 4 | How set plays are picked and previewed, and whether users can edit the shape, runners or branches. |
| AFL Evolution 2 | What the user controls at a restart and how an on field instruction is represented. |
| Arena Football, CFL Football '99 and the Matrix Games Maximum Football | Whether the rule sets change formations, situations and eligible actions in the editor, and whether a custom design can travel between teams or formats. Distinguish the Matrix title from the recent game with the same name. |

For each game, record how to browse, edit, assign, save and share a play or tactic and label each feature as built in or supplied by the community. The available sources establish useful patterns for specific games. A claim about older games being more customizable overall would require a broader comparison.

## What is actually in Viperball

The current catalog contains **16 offense schools, 10 defense schools and 27 packages**, split into 14 offense and 13 defense. Offense has four formation shells: tight, split, spread and heavy. A play family such as sweep, power, lateral spread or kick pass chooses an engine outcome model. Kick passes have quick kick, territory, bomb and kick lateral subtypes. A package usually describes a set of possible choices under a pre snap situation. It can suggest several formations and families. Browsing the catalog as if every package were an exact route diagram would imply more precision than its data carries.

The defense already reads visible pre snap context, including formation, down and distance. Its packages affect alignment, pressure and what the defense is looking for. Several defensive effects are tied to built in package IDs. Copying existing defensive concepts is a viable first step. A newly named defensive concept with original behavior needs a reusable effect model behind the editor.

College New already accepts a built in offense and defense for each human team. Dynasty New accepts the selected team and creates the staff, but the creation request lacks initial book selections. The college season sim already synchronizes a team's installed packages before the game. The synchronizer currently keeps packages based on school, roster fit and staff. That means user assignments need a separate source of authority so the next sync can tell that an installed selection is intentional.

[Catalog inventory](playbook_packages/INVENTORY.md) · [Engine choices](../engine/game_engine.py#L349) · [Defensive calls](../engine/game_engine.py#L4733) · [Team creation routes](../stats_site/router.py#L1075) · [Installation sync](../engine/team_installation.py#L423)

## Example book assembled from the catalog

Use Ghost as the offensive school. Borrow **Heavy Push** from Ground Control for short yardage, **Quick Kick Chain** from East Coast for long yardage, and **Fast Break** from Quick Strike for the first snap after a takeaway. On defense, use Fortress with its **Short Yardage Wall** and add **Kick Range Shell** from Lockdown. The live catalog lists all five packages as compatible with their proposed base schools. A chosen roster still has to meet their personnel needs.

This example can exercise the entire feature without a new play family. A later edit to Fast Break might distinguish an interception bonus from an ordinary turnover and let the user give each trigger a different priority. The UI should reveal which parts of the recipe are supported by the current engine.

## The 2D editor

Use a catalog on the left, a field in the center and an inspector on the right. The catalog can filter by original school, side, situation and personnel traits. Open any built in book and add a reference to one of its packages. Duplicate a concept when you want to edit it. Show its original school and the parts your roster can run effectively.

On offense, the field shows the formation and the intended sequence of ball actions. A run, a legal lateral, a kick pass and a kick at goal should each have a clearly distinct mark. On defense, show alignment, intended rush, and focus or coverage area only at the detail the engine supports. The inspector shows **when to call this**, **who it uses**, and **what tradeoff comes with it**. The field should be useful with click and keyboard controls. Start with SVG and ordinary HTML controls. Free placement becomes valuable when the engine has more positional controls or users need to annotate teaching diagrams.

A built in package may represent several options. Its preview can illustrate one representative concept, with alternatives selectable. Generated field arrows communicate intent. The simulation has no recorded player paths to replay.

Group the call sheet by situations players already recognize, including opening snap, short yardage, kick range, backed up, after a takeaway and protecting a lead. Let a user express **all** or **any** explicitly when combining conditions. When two recipes overlap, preview which gets priority and why. That avoids surprises such as a first snap after a takeaway being treated like every other first snap.

## Selecting a custom book and letting the coach run it

1. Add **Offensive playbook** and **Defensive playbook** beside team selection in College New and Dynasty New. Offer **Staff default**, built in schools, or saved custom books for the appropriate side. Summarize which school the book uses and flag roster or school incompatibility before confirming.
2. Keep book definitions in a library. A team assignment points to one saved revision for that side. Store its resolved content with the save so editing or importing a later revision does not silently change an existing season. Save and load the selection through the existing college and dynasty entry points.
3. Treat the chosen book as a team decision. When staff changes, the selected book remains installed while familiarity and execution follow the existing staff and roster mechanics. The player can intentionally hand control back to the staff. Separate user installed packages from coordinator suggestions when synchronizing.
4. For the first release, assemble offense and defense from existing compatible packages. Support ordering or a preferred call for a matching situation. Resolve preference within legal choices, with a base book fallback. Offense currently uses a bounded weighted selection, so a stronger call sheet priority is an engine change. For defense, carry the original package's known effects into a borrowed entry. The defense must work from visible information.
5. Export the book as versioned JSON. Validate allowed concepts, references, side, conditions and bounds. Preview imported books as drafts with their provenance and compatibility issues visible. Store an explicit assignment only after the user confirms it.
6. Add a report showing eligible, selected and run counts, plus outcomes and sample sizes. Link each observed call to its snap. Compare usage against the user's intended priority. For defense, show intention and actual commitment where events provide both.

The first implementation should prove that a selected custom offense and defense affect relevant calls through a normal season week, survive saving and loading, and stay assigned across a coordinator change. Validate that an imported book can be assigned from initial team setup. Include seeded comparisons, illegal call fallbacks and an unchanged default path for existing saves.

## Design space the current books leave open

| Concept | Why it is worth designing | What the engine would need |
| --- | --- | --- |
| Same look, two threats | A Split quick kick and a Split lateral concept give the offense a way to exploit a defense that adjusts to the first call. | A small amount of call history and a conditional sequence. The current package selector picks an optional plan for each snap. |
| The bonus possession call sheet | A takeaway can lead to a planned opening strike or a safer first snap depending on field position and kicker or midfield availability. This gives the user an identity for a Viperball specific restart. | The engine already exposes first snap and takeaway situations. A matching rule can be built first. Treating bonus possessions as a distinct design case with personnel based fallback needs additional editor and selector support. |
| The sixth down decision card | Let users decide when to pursue a kick at goal, play for territory or keep attacking. This is a valuable expression of the invented sport's six down structure. | The existing kick and punt decisions run through their own gate before the ordinary package path. Expose safe inputs to that decision separately. |
| Rush or protect the lateral lane | A defense can show the same alignment but commit extra pressure against a kick threat or hold defenders for a lateral chain. | Begin by borrowing existing packages. Authorable rush and focus combinations need bounded assignment choices and explicit costs, with roster and fatigue effects grounded in the existing contests. |

Prioritize the book library, two selectors and postgame proof. Then add the first genuinely new tool for designing a concept: paired calls from the same formation. The result should reward the player for recognizing what the defense is giving them through preparation, even when the entire week is simulated at once.
