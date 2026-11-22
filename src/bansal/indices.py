"""DMLPI, DSMLPI (equações 14 e 26), MLPI e SMLPI (seção 4.3.2), com EC e TC."""

import numpy as np

from . import models
from .simplex import Inviavel

MODELOS = {
    "DMLPI": "M1",
    "DSMLPI": "M2",
    "MLPI": "ML",
    "SMLPI": "SML",
}


def calcular_ddfs(painel, anos, modelo, progresso=None):
    """Os quatro DDFs D^{t+a}(t+b) por banco e par (t, t+1). Devolve lista de dicts."""
    T0 = anos[0]
    n = len(painel[T0][models.NPL])
    cache = {}

    direcoes = {}

    def ddf(F, E, a, o):
        if modelo == "M1":
            chave = (F, E, o)
            if chave not in cache:
                if F not in direcoes:
                    direcoes[F] = models.direcoes_m1(painel, F)
                cache[chave] = models.ddf_rede(painel, [F], E, o, direcoes[F])
        elif modelo == "M2":
            chave = (F, E, a, o)
            if chave not in cache:
                if (F, a) not in direcoes:
                    direcoes[F, a] = models.direcoes_m2(painel, T0, F, a)
                cache[chave] = models.ddf_rede(painel, list(range(T0, F + 1)), E, o, direcoes[F, a])
        elif modelo == "ML":
            chave = (F, E, o)
            if chave not in cache:
                cache[chave] = models.ddf_caixa_preta(painel, [F], E, o)
        else:
            chave = (F, E, o)
            if chave not in cache:
                cache[chave] = models.ddf_caixa_preta(painel, list(range(T0, F + 1)), E, o)
        return cache[chave]

    def ddf_ou_nan(F, E, a, o):
        try:
            return ddf(F, E, a, o)
        except Inviavel:
            return float("nan")

    linhas = []
    pares = list(zip(anos[:-1], anos[1:]))
    total = len(pares) * n
    for k, (t, t1) in enumerate(pares):
        for o in range(n):
            linhas.append({
                "ano": t1, "banco": o,
                "D00": ddf_ou_nan(t, t, 0, o), "D01": ddf_ou_nan(t, t1, 0, o),
                "D10": ddf_ou_nan(t1, t, 1, o), "D11": ddf_ou_nan(t1, t1, 1, o),
            })
            if progresso:
                progresso((k * n + o + 1) / total)
    return linhas


def componentes(D00, D01, D10, D11):
    """Equação (14): EC, TC e índice."""
    ec = (1 + D00) / (1 + D11)
    tc = np.sqrt((1 + D11) / (1 + D01) * (1 + D10) / (1 + D00))
    return ec, tc, ec * tc


def media_geometrica(v):
    v = np.asarray(v, float)
    return float(np.exp(np.log(v).mean()))
