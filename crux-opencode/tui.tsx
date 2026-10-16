// The entry OpenCode 2 loads: the run band above the composer, the run dashboard panel and the
// /crux-dashboard command. This is the one file that imports a host package or a built-in module and
// the one file that names the host's context. Everything else is a pure module that reaches the host
// through the Host value built here. The file is written in a closed set of fixed forms, which the
// release source check matches token for token.
import { Plugin } from '@opencode/plugin/tui'
import { createEffect } from 'solid-js'
import { readFileSync, realpathSync, statSync } from 'node:fs'
import { dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawn } from 'node:child_process'
import { runCommand } from './lib/command.ts'
import type { Host, KeptEnvelope, ReaderSink } from './lib/host.ts'
import { registerAll } from './lib/lifecycle.ts'
import { isSupported } from './lib/plan.ts'
import { createScheduler } from './lib/refresh.ts'
import { bandNode, panelNode, readView } from './lib/render.ts'
import type { PlainNode } from './lib/render.ts'

export default Plugin.define({
  id: 'crux-opencode',
  setup(context) {
    const asText = (v: unknown) => (typeof v === 'string' ? v : undefined)
    const asNumber = (v: unknown) => (typeof v === 'number' ? v : undefined)
    const asByte = (v: unknown) => (typeof v === 'number' ? v : -1)

    const [state, setState] = context.storage.memory('crux-dashboard', { initial: { current: null, running: false } })

    const host: Host = {
      version: asText(context.app?.version),
      directory: asText(context.location.directory),
      cloneDir: asText(dirname(dirname(fileURLToPath(import.meta.url)))),
      // One case per name the manifest lists in env_reads. The source check compares these cases to
      // that list and to the process.env reads, so a name added in one place and not the others fails.
      // Each read is spelled with a literal name so the check can read the name.
      env: (name: string) => {
        switch (name) {
          case 'HOME':
            return asText(process.env.HOME)
          default:
            return undefined
        }
      },
      isFile: (p: string) => {
        try {
          return statSync(p).isFile() === true
        } catch {
          return false
        }
      },
      isDir: (p: string) => {
        try {
          return statSync(p).isDirectory() === true
        } catch {
          return false
        }
      },
      real: (p: string) => {
        try {
          return asText(realpathSync(p))
        } catch {
          return undefined
        }
      },
      read: (p: string) => {
        try {
          return asText(readFileSync(p, 'utf8'))
        } catch {
          return undefined
        }
      },
      // Starts the one reader process. The launch plan builds argv for /usr/bin/env, whose first
      // argument is -i. Any other first argument means the argv did not come from the plan, so the
      // host starts nothing. -i also empties the environment, and the empty env {} below makes the
      // spawn carry no inherited variable even if env ignored its flag.
      start: (argv: string[], cwd: string, sink: ReaderSink) => {
        if (argv[0] !== '-i') {
          return undefined
        }
        try {
          const child = spawn('/usr/bin/env', argv, { env: {}, cwd, stdio: ['ignore', 'pipe', 'pipe'] })
          try {
            child.on('spawn', () => {
              sink.spawned()
            })
            child.on('exit', () => {
              sink.exited()
            })
            child.stdout.on('data', (chunk) => {
              try {
                sink.out(Array.from(chunk, asByte))
              } catch {
                sink.out([-1])
              }
            })
            child.stderr.on('data', (chunk) => {
              try {
                sink.err(Array.from(chunk, asByte))
              } catch {
                sink.err([-1])
              }
            })
            child.on('error', () => {
              sink.failed()
            })
            child.on('close', (code) => {
              sink.closed(asNumber(code))
            })
            return {
              term: () => {
                try {
                  child.kill('SIGTERM')
                } catch {}
              },
              hard: () => {
                try {
                  child.kill('SIGKILL')
                } catch {}
              },
            }
          } catch {
            try {
              child.kill('SIGKILL')
            } catch {}
            return 'untracked'
          }
        } catch {
          return undefined
        }
      },
      after: (ms: number, fn: () => void) => {
        const id = setTimeout(() => {
          fn()
        }, ms)
        return () => {
          clearTimeout(id)
        }
      },
      every: (ms: number, fn: () => void) => {
        const id = setInterval(() => {
          fn()
        }, ms)
        return () => {
          clearInterval(id)
        }
      },
      leaseRead: () => {
        try {
          const r = state.running
          return r === true ? 'held' : r === false ? 'free' : 'unknown'
        } catch {
          return 'unknown'
        }
      },
      leaseWrite: (b: boolean) => {
        try {
          setState((draft) => {
            draft.running = b === true
          })
          return true
        } catch {
          return false
        }
      },
      writeKept: (v: KeptEnvelope | null) => {
        try {
          setState((draft) => {
            draft.current = v
          })
        } catch {
          try {
            setState((draft) => {
              draft.current = null
            })
          } catch {}
        }
      },
      openPanel: () => {
        try {
          return context.ui.panel.open('crux-dashboard') === true
        } catch {
          return false
        }
      },
      panelOpen: () => {
        try {
          return context.ui.panel.current() !== undefined
        } catch {
          return false
        }
      },
      closePanel: () => {
        try {
          context.ui.panel.close()
          return true
        } catch {
          return false
        }
      },
      toast: (code: string) => {
        try {
          context.ui.toast.show({ message: code })
        } catch {}
      },
    }

    const supported = isSupported(host.version)

    const scheduler = createScheduler(host)

    const view = () => readView(supported, () => state.current)

    // Each case returns the theme leaf, or the base text colour when the theme leaves it undefined.
    // The source check accepts only that form: `leaf ?? context.theme.text.base`. The text.base case
    // repeats the base on both sides because the check holds every case to the same shape.
    const colour = (token: string) => {
      try {
        switch (token) {
          case 'syntax.keyword':
            return context.theme.syntax.keyword ?? context.theme.text.base
          case 'syntax.type':
            return context.theme.syntax.type ?? context.theme.text.base
          case 'syntax.function':
            return context.theme.syntax.function ?? context.theme.text.base
          case 'text.feedback.info.base':
            return context.theme.text.feedback.info.base ?? context.theme.text.base
          case 'text.feedback.success.base':
            return context.theme.text.feedback.success.base ?? context.theme.text.base
          case 'text.feedback.error.base':
            return context.theme.text.feedback.error.base ?? context.theme.text.base
          case 'text.feedback.warning.base':
            return context.theme.text.feedback.warning.base ?? context.theme.text.base
          case 'text.muted':
            return context.theme.text.muted ?? context.theme.text.base
          case 'text.base':
            return context.theme.text.base ?? context.theme.text.base
          default:
            return context.theme.text.base
        }
      } catch {
        return undefined
      }
    }

    const draw = (node: PlainNode | null) => {
      if (node === null) {
        return undefined
      }
      if (node.kind === 'spacer') {
        return <box width={node.width} />
      }
      if (node.kind === 'text') {
        return (
          <text>
            {node.spans.map((s) =>
              s.bold ? <b style={{ fg: colour(s.token) }}>{s.text}</b> : <span style={{ fg: colour(s.token) }}>{s.text}</span>,
            )}
          </text>
        )
      }
      if (node.border === null) {
        return (
          <box width={node.width} flexDirection={node.direction}>
            {node.children.map((c) => draw(c))}
          </box>
        )
      }
      return (
        <box
          width={node.width}
          flexDirection={node.direction}
          border={true}
          borderStyle="rounded"
          borderColor={colour(node.border)}
          paddingLeft={node.padding}
          paddingRight={node.padding}
        >
          {node.children.map((c) => draw(c))}
        </box>
      )
    }

    const paint = (n: PlainNode | null) => {
      try {
        return draw(n)
      } catch {
        return undefined
      }
    }

    // The band slot passes its component no input, so the band draws with an undefined width.
    // The manifest's render_input lists no field for session.composer.top.
    const Band = () => <>{paint(bandNode(view(), undefined))}</>

    const Panel = (input) => {
      const inputName = () => {
        try {
          return asText(input.name)
        } catch {
          return undefined
        }
      }
      const inputWidth = () => {
        try {
          return asNumber(input.width)
        } catch {
          return undefined
        }
      }
      createEffect(() => {
        if (inputName() === 'crux-dashboard') {
          scheduler.request('panel')
        }
      })
      return <>{paint(panelNode(view(), inputName(), inputWidth()))}</>
    }

    // A registrar that returns a disposer: attempt keeps it and calls it, guarded, on cleanup.
    const attempt = (register: () => unknown) => {
      try {
        const d = register()
        return () => {
          try {
            d()
          } catch {}
        }
      } catch {
        return undefined
      }
    }

    // A registrar that returns nothing (keymap.layer), so there is no disposer to keep. The cleanup
    // it hands back does nothing; registerAll still counts the registration as made.
    const attemptVoid = (register: () => unknown) => {
      try {
        register()
        return () => {}
      } catch {
        return undefined
      }
    }

    const registrations = [
      () => attempt(() => context.ui.slot({ append: 'session.composer.top', render: Band })),
      () => attempt(() => context.ui.slot({ append: 'session.panel', render: Panel })),
      () =>
        attemptVoid(() =>
          context.keymap.layer(() => ({
            mode: 'global',
            commands: [
              {
                id: 'crux-dashboard',
                title: 'Toggle the crux dashboard',
                group: 'Crux',
                palette: true,
                slash: { name: 'crux-dashboard' },
                run: () => {
                  runCommand(host, scheduler)
                },
              },
            ],
            bindings: [],
          })),
        ),
    ]

    const cleanup = registerAll(registrations, supported ? () => { scheduler.start() } : undefined, () => { scheduler.stop() })

    return cleanup
  },
})
