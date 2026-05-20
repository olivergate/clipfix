# clipfix

[![test](https://github.com/olivergate/clipfix/actions/workflows/test.yml/badge.svg)](https://github.com/olivergate/clipfix/actions/workflows/test.yml)

> A tiny clipboard hygiene tool. Strips leading whitespace from copied code
> blocks and joins URLs that got soft-wrapped onto multiple lines.

Bind it to a macOS hotkey (e.g. `⌃⌥⌘V`) and your "clean paste" is one
keystroke away.

## The problem

You copy a snippet out of Claude, ChatGPT, a terminal pager, or a Slack
code block, and you get one of these:

```
  set -euo pipefail
  BACKUP=~/.claude/credentials.backup.json
  security find-generic-password -s "Claude Code-credentials" -w > "$BACKUP"
```

Every line has two spaces of indentation that breaks the snippet when you
paste into a shell. Or you get this:

```
https://retro-claude.vercel.app/oauth/authorize?response_type=code&client_id=ec5
3f589-ceea-4760-86dc-e431fad305a1&code_challenge=KnjMuRfjsyhO3XaLla90h4P5Mr9-0y0
```

A URL with literal newlines in the middle of tokens, because the terminal
that printed it was narrower than the URL.

`clipfix` cleans up both, in one keystroke.

## How it works

Two transformations, applied in this order:

1. **Join soft-wrapped URLs.** A URL is matched only if it starts with
   `http(s)://`, continues with RFC 3986 URL-safe characters, and the line
   break has *no surrounding whitespace*. That last condition is the
   heuristic that keeps unrelated lines from getting glued together — if
   the next line is indented or starts with a space, the URL is considered
   ended.
2. **Strip common leading whitespace** via Python's `textwrap.dedent`.
   Relative indentation inside the block is preserved.

URL-unwrap runs before dedent, so the original indentation is what
determines whether a line continues a URL — not the post-dedent text.

## Install

Clone the repo and symlink the script into `~/.local/bin` (a standard
user-bin location that's on `$PATH` on most modern setups — no sudo
required):

```bash
git clone https://github.com/olivergate/clipfix.git
cd clipfix
mkdir -p ~/.local/bin
ln -sf "$PWD/clipfix" ~/.local/bin/clipfix
```

Verify it's on your `$PATH`:

```bash
which clipfix    # should print ~/.local/bin/clipfix
```

If `which clipfix` finds nothing, add `~/.local/bin` to your shell's
PATH — for zsh, append this to `~/.zshrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Prefer a system-wide install? Symlink into `/usr/local/bin` instead
(needs sudo on most setups):

```bash
sudo ln -sf "$PWD/clipfix" /usr/local/bin/clipfix
```

Requires Python 3.10+ (ships with recent macOS). No third-party
dependencies — `clipfix` uses only the standard library.

## Usage

```bash
clipfix                 # macOS: read clipboard, transform, write clipboard
pbpaste | clipfix       # stdin -> stdout (works on Linux too)
clipfix < snippet.txt   # file -> stdout
```

In clipboard mode the script prints a one-line summary to stderr:

```
clipfix: cleaned clipboard (412 -> 387 chars)
```

Exit codes:

| Code | Meaning                                                       |
| ---- | ------------------------------------------------------------- |
| 0    | Success                                                       |
| 1    | No input (empty clipboard, empty stdin)                       |
| 2    | Clipboard mode requested but `pbpaste`/`pbcopy` not available |

## Bind to a macOS hotkey

The workflow is a three-keystroke chord:

1. Select text → **⌘C** (copy as normal — clipboard now holds the messy text)
2. **⌘⌥C** (`clipfix` cleans the clipboard in place — no visible feedback)
3. **⌘V** in your target app (pastes the cleaned text)

The middle step is what `clipfix` adds. No keystroke simulation, no
Accessibility permission, no Services menu — it just transforms whatever
is on your clipboard.

### Setup

1. Open **Shortcuts.app** (built into macOS).
2. **File → New Shortcut**, name it `Clean Copy`.
3. Add one action: **Run Shell Script**.
   - Shell: `/bin/zsh`
   - Pass Input: **to stdin** (the default — doesn't matter, we ignore stdin)
   - Script (replace `<your-home>` with your actual home directory —
     Shortcuts doesn't reliably expand `~`):
     ```
     /Users/<your-home>/.local/bin/clipfix
     ```
     If you symlinked into `/usr/local/bin` instead, use that path.
4. In the shortcut's info panel (ⓘ icon, top-right):
   - Leave "Use as Quick Action" **off**.
   - Set **Keyboard Shortcut** to **⌘⌥C**.
5. Close the editor (⌘W) — Shortcuts saves automatically.

### About the ⌘⌥C hotkey

`⌘⌥C` collides with **Finder's "Copy as Pathname"** when Finder is the
frontmost app. When you've got text selected in any normal text context
(browser, editor, terminal, chat), Finder isn't focused, so the
Shortcut wins. But if you find yourself reaching for "Copy as Pathname"
in Finder, pick a different hotkey — `⌃⌥⌘C` (three modifiers) is
collision-free.

### Why not one-keystroke?

The obvious dream is `select → ⌘⌥C → ⌘V` (skip the manual ⌘C). It's
achievable on macOS in two ways and both have real costs:

- **Simulate ⌘C via `osascript`.** Requires Accessibility permission for
  `osascript`, which macOS will prompt for the first time and is fiddly
  to grant correctly.
- **Use Shortcuts.app's "Receive from Quick Actions".** Should pass the
  selection to the Shortcut as input, but in practice the integration is
  unreliable — Quick Actions don't always register, and a hotkey bound
  in the info panel doesn't always invoke the Shortcut in Quick Action
  context.

The three-keystroke flow above sidesteps both problems. It works in
every app, needs no permissions, and the cost is one extra chord you
were already pressing (⌘C is muscle memory anyway).

## Development

Tests use `pytest` and the standard library only.

```bash
git clone https://github.com/olivergate/clipfix.git
cd clipfix
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
pytest tests/ -v
```

The suite covers:

- **Unit tests** for `unwrap_urls` and `clean`, exercising the URL
  heuristic on real-world inputs (including the OAuth URL from the
  motivating issue) and the dedent behavior on various indentation
  shapes.
- **CLI integration tests** that invoke the script via subprocess and
  pipe data through stdin/stdout, mirroring how a shell pipeline or
  Shortcut would call it.
- **macOS clipboard round-trip test** that copies a sentinel value to
  the real system clipboard, runs `clipfix` in clipboard mode, and
  asserts the result — restoring the original clipboard afterwards so
  it doesn't trash your paste buffer. Skipped on non-macOS runners.

CI runs the suite on macOS and Ubuntu across Python 3.10–3.13 via
[`.github/workflows/test.yml`](.github/workflows/test.yml).

## Examples

**Indented bash snippet:**

```
  set -euo pipefail
  BACKUP=~/.claude/credentials.backup.json
  security find-generic-password -s "Claude Code-credentials" -w > "$BACKUP"
```

→

```
set -euo pipefail
BACKUP=~/.claude/credentials.backup.json
security find-generic-password -s "Claude Code-credentials" -w > "$BACKUP"
```

**Soft-wrapped URL:**

```
https://example.com/oauth/authorize?response_type=code&client_id=ec53f589-ceea-4
760-86dc-e431fad305a1&code_challenge=KnjMuRfjsyhO3XaLla90h4P5Mr9-0y00Qdylv2EWATU
```

→ (single line)

```
https://example.com/oauth/authorize?response_type=code&client_id=ec53f589-ceea-4760-86dc-e431fad305a1&code_challenge=KnjMuRfjsyhO3XaLla90h4P5Mr9-0y00Qdylv2EWATU
```

**Both at once** — indented snippet that also contains a wrapped URL:

```
  curl 'https://example.com/api/v1/things?token=eyJhbGciOiJIUzI1NiIsInR
5cCI6IkpXVCJ9.deadbeef'
  echo done
```

→

```
curl 'https://example.com/api/v1/things?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.deadbeef'
echo done
```

(The `echo done` stays on its own line because the original indentation
on that line told `clipfix` the URL had ended.)

## License

MIT — see [LICENSE](LICENSE).
