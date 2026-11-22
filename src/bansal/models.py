"""Funções distância direcionais dos modelos (M1) e (M2) do paper e da caixa-preta da seção 4.3.2.

`painel[ano][variavel]` é um vetor com um valor por banco (mesma ordem em todos os anos).
"""

import numpy as np

from .simplex import maximizar

# Tabela 1 e Figura 2
INSUMOS = {1: ["labor", "fixed_assets"], 2: ["borrowings"], 3: ["provision"]}  # X, eq. (5)
QUASE_FIXO = "equity"  # V, divisão 1, eq. (6)
NPL = "npl"  # W de t-1 (eq. 7) e U de t (eq. 9), divisão 2
CARRYOVERS = ["unused_assets", "net_profit"]  # C, divisão 2, eqs. (10) e (11)
PRODUTOS = ["net_interest_income", "non_interest_income"]  # Y, divisão 3, eq. (8)
ELOS = {1: ["deposits"], 2: ["performing_loans", "investments"]}  # Z, eq. (12)

# Seção 4.3.1
M1_XI, M1_PI = 3.0, 1.0
M2_ETA = {0: 3.0, 1: 1.5}
M2_DELTA = 1.0


def _direcoes(painel, anos_f, anos_c, k_max, delta):
    """Constantes de direção sobre os anos da fronteira (anos_f) e do carryover defasado (anos_c)."""
    def junta(var, anos):
        return np.concatenate([painel[a][var] for a in anos])

    d = {}
    for div, vs in INSUMOS.items():
        for v in vs:
            d["mu", v] = k_max * np.abs(junta(v, anos_f)).max()
    d["rho"] = np.concatenate([painel[a - 1][NPL] for a in anos_f]).min() - delta
    d["omega"] = k_max * np.abs(junta(NPL, anos_f)).max()
    for v in PRODUTOS:
        d["nu", v] = junta(v, anos_f).min() - delta
    for v in CARRYOVERS:
        d["gamma", v] = junta(v, anos_f).min() - delta
        d["alpha", v] = k_max * np.abs(junta(v, anos_c)).max()
    return d


def ddf_rede(painel, anos_f, ano_e, o, d):
    """DDF da rede para o banco o, dados do ano ano_e, tecnologia formada pelos anos anos_f.

    Com anos_f = [F] é o (M1); com anos_f = [T0, ..., F] é o (M2). Devolve beta ótimo.
    """
    n = len(painel[ano_e][NPL])
    T = len(anos_f)
    bloco = 4 * n  # lambda1, phi1, lambda2, lambda3 por ano
    nv = T * bloco + 1
    ib = nv - 1

    def col(tau, parte):
        return tau * bloco + parte * n + np.arange(n)

    E = painel[ano_e]
    E_ant = painel[ano_e - 1]
    linhas, rhs = [], []

    def nova():
        return np.zeros(nv)

    divisao_parte = {1: 0, 2: 2, 3: 3}
    for div, vs in INSUMOS.items():
        for v in vs:
            r = nova()
            for t, a in enumerate(anos_f):
                r[col(t, divisao_parte[div])] = painel[a][v]
            r[ib] = E[v][o] + d["mu", v]
            linhas.append(r)
            rhs.append(E[v][o])

    r = nova()
    for t, a in enumerate(anos_f):
        r[col(t, 0)] = painel[a][QUASE_FIXO]
        r[col(t, 1)] = painel[a][QUASE_FIXO]
    linhas.append(r)
    rhs.append(E[QUASE_FIXO][o])

    w_o = E_ant[NPL][o]
    r = nova()
    for t, a in enumerate(anos_f):
        r[col(t, 2)] = -painel[a - 1][NPL]
    r[ib] = w_o - d["rho"]
    linhas.append(r)
    rhs.append(-w_o)

    r = nova()
    for t, a in enumerate(anos_f):
        r[col(t, 2)] = painel[a][NPL]
    r[ib] = E[NPL][o] + d["omega"]
    linhas.append(r)
    rhs.append(E[NPL][o])

    for v in CARRYOVERS:
        r = nova()
        for t, a in enumerate(anos_f):
            r[col(t, 2)] = -painel[a][v]
        r[ib] = E[v][o] - d["gamma", v]
        linhas.append(r)
        rhs.append(-E[v][o])

        r = nova()
        for t, a in enumerate(anos_f):
            r[col(t, 2)] = painel[a - 1][v]
        r[ib] = E_ant[v][o] + d["alpha", v]
        linhas.append(r)
        rhs.append(E_ant[v][o])

    for v in PRODUTOS:
        r = nova()
        for t, a in enumerate(anos_f):
            r[col(t, 3)] = -painel[a][v]
        r[ib] = E[v][o] - d["nu", v]
        linhas.append(r)
        rhs.append(-E[v][o])

    eq, beq = [], []
    for k, vs in ELOS.items():
        de, para = divisao_parte[k], divisao_parte[k + 1]
        for v in vs:
            r = nova()
            for t, a in enumerate(anos_f):
                r[col(t, de)] = painel[a][v]
                r[col(t, para)] = -painel[a][v]
            eq.append(r)
            beq.append(0.0)
    for parte in (0, 2, 3):
        r = nova()
        for t in range(T):
            r[col(t, parte)] = 1.0
        eq.append(r)
        beq.append(1.0)

    c = nova()
    c[ib] = 1.0
    valor, _ = maximizar(c, np.array(linhas), np.array(rhs), np.array(eq), np.array(beq), livres=[ib])
    return valor


def direcoes_m1(painel, F):
    return _direcoes(painel, [F], [F - 1], M1_XI, M1_PI)


def direcoes_m2(painel, T0, F, a):
    return _direcoes(painel, list(range(T0, F + 1)), list(range(T0 - 1, F)), M2_ETA[a], M2_DELTA)


# Caixa-preta (seção 4.3.2): insumos da divisão 1 sem o quase-fixo, produtos da divisão 3, NPL indesejável.
CP_INSUMOS = ["labor", "fixed_assets"]
CP_PRODUTOS = PRODUTOS
CP_INDESEJAVEL = NPL


def ddf_caixa_preta(painel, anos_f, ano_e, o):
    """DDF orientada a produto, direção igual aos valores observados, VRS (Chung et al. 1997).

    max beta s.a. sum lambda x <= x_o; sum lambda y >= (1 + beta) y_o; sum lambda u = (1 - beta) u_o; sum lambda = 1.
    """
    E = painel[ano_e]
    n = len(E[NPL])
    nv = len(anos_f) * n + 1
    ib = nv - 1
    linhas, rhs = [], []
    for v in CP_INSUMOS:
        r = np.zeros(nv)
        r[:ib] = np.concatenate([painel[a][v] for a in anos_f])
        linhas.append(r)
        rhs.append(E[v][o])
    for v in CP_PRODUTOS:
        r = np.zeros(nv)
        r[:ib] = -np.concatenate([painel[a][v] for a in anos_f])
        r[ib] = E[v][o]
        linhas.append(r)
        rhs.append(-E[v][o])
    eq = np.zeros((2, nv))
    eq[0, :ib] = np.concatenate([painel[a][CP_INDESEJAVEL] for a in anos_f])
    eq[0, ib] = E[CP_INDESEJAVEL][o]
    eq[1, :ib] = 1.0
    c = np.zeros(nv)
    c[ib] = 1.0
    valor, _ = maximizar(c, np.array(linhas), np.array(rhs), eq, np.array([E[CP_INDESEJAVEL][o], 1.0]), livres=[ib])
    return valor
