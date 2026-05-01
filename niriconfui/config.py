"""Caminhos e constantes globais do niriconfui."""

from __future__ import annotations

import os
from pathlib import Path

_config_dir = Path(os.environ.get("NIRICONFUI_CONFIG_DIR", Path.home() / ".config" / "niri"))

# Config original do usuário — leitura/comentar
USER_CONFIG = _config_dir / "config.kdl"

# Arquivo gerenciado pelo niriconfui
APP_CONFIG = _config_dir / "niriconfui.kdl"

# Backup automático antes de qualquer escrita
BACKUP_DIR = _config_dir / "niriconfui_backup"
