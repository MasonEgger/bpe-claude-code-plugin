---
name: lessons
description: View, search, and manage accumulated lessons from .ai-sessions/lessons.md
argument-hint: "[search term | recent | all | categories | prune | promote]"
model: sonnet
disable-model-invocation: true
---

# Lessons Command

View and manage accumulated lessons from `.ai-sessions/lessons.md`.

## Behavior

1. Read `.ai-sessions/lessons.md`
   - If the file does not exist, inform the user: "No lessons file found. Run `/bpe:session-summary` at the end of a session to start capturing lessons."
   - If the file exists, proceed based on arguments.

2. **No arguments** (`/bpe:lessons`): Display the full `## Recent` section and list available categories with their lesson counts.

3. **With search term** (`/bpe:lessons $ARGUMENTS`): Search the entire lessons.md for entries matching the argument. Display matching lessons grouped by category. If no matches, say so.

4. **Special arguments**:
   - `recent` - Show the Recent section (default if no args)
   - `all` - Display the entire lessons.md file
   - `categories` - List just the category headings with counts
   - `prune` - Review lessons.md for duplicates, outdated entries, or lessons that have already been incorporated elsewhere. Check all of the following for existing coverage:
     - The project's `CLAUDE.md`
     - All global rule files in `~/.claude/rules/*.md`
     - `~/.claude/CLAUDE.md`
     
     For each lesson that is already covered, note where it exists. Present findings to the user grouped by status:
     ```
     ## Already incorporated
     - [lesson]: covered in ~/.claude/rules/python.md
     - [lesson]: covered in project CLAUDE.md
     
     ## Duplicates
     - [lesson]: duplicate of [other lesson] in lessons.md
     
     ## Outdated
     - [lesson]: reason it appears outdated
     ```
     Ask the user to confirm before making changes. Pruned lessons are NOT deleted; they are moved to `.ai-sessions/lessons-pruned.md` with a record of what happened to each one:
     ```
     ## Pruned <date>
     - [lesson]: promoted to ~/.claude/rules/python.md
     - [lesson]: duplicate of [other lesson]
     - [lesson]: outdated: [reason]
     ```
     Append to the file if it already exists. Then remove the pruned lessons from lessons.md.
   - `promote` - Identify lessons that appear broadly applicable or have been validated across multiple sessions. For each promotable lesson, classify its destination:

     **Pre-flight: version-control guard (REFUSE on failure).** Before doing any classification work, run:
     ```bash
     git -C ~/.claude/rules rev-parse --show-toplevel 2>/dev/null
     ```
     If this exits non-zero or returns nothing, the rules destination is not version-controlled; promotions would be lost on re-provision. Refuse to continue with: "`~/.claude/rules` is not in a git repo. Promotions to global rules would not be backed up. Fix your dotfiles setup so `~/.claude/rules` is symlinked (or copied) from a version-controlled source, then re-run." Skip the rest of promote.
     
     Otherwise, classify destinations:
     1. **Project-local**: Lessons specific to this codebase (architecture decisions, project-specific conventions, repo-specific workflows) → add to the project's `CLAUDE.md`.
     2. **Global**: Lessons that apply across all projects (language standards, tooling preferences, general workflow patterns) → add to the matching file in `~/.claude/rules/`. Read the existing rule files in `~/.claude/rules/*.md` to find the best fit by topic. If no existing rule file is a good fit, suggest creating a new one with appropriate `paths:` frontmatter (e.g., `paths: ["**/*.py"]` for Python-specific rules).
     
     Present the proposed promotions grouped by destination:
     ```
     ## Project CLAUDE.md
     - [lesson]: reason it's project-specific
     
     ## ~/.claude/rules/python.md (existing)
     - [lesson]: reason it fits here
     
     ## ~/.claude/rules/deployment.md (new file)
     - [lesson]: reason a new rule file is needed
     ```
     Ask the user to confirm, adjust destinations, or skip individual lessons before making any changes. After confirmed promotions are applied:
     1. Remove the promoted lessons from `.ai-sessions/lessons.md`.
     2. Append a provenance record to `.ai-sessions/lessons-pruned.md` under a `## Promoted <date>` heading, one bullet per lesson with its destination, matching how `prune` records dispositions. Use `date +%Y-%m-%d` for the heading. Example:
        ```
        ## Promoted 2026-06-10
        - [lesson text]: promoted to ~/.claude/rules/python.md
        - [lesson text]: promoted to project CLAUDE.md
        ```
        Append to the file if it already exists; create it otherwise. This is the only durable record of what came from where after `lessons.md` loses the entry.

## Output Format

When displaying lessons, use clean markdown formatting. Group by category when showing search results. Always show the date associated with each lesson.
