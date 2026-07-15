"""
Cache Manager — ponto único de download de planilhas Google Sheets.

Fluxo por chamada:
  1. Verifica cache em disco  cache/sheets/<id>_<gid>.csv
  2. Se fresco (idade < TTL)  → retorna do disco imediatamente (zero rede)
  3. Se obsoleto              → tenta download → salva no disco → retorna
  4. Se download falha        → usa cache obsoleto (degradação graciosa, sem tela de erro)
  5. Se sem cache nenhum      → retorna None

Benefícios:
  - Todas as páginas que precisam da mesma planilha compartilham o mesmo arquivo.
  - Timeout do Sheets nunca derruba o dashboard (fallback para dado anterior).
  - Dados são consistentes entre páginas 3, 4 e eficiência (mesmo CSV em disco).
"""

from __future__ import annotations

import io
import logging
import os
import threading
import time
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent.parent / "cache" / "sheets"

# Trava por arquivo de cache — evita que 2 sessões (o Streamlit Community
# Cloud roda o app como um processo único, uma thread por sessão) disparem
# o download da MESMA planilha ao mesmo tempo quando o cache expira: a
# segunda sessão espera a primeira terminar e reaproveita o cache recém-
# atualizado, em vez de duplicar a chamada de rede (13/07/2026).
_locks_guard = threading.Lock()
_locks: dict[str, threading.Lock] = {}


def _lock_for(key: str) -> threading.Lock:
    with _locks_guard:
        lock = _locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _locks[key] = lock
        return lock


def _write_atomic(path: Path, content: str) -> None:
    """Grava em arquivo temporário e substitui via os.replace() (atômico em
    Windows e Linux) — evita que uma leitura concorrente pegue um CSV
    parcialmente escrito no meio de path.write_text()."""
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    # Evita que o CDN do Google (ou um proxy no meio do caminho) sirva uma
    # resposta em cache logo após uma edição recente na planilha — sem isso,
    # nosso próprio cache local pode ser invalidado corretamente e ainda assim
    # receber um CSV desatualizado do lado do Google.
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}
_DEFAULT_TTL = 120  # segundos


# ─── internos ──────────────────────────────────────────────────────────────────

def _cache_path(sheet_id: str, gid: str) -> Path:
    safe = f"{sheet_id}_{gid}".replace("/", "_").replace("\\", "_")
    return _CACHE_DIR / f"{safe}.csv"


def _download(sheet_id: str, gid: str, timeout: int = 30) -> str | None:
    """
    Tenta baixar CSV via gviz/tq (rápido) com fallback para /export.
    Tenta cada URL duas vezes com backoff de 2s antes de passar para a próxima.
    """
    urls = [
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&gid={gid}",
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}",
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv",
    ]
    for url_idx, url in enumerate(urls):
        for retry in range(2):
            try:
                r = requests.get(url, timeout=timeout, headers=_HEADERS)
                r.raise_for_status()
                content = r.text
                if content.strip():
                    logger.info(
                        "✓ Download OK: %s_%s (url=%d, retry=%d)",
                        sheet_id[:20], gid, url_idx + 1, retry,
                    )
                    return content
            except requests.exceptions.Timeout:
                logger.warning(
                    "⏱ Timeout url=%d retry=%d: %s_%s",
                    url_idx + 1, retry, sheet_id[:20], gid,
                )
                if retry == 0:
                    time.sleep(2)
            except requests.exceptions.HTTPError as e:
                logger.debug("✗ HTTP %s url=%d: %s", e.response.status_code, url_idx + 1, url[:60])
                break  # erro HTTP → tenta próxima URL sem retry
            except Exception as e:
                logger.debug("✗ url=%d: %s", url_idx + 1, str(e)[:80])
                break
    return None


# ─── API pública ───────────────────────────────────────────────────────────────

def get_raw(sheet_id: str, gid: str = "0", ttl: int = _DEFAULT_TTL) -> str | None:
    """
    Retorna texto CSV bruto. Gerencia cache em disco com TTL e fallback obsoleto.

    Parameters
    ----------
    sheet_id : ID da planilha Google Sheets
    gid      : ID da aba (sheet)
    ttl      : Tempo de vida do cache em segundos

    Returns
    -------
    Texto CSV ou None se não há dados disponíveis.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(sheet_id, gid)

    # Trava por arquivo: se 2 sessões chegam aqui com cache expirado ao
    # mesmo tempo, a segunda espera a primeira terminar (que já vai deixar
    # o cache fresco) em vez de disparar outro download em paralelo.
    with _lock_for(str(path)):
        # Verifica frescor
        is_fresh = False
        cache_age = None
        if path.exists():
            cache_age = time.time() - path.stat().st_mtime
            is_fresh = cache_age < ttl

        if is_fresh:
            logger.debug("✓ Cache fresco (%.0fs < %ds): %s", cache_age, ttl, path.name)
            return path.read_text(encoding="utf-8")

        if cache_age is not None:
            logger.debug("↻ Cache obsoleto (%.0fs ≥ %ds): tentando atualizar %s", cache_age, ttl, path.name)
        else:
            logger.debug("↻ Sem cache: baixando %s_%s", sheet_id[:20], gid)

        # Tenta download
        content = _download(sheet_id, gid)
        if content:
            _write_atomic(path, content)
            logger.info("✓ Cache salvo: %s", path.name)
            return content

        # Fallback para cache obsoleto
        if path.exists():
            age_min = (time.time() - path.stat().st_mtime) / 60
            logger.warning(
                "⚠ Download falhou — usando cache com %.0f min de idade: %s",
                age_min, path.name,
            )
            return path.read_text(encoding="utf-8")

        logger.error("✗ Sem dados disponíveis para %s_%s", sheet_id[:20], gid)
        return None


def get_dataframe(
    sheet_id: str,
    gid: str = "0",
    ttl: int = _DEFAULT_TTL,
    dtype=str,
    skiprows: int = 0,
) -> pd.DataFrame | None:
    """
    Retorna DataFrame a partir do cache CSV.

    Parâmetros iguais a get_raw() mais:
    dtype    : dtype passado ao pd.read_csv (default=str preserva valores originais)
    skiprows : linhas a pular antes do header
    """
    content = get_raw(sheet_id, gid, ttl)
    if content is None:
        return None
    try:
        df = pd.read_csv(io.StringIO(content), dtype=dtype, skiprows=skiprows)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.dropna(how="all")
        return df
    except Exception as e:
        logger.error("Erro ao parsear CSV %s_%s: %s", sheet_id[:20], gid, e)
        return None


def invalidate(sheet_id: str, gid: str = "0") -> bool:
    """Remove cache de uma planilha. Retorna True se havia cache."""
    path = _cache_path(sheet_id, gid)
    if path.exists():
        path.unlink()
        logger.info("Cache removido: %s", path.name)
        return True
    return False


def invalidate_all() -> int:
    """Remove todo o cache. Retorna quantidade de arquivos removidos."""
    if not _CACHE_DIR.exists():
        return 0
    count = 0
    for f in _CACHE_DIR.glob("*.csv"):
        f.unlink()
        count += 1
    logger.info("Cache limpo: %d arquivos removidos", count)
    return count


def get_raw_sheet(sheet_id: str, sheet_name: str, ttl: int = _DEFAULT_TTL) -> str | None:
    """
    Retorna CSV de uma aba específica por NOME (sem precisar do gid).
    Cache em disco: cache/sheets/{sheet_id}_{sheet_name_safe}.csv

    Diferença de get_raw(): usa o parâmetro ?sheet= da API gviz, que aceita o
    nome da aba em vez do gid numérico. Útil para planilhas com muitas abas onde
    os gids não são fixos.
    """
    import urllib.parse

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() else "_" for c in sheet_name)
    path = _CACHE_DIR / f"{sheet_id}_{safe}.csv"

    with _lock_for(str(path)):
        is_fresh = False
        cache_age = None
        if path.exists():
            cache_age = time.time() - path.stat().st_mtime
            is_fresh = cache_age < ttl

        if is_fresh:
            logger.debug("✓ Cache fresco (%.0fs): %s", cache_age, path.name)
            return path.read_text(encoding="utf-8")

        if cache_age is not None:
            logger.debug("↻ Cache obsoleto (%.0fs): atualizando %s", cache_age, path.name)

        encoded = urllib.parse.quote(sheet_name)
        url = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            f"/gviz/tq?tqx=out:csv&sheet={encoded}"
        )
        try:
            r = requests.get(url, timeout=30, headers=_HEADERS, allow_redirects=True)
            r.raise_for_status()
            content = r.text
            if content.strip():
                _write_atomic(path, content)
                logger.info("✓ Cache salvo (sheet=%r): %s", sheet_name, path.name)
                return content
        except requests.exceptions.HTTPError as e:
            logger.warning("✗ HTTP %s (sheet=%r): %s", e.response.status_code, sheet_name, url[:80])
        except Exception as e:
            logger.warning("✗ get_raw_sheet falhou (sheet=%r): %s", sheet_name, str(e)[:100])

        if path.exists():
            age_min = (time.time() - path.stat().st_mtime) / 60
            logger.warning("⚠ Usando cache obsoleto (%.0f min): %s", age_min, path.name)
            return path.read_text(encoding="utf-8")

        logger.error("✗ Sem dados para sheet=%r", sheet_name)
        return None


def cache_status() -> list[dict]:
    """
    Retorna lista com informações de cada arquivo em cache.
    Útil para exibir status no sidebar dos dashboards.
    """
    if not _CACHE_DIR.exists():
        return []
    now = time.time()
    result = []
    for f in sorted(_CACHE_DIR.glob("*.csv")):
        age_s = now - f.stat().st_mtime
        result.append({
            "arquivo": f.name,
            "tamanho_kb": round(f.stat().st_size / 1024, 1),
            "idade_min": round(age_s / 60, 1),
            "idade_s": round(age_s),
        })
    return result
