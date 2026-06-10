# AAR Parser Instructions (shared by all parsing agents)

You are parsing After-Action Reports (AARs) into structured JSON records. This is EXTRACTION, not summarization. Fidelity matters more than tidiness: never invent, infer, or "improve" content. Gaps are data — a missing section must be recorded as missing (null/[]), not filled in.

For EACH assigned file, read the full file and write ONE JSON record to `/home/user/viperball/aar-records/<record_id>.json`.

`record_id` = `viperball--<date YYYY-MM-DD or "undated">--<kebab-slug-of-title>`.
- Date: only use a date that literally appears in the document (header metadata like "**Date:** 2026-03-27", or a date in the title/first heading). Filename dates may be used ONLY if the same date is confirmed nowhere in the doc — in that case use "undated" and note in parser_notes where you looked. Never guess.
- Slug: kebab-case of the first heading, lowercase, alphanumerics and hyphens only, drop leading "after-action report"/"aar"/"after action review" prefixes' punctuation but keep the substantive words; keep it deterministic and reasonably short (max ~8 words).

Schema — every key must be present; use null or [] when absent; never fabricate:

```json
{
  "record_id": "",
  "source_path": "relative path from repo root, e.g. docs/AAR_x.md",
  "repo": "viperball",
  "parsed_at": "2026-06-10",
  "genre_confidence": "high | medium | low",
  "date": "YYYY-MM-DD or null",
  "title": "verbatim first heading (without leading # markers)",
  "scope": "verbatim scope/summary statement, or null",
  "rationale": [
    { "item": "verbatim or lightly trimmed 'why' point", "references": ["design docs, issues, prior AARs cited"] }
  ],
  "delegation_events": [
    { "decision": "what was decided", "decided_by": "owner | agent | joint | unclear", "quote": "verbatim sentence recording the decision" }
  ],
  "actions": [
    { "description": "what was done", "artifacts": ["file paths, modules, commands named"], "kind": "new | modified | config | docs | data | other" }
  ],
  "risk_posture": [
    "verbatim statements of chosen caution/aggressiveness, e.g. 'deliberately conservative', 'semantics unchanged'"
  ],
  "validation_claims": [
    { "claim": "verbatim claim, e.g. 'pytest -q → 102 passed'", "evidence_cited": "tests | manual verification | metrics | render/smoke | none", "checkable_against_repo": "yes | no | unclear", "check_method": "how a reviewer would verify it, one line", "verified": "not_checked" }
  ],
  "non_actions": [
    { "item": "what was explicitly not done", "reason": "verbatim reason given", "category": "deferred | out_of_scope | declined_by_owner | blocked | unclear", "status": "unknown" }
  ],
  "residual_risks": ["known weaknesses or debt acknowledged in the document"],
  "open_hooks": ["affordances left for future work, e.g. 'the hook is there if X ever wants Y'"],
  "section_headers_original": ["every markdown heading in the document, in order, verbatim including # markers' text (the heading text, not the # chars)"],
  "unmapped_content": "verbatim text that did not fit any field above. Do not discard anything substantive. If everything mapped, null.",
  "quality_vector": {
    "has_scope": false,
    "has_rationale": false,
    "has_delegation_record": false,
    "has_validation": false,
    "has_negative_space": false,
    "has_residual_risk": false
  },
  "parser_notes": "anything odd: malformed structure, suspected missing sections, duplicate of another AAR, etc. null if nothing."
}
```

Rules:
- Verbatim where the schema says verbatim. Trim whitespace only.
- `unmapped_content` is load-critical. When in doubt, put text there rather than forcing it into a field. Large tables of data, design discussion, mechanics explanations that aren't actions/rationale/validation go here (verbatim, can be long).
- Set every `validation_claims[].verified` to "not_checked". Do NOT verify claims against the repo.
- Set every `non_actions[].status` to "unknown".
- One document = one record, even if it covers multiple workstreams.
- quality_vector flags: true iff the corresponding field is non-empty/non-null (has_negative_space ↔ non_actions, has_delegation_record ↔ delegation_events, has_residual_risk ↔ residual_risks).
- Do NOT modify, rename, or refactor the source AAR files.
- Output must be valid JSON (validate before writing; e.g. write then `python3 -m json.tool`).

When done, reply with a markdown list of `{record_id, source_path, date (or null), title, genre_confidence}` for each record you wrote.
