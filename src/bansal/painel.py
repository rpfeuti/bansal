"""Carrega o painel padronizado no formato esperado por models.py e indices.py."""

from pathlib import Path

import numpy as np
import pandas as pd

from . import models
from .nomes import BANCOS, GRUPO, NOME

RAIZ = Path(__file__).resolve().parents[2]
PAD = RAIZ / "data" / "padronizada" / "painel.xlsx"
IDS = [b[0] for b in BANCOS]
VARIAVEIS = (
    models.INSUMOS[1] + models.INSUMOS[2] + models.INSUMOS[3]
    + [models.QUASE_FIXO, models.NPL] + models.CARRYOVERS + models.PRODUTOS
    + models.ELOS[1] + models.ELOS[2]
)


def carregar(caminho=PAD):
    """painel[ano][variavel] = vetor n; metadados e covariáveis por (banco, ano)."""
    return montar(pd.read_excel(caminho, sheet_name="painel"), pd.read_excel(caminho, sheet_name="covariaveis"))


def montar(p, c):
    """O mesmo de carregar, a partir das tabelas painel e covariaveis (colunas bank_id, ano, ...)."""
    anos = sorted(p["ano"].unique())
    painel = {}
    for a in anos:
        g = p[p["ano"] == a].set_index("bank_id").reindex(IDS)
        painel[a] = {v: g[v].to_numpy(float) for v in VARIAVEIS}
    cov = c.set_index(["bank_id", "ano"]).reindex(
        pd.MultiIndex.from_product([IDS, anos], names=["bank_id", "ano"]))
    meta = {"ids": IDS, "nomes": [NOME[i] for i in IDS], "grupos": [GRUPO[i] for i in IDS], "anos": anos}
    return painel, cov, meta
