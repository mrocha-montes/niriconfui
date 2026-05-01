"""niriconfui entry point."""

from __future__ import annotations

import sys

try:
    import gi
except ModuleNotFoundError:
    print("\033[31mErro: PyGObject não encontrado.\033[0m", file=sys.stderr)
    print("Instale com: sudo pacman -S python-gobject gtk4 libadwaita", file=sys.stderr)
    sys.exit(1)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib

from niriconfui import __app_id__
from niriconfui.window import NiriConfUIWindow


class NiriConfUIApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        GLib.set_application_name("niriconfui")
        GLib.set_prgname("niriconfui")

    def do_activate(self) -> None:
        win = self.get_active_window()
        if win is None:
            win = NiriConfUIWindow(application=self)
        win.present()


def main() -> int:
    app = NiriConfUIApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
