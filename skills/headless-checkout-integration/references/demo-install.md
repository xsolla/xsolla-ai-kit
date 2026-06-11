# Headless Checkout Demo (Full React + Vite)

Guide for an AI agent. `headless-checkout-demo` is the **most complete** reference implementation — React +
TypeScript + Vite, covering every payment method, all NextActions, 3DS, saved methods, styling, and the return page.

**When to use this vs fetching docs:**

- **This demo** — the richest, most complete source of truth, and **fast to access** once installed (the agent reads
  local files, no `web_fetch` round-trips). **Cost:** requires cloning the repo locally and linking it to the agent.
- **`documentation.md` / GitHub examples** — no local setup, always current, but each lookup is a network fetch and the
  single-file examples are narrower than the demo.

Note the trade-off in *kind*, not just access cost: the docs/examples give **abstract** patterns (framework-agnostic,
minimal), while the demo is **one concrete implementation** — a specific React + Vite app with specific UI choices. A
concrete example isn't always better than an abstract one: shops differ, and so do their interfaces and frameworks.
Demo code may need adapting (or may not transfer at all) to a different stack, whereas an abstract doc pattern maps onto
any of them.

Prefer the demo when building a real integration that will reference many patterns, especially on a similar React/Vite
stack; prefer doc/example fetches for a one-off lookup, when you can't clone locally, or when the shop's framework and
UI differ enough that the abstract pattern transfers more cleanly.

---

## Step 1: Clone the Repo

The repository is **not** directly readable by the agent over the network — it must live on disk next to the
shop project.

```bash
# from your project root
cd ..
git clone https://github.com/xsolla/headless-checkout-demo.git
```

This puts `headless-checkout-demo/` as a sibling of your project directory.

---

## Step 2: Install & Run (optional)

To run the demo locally as well as read it:

```bash
cd headless-checkout-demo
npm install
npm run dev          # Vite dev server
```

A sandbox payment token is still required to drive a live payment — see `initialization.md` (Method 3).

---

## Step 3: Link the Demo to the Agent

### Claude Code

`/add-dir` is the way to link the demo **on the fly** — it adds the repo to the session's working directories for the
rest of the session, with no file edits. The agent **cannot run `/add-dir` itself** (it's an interactive CLI command,
not a shell command). So **ask the user to run it**, with the absolute path already filled in:

> Run this in the input box to link the demo to my context for this session:
>
> ```
> /add-dir /absolute/path/to/headless-checkout-demo
> ```

Resolve the absolute path first (e.g. the sibling you cloned in Step 1) and paste the real path into the message — don't
leave a placeholder. **After the user confirms they've run it, continue with their original request** using the demo as
a reference.

> The agent can already read the cloned repo by absolute path (Read/Grep/Bash) without `/add-dir`. `/add-dir` adds value
> by putting the demo into the session's working dirs so it's picked up by background context and search — prefer it for
> sustained work against the demo.

**Durable alternative (persists across sessions):** import into `CLAUDE.md` using `@` syntax, or launch with
`claude --add-dir <path>`. Use this only when the demo should load automatically every session — for a one-off task,
`/add-dir` is cleaner (no committed/tracked changes):

```markdown
# Reference implementation

See @../headless-checkout-demo/README.md for Headless Checkout patterns.
```

Or reference specific files/dirs inline in a single message:

```
@../headless-checkout-demo/src/
```

### Cursor

Add both repos to a shared workspace via a `.code-workspace` file:

```json
{
  "folders": [
    {
      "path": "."
    },
    {
      "path": "../headless-checkout-demo"
    }
  ]
}
```

Cursor indexes all folders in the workspace — use `@headless-checkout-demo` or `@codebase` to query across both repos.

---

## What's Inside

The demo is the broadest single source for patterns this skill references:

- Full `init()` + `setToken()` bootstrap and token handling
- Payment methods list, selection, and country handling
- Bank-card form built from `form.fields`, all five NextActions, both 3DS paths
- `redirect` flow (e-wallets, 3DS-via-redirect), QR, mobile, Google/Apple Pay
- Saved methods, custom styling (`setSecureComponentStyles`), the return page

When a pattern in another reference points at an example, the demo usually has a richer, runnable version of it.

---

## Checklist

- [ ] `headless-checkout-demo` cloned as a sibling of the project
- [ ] (optional) `npm install && npm run dev` runs the demo locally
- [ ] Demo linked to the agent — Claude Code: user ran `/add-dir <abs-path>` (or `@` import / `--add-dir` for durable);
      Cursor: workspace folder added
- [ ] Continued with the user's original request once the link is confirmed
- [ ] Sandbox token available for live payments (see `initialization.md`)