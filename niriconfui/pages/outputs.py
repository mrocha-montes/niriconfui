"""Página de configuração de outputs (monitores)."""

from __future__ import annotations

from typing import Any

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from niriconfui.pages.base import BasePage
from niriconfui.state import AppState

TRANSFORMS = ["normal", "90", "180", "270", "flipped", "flipped-90", "flipped-180", "flipped-270"]
TRANSFORM_LABELS = ["Normal", "90°", "180°", "270°", "Espelhado", "Espelhado 90°", "Espelhado 180°", "Espelhado 270°"]

# O niri retorna transform com inicial maiúscula (ex: "Normal", "270")
# Normaliza pra lowercase pra comparar com TRANSFORMS
def _normalize_transform(t: str) -> str:
    return t.lower() if t else "normal"


class OutputsPage(BasePage):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        self.set_title("Outputs")
        self.set_description("Configuração de monitores")
        self._built = False
        # Container único que controlamos — evita tentar remover ScrolledWindow
        self._container = Adw.PreferencesGroup()
        self.add(self._container)
        self._groups: list[Adw.PreferencesGroup] = [self._container]

    def _clear(self) -> None:
        """Remove todos os grupos que adicionamos."""
        for g in self._groups:
            try:
                self.remove(g)
            except Exception:
                pass
        self._groups = []

    def _add_group(self, group: Adw.PreferencesGroup) -> None:
        self.add(group)
        self._groups.append(group)

    def refresh(self) -> None:
        if self._built:
            return
        self._build_ui()
        self._built = True

    def _build_ui(self) -> None:
        self._clear()
        outputs = self._state.outputs

        if not outputs:
            if self._state.niri_running:
                self._build_loading()
                from niriconfui import niri_ipc
                niri_ipc.get_outputs(self._on_outputs_loaded)
            else:
                self._build_empty()
            return

        self._build_outputs(outputs)

    def _build_loading(self) -> None:
        group = Adw.PreferencesGroup()
        sp = Gtk.Spinner(spinning=True)
        sp.set_size_request(32, 32)
        sp.set_margin_top(48)
        sp.set_halign(Gtk.Align.CENTER)
        group.add(sp)
        self._add_group(group)

    def _build_empty(self) -> None:
        group = Adw.PreferencesGroup()
        status = Adw.StatusPage(
            title="Nenhum output encontrado",
            description="O niri não está rodando e nenhum config foi detectado.\n"
                        "Configure manualmente abaixo ou inicie o niri primeiro.",
            icon_name="display-symbolic",
        )
        group.add(status)
        self._add_group(group)

        add_group = Adw.PreferencesGroup(title="Adicionar Output")
        entry = Adw.EntryRow(title="Nome do output (ex: HDMI-1, DP-1)")
        add_group.add(entry)
        btn = Gtk.Button(label="Adicionar")
        btn.add_css_class("suggested-action")
        btn.set_margin_top(8)
        btn.connect("clicked", lambda _: self._add_manual_output(entry.get_text()))
        add_group.add(btn)
        self._add_group(add_group)

    def _on_outputs_loaded(self, outputs_list: list[dict]) -> None:
        """Callback do IPC — converte formato niri pra nosso dict."""
        self._clear()

        if not outputs_list:
            self._build_empty()
            return

        outputs: dict[str, dict[str, Any]] = {}
        for o in outputs_list:
            name = o.get("name", "")
            if not name:
                continue

            logical = o.get("logical") or {}

            # FIX: current_mode é um índice inteiro, não um objeto
            # O objeto do modo fica em o["modes"][current_mode_index]
            mode_index = o.get("current_mode")
            modes = o.get("modes", [])
            if mode_index is not None and isinstance(mode_index, int) and mode_index < len(modes):
                mode_obj = modes[mode_index]
            else:
                mode_obj = {}

            width = mode_obj.get("width", 1920)
            height = mode_obj.get("height", 1080)
            refresh = mode_obj.get("refresh_rate", 60000)
            mode_str = f"{width}x{height}@{refresh / 1000:.3f}"

            # FIX: transform vem capitalizado do niri ("Normal", "270")
            # normaliza pra lowercase pra bater com TRANSFORMS
            raw_transform = logical.get("transform", "normal")
            transform = _normalize_transform(raw_transform)

            outputs[name] = {
                "make": o.get("make", ""),
                "model": o.get("model", ""),
                "mode": mode_str,
                "available_modes": modes,
                "scale": logical.get("scale", 1.0),
                "transform": transform,
                "position_x": logical.get("x", 0),
                "position_y": logical.get("y", 0),
                "vrr_supported": o.get("vrr_supported", False),
                "vrr": o.get("vrr_enabled", False),
            }

            for key, val in outputs[name].items():
                self._state.set_output_prop(name, key, val)

        self._build_outputs(outputs)

    def _build_outputs(self, outputs: dict[str, dict[str, Any]]) -> None:
        for name, props in outputs.items():
            self._build_output_group(name, props)

    def _build_output_group(self, name: str, props: dict[str, Any]) -> None:
        make = props.get("make", "")
        model = props.get("model", "").strip()
        subtitle = f"{make} {model}".strip() if (make or model) else None

        group = Adw.PreferencesGroup(title=name)
        if subtitle:
            group.set_description(subtitle)
        self._add_group(group)

        # Mode — ComboRow com os modos disponíveis
        available_modes = props.get("available_modes", [])
        if available_modes:
            mode_labels = [
                f"{m['width']}x{m['height']}@{m['refresh_rate']/1000:.3f}"
                for m in available_modes
            ]
            mode_model = Gtk.StringList.new(mode_labels)
            mode_row = Adw.ComboRow(title="Resolução / Refresh Rate")
            mode_row.set_model(mode_model)
            current_mode = props.get("mode", "")
            if current_mode in mode_labels:
                mode_row.set_selected(mode_labels.index(current_mode))
            mode_row.connect(
                "notify::selected",
                lambda r, _, n=name, labels=mode_labels: self._state.set_output_prop(n, "mode", labels[r.get_selected()])
            )
            group.add(mode_row)
        else:
            mode_row = Adw.EntryRow(title="Mode (ex: 1920x1080@60.000)")
            mode_row.set_text(props.get("mode", ""))
            mode_row.connect("changed", lambda r, n=name: self._state.set_output_prop(n, "mode", r.get_text()))
            group.add(mode_row)

        # Scale
        scale_row = Adw.SpinRow.new_with_range(0.5, 4.0, 0.25)
        scale_row.set_title("Escala")
        scale_row.set_value(float(props.get("scale", 1.0)))
        scale_row.connect("changed", lambda r, n=name: self._state.set_output_prop(n, "scale", r.get_value()))
        group.add(scale_row)

        # Transform
        transform_model = Gtk.StringList.new(TRANSFORM_LABELS)
        transform_row = Adw.ComboRow(title="Transform")
        transform_row.set_model(transform_model)
        current_transform = props.get("transform", "normal")
        if current_transform in TRANSFORMS:
            transform_row.set_selected(TRANSFORMS.index(current_transform))
        transform_row.connect("notify::selected", self._on_transform_changed, name)
        group.add(transform_row)

        # Position
        pos_group = Adw.PreferencesGroup(title=f"Posição — {name}")
        self._add_group(pos_group)

        x_row = Adw.SpinRow.new_with_range(-10000, 10000, 1)
        x_row.set_title("X")
        x_row.set_value(int(props.get("position_x", 0)))
        x_row.connect("changed", lambda r, n=name: self._state.set_output_prop(n, "position_x", int(r.get_value())))
        pos_group.add(x_row)

        y_row = Adw.SpinRow.new_with_range(-10000, 10000, 1)
        y_row.set_title("Y")
        y_row.set_value(int(props.get("position_y", 0)))
        y_row.connect("changed", lambda r, n=name: self._state.set_output_prop(n, "position_y", int(r.get_value())))
        pos_group.add(y_row)

        # VRR — só mostra se o monitor suporta
        if props.get("vrr_supported", False):
            vrr_row = Adw.SwitchRow(title="Variable Refresh Rate")
            vrr_row.set_active(bool(props.get("vrr", False)))
            vrr_row.connect("notify::active", lambda r, _, n=name: self._state.set_output_prop(n, "vrr", r.get_active()))
            pos_group.add(vrr_row)

    def _on_transform_changed(self, row: Adw.ComboRow, _param, name: str) -> None:
        idx = row.get_selected()
        if 0 <= idx < len(TRANSFORMS):
            self._state.set_output_prop(name, "transform", TRANSFORMS[idx])

    def _add_manual_output(self, name: str) -> None:
        name = name.strip()
        if not name:
            return
        self._state.set_output_prop(name, "mode", "1920x1080@60.000")
        self._state.set_output_prop(name, "scale", 1.0)
        self._state.set_output_prop(name, "transform", "normal")
        self._state.set_output_prop(name, "position_x", 0)
        self._state.set_output_prop(name, "position_y", 0)
        self._built = False
        self.refresh()
