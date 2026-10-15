// The capability manifest of crux-mods: every event the mods hook, every call
// they make on `$`, every environment variable they read, the session state
// they keep, and the one process they may start. The release gate compares this
// object with what `claude plugin validate --strict --json` lists and refuses on
// any difference.
// The object between the markers is strict JSON: the gate parses it with a
// JSON parser, so it carries no comment, no single-quoted string and no trailing
// comma.
//
// claude_code: min is the first Claude Code with strict validation of mods. There
// is no max: the gate refuses a newer Claude Code only when its validator listing
// does not parse or differs from this manifest. Each recorded output under
// tests/fixtures/validator/ keeps the parser tested against a real listing.
// events: behaviour is observe, draw or command-text, or a behaviour-changing value
// that names an Accepted decision. Observe, draw and command-text need no decision:
// the hook changes nothing Claude Code does, and command-text answers only a command
// this module registers. The exception is an observe entry for a hook that reads
// what the user types: it names the Accepted decision that admitted the hook. The
// gate refuses a named decision that is not Accepted, but it accepts null on an
// observe entry, so a crux-mods test pins the prompt.submit entry's decision field.
// gating and has_catch repeat what the validator lists for a hook whose failure
// can stop the event; tools/mods_gate.py compares both.
// launch.timeout_ms: the reader takes about 0.3 s on a tree of 144 runs; 10 s
// leaves room for a cold uv cache, and the reader stops itself at 8 s.
// state_declared, state_reads, state_writes: the session-state keys that
// types/index.d.ts declares, that the hooks read and that the hooks write. Claude
// Code holds session state in memory for the session and writes no file. An
// absent list means none.
// notes: the text the user guide's generated reach tables take from, one entry per
// name above, rendered by crux/scripts/generate-mods-reach-tables.py. The mods never
// read it, and the gate does not compare it.
// BEGIN CAPABILITIES
export const capabilities = {
  "format_version": 1,
  "plugin": "crux-mods",
  "claude_code": {"min": "2.1.287"},
  "events": [
    {"event": "session.start", "behaviour": "observe", "decision": null},
    {"event": "tool.call", "behaviour": "observe", "decision": null, "gating": true, "has_catch": false},
    {"event": "prompt.submit", "behaviour": "observe", "decision": "ADR-0156", "gating": true, "has_catch": false},
    {"event": "ui.render{component=AbovePrompt}", "behaviour": "draw", "decision": null},
    {"event": "ui.render{component=Pane}", "behaviour": "draw", "decision": null},
    {"event": "command.run{command=crux-dashboard}", "behaviour": "command-text", "decision": null}
  ],
  "calls": ["$.agent.list", "$.clock.after", "$.clock.every", "$.command.register", "$.env.get", "$.fs.read", "$.fs.stat", "$.process.run", "$.session.root", "$.state.get", "$.state.set", "$.ui.invalidate", "$.ui.open", "$.ui.resolve"],
  "env_reads": ["CLAUDE_CONFIG_DIR", "DYLD_FALLBACK_FRAMEWORK_PATH", "DYLD_FALLBACK_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH", "DYLD_IMAGE_SUFFIX", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "DYLD_ROOT_PATH", "DYLD_VERSIONED_FRAMEWORK_PATH", "DYLD_VERSIONED_LIBRARY_PATH", "HOME", "LD_AUDIT", "LD_LIBRARY_PATH", "LD_PRELOAD"],
  "env_writes": [],
  "state_declared": ["crux-mods.current"],
  "state_reads": ["crux-mods.current"],
  "state_writes": ["crux-mods.current"],
  "launch": {
    "launcher": "/usr/bin/env",
    "launcher_args": ["-i"],
    "uv_locations": ["/opt/homebrew/bin/uv", "/usr/local/bin/uv", "{HOME}/.local/bin/uv", "{HOME}/.cargo/bin/uv"],
    "uv_args": ["run", "--offline", "--no-project", "--no-config", "--quiet"],
    "env_allow": ["HOME", "PATH", "UV_OFFLINE", "UV_NO_CONFIG", "UV_PYTHON_DOWNLOADS", "PYTHONDONTWRITEBYTECODE", "CRUX_NO_UV_REEXEC", "NO_COLOR"],
    "env_constants": {"PATH": "/usr/bin:/bin", "UV_OFFLINE": "1", "UV_NO_CONFIG": "1", "UV_PYTHON_DOWNLOADS": "never", "PYTHONDONTWRITEBYTECODE": "1", "CRUX_NO_UV_REEXEC": "1", "NO_COLOR": "1"},
    "env_derived": {"HOME": "env:HOME"},
    "loader_vars": ["LD_PRELOAD", "LD_AUDIT", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH", "DYLD_FALLBACK_LIBRARY_PATH", "DYLD_FALLBACK_FRAMEWORK_PATH", "DYLD_VERSIONED_LIBRARY_PATH", "DYLD_VERSIONED_FRAMEWORK_PATH", "DYLD_ROOT_PATH", "DYLD_IMAGE_SUFFIX"],
    "scripts": {"visualize-run-progress": {"path": "scripts/visualize-run-progress.py", "args": ["--json", "--project-root", "{project_root}"]}},
    "timeout_ms": 10000
  },
  "notes": {
    "events": {
      "session.start": {"sees": "That a session started. It then registers `/crux-dashboard`, starts the 15-second refresh and runs the reader.", "keeps": "Nothing from the event."},
      "tool.call": {"sees": "Each tool call's tool name, and the file path of a Write, Edit, MultiEdit or NotebookEdit call or the command of a Bash call.", "keeps": "Nothing. A call that names a run file schedules a refresh 1.5 seconds later."},
      "prompt.submit": {"sees": "The text and origin kind of every prompt you submit, and whether it carries attachments. It reads nothing while the `read_prompts` setting is off.", "keeps": "Nothing of it. The prompt goes on unchanged. A prompt you type or send through the bridge, with no attachment, that is one of the phrases that ask to see the run opens the `/crux-dashboard` pane and starts a refresh."},
      "ui.render{component=AbovePrompt}": {"sees": "The band's width and whether a survey is showing.", "keeps": "Nothing from the event.", "surface": "the band above the prompt"},
      "ui.render{component=Pane}": {"sees": "The pane's request id, width and placement.", "keeps": "Nothing from the event.", "surface": "the `/crux-dashboard` pane"},
      "command.run{command=crux-dashboard}": {"sees": "That you ran `/crux-dashboard`. It reads nothing else from the event.", "keeps": "Nothing from the event. It refreshes, opens the pane and answers with text that Claude reads."}
    },
    "calls": {
      "$.agent.list": {"sees": "This session's subagents, and each one's status, type and description.", "keeps": "Nothing. It reads the list again for each drawing."},
      "$.clock.after": {"sees": "Nothing. It sets the one-time timer for the refresh after a run-file write, and for the refresh after a prompt that asks to see the run.", "keeps": "The pending timer, until it fires."},
      "$.clock.every": {"sees": "Nothing. It sets the 15-second refresh timer.", "keeps": "The timer, for the session."},
      "$.command.register": {"sees": "Nothing. It registers the `/crux-dashboard` command.", "keeps": "Nothing."},
      "$.env.get": {"sees": "The values of the environment variables in the rows below.", "keeps": "Nothing between launches."},
      "$.fs.read": {"sees": "Two files: Claude Code's plugin record (`plugins/installed_plugins.json` in the Claude config directory) and the `plugin.json` of `crux-mods` itself.", "keeps": "Nothing between launches. It takes the installed crux's path and version, and its own version, from them."},
      "$.fs.stat": {"sees": "Whether a path exists, its kind and its resolved path. It checks the launcher, the project root, the Claude config directory, the plugin record, the installed crux, `HOME`, uv, uv's cache and uv's interpreter directory.", "keeps": "Nothing between launches."},
      "$.process.run": {"sees": "The reader's exit code, standard output and standard error.", "keeps": "Nothing of its own: the checked output is what `$.state.set` keeps. Standard error only selects a status code."},
      "$.session.root": {"sees": "The session's project root.", "keeps": "Nothing between launches. The reader receives it as `--project-root`."},
      "$.state.get": {"sees": "The last reader result this mod kept, under `crux-mods.current`.", "keeps": "Nothing. It reads the value again for each drawing."},
      "$.state.set": {"sees": "Nothing.", "keeps": "The last reader result, once checked, under `crux-mods.current` for the session, so a reload of the mod's code keeps the band and the pane. Claude Code holds it in memory and writes no file. Other plugins in the session can read it."},
      "$.ui.invalidate": {"sees": "Nothing. It asks Claude Code to draw the band and the pane again after each refresh.", "keeps": "Nothing."},
      "$.ui.open": {"sees": "Nothing. It opens the `/crux-dashboard` pane.", "keeps": "Nothing."},
      "$.ui.resolve": {"sees": "The `Box` and `Text` components Claude Code draws with.", "keeps": "Nothing."}
    },
    "env_reads": {
      "CLAUDE_CONFIG_DIR": {"sees": "Its value, to find the Claude config directory and to refuse one that differs from where the plugin was loaded.", "keeps": "Nothing between launches."},
      "HOME": {"sees": "Its value, to find uv, uv's cache, uv's interpreter directory and the default Claude config directory.", "keeps": "Nothing between launches. The reader starts with it as its `HOME`."}
    },
    "loader_vars": {"sees": "Whether any is set. The mod starts no reader while one is, because `/usr/bin/env` would start under it.", "keeps": "Nothing."},
    "env_writes": {},
    "launch": {
      "visualize-run-progress": {"sees": "Your project's crux configuration and the runs, books and council records in its documentation tree, read by the installed crux's reader.", "keeps": "Nothing. The reader writes no file and answers with one JSON object on its standard output."}
    },
    "never": "Directly or through the process it starts, it makes no network request, calls no model and reads no credential or environment secret. It writes nothing in your documentation tree or your project: its only write is uv's cache, and it refuses a uv cache inside your project.",
    "surfaces": [
      {"event": "ui.render{component=AbovePrompt}", "part": "the book and run of the run whose run file changed last", "from": ["visualize-run-progress:runs[].book_id", "visualize-run-progress:runs[].run_id", "visualize-run-progress:runs[].modified_s"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "the prompt strip: one glyph per prompt, with `|` between modules", "from": ["visualize-run-progress:runs[].prompts[].state", "visualize-run-progress:runs[].prompts[].module_tag", "visualize-run-progress:runs[].current_prompt", "visualize-run-progress:runs[].prompts[].n"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "the current prompt's module kind word", "from": ["visualize-run-progress:runs[].prompts[].module_tag", "visualize-run-progress:runs[].current_prompt", "visualize-run-progress:runs[].prompts[].n"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "the current prompt's position out of the total", "from": ["visualize-run-progress:runs[].current_prompt", "visualize-run-progress:runs[].progress.total"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "the percent done", "from": ["visualize-run-progress:runs[].progress.pct"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "the time the current prompt has run", "from": ["visualize-run-progress:runs[].current_prompt", "visualize-run-progress:runs[].prompts[].n", "visualize-run-progress:runs[].prompts[].state", "visualize-run-progress:runs[].prompts[].started_s", "visualize-run-progress:runs[].prompts[].completed_s", "visualize-run-progress:now_s"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "an escalation of the current prompt's module", "from": ["visualize-run-progress:runs[].current_prompt", "visualize-run-progress:runs[].prompts[].n", "visualize-run-progress:runs[].prompts[].module_tag", "visualize-run-progress:runs[].escalations[].prompt", "visualize-run-progress:runs[].escalations[].module_tag", "visualize-run-progress:runs[].escalations[].round"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "a stall", "from": ["visualize-run-progress:runs[].status", "visualize-run-progress:runs[].modified_s", "visualize-run-progress:now_s", "$.agent.list:status"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "the current prompt's title", "from": ["visualize-run-progress:runs[].current_prompt", "visualize-run-progress:runs[].prompts[].n", "visualize-run-progress:runs[].prompts[].title"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "the last council round and its aggregate action", "from": ["visualize-run-progress:runs[].councils[].prompt", "visualize-run-progress:runs[].councils[].round", "visualize-run-progress:runs[].councils[].aggregate_action"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "the last gate with a recorded state", "from": ["visualize-run-progress:runs[].gates[].n", "visualize-run-progress:runs[].gates[].state"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "the number of running subagents", "from": ["$.agent.list:status"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "how many other runs are in progress", "from": ["visualize-run-progress:runs"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "the last completed run, for 48 hours after it completed", "from": ["visualize-run-progress:last_completed_status", "visualize-run-progress:last_completed.book_id", "visualize-run-progress:last_completed.run_id", "visualize-run-progress:last_completed.started_s", "visualize-run-progress:last_completed.completed_s", "visualize-run-progress:last_completed.progress.counts.done", "visualize-run-progress:last_completed.progress.total", "visualize-run-progress:now_s"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "the line `run in progress, view refused`", "from": ["visualize-run-progress:runs", "visualize-run-progress:last_completed_status"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "the status code", "from": ["launch:outcome", "visualize-run-progress:error.code", "visualize-run-progress:format_version", "visualize-run-progress:runs", "visualize-run-progress:last_completed_status"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "the band's width", "from": ["ui.render{component=AbovePrompt}:props.bodyColumns"]},
      {"event": "ui.render{component=AbovePrompt}", "part": "no band while a survey shows", "from": ["ui.render{component=AbovePrompt}:props.hasSurvey"]},
      {"event": "ui.render{component=Pane}", "part": "the legend of the glyphs and module kinds in view", "from": ["visualize-run-progress:runs[].prompts[].state", "visualize-run-progress:runs[].prompts[].module_tag", "visualize-run-progress:runs[].councils[].seats[].decision"]},
      {"event": "ui.render{component=Pane}", "part": "each run panel's heading: book, run, status, current prompt and percent", "from": ["visualize-run-progress:runs[].book_id", "visualize-run-progress:runs[].run_id", "visualize-run-progress:runs[].status", "visualize-run-progress:runs[].current_prompt", "visualize-run-progress:runs[].progress.total", "visualize-run-progress:runs[].progress.pct"]},
      {"event": "ui.render{component=Pane}", "part": "the prompt strip, each module labelled with its kind word", "from": ["visualize-run-progress:runs[].prompts[].state", "visualize-run-progress:runs[].prompts[].module_tag", "visualize-run-progress:runs[].current_prompt", "visualize-run-progress:runs[].prompts[].n"]},
      {"event": "ui.render{component=Pane}", "part": "the progress bar of `\u25ae` and `\u25af`", "from": ["visualize-run-progress:runs[].progress.total", "visualize-run-progress:runs[].progress.pct"]},
      {"event": "ui.render{component=Pane}", "part": "when the run started, and how long it has run or took", "from": ["visualize-run-progress:runs[].status", "visualize-run-progress:runs[].started_s", "visualize-run-progress:runs[].completed_s", "visualize-run-progress:now_s"]},
      {"event": "ui.render{component=Pane}", "part": "one lane per prompt on one time axis", "from": ["visualize-run-progress:runs[].status", "visualize-run-progress:runs[].started_s", "visualize-run-progress:runs[].completed_s", "visualize-run-progress:runs[].prompts[].n", "visualize-run-progress:runs[].prompts[].state", "visualize-run-progress:runs[].prompts[].started_s", "visualize-run-progress:runs[].prompts[].completed_s", "visualize-run-progress:now_s", "ui.render{component=Pane}:props.bodyColumns"]},
      {"event": "ui.render{component=Pane}", "part": "`lanes withheld`, in place of the lanes of a long run or of a pane past its size budget", "from": ["visualize-run-progress:runs[].status", "visualize-run-progress:runs[].started_s", "visualize-run-progress:runs[].completed_s", "visualize-run-progress:now_s", "visualize-run-progress:runs[].prompts", "ui.render{component=Pane}:props.bodyColumns"]},
      {"event": "ui.render{component=Pane}", "part": "the counts of prompts by state", "from": ["visualize-run-progress:runs[].progress.counts.done", "visualize-run-progress:runs[].progress.counts.skipped", "visualize-run-progress:runs[].progress.counts.blocked", "visualize-run-progress:runs[].progress.counts.running", "visualize-run-progress:runs[].progress.counts.pending"]},
      {"event": "ui.render{component=Pane}", "part": "the stall line and its note", "from": ["visualize-run-progress:runs[].status", "visualize-run-progress:runs[].modified_s", "visualize-run-progress:now_s", "$.agent.list:status"]},
      {"event": "ui.render{component=Pane}", "part": "the escalation lines and their note", "from": ["visualize-run-progress:runs[].current_prompt", "visualize-run-progress:runs[].prompts[].n", "visualize-run-progress:runs[].prompts[].module_tag", "visualize-run-progress:runs[].escalations[].prompt", "visualize-run-progress:runs[].escalations[].module_tag", "visualize-run-progress:runs[].escalations[].round"]},
      {"event": "ui.render{component=Pane}", "part": "a row per prompt: its state, module tag, title and duration", "from": ["visualize-run-progress:runs[].status", "visualize-run-progress:runs[].current_prompt", "visualize-run-progress:runs[].prompts[].n", "visualize-run-progress:runs[].prompts[].state", "visualize-run-progress:runs[].prompts[].module_tag", "visualize-run-progress:runs[].prompts[].title", "visualize-run-progress:runs[].prompts[].started_s", "visualize-run-progress:runs[].prompts[].completed_s", "visualize-run-progress:now_s"]},
      {"event": "ui.render{component=Pane}", "part": "the count of refused council files", "from": ["visualize-run-progress:runs[].councils_skipped"]},
      {"event": "ui.render{component=Pane}", "part": "the count of runs past the five shown", "from": ["visualize-run-progress:runs"]},
      {"event": "ui.render{component=Pane}", "part": "the councils grid, with the newest record's aggregate action and whether it converged", "from": ["visualize-run-progress:runs[].book_id", "visualize-run-progress:runs[].run_id", "visualize-run-progress:runs[].councils[].prompt", "visualize-run-progress:runs[].councils[].round", "visualize-run-progress:runs[].councils[].council_kind", "visualize-run-progress:runs[].councils[].outcome", "visualize-run-progress:runs[].councils[].quorum_met", "visualize-run-progress:runs[].councils[].degraded", "visualize-run-progress:runs[].councils[].aggregate_action", "visualize-run-progress:runs[].councils[].converged", "visualize-run-progress:runs[].councils[].seats[].role", "visualize-run-progress:runs[].councils[].seats[].decision", "visualize-run-progress:runs[].councils[].seats[].errored"]},
      {"event": "ui.render{component=Pane}", "part": "the gates panel", "from": ["visualize-run-progress:runs[].book_id", "visualize-run-progress:runs[].run_id", "visualize-run-progress:runs[].gates[].n", "visualize-run-progress:runs[].gates[].state", "visualize-run-progress:runs[].gates[].gate_class"]},
      {"event": "ui.render{component=Pane}", "part": "the agents panel", "from": ["$.agent.list:status", "$.agent.list:type", "$.agent.list:description"]},
      {"event": "ui.render{component=Pane}", "part": "the last run when none is in progress, with its summary", "from": ["visualize-run-progress:last_completed", "visualize-run-progress:last_completed_status", "visualize-run-progress:last_completed_undated", "visualize-run-progress:last_completed.summary", "visualize-run-progress:last_completed.summary_truncated"]},
      {"event": "ui.render{component=Pane}", "part": "the `undetermined` row", "from": ["visualize-run-progress:last_completed_status", "visualize-run-progress:last_completed_unresolved", "visualize-run-progress:last_completed_undated"]},
      {"event": "ui.render{component=Pane}", "part": "the line saying the reader refused a run in progress", "from": ["visualize-run-progress:runs", "visualize-run-progress:last_completed_status"]},
      {"event": "ui.render{component=Pane}", "part": "the reader's version and the count of refused run files", "from": ["visualize-run-progress:reader_version", "visualize-run-progress:runs_skipped"]},
      {"event": "ui.render{component=Pane}", "part": "the status code", "from": ["launch:outcome", "visualize-run-progress:error.code", "visualize-run-progress:format_version", "visualize-run-progress:runs", "visualize-run-progress:last_completed_status"]},
      {"event": "ui.render{component=Pane}", "part": "the layout: borders, one or two columns, and the inline layout with its `+N more` row", "from": ["ui.render{component=Pane}:props.bodyColumns", "ui.render{component=Pane}:props.placement", "visualize-run-progress:runs[].modified_s"]}
    ]
  }
} as const;
// END CAPABILITIES
