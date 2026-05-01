"""Comunicação local com o niri via `niri msg`. Sem dependências externas em runtime."""

from __future__ import annotations

import json
import os
from typing import Callable


def _run_sync(args: list[str], timeout: float = 5.0) -> tuple[str, str, int]:
    import subprocess
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.stdout, r.stderr, r.returncode
    except FileNotFoundError:
        return "", "niri: comando não encontrado", 1
    except subprocess.TimeoutExpired:
        return "", "niri msg: timeout", 1


def _run_async(args: list[str], callback: Callable[[str, str, int], None]) -> None:
    import gi
    gi.require_version("Gio", "2.0")
    gi.require_version("GLib", "2.0")
    from gi.repository import Gio, GLib

    try:
        proc = Gio.Subprocess.new(
            args,
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE,
        )
    except GLib.Error:
        GLib.idle_add(lambda: callback("", "niri: não encontrado", 1) or False)
        return

    def _on_done(source: Gio.Subprocess, result: Gio.AsyncResult) -> None:
        try:
            _, stdout_bytes, stderr_bytes = source.communicate_finish(result)
            stdout = stdout_bytes.get_data().decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.get_data().decode("utf-8", errors="replace") if stderr_bytes else ""
            rc = 0 if source.get_exit_status() == 0 else 1
        except GLib.Error as exc:
            stdout, stderr, rc = "", str(exc), 1
        callback(stdout, stderr, rc)

    proc.communicate_async(None, None, _on_done)


def is_niri_running() -> bool:
    stdout, _, rc = _run_sync(["niri", "msg", "version"])
    return rc == 0 and bool(stdout.strip())


def get_version() -> str:
    stdout, _, rc = _run_sync(["niri", "--version"])
    return stdout.strip() if rc == 0 else "desconhecida"


def has_touchpad() -> bool:
    try:
        for dev in os.listdir("/sys/class/input"):
            name_file = f"/sys/class/input/{dev}/device/name"
            if os.path.exists(name_file):
                with open(name_file) as fh:
                    if "touchpad" in fh.read().lower():
                        return True
    except Exception:
        pass
    return False


def validate_config(config_path: str | None = None) -> tuple[bool, str]:
    cmd = ["niri", "validate"]
    if config_path:
        cmd += ["--config", config_path]
    stdout, stderr, rc = _run_sync(cmd, timeout=10.0)
    if rc == 0:
        return True, stdout.strip() or "Config válido."
    return False, stderr.strip() or stdout.strip() or "Erro desconhecido."


def get_outputs(callback: Callable[[list[dict]], None]) -> None:
    def _done(stdout: str, _stderr: str, rc: int) -> None:
        if rc != 0:
            callback([])
            return
        try:
            data = json.loads(stdout)
            callback(list(data.values()) if isinstance(data, dict) else data)
        except json.JSONDecodeError:
            callback([])
    _run_async(["niri", "msg", "--json", "outputs"], _done)
