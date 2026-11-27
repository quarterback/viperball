# Playbook Cookbook review

## What the current engine supports

Season games already pass installed packages to the engine. Offensive packages use formation, play family, kick pass subtype, and live game situations. The coordinator may select an eligible package, which biases the call within the existing legal choices. The game log distinguishes eligibility, selection, and the actual choices. The built in catalog validates its package definitions. Dynasty saves retain team installations.

The focused catalog, offensive package execution, and team installation suites passed all 43 tests.

## Proposed design

Let a user start from a built in concept or assemble a recipe from the engine vocabulary. Give it a name, a formation, an action, and explicit conditions for when it should be called. Let the user group recipes into a named book, save drafts, and install a revision for their team before the usual week or season simulation. Show what the coordinator called and what happened afterward.

Store custom recipes separately from the built in catalog. Share them as versioned JSON. Validate imports and preview them as drafts. Keep installation and team familiarity in the current save. Keep the exact installed revision available for postgame reporting.

Start with offensive recipes. An initial preference can use the existing package weights. An explicit call order or a pair of plays that use the same look would need a followup in the selector. Field diagrams can show the formation and intended action. Drawn paths can inform the diagram today and would need action support in the engine to affect the sim.

This review changed documentation only.
