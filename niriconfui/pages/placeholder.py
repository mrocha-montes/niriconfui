"""Página placeholder para seções ainda não implementadas."""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from niriconfui.pages.base import BasePage
from niriconfui.state import AppState


class PlaceholderPage(BasePage):
    def __init__(self, state: AppState, page_id: str) -> None:
        super().__init__(state)
        self.set_title(page_id.replace("_", " ").capitalize())

        group = Adw.PreferencesGroup()
        self.add(group)

        status = Adw.StatusPage(
            title="Em breve",
            description=f"A página '{page_id}' ainda não foi implementada.",
            icon_name="preferences-system-symbolic",
        )
        status.set_vexpand(True)
        group.add(status)
