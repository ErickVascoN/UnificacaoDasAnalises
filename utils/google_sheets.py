# -*- coding: utf-8 -*-
"""Utilitários para acesso a planilhas Google Sheets via exportação CSV."""

from __future__ import annotations


def build_export_urls(spreadsheet_id: str, gid: str | None = None) -> list[str]:
    """
    Gera as URLs de download CSV de uma planilha Google Sheets.

    Tenta sem GID primeiro (mais confiável para a primeira aba),
    depois com GID se especificado.
    """
    base = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    urls = [
        f"{base}/export?format=csv",
        f"{base}/gviz/tq?tqx=out:csv",
    ]
    if gid:
        urls += [
            f"{base}/export?format=csv&gid={gid}",
            f"{base}/gviz/tq?tqx=out:csv&gid={gid}",
        ]
    return urls
