"""Calcpad discovery and synchronous process boundary (no GTK).

run_cli owns the temporary input; successful output ownership transfers to the
caller. Error rendering/escaping and source acquisition are injected so the
existing desktop error presentation and lazy source reads remain unchanged.
"""
from __future__ import annotations
from collections.abc import Callable, Sequence
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

def discover_cli():
    env = os.environ.get("CALCPAD_CLI")
    if env:
        p = Path(env).expanduser()
        if p.suffix.lower() == ".dll" and p.is_file():
            return ["dotnet", str(p)], f"DLL from $CALCPAD_CLI: {p}"
        if p.is_file() and os.access(p, os.X_OK):
            return [str(p)], f"Binary from $CALCPAD_CLI: {p}"
    for cmd in ("CalcpadCli", "calcpad-cli", "calcpadcli"):
        path = shutil.which(cmd)
        if path: return [path], f"PATH: {path}"
    for dll in ("/usr/share/CalcpadCE/Cli.dll",
                "/usr/lib/calcpadce/Cli.dll",
                "/opt/CalcpadCE/Cli.dll",
                str(Path.home() / ".local/share/CalcpadCE/Cli.dll")):
        if Path(dll).is_file():
            return ["dotnet", dll], f"System DLL: {dll}"
    home = Path.home() / "CalcpadCE/Calcpad.Cli/bin"
    for cfg in ("Release", "Debug"):
        for tfm in ("net10.0", "net9.0", "net8.0"):
            for name in ("Cli.dll", "Calcpad.Cli.dll"):
                p = home / cfg / tfm / name
                if p.is_file():
                    return ["dotnet", str(p)], f"Local build: {p}"
    return None, ("CalcpadCli not found.\n"
                  "Build it from source:\n"
                  "  git clone https://github.com/imartincei/CalcpadCE.git\n"
                  "  cd CalcpadCE\n"
                  "  dotnet publish -c Release Calcpad.Cli -o ~/.local/share/CalcpadCE\n"
                  "  export CALCPAD_CLI=$HOME/.local/share/CalcpadCE/Cli.dll")

def run_cli(
    command: Sequence[str] | None,
    hint: str,
    out_format: str,
    body_only: bool,
    get_source: Callable[[], str],
    wrap_preview: Callable[[str], str],
    escape: Callable[[str], str],
    source_text: str | None = None,
) -> tuple[str | None, str | None]:
    if not command:
        return None, wrap_preview(
            f"<pre style='color:#b00;font-family:monospace;padding:1em'>"
            f"{escape(hint)}</pre>")
    try:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".cpd", delete=False, encoding="utf-8")
        tmp.write(source_text if source_text is not None else get_source()); tmp.close(); in_path = tmp.name
    except OSError as e:
        return None, wrap_preview(
            f"<pre style='color:#b00'>Cannot create temp file: {e}</pre>")
    out_path = str(Path(in_path).with_suffix(f".{out_format}"))
    cmd = list(command) + [in_path, out_path, "-s"]
    if body_only and out_format in ("html","htm"): cmd.append("-b")
    env = os.environ.copy(); env["DOTNET_CLI_UI_LANGUAGE"] = "en"
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
        if r.returncode != 0 or not Path(out_path).exists():
            msg = ((r.stderr or "") + "\n" + (r.stdout or "")).strip() \
                  or f"CLI exit code {r.returncode}"
            return None, wrap_preview(
                f"<pre style='color:#b00;font-family:monospace;padding:1em'>"
                f"{escape(msg)}</pre>")
        return out_path, None
    except subprocess.TimeoutExpired:
        return None, wrap_preview(
            "<pre style='color:#b00'>Calculation timed out (60s).</pre>")
    except OSError as e:
        return None, wrap_preview(
            f"<pre style='color:#b00'>{escape(str(e))}</pre>")
    finally:
        try: os.unlink(in_path)
        except OSError: pass
