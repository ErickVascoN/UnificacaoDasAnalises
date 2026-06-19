# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# Activate venv first (Windows)
venv\Scripts\activate

# Run from project root
streamlit run app.py
```

The app opens at `http://localhost:8501`. On Windows, `Abrir Dashboard.bat` does the same thing.

To force a data refresh during development, click **🔄 Atualizar Dados** in any page's sidebar — this calls `invalidate_all()` + `st.cache_data.clear()`.

## Architecture Overview

**Streamlit multipage app** — `app.py` is the Home, `pages/` holds each dashboard. Each page calls `st.set_page_config` with its own title and CSS. Navigation between pages uses `utils/navigation.py:safe_switch()` (wraps `st.switch_page`).

**Authentication** — two-level password system in `utils/auth.py`. Passwords are in `config/settings.py` (`SENHA_USUARIO`, `SENHA_ADMIN`). Session state keys: `auth_nivel` ("" | "usuario" | "admin") and `auth_target`. Cards with `"admin_only": True` in `config/sectors.py` are blocked for `nivel == "usuario"`.

**Data flow** — all Google Sheets data goes through `utils/cache_manager.py:get_raw(sheet_id, gid, ttl)`, which caches CSV files in `cache/sheets/`. Never call `requests.get` directly in a page. For XLSX use `utils/sheets_loader.py`. The fallback is always the last valid cached file — the dashboard never crashes on a network error.

**Two loader patterns:**
- `utils/faccao_loader.py` — external facções (quarterizadas + named tabs). One Sheets file, multiple tabs by GID. Returns `DATA, FACCAO, PRESTADOR, PRODUTO, CLIENTE, QUANTIDADE`.
- `utils/producao_interno_loader.py` — internal collaborators (LITTEX, GGTTEX). One Sheets file per unit. Detects columns by substring (headers can be merged/shifted).

**Date parsing** — always use `utils/date_parser.py:parse_date_series(series, default_order="DMY")`. It detects the column's format by scanning all values before converting any, avoiding the day/month inversion bug. Pass `default_order="MDY"` for planilhas with a US locale (LITTEX, GGTTEX).

**Text normalization** — `utils/normalize.py` provides:
- `normalize_text(v)` — uppercase + strip accents + collapse spaces. Use for product/client name matching.
- `normalize_op(v)` — strips PROG/PGR/OP prefixes. Use whenever matching OP numbers across sheets.
- `is_blank(v)` — True for NaN / None / "-" / "" / "N/A". Never drop rows just because a key field is blank — fill with a placeholder ("SEM OP") instead.

**Configuration** — `config/settings.py` holds all Sheets IDs, TTLs, hardcoded metas (`METAS_FACCOES`), product aliases (`FACCOES_PRODUTO_ALIAS`), and client aliases (`FACCOES_CLIENTE_ALIAS`). `config/sectors.py` defines the cards on the Home page. `config/changelog.py` — insert a new entry at the top whenever making a meaningful change.

**Home page composition** — `app.py` calls:
1. `render_sidebar()` — login, nav, logout
2. `render_hero()` — title banner
3. `render_sector_tabs()` — tabs "Análise de Dados" / "Controladoria" with sector cards
4. `render_sector_cards()` in `components/sector_card.py` — reads `admin_only`, `maintenance`, `coming_soon` flags from each sector dict; handles dimming, badges, and inline auth prompt.

## Key Rules (from PADROES.md)

1. **Load sheets** → always via `cache_manager.get_raw` / `get_dataframe`. Never raw `requests`.
2. **Parse dates** → always `parse_date_series`. Never `pd.to_datetime(dayfirst=...)` inline.
3. **Match OPs** → always `normalize_op` on both sides before comparing.
4. **Don't drop blank rows** — a missing OP/product field doesn't mean the row is invalid.
5. **Find columns by content** — column named "DATA" may contain company names in some sheets. Use substring detection or the dedicated loader (`lencol_loader_smart`).

## Facções Meta Matching

Meta (goal) for facções is matched by `(produto, cliente)` — not by facção name. Multiple facções producing the same `(produto, cliente)` pair all count toward the same meta. The facção field is just the cost center. `FACCOES_PRODUTO_ALIAS` and `FACCOES_CLIENTE_ALIAS` in `config/settings.py` normalize names before matching. `NC INDUSTRIA` = `NIAZITTEX` (same company — also handled by `"NIAZI" in name` substring rule).

## Sheets GID vs. Name

Always use GID (numeric tab ID) to download a specific tab — the `?sheet=name` parameter returns the first tab when the named tab is empty or hidden, causing data from the wrong facção to appear. GIDs are stable; tab names are not reliable.
