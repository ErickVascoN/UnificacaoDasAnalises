"""Helpers de UI compartilhados entre as páginas Streamlit."""
import streamlit as st


def multiselect_reset_on_grow(label, options, key, reset_to="full", **kwargs):
    """Multiselect que resincroniza a seleção com as opções disponíveis toda
    vez que elas mudam. Por padrão o Streamlit só REDUZ a seleção guardada em
    session_state quando as opções mudam (nunca a expande de volta pro novo
    default) — então filtros em cascata (ex.: Ano → Mês → Cliente → Produto)
    ficam "presos" num subconjunto depois que o usuário estreita um filtro
    upstream (ex.: um período com só 1 produto) e depois alarga de novo: o
    widget downstream continua mostrando só o que existia no recorte
    estreito, escondendo dados reais em todas as abas que dependem dele.
    Bug real encontrado em produção 08/07/2026: Previttex Matriz só mostrava
    Cobertor Velour pro cliente Camesa, embora ela produzisse mais produtos
    pra esse cliente. Resetar sempre que as opções mudam evita esconder dados.

    reset_to : "full" (default) reseta pra todas as opções selecionadas —
    usado quando o padrão da tela é "tudo selecionado" (`default=options`).
    "empty" reseta pra seleção vazia — usado quando a tela trata seleção
    vazia como "sem filtro / todos" (normalmente com `placeholder="Todos"`),
    pra manter o visual limpo em vez de mostrar todo mundo selecionado."""
    opts_tuple = tuple(options)
    opts_key = f"{key}__opts_snapshot"
    if st.session_state.get(opts_key) != opts_tuple:
        st.session_state[key] = list(options) if reset_to == "full" else []
        st.session_state[opts_key] = opts_tuple
    return st.multiselect(label, options, key=key, **kwargs)
