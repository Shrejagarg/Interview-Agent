# This Project — Custom Skill Authoring

Use this skill when creating, editing, or evaluating skills in this repo.

## Where skills live and how they load

- Project skills are vendored in **`.agents/skills/<name>/`**; each folder has exactly one `SKILL.md` (opencode scans recursively for `SKILL.md` via `opencode.json` → `skills.paths: [".agents/skills"]`).
- Org-convention: keep a per-skill `references/project.md` when a skill needs project-specific facts, rather than editing the generic `SKILL.md`.

## Imported vs local skills

- Vendored third-party skills are tracked in **`skills-lock.json`** with `source`, `sourceType`, `skillPath`, and `computedHash` (SHA-256 of that SKILL.md). Updating an imported SKILL.md requires recomputing its hash — prefer adding `references/` instead.
- **Local project skills** (e.g., `interview-project`) are authored directly and are *not* registered in `skills-lock.json`.
- Every skill folder ships a `LICENSE.txt` (Apache 2.0).

## Authoring checklist

1. Frontmatter: `name` lowercase-hyphen and matching the folder name; `description` concrete and trigger-loaded.
2. Fold the repo's golden rules and routing into a `references/project.md` when relevant.
3. No nested `SKILL.md` anywhere in the tree; names must be unique across `.agents/skills/`.
4. Keep `SKILL.md` concise (inline the critical rules, push depth to references/scripts).
5. After adding/changing a skill, opencode must be restarted to pick it up.