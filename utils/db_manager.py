"""Banco de dados SQLite local — backup permanente de todos os dados da central."""

import logging
import sqlite3
from pathlib import Path

import pandas as pd

_DB_PATH = Path("data/zanattex.db")
_log = logging.getLogger(__name__)


def get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(_DB_PATH, check_same_thread=False)


def _sql_type(dtype) -> str:
    if pd.api.types.is_integer_dtype(dtype):
        return "INTEGER"
    if pd.api.types.is_float_dtype(dtype):
        return "REAL"
    return "TEXT"


def _ensure_table(conn: sqlite3.Connection, tabela: str, df: pd.DataFrame, chave: list[str]) -> None:
    """Cria a tabela (se não existir) e adiciona colunas novas sem apagar dados.

    df já deve conter a coluna _inserido_em quando esta função é chamada.
    """
    cur = conn.cursor()

    # Gera definições de todas as colunas (incluindo _inserido_em que já está em df)
    col_defs = ", ".join(f'"{c}" {_sql_type(df[c].dtype)}' for c in df.columns)
    unique_def = ", ".join(f'"{c}"' for c in chave)

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS "{tabela}" (
            {col_defs},
            UNIQUE({unique_def})
        )
    """)

    cur.execute(f'PRAGMA table_info("{tabela}")')
    existing = {row[1] for row in cur.fetchall()}
    for col in df.columns:
        if col not in existing:
            cur.execute(f'ALTER TABLE "{tabela}" ADD COLUMN "{col}" {_sql_type(df[col].dtype)}')

    conn.commit()


def upsert_df(df: pd.DataFrame, tabela: str, chave: list[str]) -> int:
    """
    Insere ou atualiza registros no banco. Retorna a quantidade de linhas processadas.
    A chave única é a combinação das colunas em `chave` — conflitos são substituídos.
    """
    if df.empty:
        return 0

    missing = [c for c in chave if c not in df.columns]
    if missing:
        _log.warning("upsert_df(%s): colunas de chave ausentes no df: %s", tabela, missing)
        return 0

    try:
        df = df.copy()
        # Datetime → string para SQLite
        for col in df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
            df[col] = df[col].dt.strftime("%Y-%m-%d")
        # NaN → None (NULL no SQLite)
        df = df.where(pd.notna(df), None)
        df["_inserido_em"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_conn()
        _ensure_table(conn, tabela, df, chave)

        cols = list(df.columns)
        col_names = ", ".join(f'"{c}"' for c in cols)
        placeholders = ", ".join("?" for _ in cols)

        cur = conn.cursor()
        cur.executemany(
            f'INSERT OR REPLACE INTO "{tabela}" ({col_names}) VALUES ({placeholders})',
            [tuple(row) for row in df.itertuples(index=False, name=None)],
        )
        conn.commit()
        conn.close()
        return len(df)
    except Exception:
        _log.exception("db_manager.upsert_df(%s)", tabela)
        return 0


def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Executa uma query SELECT e retorna DataFrame. Retorna DataFrame vazio em caso de erro."""
    try:
        conn = get_conn()
        df = pd.read_sql_query(sql, conn, params=params)
        conn.close()
        return df
    except Exception:
        _log.exception("db_manager.query")
        return pd.DataFrame()


def tabelas_status() -> pd.DataFrame:
    """Retorna um resumo de cada tabela: registros, data mínima e máxima."""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '_tmp_%' ORDER BY name"
        )
        tabelas = [row[0] for row in cur.fetchall()]

        rows = []
        for t in tabelas:
            cur.execute(f'SELECT COUNT(*) FROM "{t}"')
            n = cur.fetchone()[0]
            try:
                cur.execute(f'SELECT MIN(DATA), MAX(DATA) FROM "{t}"')
                d_min, d_max = cur.fetchone()
            except Exception:
                d_min, d_max = None, None
            rows.append({
                "Tabela": t,
                "Registros": n,
                "Data Mínima": d_min or "—",
                "Data Máxima": d_max or "—",
            })

        conn.close()
        return pd.DataFrame(rows)
    except Exception:
        _log.exception("db_manager.tabelas_status")
        return pd.DataFrame()
