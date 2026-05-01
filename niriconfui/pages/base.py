"""Classe base para todas as páginas do niriconfui."""

from __future__ import annotations

from typing import TYPE_CHECKING

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

if TYPE_CHECKING:
    from niriconfui.state import AppState


class BasePage(Adw.PreferencesPage):
    """Todas as páginas herdam daqui.
    
    Fornece acesso ao AppState e método refresh() que cada página
    deve implementar para atualizar a UI com o estado atual.
    """

    def __init__(self, state: "AppState") -> None:
        super().__init__()
        self._state = state

    def refresh(self) -> None:
        """Atualiza a UI com o estado atual. Sobrescrever em cada página."""
        pass

    def _show_toast(self, message: str) -> None:
        """Mostra um toast na janela pai se disponível."""
        root = self.get_root()
        if isinstance(root, Adw.ApplicationWindow):
            overlay = root.get_content()
            if isinstance(overlay, Adw.ToastOverlay):
                overlay.add_toast(Adw.Toast.new(message))
