"""Calcula índices, Tabelas 2-6 / B1 / B2 e grava em data/saida/.

Rodar: $env:PYTHONPATH='src'; python -m bansal.calcular
"""

from pathlib import Path

import numpy as np
import pandas as pd

from . import indices, models
from .gmm import system_gmm
from .li_test import li_teste
from .nomes import BANCOS, GRUPO, NOME
from .painel import carregar

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "data" / "saida"
ARTIGO = RAIZ / "data" / "raw" / "artigo_tabelas.xlsx"

# Covariáveis usadas em cada coluna da Tabela 6 (hífen no paper = omitida).
GMM_XS = {
    "EC_M1": ["G_NPLs", "SIZE", "IC", "LIQUIDITY", "BME", "PRIORITY", "DIVERSIFICATION"],
    "TC_M1": ["G_NPLs", "SIZE", "IC", "EQTA", "BME", "PRIORITY", "DIVERSIFICATION"],
    "DMLPI": ["G_NPLs", "SIZE", "IC", "EQTA", "BME", "PRIORITY", "DIVERSIFICATION"],
    "EC_M2": ["G_NPLs", "SIZE", "IC", "EQTA", "LIQUIDITY", "BME", "PRIORITY", "DIVERSIFICATION"],
    "TC_M2": ["G_NPLs", "SIZE", "IC", "EQTA", "BME", "PRIORITY", "DIVERSIFICATION"],
    "DSMLPI": ["G_NPLs", "SIZE", "IC", "EQTA", "LIQUIDITY", "BME", "PRIORITY", "DIVERSIFICATION"],
}


def _progresso(nome):
    def f(fração):
        print(f"\r  {nome}: {100 * fração:5.1f}%", end="", flush=True)
        if fração >= 1:
            print(flush=True)
    return f


def indices_banco_ano(painel, meta):
    """Linhas banco × ano × modelo com EC, TC e índice."""
    anos_idx = [a for a in meta["anos"] if a >= 2010]
    linhas = []
    for modelo, chave in indices.MODELOS.items():
        print(f"calculando {modelo}", flush=True)
        ddfs = indices.calcular_ddfs(painel, anos_idx, chave, progresso=_progresso(modelo))
        for r in ddfs:
            ec, tc, idx = indices.componentes(r["D00"], r["D01"], r["D10"], r["D11"])
            i = r["banco"]
            linhas.append({
                "indice": modelo, "bank_id": meta["ids"][i], "banco": meta["nomes"][i],
                "grupo": meta["grupos"][i], "ano": r["ano"],
                "EC": ec, "TC": tc, "IDX": idx,
                "D00": r["D00"], "D01": r["D01"], "D10": r["D10"], "D11": r["D11"],
            })
    return pd.DataFrame(linhas)


def tabela2(painel, meta):
    anos = [a for a in meta["anos"] if a >= 2010]
    cols = list(dict.fromkeys(
        models.INSUMOS[1] + [models.QUASE_FIXO] + models.ELOS[1] + models.INSUMOS[2]
        + [models.NPL] + models.CARRYOVERS + models.ELOS[2] + models.INSUMOS[3] + models.PRODUTOS))
    blocos = [pd.DataFrame({v: painel[a][v] for v in cols}) for a in anos]
    d = pd.concat(blocos, ignore_index=True)
    # Curtose de Pearson (não excesso), como na Tabela 2 do paper (labor ≈ 4,72).
    rows = []
    for v in cols:
        s = d[v]
        rows.append({
            "variavel": v, "mean": s.mean(), "sd": s.std(ddof=1),
            "kurtosis": s.kurtosis() + 3, "skewness": s.skew(),
            "median": s.median(), "max": s.max(), "min": s.min(),
        })
    return pd.DataFrame(rows)


def _geo(s):
    s = np.asarray(s, float)
    s = s[np.isfinite(s) & (s > 0)]
    return float(np.exp(np.log(s).mean())) if s.size else np.nan


def tabela_ano(det, modelo, prefixos):
    """Tabela 3 / 5: painéis todos/publico/privado × ano e média 2010-17."""
    d = det[det["indice"] == modelo]
    col_ec, col_tc, col_idx = prefixos
    linhas = []
    for painel, g in (("todos", d), ("publico", d[d["grupo"] == "publico"]),
                      ("privado", d[d["grupo"] == "privado"])):
        for ano, ga in g.groupby("ano"):
            linhas.append({"painel": painel, "ano": str(int(ano)),
                           col_ec: _geo(ga["EC"]), col_tc: _geo(ga["TC"]), col_idx: _geo(ga["IDX"])})
        linhas.append({"painel": painel, "ano": "2010-17",
                       col_ec: _geo(g["EC"]), col_tc: _geo(g["TC"]), col_idx: _geo(g["IDX"])})
    return pd.DataFrame(linhas)


def tabela4(det):
    """Médias geométricas por banco no período (DMLPI e DSMLPI)."""
    linhas = []
    for bid, nome, grupo in BANCOS:
        row = {"banco": nome, "grupo": grupo}
        for modelo, cols in (("DMLPI", ("EC_M1", "TC_M1", "DMLPI")),
                             ("DSMLPI", ("EC_M2", "TC_M2", "DSMLPI"))):
            g = det[(det["indice"] == modelo) & (det["bank_id"] == bid)]
            row[cols[0]] = _geo(g["EC"])
            row[cols[1]] = _geo(g["TC"])
            row[cols[2]] = _geo(g["IDX"])
        linhas.append(row)
    out = pd.DataFrame(linhas)
    # Linha de média geométrica do painel privado (como no paper).
    priv = out[out["grupo"] == "privado"]
    geo = {"banco": "Geometric mean", "grupo": "privado"}
    for c in ("EC_M1", "TC_M1", "DMLPI", "EC_M2", "TC_M2", "DSMLPI"):
        geo[c] = _geo(priv[c])
    return pd.concat([out, pd.DataFrame([geo])], ignore_index=True)


def tabela_b(det, modelo, bancos):
    g = det[(det["indice"] == modelo) & det["bank_id"].isin(bancos)]
    return g[["indice", "banco", "ano", "EC", "TC", "IDX"]].sort_values(["banco", "ano"])


def li_por_componente(det):
    rows = []
    for modelo, cols in (("DMLPI", ("EC_M1", "TC_M1", "DMLPI")),
                         ("DSMLPI", ("EC_M2", "TC_M2", "DSMLPI"))):
        d = det[det["indice"] == modelo]
        for comp, col in (("EC", cols[0]), ("TC", cols[1]), ("IDX", cols[2])):
            pub = d.loc[d["grupo"] == "publico", comp].to_numpy()
            priv = d.loc[d["grupo"] == "privado", comp].to_numpy()
            T, p = li_teste(pub, priv)
            rows.append({"componente": col, "teste_li": T, "p_valor": p})
    return pd.DataFrame(rows)


def _matriz(y_df, anos, ids):
    """N × T a partir de DataFrame indexado por (bank_id, ano)."""
    return np.array([[y_df.get((b, a), np.nan) for a in anos] for b in ids], float)


def tabela6(det, cov, meta):
    anos = [a for a in meta["anos"] if a >= 2011]
    ids = meta["ids"]
    linhas = []
    for dep, xs_nomes in GMM_XS.items():
        modelo = "DMLPI" if dep.endswith("M1") or dep == "DMLPI" else "DSMLPI"
        if dep.startswith("EC"):
            ycol = "EC"
        elif dep.startswith("TC"):
            ycol = "TC"
        else:
            ycol = "IDX"
        d = det[det["indice"] == modelo].set_index(["bank_id", "ano"])[ycol]
        y = _matriz(d, anos, ids)
        xs = [_matriz(cov[x], anos, ids) for x in xs_nomes]
        nomes = ["L.dep", *xs_nomes, "Constant"]
        r = system_gmm(y, xs, nomes)
        for nome, coef, ep in zip(r["nomes"], r["coef"], r["ep"]):
            linhas.append({"regressor": nome, "estatistica": "coef", "coluna": dep, "valor": coef})
            linhas.append({"regressor": nome, "estatistica": "ep", "coluna": dep, "valor": ep})
        for k, v in (("AR(1)", r["AR1"]), ("AR(2)", r["AR2"]), ("Sargan", r["sargan_p"]),
                     ("Hansen J", r["hansen_p"])):
            linhas.append({"regressor": k, "estatistica": "p", "coluna": dep, "valor": v})
        linhas.append({"regressor": "Wald Chi2", "estatistica": "estat", "coluna": dep, "valor": r["wald"]})
    longo = pd.DataFrame(linhas)
    return longo.pivot_table(index=["regressor", "estatistica"], columns="coluna",
                             values="valor", aggfunc="first").reset_index()


def main():
    painel, cov, meta = carregar()
    SAIDA.mkdir(parents=True, exist_ok=True)

    t2 = tabela2(painel, meta)
    t2.to_excel(SAIDA / "tabela2.xlsx", index=False)
    print("Tabela 2 gravada", flush=True)

    det = indices_banco_ano(painel, meta)
    det.to_excel(SAIDA / "indices_detalhe.xlsx", index=False)

    t3 = tabela_ano(det, "DMLPI", ("EC_M1", "TC_M1", "DMLPI")).merge(
        tabela_ano(det, "DSMLPI", ("EC_M2", "TC_M2", "DSMLPI")), on=["painel", "ano"])
    t5 = tabela_ano(det, "MLPI", ("EC_ML", "TC_ML", "MLPI")).merge(
        tabela_ano(det, "SMLPI", ("EC_SML", "TC_SML", "SMLPI")), on=["painel", "ano"])
    t4 = tabela4(det)
    t3.to_excel(SAIDA / "tabela3.xlsx", index=False)
    t4.to_excel(SAIDA / "tabela4.xlsx", index=False)
    t5.to_excel(SAIDA / "tabela5.xlsx", index=False)

    pub = [b for b, _, g in BANCOS if g == "publico"]
    priv = [b for b, _, g in BANCOS if g == "privado"]
    b1 = pd.concat([tabela_b(det, "DMLPI", pub), tabela_b(det, "DSMLPI", pub)])
    b2 = pd.concat([tabela_b(det, "DMLPI", priv), tabela_b(det, "DSMLPI", priv)])
    b1.to_excel(SAIDA / "tabelaB1.xlsx", index=False)
    b2.to_excel(SAIDA / "tabelaB2.xlsx", index=False)

    li = li_por_componente(det)
    li.to_excel(SAIDA / "tabela3_li.xlsx", index=False)
    print("teste de Li gravado", flush=True)

    t6 = tabela6(det, cov, meta)
    t6.to_excel(SAIDA / "tabela6.xlsx", index=False)
    print("Tabela 6 gravada", flush=True)

    print("Saídas em", SAIDA)


if __name__ == "__main__":
    main()
