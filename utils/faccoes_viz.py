"""Visualizações genéricas de produção por dimensão (Facção ou Cliente).

Extraído de pages/5_Producao_Faccoes.py (tab "Por Facção") para reaproveitar
o mesmo heatmap e cálculo de regularidade/assiduidade tanto na comparação
entre facções quanto no drill-down por facção do Produção Geral (que quebra
por CLIENTE em vez de FACCAO). A lógica não muda — só parametriza a coluna
de agrupamento.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go

_DARK_LAYOUT_PADRAO = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#CBD5E0"),
    xaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748"),
    yaxis=dict(gridcolor="#2D3748", zerolinecolor="#2D3748"),
    separators=",.",
)


def heatmap_por_dimensao(
    df: pd.DataFrame,
    dim_col: str = "FACCAO",
    data_col: str = "DATA",
    qty_col: str = "QUANTIDADE",
    dark_layout: dict | None = None,
) -> go.Figure:
    """Heatmap dimensão × dia (linhas = dim_col, colunas = dia), escala log de cor.

    Célula em branco = sem produção naquele dia. Reaproveitável para
    dim_col="FACCAO" ou dim_col="CLIENTE".
    """
    layout = dark_layout or _DARK_LAYOUT_PADRAO

    df_hm = df.copy()
    df_hm["DATA_DAY"] = df_hm[data_col].dt.normalize()

    pivot = df_hm.pivot_table(
        index=dim_col, columns="DATA_DAY", values=qty_col, aggfunc="sum", fill_value=0
    )
    pivot = pivot[sorted(pivot.columns)]
    col_labels = [pd.Timestamp(c).strftime("%d/%m") for c in pivot.columns]

    z_raw = pivot.values.astype(float)
    z_color = np.where(z_raw > 0, np.log1p(z_raw), np.nan)
    text = [
        [f"{int(v):,}".replace(",", ".") if v > 0 else "" for v in row]
        for row in z_raw
    ]

    fig = go.Figure(go.Heatmap(
        z=z_color,
        x=col_labels,
        y=pivot.index.tolist(),
        text=text,
        texttemplate="%{text}",
        textfont=dict(color="white", size=9),
        colorscale=[[0, "#1a3a5c"], [0.5, "#2aa89a"], [1, "#4ECDC4"]],
        showscale=False,
        hovertemplate="<b>%{y}</b><br>%{x}: %{text} peças<extra></extra>",
    ))
    fig.update_layout(
        title=f"Mapa de Calor: {dim_col.title()} × Dia (escala log de cores)",
        xaxis_title="Dia", yaxis_title="",
        height=max(350, len(pivot) * 38 + 120),
        margin=dict(t=60, l=170, r=20, b=50),
        **layout,
    )
    return fig


def consistencia_por_dimensao(
    df: pd.DataFrame,
    data_ini: date,
    data_fim: date,
    dim_col: str = "FACCAO",
    data_col: str = "DATA",
    qty_col: str = "QUANTIDADE",
) -> pd.DataFrame:
    """Regularidade (uniformidade da produção diária) + assiduidade por dimensão.

    Regularidade = 100% quando a produção diária é perfeitamente constante
    (coeficiente de variação = 0). Assiduidade = % de dias úteis do período
    em que houve produção. Reaproveitável para dim_col="FACCAO" ou "CLIENTE".

    Retorna DataFrame com colunas:
    [dim_col, "Dias Ativos", "Assiduidade (%)", "Média/Dia", "Regularidade (%)",
     "Melhor Dia", "Pior Dia (>0)"]
    """
    du_per = sum(
        1 for i in range((data_fim - data_ini).days + 1)
        if (data_ini + timedelta(days=i)).weekday() < 5
    )

    rows = []
    for valor in sorted(df[dim_col].unique()):
        sub = df[df[dim_col] == valor]
        diario = sub.groupby(sub[data_col].dt.date)[qty_col].sum()
        dias_ativos = len(diario)
        total = int(diario.sum())
        media_dia = total / dias_ativos if dias_ativos > 0 else 0
        if dias_ativos >= 2 and media_dia > 0:
            cv = diario.std(ddof=0) / media_dia
            regularidade = max(0.0, min(100.0, 100.0 * (1.0 - cv)))
        else:
            regularidade = 100.0 if dias_ativos >= 1 else 0.0
        assiduidade = min(100.0, dias_ativos / du_per * 100) if du_per > 0 else 0.0
        melhor = int(diario.max()) if dias_ativos else 0
        pior = int(diario[diario > 0].min()) if (diario > 0).any() else 0
        rows.append({
            dim_col:              valor,
            "Dias Ativos":        dias_ativos,
            "Assiduidade (%)":    round(assiduidade, 1),
            "Média/Dia":          round(media_dia),
            "Regularidade (%)":   round(regularidade, 1),
            "Melhor Dia":         melhor,
            "Pior Dia (>0)":      pior,
        })
    return pd.DataFrame(rows)
