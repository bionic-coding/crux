---
name: conductor
description: Fixture role conductor for the role-skill pairing test.
tools: Read, Grep, Glob, Agent(writer), Skill
model: sonnet
skills: [tree-skill]
metadata:
  tags: "fixture"
  bundles: "fixture"
  risk_level: "low"
  skill_lanes: "tree-skill=delegates:writer"
---

# conductor

Fixture body for conductor.
