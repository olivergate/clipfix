# clipfix

[![test](https://github.com/olivergate/clipfix/actions/workflows/test.yml/badge.svg)](https://github.com/olivergate/clipfix/actions/workflows/test.yml)

A tiny clipboard hygiene tool for macOS. Bound to a hotkey, it cleans up
text you've just copied:

- Strips common leading whitespace (indented code blocks paste-ready).
- Rejoins URLs that got soft-wrapped onto multiple lines.

## Install

Clone the repo and symlink `clipfix` onto your `PATH`:

```bash
git clone https://github.com/olivergate/clipfix.git
cd clipfix
mkdir -p ~/.local/bin
ln -sf "$PWD/clipfix" ~/.local/bin/clipfix
```

Verify:

```bash
which clipfix    # should print ~/.local/bin/clipfix
```

If `which clipfix` finds nothing, add `~/.local/bin` to your `PATH` —
for zsh, append this to `~/.zshrc` and open a new terminal:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Requires Python 3.10+ (ships with recent macOS). No third-party
dependencies.

## Bind to a macOS hotkey

The workflow is three keystrokes:

1. Select text → **⌘C** (copy as normal)
2. **⌘⌥C** (`clipfix` cleans the clipboard in place — no visible feedback)
3. **⌘V** in your target app (pastes the cleaned text)

### Setup

1. Open **Shortcuts.app**.
2. **File → New Shortcut**, name it `Clean Copy`.
3. Add one **Run Shell Script** action:
   - Shell: `/bin/zsh`
   - Script (Shortcuts doesn't reliably expand `~`, so use the absolute
     path):
     ```
     /Users/<your-home>/.local/bin/clipfix
     ```
4. Click the **ⓘ** info button (top-right) and set **Keyboard Shortcut**
   to **⌘⌥C**.
5. Close the editor (⌘W).

### Hotkey collision

`⌘⌥C` is also Finder's "Copy as Pathname". When Finder is the frontmost
app, Finder wins. In any other text context (browser, editor, terminal,
chat) the Shortcut wins. If you actively use Finder's pathname copy,
pick `⌃⌥⌘C` instead.

## Usage from the command line

```bash
clipfix                 # read clipboard, transform, write clipboard
pbpaste | clipfix       # stdin -> stdout
clipfix < snippet.txt   # file -> stdout
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
pytest tests/ -v
```

CI runs the suite on macOS and Ubuntu across Python 3.10-3.13.

## License

MIT — see [LICENSE](LICENSE).
