"""Base padronizada: painel 2009-2017 dos 42 bancos a partir de data/raw.

Rodar da raiz do projeto: python -m bansal.padronizar  (com src no PYTHONPATH).
Saída: data/padronizada/painel.xlsx (abas painel, covariaveis, nominal, fonte, faltantes).
"""

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .nomes import BANCOS, GRUPO, NOME, bank_id

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "data" / "raw"
SAIDA = RAIZ / "data" / "padronizada"
ANOS = list(range(2009, 2018))
IDS = [b[0] for b in BANCOS]

# Rótulos do B1 do STRBI (início do texto, espaços normalizados).
ROTULOS_B1 = {
    "capital": r"1\. ?Capital$",
    "reservas": r"2\. ?Reserves and Surplus",
    "depositos": r"3\. ?Deposits$",
    "emprestimos_tomados": r"4\. ?Borrowings$",
    "caixa": r"1\.? ?Cash in hand",
    "rbi": r"2\. ?Balances with R",
    "investimentos": r"6\. ?Investments$",
    "adiantamentos": r"7\. ?Advances$",
    "prioritario": r"\(i\) ?Priority sectors?$",
    "ativo_fixo": r"8\. ?Fixed Assets$",
    "ativo_total": r"Total Assets$",
}

VARIAVEIS = ["labor", "fixed_assets", "equity", "deposits", "borrowings", "npl", "unused_assets", "net_profit",
             "performing_loans", "investments", "provision", "net_interest_income", "non_interest_income"]
COVARIAVEIS = ["G_NPLs", "SIZE", "IC", "EQTA", "LIQUIDITY", "BME", "PRIORITY", "DIVERSIFICATION"]


def _texto(c):
    return re.sub(r"\s+", " ", str(c)).strip() if isinstance(c, str) else None


def _numero(c):
    if isinstance(c, (int, float)) and not pd.isna(c):
        return float(c)
    s = _texto(c)
    if s is None:
        return np.nan
    if s in {"-", "--", "—"}:
        return 0.0
    try:
        return float(s.replace(",", "").replace(" ", ""))
    except ValueError:
        return np.nan


def ler_b1(nome):
    """B1 de uma edição do STRBI em formato longo, Rs lakh."""
    arq = RAW / "strbi" / f"{nome}.xlsx"
    linhas = []
    for aba, df in pd.read_excel(arq, sheet_name=None, header=None).items():
        if aba == "fonte":
            continue
        m = df.values
        cab = " ".join(str(c) for c in m[:8].ravel() if isinstance(c, str))
        fator = 10.0 if "Million" in cab else 1.0
        anos_lin = next(i for i in range(min(15, len(m)))
                        if sum(bool(re.fullmatch(r"\s*20\d\d\s*", str(c))) for c in m[i]) >= 2)
        col_ano = {j: int(str(c).strip()) for j, c in enumerate(m[anos_lin]) if re.fullmatch(r"\s*20\d\d\s*", str(c))}
        primeira = min(col_ano)
        banco_col = {}
        for i in range(max(0, anos_lin - 3), anos_lin):
            mapa, atual = {}, None
            for j in range(primeira, m.shape[1]):
                t = _texto(m[i, j])
                if t:
                    atual = t
                if j in col_ano and atual is not None:
                    mapa[j] = atual
            if sum(bank_id(t) is not None for t in mapa.values()) > sum(
                    bank_id(t) is not None for t in banco_col.values()):
                banco_col = mapa
        for i in range(anos_lin + 1, len(m)):
            rot = next((_texto(c) for c in m[i, :primeira] if _texto(c)), None)
            if rot is None:
                continue
            item = next((k for k, rx in ROTULOS_B1.items() if re.match(rx, rot, re.I)), None)
            if item is None:
                continue
            for j, ano in col_ano.items():
                b = bank_id(banco_col.get(j, ""))
                if b is None:
                    continue
                linhas.append({"bank_id": b, "ano": ano, "item": item, "valor": _numero(m[i, j]) * fator,
                               "fonte": f"strbi/{nome}.xlsx, aba {aba}"})
    out = pd.DataFrame(linhas)
    return out.drop_duplicates(["bank_id", "ano", "item"], keep="first")


def ler_b1_2014():
    d = pd.read_excel(RAW / "2014" / "b1_2014.xlsx", sheet_name="b1_2014")
    d = d.melt(id_vars="bank_id", var_name="item", value_name="valor")
    d["valor"] *= 100.0
    d["ano"] = 2014
    d["fonte"] = "2014/b1_2014.xlsx (relatórios anuais)"
    return d


def _banco_item(col):
    """(bank_id, item) a partir do nome de coluna do Measure."""
    m = re.match(r"^(.*?) \([^)]*\): (.*)$", col)
    if m:
        return bank_id(m.group(1)), m.group(2)
    partes = [p.strip() for p in col.split(",")]
    for k in (0, 1):
        if k < len(partes) and bank_id(partes[k]):
            return bank_id(partes[k]), ", ".join(partes[k + 1:])
    return None, None


def ler_measure(nome, itens, fator=100.0, somar=False):
    """Séries de março do Measure. itens: {item_padronizado: [itens exatos ou regex]}."""
    d = pd.read_excel(RAW / f"measure_{nome}.xlsx", sheet_name="dados", header=0)
    data = pd.to_datetime(d.iloc[:, 0])
    d = d[(data.dt.month == 3) & data.dt.year.between(ANOS[0], ANOS[-1])]
    anos = data[d.index].dt.year.values
    linhas = []
    for col in d.columns[1:]:
        b, it = _banco_item(str(col))
        if b is None:
            continue
        for chave, alvos in itens.items():
            if any(it == a if isinstance(a, str) else a.fullmatch(it) for a in alvos):
                for ano, v in zip(anos, d[col].values):
                    if pd.notna(v):
                        linhas.append({"bank_id": b, "ano": int(ano), "item": chave, "valor": float(v) * fator,
                                       "fonte": f"measure_{nome}.xlsx: {it}", "rotulo": it})
    out = pd.DataFrame(linhas)
    if somar:
        g = out.groupby(["bank_id", "ano", "item", "rotulo"], as_index=False).agg(valor=("valor", "first"),
                                                                                    fonte=("fonte", "first"))
        out = g.groupby(["bank_id", "ano", "item"], as_index=False).agg(valor=("valor", "sum"))
        out["fonte"] = f"measure_{nome}.xlsx: soma de " + ", ".join(
            a if isinstance(a, str) else a.pattern for v in itens.values() for a in v)
        return out
    return out.drop_duplicates(["bank_id", "ano", "item"], keep="first").drop(columns="rotulo")


def deflator():
    d = pd.read_excel(RAW / "mospi_gva.xlsx")
    idx = d["indice_implicito_2011_12"].copy()
    calc = d["gva_corrente_crore"] / d["gva_constante_2011_12_crore"] * 100
    idx = idx.fillna(calc)
    return {int(af[:4]) + 1: v for af, v in zip(d["ano_fiscal"], idx)}


def montar():
    # Balanço: B1 2009-2013 (edição mais recente para ano repetido), 2014 dos relatórios, Measure 2015-2017.
    b1 = pd.concat([ler_b1("b1_2013"), ler_b1("b1_2011"), ler_b1("b1_2010")])
    b1 = b1.drop_duplicates(["bank_id", "ano", "item"], keep="first")
    b1 = b1[b1["ano"].between(2009, 2013)]
    caixa_rbi = (b1[b1["item"].isin(["caixa", "rbi"])].groupby(["bank_id", "ano"], as_index=False)
                 .agg(valor=("valor", "sum"), fonte=("fonte", "first")).assign(item="caixa_rbi"))
    b1 = pd.concat([b1[~b1["item"].isin(["caixa", "rbi"])], caixa_rbi])

    g = ", global operations"
    bs = ler_measure("banks_balance_sheet", {
        "capital": ["paid-up share capital" + g], "reservas": ["reserves and surplus" + g],
        "depositos": ["total deposits" + g], "emprestimos_tomados": ["total borrowings" + g],
        "caixa_rbi": ["cash funds" + g], "adiantamentos": ["net loans and advances" + g],
        "ativo_fixo": ["fixed assets (net)" + g], "ativo_total": ["total assets" + g]})
    inv = ler_measure("banks_balance_sheet", {"investimentos": ["SLR/approved securities" + g,
                                                                 "non-SLR investments" + g]}, somar=True)
    bs = pd.concat([bs, inv])
    bs = bs[bs["ano"].between(2015, 2017)]

    prio = ler_measure("priority_sector_banks", {"prioritario": [
        "Total Priority Sector Advances (PSA), Priority Sector, Amount Outstanding",
        "Priority Sector, Amount Outstanding"]})
    prio = prio[prio["ano"].between(2014, 2017)]

    res = ler_measure("bank_earnings", {
        "juros_recebidos": ["Earnings, Total (I)"], "outras_receitas": ["Earnings, Total (II)"],
        "juros_pagos": ["Expenses, Total (III)"], "despesas_operacionais": ["Expenses, Total (IV)"],
        "salarios": ["Expenses, Payments to and provisions for employees"],
        "provisoes": ["Expenses, Provisions and Contingencies"],
        "lucro": ["Expenses, Profit (Loss) during the year"]})
    npa = ler_measure("credit_npa_movement", {"npa_bruto": ["gross NPAs at the end of the year"]})
    emp = ler_measure("employees_banks", {"empregados": ["Total"]}, fator=1.0)
    ag = ler_measure("offices_banks", {"agencias": [re.compile(r".*, Branch")]}, fator=1.0, somar=True)

    longo = pd.concat([b1, ler_b1_2014(), bs, prio, res, npa, emp, ag], ignore_index=True)
    longo = longo[longo["bank_id"].isin(IDS) & longo["ano"].isin(ANOS)]
    nom = longo.pivot_table(index=["bank_id", "ano"], columns="item", values="valor", aggfunc="first")
    idx = pd.MultiIndex.from_product([IDS, ANOS], names=["bank_id", "ano"])
    nom = nom.reindex(idx)
    fonte = longo[["item", "ano", "fonte"]].drop_duplicates().sort_values(["item", "ano", "fonte"])
    return nom, fonte


def variaveis(nom):
    v = pd.DataFrame(index=nom.index)
    v["labor"] = nom["empregados"]
    v["fixed_assets"] = nom["ativo_fixo"]
    v["equity"] = nom["capital"] + nom["reservas"]
    v["deposits"] = nom["depositos"]
    v["borrowings"] = nom["emprestimos_tomados"]
    v["npl"] = nom["npa_bruto"]
    v["unused_assets"] = (nom["ativo_total"] - nom["caixa_rbi"] - nom["ativo_fixo"] - nom["adiantamentos"]
                          - nom["investimentos"])
    v["net_profit"] = nom["lucro"]
    v["performing_loans"] = nom["adiantamentos"] - nom["npa_bruto"]
    v["investments"] = nom["investimentos"]
    v["provision"] = nom["provisoes"]
    v["net_interest_income"] = nom["juros_recebidos"] - nom["juros_pagos"]
    v["non_interest_income"] = nom["outras_receitas"]
    return v


def covariaveis(nom, v, defl):
    c = pd.DataFrame(index=nom.index)
    npl = v["npl"]
    ant = npl.groupby(level="bank_id").shift(1)
    c["G_NPLs"] = (npl - ant) / ant
    ta = nom["ativo_total"]
    real = ta / (pd.Series(nom.index.get_level_values("ano").map(defl), index=nom.index) / 100)
    c["SIZE"] = np.log(real)
    c["IC"] = nom["despesas_operacionais"] / ta
    c["EQTA"] = v["equity"] / ta
    c["LIQUIDITY"] = nom["adiantamentos"] / nom["depositos"]
    c["BME"] = nom["salarios"] / nom["despesas_operacionais"]
    c["PRIORITY"] = nom["prioritario"] / ta
    nii, non = v["net_interest_income"], v["non_interest_income"]
    s = nii + non
    c["DIVERSIFICATION"] = 1 - (nii / s) ** 2 - (non / s) ** 2
    return c


def main():
    nom, fonte = montar()
    defl = deflator()
    v = variaveis(nom)
    fator = pd.Series(nom.index.get_level_values("ano").map(defl), index=nom.index) / 100
    p = v.copy()
    monet = [x for x in VARIAVEIS if x != "labor"]
    p[monet] = p[monet].div(fator, axis=0)
    p = p.div(nom["agencias"], axis=0)
    c = covariaveis(nom, v, defl)

    def com_nomes(df):
        df = df.reset_index()
        df.insert(1, "nome", df["bank_id"].map(NOME))
        df.insert(2, "grupo", df["bank_id"].map(GRUPO))
        return df

    nominal = nom.copy()
    falt = []
    for nome_aba, df, cols in (("painel", p, VARIAVEIS), ("covariaveis", c, COVARIAVEIS)):
        for (b, a), row in df[cols].iterrows():
            for col in cols:
                if pd.isna(row[col]) and not (col == "G_NPLs" and a == ANOS[0]):
                    falt.append({"bank_id": b, "ano": a, "aba": nome_aba, "variavel": col})
    for (b, a), row in nom.iterrows():
        for col in nom.columns:
            if pd.isna(row[col]):
                falt.append({"bank_id": b, "ano": a, "aba": "nominal", "variavel": col})
    falt = pd.DataFrame(falt, columns=["bank_id", "ano", "aba", "variavel"])

    SAIDA.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(SAIDA / "painel.xlsx") as w:
        com_nomes(p).to_excel(w, sheet_name="painel", index=False)
        com_nomes(c).to_excel(w, sheet_name="covariaveis", index=False)
        com_nomes(nominal).to_excel(w, sheet_name="nominal", index=False)
        fonte.to_excel(w, sheet_name="fonte", index=False)
        pd.DataFrame({"ano": list(defl), "indice_2011_12": list(defl.values())}).to_excel(
            w, sheet_name="deflator", index=False)
        falt.to_excel(w, sheet_name="faltantes", index=False)

    print("Base gravada em", SAIDA / "painel.xlsx")
    print("\nBancos com as 13 variáveis completas, por ano:")
    for a in ANOS:
        print(f"  {a}: {int(p.xs(a, level='ano')[VARIAVEIS].notna().all(axis=1).sum())}/42")
    print("\nBancos com as 8 covariáveis completas, por ano:")
    for a in ANOS:
        cols = COVARIAVEIS if a > ANOS[0] else COVARIAVEIS[1:]
        print(f"  {a}: {int(c.xs(a, level='ano')[cols].notna().all(axis=1).sum())}/42")
    if falt.empty:
        print("\nFaltantes: nenhum.")
    else:
        print(f"\nFaltantes ({len(falt)} células):")
        for (aba, var), g in falt.groupby(["aba", "variavel"]):
            itens = ", ".join(f"{b} {a}" for b, a in zip(g["bank_id"], g["ano"]))
            print(f"  [{aba}] {var}: {itens}")


if __name__ == "__main__":
    sys.exit(main())
