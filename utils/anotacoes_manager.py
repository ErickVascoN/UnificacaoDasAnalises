"""Gerenciador de anotações nos gráficos. Persiste em data/anotacoes.json."""

import json
import uuid
from datetime import date
from pathlib import Path

import plotly.graph_objects as go

_PATH = Path("data/anotacoes.json")

# Schema de cada entrada:
# {
#   "id": str (8 chars),
#   "data": "YYYY-MM-DD",
#   "texto": str,
#   "cor": str (hex),
#   "paginas": list[str]  # ["all"] | ["faccoes", "geral", ...]
# }


def load_anotacoes() -> list[dict]:
    if _PATH.exists():
        try:
            return json.loads(_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_anotacoes(lista: list[dict]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8")


def add_anotacao(data_str: str, texto: str, cor: str = "#F59E0B", paginas: list[str] | None = None) -> None:
    lista = load_anotacoes()
    lista.append({
        "id": str(uuid.uuid4())[:8],
        "data": data_str,
        "texto": texto,
        "cor": cor,
        "paginas": paginas or ["all"],
    })
    save_anotacoes(lista)


def remove_anotacao(anotacao_id: str) -> None:
    lista = [a for a in load_anotacoes() if a["id"] != anotacao_id]
    save_anotacoes(lista)


def apply_to_fig(
    fig: go.Figure,
    data_ini: date,
    data_fim: date,
    pagina: str = "all",
    x_fmt: str | None = None,
) -> go.Figure:
    """
    Adiciona linhas verticais nas anotações que caem no intervalo [data_ini, data_fim].

    x_fmt: formato do eixo X quando ele for string (ex: "%d/%m" para gráficos mensais).
           None para eixos de datetime.
    """
    for a in load_anotacoes():
        paginas = a.get("paginas", ["all"])
        if "all" not in paginas and pagina not in paginas:
            continue
        try:
            d = date.fromisoformat(a["data"])
        except (ValueError, TypeError):
            continue
        if not (data_ini <= d <= data_fim):
            continue

        cor = a.get("cor", "#F59E0B")
        texto = a.get("texto", "")

        if x_fmt is not None:
            x_val = d.strftime(x_fmt)
            fig.add_shape(
                type="line",
                x0=x_val, x1=x_val,
                y0=0, y1=1,
                xref="x", yref="paper",
                line=dict(color=cor, width=1.5, dash="dot"),
            )
            fig.add_annotation(
                x=x_val, y=0.98,
                xref="x", yref="paper",
                text=f"<b>{texto}</b>",
                showarrow=False,
                font=dict(size=10, color=cor),
                xanchor="left",
                yanchor="top",
                bgcolor="rgba(0,0,0,0.55)",
                bordercolor=cor,
                borderwidth=1,
                borderpad=3,
            )
        else:
            import pandas as pd
            fig.add_vline(
                x=pd.Timestamp(d),
                line_dash="dot",
                line_color=cor,
                annotation_text=f"<b>{texto}</b>",
                annotation_position="top left",
                annotation_font_size=10,
                annotation_font_color=cor,
            )

    return fig
