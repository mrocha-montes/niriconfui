# niriconfui

A GTK4 + libadwaita configuration GUI for the [niri](https://github.com/YaLTeR/niri) Wayland compositor.

## Philosophy

- Reads your existing `~/.config/niri/config.kdl`
- Manages its own `~/.config/niri/niriconfui.kdl`
- Never silently overwrites your config — always backs up first
- 100% offline at runtime

## Requirements

- Python 3.11+
- GTK4 + libadwaita (`python-gobject`, `gtk4`, `libadwaita` on Arch)
- niri compositor

## Installation (development)

```bash
git clone https://github.com/mrocha-montes/niriconfui
cd niriconfui
uv sync
uv run niriconfui
```
