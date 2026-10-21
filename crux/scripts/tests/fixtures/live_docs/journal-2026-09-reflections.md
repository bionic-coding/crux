# Journal 2026-09 (fixture)

Three entries copied verbatim from the live 2026-09 month. Each reflects on one ADR
by `rule:<slug>` only, which is the shape CLN-JR-1 must recognise. The live journal changes with
every logged operation, so the tests read this copy instead.

## [2026-09-11 13:57] decision | accept per-agent Codex runtime overrides

The catalog contract allowed per-agent overrides only for OpenCode, so the reviewer retune required an architectural change.
The accepted schema-v3 path adds one complete, atomic Codex override while retaining level defaults for the other nine roles.
The quality loop rolled back an early acceptance after the body crossed its budget by one line, then reviewed the corrected Proposed record again.
If I repeated this change, I would run the body-budget gate before the first acceptance transition.
Friction: The requested reviewer-only effort could not be expressed without amending the shared-level contract.
Refs: [[promptbooks/PB-0102-codex-reviewer-sol-xhigh]] rule:per-agent-codex-runtime-override

## [2026-09-11 12:22] bug | remove project Codex agent shadows

I first treated the tracked projection as harmless dogfood. The beta exposed that Codex gives project agents precedence, hiding the personal agents' installed skill bindings.
If I repeated this rollout, I would include a same-repository shadow check before validating role behavior.
Friction: The derived-output contract tried to recreate the shadowing files after their deletion.
Refs: rule:personal-codex-agents-are-dogfood

## [2026-09-11 09:48] implementation | PB-0101: personal Codex agents now carry their model and skills

The cycle added a personal default for all ten Codex roles while preserving explicit project installation. Each installed file carries the catalog model, reasoning effort, sandbox, and absolute paths to its declared skills. Static health reports managed drift, plugin relocation, project shadows, unsafe files, and the absence of fresh-session runtime evidence.
What went well: independent reviewers turned vague compatibility concerns into executable boundaries. The final suite covers the default home, relocation, exact role bindings, idempotence, malformed inputs, and every managed filesystem type we found.
What was hard: the first atomic-write repair protected leaf files but reopened the directory by path after validation. A security reviewer demonstrated that swapping the directory redirected all ten writes outside the selected Codex home. The repair now pins one contained directory descriptor across drift checks, writes, removals, and post-write health.
What I would do differently: define the directory identity as part of the first implementation unit. Then write the parent-swap exploit before building the installer around path-based checks.
Friction: each filesystem repair exposed the next race one level higher, so the review loop needed a final full-suite run after the apparent hardlink and leaf-symlink fixes were already green.

Refs: [[promptbooks/PB-0101-install-personal-codex-agents]] rule:personal-agent-scope rule:model-and-skill-bindings rule:refresh-is-idempotent-and-bounded rule:health-separates-static-and-runtime-evidence
