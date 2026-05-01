"""Estado central da aplicação.

Fluxo de inicialização:
1. Lê o config.kdl original do usuário
2. Extrai os valores pra popular a UI
3. Escreve niriconfui.kdl com as configs gerenciadas
4. O config.kdl do usuário só é tocado pra adicionar o include
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from niriconfui.config import APP_CONFIG, BACKUP_DIR, USER_CONFIG


@dataclass
class RuntimeInfo:
    niri_running: bool = False
    has_touchpad: bool = False
    niri_version: str = ""


@dataclass
class ConfigData:
    outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw_user_kdl: str = ""
    app_config_existed: bool = False


class AppState:
    def __init__(self) -> None:
        self._runtime = RuntimeInfo()
        self._config = ConfigData()
        self._dirty = False

    def load(self) -> None:
        from niriconfui import niri_ipc
        self._runtime = RuntimeInfo(
            niri_running=niri_ipc.is_niri_running(),
            has_touchpad=niri_ipc.has_touchpad(),
            niri_version=niri_ipc.get_version(),
        )
        self._config = ConfigData(
            app_config_existed=APP_CONFIG.exists(),
        )
        if USER_CONFIG.exists():
            self._config.raw_user_kdl = USER_CONFIG.read_text(encoding="utf-8")
            self._extract_user_config()
        if APP_CONFIG.exists():
            self._load_app_config()

    def _extract_user_config(self) -> None:
        try:
            import kdl
            doc = kdl.parse(self._config.raw_user_kdl)
            for node in doc.nodes:
                if node.name == "output":
                    name = node.args[0] if node.args else None
                    if name:
                        self._config.outputs[name] = self._extract_output_node(node)
        except Exception:
            pass

    def _extract_output_node(self, node: Any) -> dict[str, Any]:
        data: dict[str, Any] = {}
        for child in node.nodes:
            if child.name == "mode" and child.args:
                data["mode"] = child.args[0]
            elif child.name == "scale" and child.args:
                data["scale"] = child.args[0]
            elif child.name == "transform" and child.args:
                data["transform"] = child.args[0]
            elif child.name == "position":
                data["position_x"] = child.props.get("x", 0)
                data["position_y"] = child.props.get("y", 0)
            elif child.name == "variable-refresh-rate":
                data["vrr"] = True
            elif child.name == "off":
                data["off"] = True
        return data

    def _load_app_config(self) -> None:
        try:
            import kdl
            text = APP_CONFIG.read_text(encoding="utf-8")
            doc = kdl.parse(text)
            for node in doc.nodes:
                if node.name == "output":
                    name = node.args[0] if node.args else None
                    if name:
                        self._config.outputs[name] = self._extract_output_node(node)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Backup                                                               #
    # ------------------------------------------------------------------ #

    def create_backup(self) -> Path:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        dest = BACKUP_DIR / "config.kdl"
        if USER_CONFIG.exists():
            shutil.copy2(USER_CONFIG, dest)
        return dest

    def backup_exists(self) -> bool:
        return (BACKUP_DIR / "config.kdl").exists()

    # ------------------------------------------------------------------ #
    # Escrita                                                              #
    # ------------------------------------------------------------------ #

    def ensure_include(self) -> bool:
        """Garante que config.kdl tem include 'niriconfui.kdl'.

        Retorna True se já existia, False se foi adicionado agora.
        """
        if not USER_CONFIG.exists():
            return False

        content = USER_CONFIG.read_text(encoding="utf-8")
        include_line = 'include "niriconfui.kdl"'

        if include_line in content:
            return True

        addition = (
            "\n"
            "// Gerenciado pelo niriconfui — não remova esta linha\n"
            f"{include_line}\n"
        )
        USER_CONFIG.write_text(content + addition, encoding="utf-8")
        return False

    def save(self) -> None:
        """Escreve niriconfui.kdl e garante o include no config.kdl."""
        APP_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        APP_CONFIG.write_text(self._render_app_config(), encoding="utf-8")
        self.ensure_include()
        self._dirty = False

    def _render_app_config(self) -> str:
        lines = ["// Gerenciado pelo niriconfui — não edite manualmente\n"]
        for name, props in self._config.outputs.items():
            lines.append(self._render_output(name, props))
        return "\n".join(lines)

    def _render_output(self, name: str, props: dict[str, Any]) -> str:
        parts = [f'output "{name}" {{']
        if "mode" in props:
            parts.append(f'    mode "{props["mode"]}"')
        if "scale" in props:
            parts.append(f'    scale {props["scale"]}')
        if "transform" in props:
            parts.append(f'    transform "{props["transform"]}"')
        if "position_x" in props or "position_y" in props:
            x = props.get("position_x", 0)
            y = props.get("position_y", 0)
            parts.append(f'    position x={x} y={y}')
        if props.get("vrr"):
            parts.append("    variable-refresh-rate")
        if props.get("off"):
            parts.append("    off")
        parts.append("}")
        return "\n".join(parts)

    # ------------------------------------------------------------------ #
    # Propriedades                                                         #
    # ------------------------------------------------------------------ #

    @property
    def niri_running(self) -> bool:
        return self._runtime.niri_running

    @property
    def has_touchpad(self) -> bool:
        return self._runtime.has_touchpad

    @property
    def niri_version(self) -> str:
        return self._runtime.niri_version

    @property
    def outputs(self) -> dict[str, dict[str, Any]]:
        return self._config.outputs

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def mark_dirty(self) -> None:
        self._dirty = True

    def mark_clean(self) -> None:
        self._dirty = False

    def set_output_prop(self, name: str, key: str, value: Any) -> None:
        if name not in self._config.outputs:
            self._config.outputs[name] = {}
        self._config.outputs[name][key] = value
        self._dirty = True
