"""Tests for clipfix.

Covers two layers:

* Unit tests against the in-process functions (`clean`, `unwrap_urls`),
  imported directly from the `clipfix` script.
* End-to-end tests that invoke the script as a subprocess and pipe data
  through stdin/stdout, the way a Shortcut or shell pipeline would.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "clipfix"


def _load_clipfix_module():
    """Import the extension-less `clipfix` script as a module.

    `spec_from_file_location` won't infer a loader for an extensionless file,
    so we pass `SourceFileLoader` explicitly.
    """
    loader = SourceFileLoader("clipfix", str(SCRIPT_PATH))
    spec = importlib.util.spec_from_loader("clipfix", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


clipfix = _load_clipfix_module()


# ---------------------------------------------------------------------------
# unwrap_urls
# ---------------------------------------------------------------------------


class TestUnwrapUrls:
    def test_single_line_url_unchanged(self):
        url = "https://example.com/path?a=1&b=2"
        assert clipfix.unwrap_urls(url) == url

    def test_two_line_wrap_is_joined(self):
        wrapped = (
            "https://example.com/oauth/authorize?response_type=code&client_id=ec53f589-ceea-4\n"
            "760-86dc-e431fad305a1"
        )
        expected = (
            "https://example.com/oauth/authorize?response_type=code&client_id="
            "ec53f589-ceea-4760-86dc-e431fad305a1"
        )
        assert clipfix.unwrap_urls(wrapped) == expected

    def test_many_line_wrap_is_joined(self):
        wrapped = "https://a.example.com/x\n" + "\n".join(f"part{i}" for i in range(5))
        result = clipfix.unwrap_urls(wrapped)
        assert "\n" not in result
        assert result.startswith("https://a.example.com/xpart0")
        assert result.endswith("part4")

    def test_break_with_trailing_whitespace_not_joined(self):
        """A space at the start of the next line means the URL has ended."""
        text = "https://example.com/foo\n bar"
        # The leading space on the second line breaks the URL — should be untouched.
        assert clipfix.unwrap_urls(text) == text

    def test_break_with_trailing_indent_not_joined(self):
        """Indentation after the break is the strongest signal that the URL ended."""
        text = "  curl https://example.com/api\n  echo done"
        assert clipfix.unwrap_urls(text) == text

    def test_http_and_https_both_match(self):
        wrapped_http = "http://example.com/a\nb"
        wrapped_https = "https://example.com/a\nb"
        assert clipfix.unwrap_urls(wrapped_http) == "http://example.com/ab"
        assert clipfix.unwrap_urls(wrapped_https) == "https://example.com/ab"

    def test_non_url_text_with_newlines_preserved(self):
        text = "line one\nline two\nline three"
        assert clipfix.unwrap_urls(text) == text

    def test_url_in_middle_of_paragraph(self):
        text = "See https://example.com/long-path\nfoo for details."
        # `foo` directly continues the URL with no whitespace, so it joins.
        # This is the documented heuristic; if the user wants to break it
        # they should add whitespace.
        assert clipfix.unwrap_urls(text) == "See https://example.com/long-pathfoo for details."

    def test_real_world_oauth_wrap(self):
        """The exact OAuth URL from the README/issue."""
        wrapped = (
            "https://retro-claude.vercel.app/oauth/authorize?response_type=code&client_id=ec53f589-ceea-4\n"
            "760-86dc-e431fad305a1&code_challenge=KnjMuRfjsyhO3XaLla90h4P5Mr9-0y00Qdylv2EWATU&code_challe\n"
            "nge_method=S256&redirect_uri=http%3A%2F%2Flocalhost%3A54757%2Fcallback&state=oO2SA-5aXSXFptJ\n"
            "s0UoRb-9pio6UAYammlSYA1_Evl0&scope=workspace%3Aread+workspace%3Awrite&resource=https%3A%2F%2\n"
            "Fretromcp-server-production.up.railway.app%2Fmcp"
        )
        result = clipfix.unwrap_urls(wrapped)
        assert "\n" not in result
        assert result.startswith("https://retro-claude.vercel.app/oauth/authorize")
        assert result.endswith("railway.app%2Fmcp")
        # All the broken tokens should reassemble:
        assert "ec53f589-ceea-4760-86dc-e431fad305a1" in result


# ---------------------------------------------------------------------------
# clean (the full pipeline: unwrap then dedent)
# ---------------------------------------------------------------------------


class TestClean:
    def test_strips_common_two_space_indent(self):
        text = "  set -euo pipefail\n  echo hi"
        assert clipfix.clean(text) == "set -euo pipefail\necho hi"

    def test_strips_common_four_space_indent(self):
        text = "    one\n    two"
        assert clipfix.clean(text) == "one\ntwo"

    def test_preserves_relative_indentation(self):
        text = "  if true; then\n    echo yes\n  fi"
        assert clipfix.clean(text) == "if true; then\n  echo yes\nfi"

    def test_no_common_indent_no_change(self):
        text = "no indent here\nnor here"
        assert clipfix.clean(text) == text

    def test_blank_lines_dont_break_dedent(self):
        text = "  one\n\n  two"
        assert clipfix.clean(text) == "one\n\ntwo"

    def test_url_unwrap_runs_before_dedent(self):
        """If dedent ran first it would strip the indent before unwrap could
        use it as a signal, and the URL would incorrectly join the next line."""
        text = "  curl https://example.com/x\n  echo done"
        # After unwrap_urls (which sees the indent on line 2 and bails out),
        # dedent strips two spaces. URL stays intact, echo stays separate.
        assert clipfix.clean(text) == "curl https://example.com/x\necho done"

    def test_url_and_dedent_together(self):
        text = (
            "  visit https://example.com/oauth?client=ec53f589-ceea-4\n"
            "760-86dc-e431fad305a1 for details"
        )
        # Line 2 has no leading whitespace, so the URL joins. Then dedent
        # strips the leading two spaces.
        assert clipfix.clean(text) == (
            "visit https://example.com/oauth?client=ec53f589-ceea-4760-86dc-e431fad305a1 for details"
        )


# ---------------------------------------------------------------------------
# CLI / subprocess integration
# ---------------------------------------------------------------------------


def _run_cli(stdin: str | None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        input=stdin,
        capture_output=True,
        text=True,
    )


class TestCli:
    def test_stdin_to_stdout_dedent(self):
        result = _run_cli("  one\n  two")
        assert result.returncode == 0
        assert result.stdout == "one\ntwo"

    def test_stdin_to_stdout_url_unwrap(self):
        result = _run_cli("https://example.com/a\nb")
        assert result.returncode == 0
        assert result.stdout == "https://example.com/ab"

    def test_empty_stdin_falls_back_to_clipboard(self):
        """Empty stdin (e.g. from a Shortcut with `Pass Input: ignored`) must
        fall back to clipboard mode, not silently exit. We check that the
        script either succeeds or reports "clipboard is empty" — i.e. it
        clearly took the clipboard path."""
        result = _run_cli("")
        # Either success (clipboard had content) or exit 1 with the empty
        # clipboard message — both indicate clipboard mode was entered.
        if result.returncode == 1:
            assert "clipboard is empty" in result.stderr
        else:
            assert result.returncode == 0

    def test_no_trailing_newline_preserved(self):
        """Don't silently add a trailing newline — the user copied what they copied."""
        result = _run_cli("  hello")
        assert result.stdout == "hello"

    def test_trailing_newline_preserved(self):
        result = _run_cli("  hello\n")
        assert result.stdout == "hello\n"


# ---------------------------------------------------------------------------
# Clipboard mode (macOS only)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "darwin", reason="clipboard mode is macOS-only")
class TestClipboardMode:
    """Round-trip a sentinel value through the real macOS clipboard.

    Saves and restores whatever was on the clipboard so we don't trash the
    user's clipboard if they run the tests locally.
    """

    def _pbpaste(self) -> str:
        return subprocess.check_output(["pbpaste"], text=True)

    def _pbcopy(self, text: str) -> None:
        subprocess.run(["pbcopy"], input=text, text=True, check=True)

    def test_round_trip_through_clipboard(self):
        original = self._pbpaste()
        try:
            self._pbcopy("  hello\n  world")
            result = subprocess.run(
                [sys.executable, str(SCRIPT_PATH)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            assert self._pbpaste() == "hello\nworld"
            assert "cleaned clipboard" in result.stderr
        finally:
            self._pbcopy(original)
