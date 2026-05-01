"""Janela principal do niriconfui."""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from niriconfui.state import AppState


class NiriConfUIWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self._state = AppState()
        self._state.load()

        self.set_title("niriconfui")
        self.set_default_size(960, 680)

        # Toast overlay envolve tudo
        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        # NavigationSplitView — sidebar + conteúdo
        self._split = Adw.NavigationSplitView()
        self._toast_overlay.set_child(self._split)

        # Sidebar
        self._split.set_sidebar(self._build_sidebar())

        # Área de conteúdo — começa com página de outputs
        self._content_nav = Adw.NavigationPage(title="Outputs")
        self._split.set_content(self._content_nav)

        # Páginas (lazy import pra não quebrar se GTK não estiver disponível em testes)
        self._pages: dict[str, Adw.PreferencesPage] = {}
        self._init_pages()

        # Mostra primeira página
        self._show_page("outputs")

        # Banner se niri não estiver rodando
        if not self._state.niri_running:
            self._show_toast("niri não detectado — IPC indisponível, modo edição offline.")

    # ------------------------------------------------------------------ #
    # Sidebar                                                              #
    # ------------------------------------------------------------------ #

    def _build_sidebar(self) -> Adw.NavigationPage:
        sidebar_page = Adw.NavigationPage(title="niriconfui")

        toolbar = Adw.ToolbarView()
        sidebar_page.set_child(toolbar)

        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        toolbar.add_top_bar(header)

        # Save button
        save_btn = Gtk.Button(label="Salvar")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        header.pack_end(save_btn)

        # Lista de navegação
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar.set_content(scroll)

        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        list_box.add_css_class("navigation-sidebar")
        list_box.connect("row-selected", self._on_row_selected)
        scroll.set_child(list_box)

        # Grupos de navegação
        self._nav_rows: dict[str, Gtk.ListBoxRow] = {}
        sections = [
            ("Compositor", [
                ("outputs",     "display",          "Outputs"),
                ("layout",      "view-grid-symbolic","Layout"),
                ("animations",  "preferences-system-symbolic", "Animações"),
            ]),
            ("Entrada", [
                ("input",       "input-keyboard",   "Teclado & Mouse"),
                ("gestures",    "touch-symbolic",   "Gestos"),
            ]),
            ("Aparência", [
                ("appearance",  "applications-graphics", "Aparência"),
                ("window_rules","view-list-symbolic","Regras de Janela"),
            ]),
            ("Sistema", [
                ("environment", "system-run-symbolic","Variáveis de Ambiente"),
                ("startup",     "media-playback-start-symbolic", "Startup"),
                ("raw",         "text-editor-symbolic", "Config Raw"),
            ]),
        ]

        for section_title, items in sections:
            # Separador de seção
            label = Gtk.Label(label=section_title, xalign=0)
            label.add_css_class("caption")
            label.add_css_class("dim-label")
            label.set_margin_start(12)
            label.set_margin_top(12)
            label.set_margin_bottom(4)
            row = Gtk.ListBoxRow()
            row.set_child(label)
            row.set_selectable(False)
            row.set_activatable(False)
            list_box.append(row)

            for page_id, icon, title in items:
                row = self._make_nav_row(icon, title)
                self._nav_rows[page_id] = row
                list_box.append(row)

        return sidebar_page

    def _make_nav_row(self, icon: str, title: str) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        img = Gtk.Image.new_from_icon_name(icon)
        lbl = Gtk.Label(label=title, xalign=0, hexpand=True)
        box.append(img)
        box.append(lbl)
        row.set_child(box)
        return row

    # ------------------------------------------------------------------ #
    # Páginas                                                              #
    # ------------------------------------------------------------------ #

    def _init_pages(self) -> None:
        from niriconfui.pages.outputs import OutputsPage
        from niriconfui.pages.placeholder import PlaceholderPage

        self._pages["outputs"] = OutputsPage(self._state)

        # Páginas ainda não implementadas — placeholder
        for page_id in ["layout", "animations", "input", "gestures",
                         "appearance", "window_rules", "environment", "startup", "raw"]:
            self._pages[page_id] = PlaceholderPage(self._state, page_id)

    def _show_page(self, page_id: str) -> None:
        page = self._pages.get(page_id)
        if page is None:
            return
        page.refresh()

        # Wrap numa NavigationPage
        nav = Adw.NavigationPage(title=page.get_title() or page_id.capitalize())
        
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)
        toolbar.set_content(page)
        nav.set_child(toolbar)

        self._split.set_content(nav)
        self._current_page_id = page_id

    # ------------------------------------------------------------------ #
    # Sinais                                                               #
    # ------------------------------------------------------------------ #

    def _on_row_selected(self, list_box: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        if row is None:
            return
        for page_id, nav_row in self._nav_rows.items():
            if nav_row is row:
                self._show_page(page_id)
                return

    def _on_save(self, _btn) -> None:
        try:
            if not self._state.backup_exists():
                self._state.create_backup()
            include_existed = self._state.ensure_include()
            self._state.save()
            if not include_existed:
                self._show_toast("Salvo — include adicionado ao config.kdl")
            else:
                self._show_toast("Configuração salva em niriconfui.kdl")
        except Exception as e:
            self._show_toast(f"Erro ao salvar: {e}")

    def _show_toast(self, message: str) -> None:
        self._toast_overlay.add_toast(Adw.Toast.new(message))
