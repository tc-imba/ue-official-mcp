"""Optionally launch the bundled UE 5.8 project so `sync` has a server to probe.

UE is launched GUI, windowed, and WITHOUT stealing focus (never headless), then we
poll the MCP endpoint until the handshake succeeds.

The MCP plugin defaults to `bAutoStartServer=false`, so we pass
`-ModelContextProtocolStartServer` on the command line to force the HTTP server to
start, and `-ModelContextProtocolPort=N` to align with the endpoint we'll probe.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from . import probe as probe_mod


def _resolve_exe(p: Path) -> Path:
    """Accept either a UnrealEditor.exe path or an engine root directory."""
    if p.suffix.lower() == ".exe":
        return p
    return p / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"


def find_editor(engine: str | None = None) -> Path:
    """Locate UnrealEditor.exe for UE 5.8 via --engine / env / registry / default path."""
    candidates: list[Path] = []
    if engine:
        candidates.append(Path(engine))
    env = os.environ.get("UE_ENGINE_PATH")
    if env:
        candidates.append(Path(env))

    if sys.platform == "win32":
        try:
            import winreg  # noqa: PLC0415 - Windows-only

            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(
                        hive, r"SOFTWARE\EpicGames\Unreal Engine\5.8"
                    ) as key:
                        value, _ = winreg.QueryValueEx(key, "InstalledDirectory")
                        if value:
                            candidates.append(Path(value))
                except OSError:
                    continue
        except Exception:  # noqa: BLE001
            pass
        candidates.append(Path(r"C:\Program Files\Epic Games\UE_5.8"))

    for cand in candidates:
        exe = _resolve_exe(cand)
        if exe.exists():
            return exe

    raise FileNotFoundError(
        "Could not locate UnrealEditor.exe for UE 5.8. Pass --engine <UE install dir or "
        "UnrealEditor.exe> or set UE_ENGINE_PATH."
    )


def _port_from_endpoint(endpoint: str | None) -> int | None:
    """Best-effort port extraction from an http://host:port/path endpoint."""
    if not endpoint:
        return None
    try:
        parsed = urlparse(endpoint)
        port = parsed.port
        if port and 1 <= port <= 65535:
            return port
    except ValueError:
        pass
    return None


def launch_editor(
    uproject: Path, engine: str | None = None, endpoint: str | None = None
) -> subprocess.Popen:
    """Start the editor on `uproject`, GUI windowed, without taking focus.

    Always passes `-ModelContextProtocolStartServer` so the MCP HTTP server starts
    even when the project's `bAutoStartServer` setting is off (it defaults off).
    If an endpoint with an explicit port is supplied, also passes
    `-ModelContextProtocolPort=N` so the server binds to that port.
    """
    exe = find_editor(engine)
    args = [str(exe), str(uproject), "-ModelContextProtocolStartServer"]
    port = _port_from_endpoint(endpoint)
    if port is not None:
        args.append(f"-ModelContextProtocolPort={port}")
    kwargs: dict = {}
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 4  # SW_SHOWNOACTIVATE — show, don't steal focus
        kwargs["startupinfo"] = startupinfo
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(
            subprocess, "DETACHED_PROCESS", 0
        )
    return subprocess.Popen(args, **kwargs)


def wait_for_endpoint(endpoint: str, timeout: float = 180.0, interval: float = 3.0) -> None:
    """Block until the MCP endpoint answers a handshake, or raise on timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if probe_mod.ping(endpoint):
            return
        time.sleep(interval)
    raise TimeoutError(
        f"MCP endpoint {endpoint} did not become ready within {timeout:.0f}s."
    )
