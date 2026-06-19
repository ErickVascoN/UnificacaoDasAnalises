"""Gerenciador de metas de facções. JSON em data/metas_faccoes.json sobrepõe settings.py."""

import json
from pathlib import Path

_PATH = Path("data/metas_faccoes.json")


def load_metas() -> list[dict]:
    """Carrega metas do JSON local (se existir) ou do settings.py como fallback."""
    if _PATH.exists():
        try:
            return json.loads(_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    from config.settings import METAS_FACCOES
    return [dict(m) for m in METAS_FACCOES]


def save_metas(lista: list[dict]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8")


def reset_metas() -> None:
    """Remove o JSON local, voltando a usar config/settings.py."""
    if _PATH.exists():
        _PATH.unlink()
