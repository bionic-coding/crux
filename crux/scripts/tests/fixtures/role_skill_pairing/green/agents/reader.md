---
name: reader
description: Fixture role reader for the role-skill pairing test.
tools: Read, Grep, Glob, Skill
model: sonnet
skills: [read-skill, supplied-skill, report-skill]
metadata:
  tags: "fixture"
  bundles: "fixture"
  risk_level: "low"
  shell_scope: "read-local"
  skill_lanes: "supplied-skill=caller-supplies, report-skill=returns-to-caller"
---

# reader

Fixture body for reader.
