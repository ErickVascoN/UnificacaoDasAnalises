"""
Dashboards dos Setores
"""
from .corte import render as render_corte
from .producao import render as render_producao
from .faturamento import render as render_faturamento

__all__ = [
    "render_corte",
    "render_producao",
    "render_faturamento",
]
