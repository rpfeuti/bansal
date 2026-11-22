"""Planilha didática: refaz em fórmulas do Excel, passo a passo, os cálculos do pacote.

Rodar da raiz: $env:PYTHONPATH="src"; python -m bansal.planilha_passo_a_passo
Saída: data/saida/planilha_passo_a_passo.xlsx

Lê as saídas já gravadas (data/padronizada/painel.xlsx e data/saida/*.xlsx); não recalcula os índices.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.formula import ArrayFormula

from . import models
from .painel import carregar

RAIZ = Path(__file__).resolve().parents[2]
PAD = RAIZ / "data" / "padronizada" / "painel.xlsx"
SAIDA = RAIZ / "data" / "saida"
ARQ = SAIDA / "planilha_passo_a_passo.xlsx"

NEG = Font(bold=True)
TIT = Font(bold=True, size=14)
CAB = PatternFill("solid", fgColor="DDEBF7")
ENTRADA = PatternFill("solid", fgColor="FFF2CC")  # célula que o usuário pode mudar
DECISAO = PatternFill("solid", fgColor="FCE4D6")  # variável de decisão do Solver
PY = PatternFill("solid", fgColor="E2EFDA")  # valor gravado pelo Python, para comparar
QUEBRA = Alignment(wrap_text=True, vertical="top")

VARS = ["labor", "fixed_assets", "equity", "deposits", "borrowings", "npl", "unused_assets", "net_profit",
        "performing_loans", "investments", "provision", "net_interest_income", "non_interest_income"]
COVS = ["G_NPLs", "SIZE", "IC", "EQTA", "LIQUIDITY", "BME", "PRIORITY", "DIVERSIFICATION"]


def cabecalho(ws, linha, nomes, col0=1):
    for j, n in enumerate(nomes):
        c = ws.cell(linha, col0 + j, n)
        c.font, c.fill = NEG, CAB


def larguras(ws, w):
    for i, x in enumerate(w, 1):
        ws.column_dimensions[L(i)].width = x


def textos(ws, linha, linhas, col=1, largura=None):
    for k, t in enumerate(linhas):
        c = ws.cell(linha + k, col, t)
        if largura:
            c.alignment = Alignment(wrap_text=False)
    return linha + len(linhas)


def rng(aba, col, n):
    return f"'{aba}'!${col}$2:${col}${n + 1}"


# ---------------------------------------------------------------- abas de dados e padronização

def aba_nominal(wb, nom):
    ws = wb.create_sheet("1_Nominal")
    cols = list(nom.columns)
    cabecalho(ws, 1, cols)
    for i, row in enumerate(nom.itertuples(index=False), 2):
        for j, v in enumerate(row, 1):
            ws.cell(i, j, None if (isinstance(v, float) and np.isnan(v)) else v)
    ws.freeze_panes = "E2"
    larguras(ws, [8, 28, 9, 6] + [14] * (len(cols) - 4))
    return {c: L(j) for j, c in enumerate(cols, 1)}


def aba_deflator(wb, defl):
    ws = wb.create_sheet("1b_Deflator")
    cabecalho(ws, 1, ["ano", "indice_2011_12"])
    for i, r in enumerate(defl.itertuples(index=False), 2):
        ws.cell(i, 1, int(r[0]))
        ws.cell(i, 2, float(r[1]))
    ws["D1"] = "Deflator implícito do VAB (MOSPI), base 2011-12 = 100. Usado em 3_Painel e em SIZE."
    larguras(ws, [8, 16])


def aba_variaveis(wb, nom, cn):
    ws = wb.create_sheet("2_Variaveis")
    n = len(nom)
    ws["A1"] = "Passo 2 (padronizar.py, variaveis): as 13 variáveis do paper em valores nominais (Rs lakh; labor em pessoas)."
    ws["A1"].font = NEG
    defs = {
        "labor": "={empregados}",
        "fixed_assets": "={ativo_fixo}",
        "equity": "={capital}+{reservas}",
        "deposits": "={depositos}",
        "borrowings": "={emprestimos_tomados}",
        "npl": "={npa_liquido}",
        "unused_assets": "={ativo_total}-{caixa_rbi}-{ativo_fixo}-{adiantamentos}-{investimentos}",
        "net_profit": "={lucro}",
        "performing_loans": "={adiantamentos}-{npa_liquido}",
        "investments": "={investimentos}",
        "provision": "={provisoes}",
        "net_interest_income": "={juros_recebidos}-{juros_pagos}",
        "non_interest_income": "={outras_receitas}",
    }
    ws["A2"] = "Fórmula de cada coluna (linha 3), com os itens da aba 1_Nominal:"
    cabecalho(ws, 4, ["bank_id", "nome", "grupo", "ano"] + VARS)
    for j, v in enumerate(VARS, 5):
        ws.cell(3, j, defs[v][1:].replace("{", "").replace("}", "")).alignment = QUEBRA
    for i in range(n):
        r, src = 5 + i, 2 + i
        for j, c in enumerate(["bank_id", "nome", "grupo", "ano"], 1):
            ws.cell(r, j, f"='1_Nominal'!{cn[c]}{src}")
        for j, v in enumerate(VARS, 5):
            f = defs[v]
            for item, col in cn.items():
                f = f.replace("{" + item + "}", f"'1_Nominal'!{col}{src}")
            ws.cell(r, j, f)
    ws.row_dimensions[3].height = 60
    ws.freeze_panes = "E5"
    larguras(ws, [8, 28, 9, 6] + [16] * 13)


def aba_painel(wb, n, cn):
    ws = wb.create_sheet("3_Painel")
    cabecalho(ws, 1, ["bank_id", "nome", "grupo", "ano", "fator_deflator", "agencias"] + VARS)
    for i in range(n):
        r, v = 2 + i, 5 + i  # linha em 3_Painel e em 2_Variaveis
        ws.cell(r, 1, f"='2_Variaveis'!A{v}")
        ws.cell(r, 2, f"='2_Variaveis'!B{v}")
        ws.cell(r, 3, f"='2_Variaveis'!C{v}")
        ws.cell(r, 4, f"='2_Variaveis'!D{v}")
        ws.cell(r, 5, f"=VLOOKUP(D{r},'1b_Deflator'!$A$2:$B$10,2,FALSE)/100")
        ws.cell(r, 6, f"='1_Nominal'!{cn['agencias']}{r}")
        for j, var in enumerate(VARS, 7):
            col = L(5 + VARS.index(var))
            if var == "labor":
                ws.cell(r, j, f"='2_Variaveis'!{col}{v}/F{r}")
            else:
                ws.cell(r, j, f"='2_Variaveis'!{col}{v}/E{r}/F{r}")
    nota = n + 3
    textos(ws, nota, [
        "Passo 3 (padronizar.py, main): variáveis monetárias ÷ (deflator/100) ÷ agências; labor só ÷ agências.",
        "Resultado: valores reais (preços de 2011-12) por agência. É o que entra nos modelos DEA (painel.py carrega esta tabela).",
    ])
    ws.freeze_panes = "G2"
    larguras(ws, [8, 28, 9, 6, 12, 10] + [16] * 13)
    return {v: L(7 + k) for k, v in enumerate(VARS)}


def aba_covariaveis(wb, n, cn):
    ws = wb.create_sheet("4_Covariaveis")
    cabecalho(ws, 1, ["bank_id", "nome", "grupo", "ano"] + COVS)
    V = lambda var, r: f"'2_Variaveis'!{L(5 + VARS.index(var))}{r}"  # noqa: E731
    N = lambda item, r: f"'1_Nominal'!{cn[item]}{r}"  # noqa: E731
    for i in range(n):
        r, v = 2 + i, 5 + i
        for j, c in enumerate("ABCD", 1):
            ws.cell(r, j, f"='2_Variaveis'!{c}{v}")
        ws.cell(r, 5, f'=IF(A{r}<>A{r - 1},"",IFERROR(({V("npl", v)}-{V("npl", v - 1)})/{V("npl", v - 1)},""))'
                if i else '=""')
        ws.cell(r, 6, f"=LN({N('ativo_total', r)}/(VLOOKUP(D{r},'1b_Deflator'!$A$2:$B$10,2,FALSE)/100))")
        ws.cell(r, 7, f"={N('despesas_operacionais', r)}/{N('ativo_total', r)}")
        ws.cell(r, 8, f"={V('equity', v)}/{N('ativo_total', r)}")
        ws.cell(r, 9, f"={N('adiantamentos', r)}/{N('depositos', r)}")
        ws.cell(r, 10, f"={N('salarios', r)}/{N('despesas_operacionais', r)}")
        ws.cell(r, 11, f"={N('prioritario', r)}/{N('ativo_total', r)}")
        nii, non = V("net_interest_income", v), V("non_interest_income", v)
        ws.cell(r, 12, f"=1-({nii}/({nii}+{non}))^2-({non}/({nii}+{non}))^2")
    textos(ws, n + 3, [
        "Passo 4 (padronizar.py, covariaveis): variáveis explicativas do GMM (Tabela 6), em valores nominais.",
        "G_NPLs = (NPL_t − NPL_t−1) / NPL_t−1   (vazio em 2009 e quando NPL_t−1 = 0)",
        "SIZE = ln(ativo total ÷ deflator/100)",
        "IC = despesas operacionais ÷ ativo total",
        "EQTA = (capital + reservas) ÷ ativo total",
        "LIQUIDITY = adiantamentos ÷ depósitos",
        "BME = salários ÷ despesas operacionais",
        "PRIORITY = crédito ao setor prioritário ÷ ativo total",
        "DIVERSIFICATION = 1 − (NII/(NII+NonII))² − (NonII/(NII+NonII))²",
    ])
    ws.freeze_panes = "E2"
    larguras(ws, [8, 28, 9, 6] + [15] * 8)


def aba_tabela2(wb, n, pc, t2_py):
    ws = wb.create_sheet("5_Tabela2")
    ws["A1"] = "Passo 5 (calcular.py, tabela2): estatística descritiva das 13 variáveis de 3_Painel, anos 2010-2017."
    ws["A1"].font = NEG
    ws["A2"] = "Curtose = KURT + 3 (curtose de Pearson, como no paper). Fórmulas matriciais filtram ano ≥ 2010."
    stats = ["mean", "sd", "kurtosis", "skewness", "median", "max", "min"]
    cabecalho(ws, 4, ["variavel"] + stats + [f"{s} (Python)" for s in stats])
    ano = rng("3_Painel", "D", n)
    for k, v in enumerate(VARS):
        r = 5 + k
        x = rng("3_Painel", pc[v], n)
        ws.cell(r, 1, v)
        fs = [f"=AVERAGEIFS({x},{ano},\">=2010\")", f"STDEV.S(IF({ano}>=2010,{x}))",
              f"KURT(IF({ano}>=2010,{x}))+3", f"SKEW(IF({ano}>=2010,{x}))", f"MEDIAN(IF({ano}>=2010,{x}))",
              f"=MAXIFS({x},{ano},\">=2010\")", f"=MINIFS({x},{ano},\">=2010\")"]
        for j, f in enumerate(fs, 2):
            ref = f"{L(j)}{r}"
            ws[ref] = f if f.startswith("=") else ArrayFormula(ref, "=" + f)
        py = t2_py.set_index("variavel").loc[v]
        for j, s in enumerate(stats, 9):
            ws.cell(r, j, float(py[s])).fill = PY
    larguras(ws, [22] + [13] * 14)


# ---------------------------------------------------------------- DDF da rede (M1) e caixa-preta (ML)

def resolver_python(painel, F, E, o, caixa_preta=False):
    """Roda o mesmo LP do pacote e devolve (beta, x) para preencher a planilha."""
    guardado = {}
    original = models.maximizar

    def captura(*a, **k):
        valor, x = original(*a, **k)
        guardado["x"] = x
        return valor, x

    models.maximizar = captura
    try:
        if caixa_preta:
            beta = models.ddf_caixa_preta(painel, [F], E, o)
        else:
            beta = models.ddf_rede(painel, [F], E, o, models.direcoes_m1(painel, F))
    finally:
        models.maximizar = original
    return beta, guardado["x"]


def aba_ddf_m1(wb, nome, n, pc, ids, banco, F, E, rotulo, beta_py, x_py):
    ws = wb.create_sheet(nome)
    P = lambda v: rng("3_Painel", pc[v], n)  # noqa: E731
    A_ID, A_ANO = rng("3_Painel", "A", n), rng("3_Painel", "D", n)
    ws["A1"] = f"Passo 6: DDF da rede, modelo (M1), {rotulo}  —  models.py, ddf_rede + direcoes_m1"
    ws["A1"].font = TIT
    ws["A3"], ws["B3"] = "Banco avaliado (o)", banco
    ws["A4"], ws["B4"] = "Ano da fronteira F (tecnologia)", F
    ws["A5"], ws["B5"] = "Ano avaliado E (dados do banco o)", E
    for c in ("B3", "B4", "B5"):
        ws[c].fill = ENTRADA
    ws["A6"], ws["B6"] = "ξ (multiplicador das direções)", models.M1_XI
    ws["A7"], ws["B7"] = "π (deslocamento das direções)", models.M1_PI
    ws["A9"], ws["B9"] = "β (variável de decisão, objetivo: MAXIMIZAR)", float(beta_py)
    ws["B9"].fill, ws["A9"].font = DECISAO, NEG
    ws["A10"], ws["B10"] = "β gravado pelo Python (indices_detalhe.xlsx)", float(beta_py)
    ws["B10"].fill = PY
    ws["D3"] = "Como usar: as células laranja (β e as colunas λ1, φ1, λ2, λ3) já trazem a solução do Python."
    ws["D4"] = "Para resolver no Excel: Dados > Solver. Objetivo $B$9, Máx.; células variáveis $B$9 e $B$62:$E$103;"
    ws["D5"] = "restrições $C$35:$C$42 <= $E$35:$E$42; $C$43:$C$47 >= $E$43:$E$47; $C$48:$C$53 = $E$48:$E$53; $C$62:$E$103 >= 0."
    ws["D6"] = "Desmarque 'Tornar variáveis irrestritas não negativas' (β é livre). Método: LP Simplex. (169 variáveis, abaixo do limite de 200.)"
    ws["D7"] = "Mudando banco/anos (amarelo), zere λ e β e rode o Solver de novo."

    # direções
    ws["A12"] = "Direções (constantes do vetor de direção, eq. 13 do paper)"
    ws["A12"].font = NEG
    cabecalho(ws, 13, ["constante", "valor", "fórmula"])
    maxabs = lambda v, ano: f"MAX(MAXIFS({P(v)},{A_ANO},{ano}),-MINIFS({P(v)},{A_ANO},{ano}))"  # noqa: E731
    dirs = [
        ("μ labor", f"=$B$6*{maxabs('labor', '$B$4')}", "ξ · max|labor| no ano F"),
        ("μ fixed_assets", f"=$B$6*{maxabs('fixed_assets', '$B$4')}", "ξ · max|fixed assets| no ano F"),
        ("μ borrowings", f"=$B$6*{maxabs('borrowings', '$B$4')}", "ξ · max|borrowings| no ano F"),
        ("μ provision", f"=$B$6*{maxabs('provision', '$B$4')}", "ξ · max|provision| no ano F"),
        ("ρ (NPL t−1)", f"=MINIFS({P('npl')},{A_ANO},$B$4-1)-$B$7", "min NPL no ano F−1 − π"),
        ("ω (NPL t)", f"=$B$6*{maxabs('npl', '$B$4')}", "ξ · max|NPL| no ano F"),
        ("ν net_interest_income", f"=MINIFS({P('net_interest_income')},{A_ANO},$B$4)-$B$7", "min no ano F − π"),
        ("ν non_interest_income", f"=MINIFS({P('non_interest_income')},{A_ANO},$B$4)-$B$7", "min no ano F − π"),
        ("γ unused_assets", f"=MINIFS({P('unused_assets')},{A_ANO},$B$4)-$B$7", "min no ano F − π"),
        ("γ net_profit", f"=MINIFS({P('net_profit')},{A_ANO},$B$4)-$B$7", "min no ano F − π"),
        ("α unused_assets", f"=$B$6*{maxabs('unused_assets', '$B$4-1')}", "ξ · max|unused| no ano F−1"),
        ("α net_profit", f"=$B$6*{maxabs('net_profit', '$B$4-1')}", "ξ · max|net profit| no ano F−1"),
    ]
    D = {}
    for k, (a, f, t) in enumerate(dirs):
        r = 14 + k
        ws.cell(r, 1, a)
        ws.cell(r, 2, f)
        ws.cell(r, 3, t)
        D[a] = f"$B${r}"

    # dados do banco avaliado
    ws["E12"] = "Dados do banco avaliado o"
    ws["E12"].font = NEG
    cabecalho(ws, 13, ["variável", "ano E", "ano E−1"], col0=5)
    o = {}
    for k, v in enumerate(VARS):
        r = 14 + k
        ws.cell(r, 5, v)
        ws.cell(r, 6, f"=SUMIFS({P(v)},{A_ID},$B$3,{A_ANO},$B$5)")
        ws.cell(r, 7, f"=SUMIFS({P(v)},{A_ID},$B$3,{A_ANO},$B$5-1)")
        o[v], o[v, -1] = f"$F${r}", f"$G${r}"

    # tabela de referência: bancos com dados do ano F (e F−1)
    T0 = 61
    ws.cell(T0 - 1, 1, "Tecnologia de referência: os 42 bancos no ano F. λ1 (divisão 1), φ1 (quase-fixo), "
                       "λ2 (divisão 2), λ3 (divisão 3).").font = NEG
    dcols = [("labor", 0), ("fixed_assets", 0), ("equity", 0), ("deposits", 0), ("borrowings", 0), ("npl", 0),
             ("npl", -1), ("unused_assets", 0), ("unused_assets", -1), ("net_profit", 0), ("net_profit", -1),
             ("performing_loans", 0), ("investments", 0), ("provision", 0), ("net_interest_income", 0),
             ("non_interest_income", 0)]
    cabecalho(ws, T0, ["bank_id", "λ1", "φ1", "λ2", "λ3"]
              + [f"{v} (F)" if d == 0 else f"{v} (F−1)" for v, d in dcols])
    col_de = {}
    for j, (v, d) in enumerate(dcols, 6):
        col_de[v, d] = L(j)
    for i, b in enumerate(ids):
        r = T0 + 1 + i
        ws.cell(r, 1, b)
        for p in range(4):
            c = ws.cell(r, 2 + p, float(x_py[p * len(ids) + i]))
            c.fill = DECISAO
        for (v, d), col in col_de.items():
            ano = "$B$4" if d == 0 else "$B$4-1"
            ws[f"{col}{r}"] = f"=SUMIFS({P(v)},{A_ID},$A{r},{A_ANO},{ano})"
    r0, r1 = T0 + 1, T0 + len(ids)
    lam = {k: f"${c}${r0}:${c}${r1}" for k, c in zip(("l1", "f1", "l2", "l3"), "BCDE")}
    dat = {k: f"${c}${r0}:${c}${r1}" for k, c in col_de.items()}
    sp = lambda l, k: f"SUMPRODUCT({lam[l]},{dat[k]})"  # noqa: E731

    # restrições
    ws["A33"] = "Restrições do LP (eqs. 5–12 do paper). Coluna C = lado esquerdo, E = lado direito; F = folga."
    ws["A33"].font = NEG
    cabecalho(ws, 34, ["restrição", "divisão", "Σ λ·dado", "sinal", "limite", "folga", "leitura"])
    B = "$B$9"
    restr = [
        ("Labor", "1", sp("l1", ("labor", 0)), "<=", f"={o['labor']}-{B}*({o['labor']}+{D['μ labor']})",
         "insumo: reduz β·(x_o + μ)"),
        ("Fixed assets", "1", sp("l1", ("fixed_assets", 0)), "<=",
         f"={o['fixed_assets']}-{B}*({o['fixed_assets']}+{D['μ fixed_assets']})", "insumo"),
        ("Borrowings", "2", sp("l2", ("borrowings", 0)), "<=",
         f"={o['borrowings']}-{B}*({o['borrowings']}+{D['μ borrowings']})", "insumo"),
        ("Provision", "3", sp("l3", ("provision", 0)), "<=",
         f"={o['provision']}-{B}*({o['provision']}+{D['μ provision']})", "insumo"),
        ("Equity (quase-fixo)", "1", f"{sp('l1', ('equity', 0))}+{sp('f1', ('equity', 0))}", "<=",
         f"={o['equity']}", "(λ1+φ1)·V ≤ V_o, eq. 6"),
        ("NPL t (indesejável)", "2", sp("l2", ("npl", 0)), "<=",
         f"={o['npl']}-{B}*({o['npl']}+{D['ω (NPL t)']})", "reduz NPL, eq. 9"),
        ("Unused assets t−1 (carryover)", "2", sp("l2", ("unused_assets", -1)), "<=",
         f"={o['unused_assets', -1]}-{B}*({o['unused_assets', -1]}+{D['α unused_assets']})", "eq. 11"),
        ("Net profit t−1 (carryover)", "2", sp("l2", ("net_profit", -1)), "<=",
         f"={o['net_profit', -1]}-{B}*({o['net_profit', -1]}+{D['α net_profit']})", "eq. 11"),
        ("NPL t−1 (entrada)", "2", sp("l2", ("npl", -1)), ">=",
         f"={o['npl', -1]}+{B}*({o['npl', -1]}-{D['ρ (NPL t−1)']})", "eq. 7"),
        ("Unused assets t (carryover)", "2", sp("l2", ("unused_assets", 0)), ">=",
         f"={o['unused_assets']}+{B}*({o['unused_assets']}-{D['γ unused_assets']})", "eq. 10"),
        ("Net profit t (carryover)", "2", sp("l2", ("net_profit", 0)), ">=",
         f"={o['net_profit']}+{B}*({o['net_profit']}-{D['γ net_profit']})", "eq. 10"),
        ("Net interest income", "3", sp("l3", ("net_interest_income", 0)), ">=",
         f"={o['net_interest_income']}+{B}*({o['net_interest_income']}-{D['ν net_interest_income']})",
         "produto: aumenta β·(y_o − ν), eq. 8"),
        ("Non-interest income", "3", sp("l3", ("non_interest_income", 0)), ">=",
         f"={o['non_interest_income']}+{B}*({o['non_interest_income']}-{D['ν non_interest_income']})", "produto"),
        ("Deposits (elo 1→2)", "1→2", sp("l1", ("deposits", 0)), "=", "=" + sp("l2", ("deposits", 0)),
         "o que a divisão 1 produz a 2 consome, eq. 12"),
        ("Performing loans (elo 2→3)", "2→3", sp("l2", ("performing_loans", 0)), "=",
         "=" + sp("l3", ("performing_loans", 0)), "eq. 12"),
        ("Investments (elo 2→3)", "2→3", sp("l2", ("investments", 0)), "=",
         "=" + sp("l3", ("investments", 0)), "eq. 12"),
        ("Σ λ1 = 1 (VRS)", "1", f"SUM({lam['l1']})", "=", 1, "retornos variáveis de escala"),
        ("Σ λ2 = 1 (VRS)", "2", f"SUM({lam['l2']})", "=", 1, ""),
        ("Σ λ3 = 1 (VRS)", "3", f"SUM({lam['l3']})", "=", 1, ""),
    ]
    assert len(restr) == 19
    for k, (nm, dv, lhs, s, rhs, leitura) in enumerate(restr):
        r = 35 + k
        ws.cell(r, 1, nm)
        ws.cell(r, 2, dv)
        ws.cell(r, 3, "=" + lhs)
        ws.cell(r, 4, s)
        ws.cell(r, 5, rhs)
        if s == "<=":
            ws.cell(r, 6, f"=E{r}-C{r}")
        elif s == ">=":
            ws.cell(r, 6, f"=C{r}-E{r}")
        else:
            ws.cell(r, 6, f"=C{r}-E{r}")
        ws.cell(r, 7, leitura)
    ws["A55"] = "Leitura de β: quanto o banco poderia, ao mesmo tempo, reduzir insumos e NPL e aumentar produtos, " \
                "em proporção das direções. β = 0: o banco está na fronteira. β < 0 só ocorre quando E ≠ F."
    ws["A56"] = "Folga ≥ 0 em todas as linhas (e ≈ 0 nas igualdades) confirma que λ e β formam uma solução viável."
    larguras(ws, [34, 14, 16, 6, 16, 14, 40] + [14] * 16)
    ws.freeze_panes = "B1"
    return "B9"


def aba_ddf_ml(wb, nome, n, pc, ids, banco, F, E, beta_py, x_py):
    ws = wb.create_sheet(nome)
    P = lambda v: rng("3_Painel", pc[v], n)  # noqa: E731
    A_ID, A_ANO = rng("3_Painel", "A", n), rng("3_Painel", "D", n)
    ws["A1"] = "Passo 6b: DDF caixa-preta (MLPI, seção 4.3.2) — models.py, ddf_caixa_preta"
    ws["A1"].font = TIT
    ws["A3"], ws["B3"] = "Banco avaliado (o)", banco
    ws["A4"], ws["B4"] = "Ano da fronteira F", F
    ws["A5"], ws["B5"] = "Ano avaliado E", E
    for c in ("B3", "B4", "B5"):
        ws[c].fill = ENTRADA
    ws["A7"], ws["B7"] = "β (decisão, MAXIMIZAR)", float(beta_py)
    ws["B7"].fill, ws["A7"].font = DECISAO, NEG
    ws["A8"], ws["B8"] = "β gravado pelo Python", float(beta_py)
    ws["B8"].fill = PY
    ws["D3"] = "Sem divisões: insumos labor e fixed assets; produtos NII e Non-II; NPL indesejável (igualdade)."
    ws["D4"] = "Solver: objetivo $B$7 Máx.; variáveis $B$7 e $B$22:$B$63; restrições $C$12:$C$13 <= $E$12:$E$13; " \
               "$C$14:$C$15 >= $E$14:$E$15; $C$16:$C$17 = $E$16:$E$17; $B$22:$B$63 >= 0; β livre; LP Simplex."
    cabecalho(ws, 11, ["restrição", "", "Σ λ·dado", "sinal", "limite"])
    cabecalho(ws, 21, ["bank_id", "λ", "labor", "fixed_assets", "net_interest_income", "non_interest_income", "npl"])
    vs = ["labor", "fixed_assets", "net_interest_income", "non_interest_income", "npl"]
    for i, b in enumerate(ids):
        r = 22 + i
        ws.cell(r, 1, b)
        ws.cell(r, 2, float(x_py[i])).fill = DECISAO
        for j, v in enumerate(vs, 3):
            ws.cell(r, j, f"=SUMIFS({P(v)},{A_ID},$A{r},{A_ANO},$B$4)")
    lam = f"$B$22:$B${21 + len(ids)}"
    col = {v: f"${L(3 + k)}$22:${L(3 + k)}${21 + len(ids)}" for k, v in enumerate(vs)}
    ov = lambda v: f"SUMIFS({P(v)},{A_ID},$B$3,{A_ANO},$B$5)"  # noqa: E731
    rs = [("Labor", "<=", f"={ov('labor')}"),
          ("Fixed assets", "<=", f"={ov('fixed_assets')}"),
          ("Net interest income", ">=", f"=(1+$B$7)*{ov('net_interest_income')}"),
          ("Non-interest income", ">=", f"=(1+$B$7)*{ov('non_interest_income')}"),
          ("NPL (indesejável)", "=", f"=(1-$B$7)*{ov('npl')}"),
          ("Σ λ = 1 (VRS)", "=", 1)]
    for k, (nm, s, rhs) in enumerate(rs):
        r = 12 + k
        ws.cell(r, 1, nm)
        ws.cell(r, 3, f"=SUMPRODUCT({lam},{col[vs[k]]})" if k < 5 else f"=SUM({lam})")
        ws.cell(r, 4, s)
        ws.cell(r, 5, rhs)
    larguras(ws, [26, 14, 16, 16, 18, 18, 14])


def aba_indice_exemplo(wb, banco, t, refs, py):
    ws = wb.create_sheet("6e_Indice_exemplo")
    ws["A1"] = f"Passo 7: do β aos índices (equação 14) — indices.py, componentes. Banco {banco}, par {t}→{t + 1}."
    ws["A1"].font = TIT
    cabecalho(ws, 3, ["DDF", "significado", "β (das abas 6_)", "Python"])
    sig = {"D00": f"fronteira {t}, dados {t}", "D01": f"fronteira {t}, dados {t + 1}",
           "D10": f"fronteira {t + 1}, dados {t}", "D11": f"fronteira {t + 1}, dados {t + 1}"}
    for k, d in enumerate(["D00", "D01", "D10", "D11"]):
        r = 4 + k
        ws.cell(r, 1, d)
        ws.cell(r, 2, sig[d])
        ws.cell(r, 3, f"='{refs[d]}'!B9")
        ws.cell(r, 4, float(py[d])).fill = PY
    cabecalho(ws, 10, ["componente", "fórmula", "valor", "Python"])
    linhas = [("EC (efficiency change)", "(1 + D00) / (1 + D11)", "=(1+C4)/(1+C7)", py["EC"]),
              ("TC (technical change)", "√[ (1 + D11)/(1 + D01) · (1 + D10)/(1 + D00) ]",
               "=SQRT((1+C7)/(1+C5)*(1+C6)/(1+C4))", py["TC"]),
              ("DMLPI = EC · TC", "EC × TC", "=C11*C12", py["IDX"])]
    for k, (a, b, f, v) in enumerate(linhas):
        r = 11 + k
        ws.cell(r, 1, a)
        ws.cell(r, 2, b)
        ws.cell(r, 3, f)
        ws.cell(r, 4, float(v)).fill = PY
    ws["A16"] = "Índice > 1: ganho de produtividade; EC > 1: o banco se aproximou da fronteira; TC > 1: a fronteira avançou."
    ws["A17"] = "O DSMLPI (M2) usa o mesmo LP, mas a fronteira junta todos os anos de 2010 até F (sequencial) e " \
                "ξ = 3 (F = t) ou 1,5 (F = t+1), π = 1 — fica com 42 × 4 × nº de anos variáveis, além do limite do Solver."
    larguras(ws, [24, 44, 16, 16])


# ---------------------------------------------------------------- índices e tabelas

def aba_indices(wb, det):
    ws = wb.create_sheet("8_Indices")
    cols = ["indice", "bank_id", "banco", "grupo", "ano", "D00", "D01", "D10", "D11"]
    cabecalho(ws, 1, cols + ["EC", "TC", "IDX", "ln EC", "ln TC", "ln IDX"])
    for i, row in enumerate(det[cols].itertuples(index=False), 2):
        for j, v in enumerate(row, 1):
            ws.cell(i, j, None if (isinstance(v, float) and np.isnan(v)) else v)
        r = i
        ws.cell(r, 10, f'=IF(COUNT(F{r},I{r})=2,(1+F{r})/(1+I{r}),"")')
        ws.cell(r, 11, f'=IF(COUNT(F{r}:I{r})=4,SQRT((1+I{r})/(1+G{r})*(1+H{r})/(1+F{r})),"")')
        ws.cell(r, 12, f'=IF(COUNT(J{r}:K{r})=2,J{r}*K{r},"")')
        for k, c in enumerate("JKL"):
            ws.cell(r, 13 + k, f'=IF(N({c}{r})>0,LN({c}{r}),"")')
    n = len(det)
    textos(ws, n + 3, [
        "Passo 8 (calcular.py, indices_banco_ano): D00–D11 são os β de cada LP (como nas abas 6_), gravados pelo Python.",
        "DMLPI = rede (M1); DSMLPI = rede sequencial (M2); MLPI = caixa-preta; SMLPI = caixa-preta sequencial.",
        "Célula vazia em D: LP inviável; o componente fica vazio. ln: usado nas médias geométricas (exp da média dos ln).",
        "As Tabelas B1 e B2 do paper são esta aba filtrada por grupo (público/privado).",
    ])
    ws.auto_filter.ref = f"A1:O{n + 1}"
    ws.freeze_panes = "F2"
    larguras(ws, [9, 8, 28, 9, 6] + [11] * 10)
    return n


def aba_tabela_ano(wb, nome, ni, modelos, py, titulo):
    ws = wb.create_sheet(nome)
    ws["A1"] = titulo
    ws["A1"].font = NEG
    ws["A2"] = "Média geométrica = EXP(média dos ln) por ano e grupo, a partir de 8_Indices (calcular.py, tabela_ano)."
    IND, GR, ANO = (rng("8_Indices", c, ni) for c in "ADE")
    LN = {c: rng("8_Indices", x, ni) for c, x in (("EC", "M"), ("TC", "N"), ("IDX", "O"))}
    nomes_cols = [c for m in modelos for c in m[1]]
    cabecalho(ws, 4, ["painel", "ano"] + nomes_cols + [f"{c} (Python)" for c in nomes_cols])
    r = 5
    pyi = py.set_index(["painel", "ano"])
    for painel, crit in (("todos", '"*"'), ("publico", '"publico"'), ("privado", '"privado"')):
        for ano in [str(a) for a in range(2011, 2018)] + ["2010-17"]:
            ws.cell(r, 1, painel)
            ws.cell(r, 2, ano)
            ca = f'"{ano}"' if ano != "2010-17" else '">0"'
            j = 3
            for modelo, cs in modelos:
                for comp, c in zip(("EC", "TC", "IDX"), cs):
                    ws.cell(r, j, f'=EXP(AVERAGEIFS({LN[comp]},{IND},"{modelo}",{GR},{crit},{ANO},{ca}))')
                    ws.cell(r, j + len(nomes_cols), float(pyi.loc[(painel, ano), c])).fill = PY
                    j += 1
            r += 1
    larguras(ws, [10, 9] + [11] * (2 * len(nomes_cols)))


def aba_tabela4(wb, ni, t4_py, ids):
    ws = wb.create_sheet("10_Tabela4")
    ws["A1"] = "Tabela 4 (calcular.py, tabela4): média geométrica 2011-2017 de cada banco."
    ws["A1"].font = NEG
    IND, BID = rng("8_Indices", "A", ni), rng("8_Indices", "B", ni)
    LN = {c: rng("8_Indices", x, ni) for c, x in (("EC", "M"), ("TC", "N"), ("IDX", "O"))}
    cols = [("DMLPI", "EC", "EC_M1"), ("DMLPI", "TC", "TC_M1"), ("DMLPI", "IDX", "DMLPI"),
            ("DSMLPI", "EC", "EC_M2"), ("DSMLPI", "TC", "TC_M2"), ("DSMLPI", "IDX", "DSMLPI")]
    cabecalho(ws, 3, ["bank_id", "banco", "grupo"] + [c[2] for c in cols] + [f"{c[2]} (Python)" for c in cols])
    for i, row in enumerate(t4_py.itertuples(index=False)):
        r = 4 + i
        if i < len(ids):
            ws.cell(r, 1, ids[i])
        ws.cell(r, 2, row.banco)
        ws.cell(r, 3, row.grupo)
        for j, (m, comp, c) in enumerate(cols, 4):
            if i < len(ids):
                ws.cell(r, j, f'=IFERROR(EXP(AVERAGEIFS({LN[comp]},{IND},"{m}",{BID},$A{r})),"")')
            else:
                col = L(j)
                faixa = f"{col}4:{col}{3 + len(ids)}"
                ref = f"{col}{r}"
                ws[ref] = ArrayFormula(ref, f'=EXP(AVERAGE(IF(($C$4:$C${3 + len(ids)}="privado")*ISNUMBER({faixa}),LN({faixa}))))')
            ws.cell(r, j + len(cols), float(getattr(row, c))).fill = PY
    larguras(ws, [8, 30, 9] + [11] * 12)


def aba_li(wb, det, ni):
    ws = wb.create_sheet("12_Li")
    ws["A1"] = "Passo 10: teste de Li (1996), Painel D da Tabela 3 — li_test.py. Exemplo: EC do DMLPI, público × privado."
    ws["A1"].font = TIT
    d = det.reset_index(drop=True)
    pub = [i for i in d.index if d.at[i, "indice"] == "DMLPI" and d.at[i, "grupo"] == "publico"]
    priv = [i for i in d.index if d.at[i, "indice"] == "DMLPI" and d.at[i, "grupo"] == "privado"]
    cabecalho(ws, 3, ["x (público)", "y (privado)"])
    for k, i in enumerate(pub):
        ws.cell(4 + k, 1, f"='8_Indices'!J{i + 2}")
    for k, i in enumerate(priv):
        ws.cell(4 + k, 2, f"='8_Indices'!J{i + 2}")
    X = f"$A$4:$A${3 + len(pub)}"
    Y = f"$B$4:$B${3 + len(priv)}"
    K = "/SQRT(2*PI())"
    passos = [
        ("n1", f"=COUNT({X})", "nº de observações públicas"),
        ("n2", f"=COUNT({Y})", "nº de observações privadas"),
        ("h", f"=1.06*STDEV.S({X},{Y})*(E4+E5)^(-0.2)", "janela de Silverman na amostra conjunta"),
        ("δ", "=E4/E5", "n1/n2"),
        ("K(0)", f"=1{K}", "kernel gaussiano em 0"),
        ("Sxx", f"{{SUM(EXP(-0.5*(({X}-TRANSPOSE({X}))/E6)^2)){K}", "Σ_i Σ_j K((x_i−x_j)/h), com diagonal"),
        ("Syy", f"{{SUM(EXP(-0.5*(({Y}-TRANSPOSE({Y}))/E6)^2)){K}", "idem para y"),
        ("Sxy", f"{{SUM(EXP(-0.5*(({X}-TRANSPOSE({Y}))/E6)^2)){K}", "Σ_i Σ_j K((x_i−y_j)/h)"),
        ("I", "=((E9-E4*E8)/(E4*(E4-1))+(E10-E5*E8)/(E5*(E5-1))-2*E11/(E4*E5))/E6",
         "distância integrada entre as densidades (sem diagonal)"),
        ("σ²", "=2*(1/(2*SQRT(PI())))*(E9/(E4^2*E6)+E7^2*E10/(E5^2*E6)+2*E7*E11/(E4*E5*E6))", "variância"),
        ("T", "=E4*SQRT(E6)*E12/SQRT(E13)", "estatística de Li"),
        ("p-valor", "=1-NORM.S.DIST(E14,TRUE)", "unilateral, N(0,1)"),
    ]
    cabecalho(ws, 3, ["passo", "valor", "o que é"], col0=4)
    for k, (a, f, t) in enumerate(passos):
        r = 4 + k
        ws.cell(r, 4, a)
        ref = f"E{r}"
        ws[ref] = ArrayFormula(ref, "=" + f[1:]) if f.startswith("{") else f
        ws.cell(r, 6, t)
    li = pd.read_excel(SAIDA / "tabela3_li.xlsx").set_index("componente")
    ws["D17"], ws["E17"] = "T (Python)", float(li.at["EC_M1", "teste_li"])
    ws["E17"].fill = PY
    ws["D19"] = "Os outros componentes (TC_M1, DMLPI, EC_M2…) seguem a mesma conta trocando as colunas x e y."
    larguras(ws, [13, 13, 3, 10, 14, 50])


def aba_gmm(wb):
    ws = wb.create_sheet("13_GMM")
    t6 = pd.read_excel(SAIDA / "tabela6.xlsx")
    ws["A1"] = "Passo 11: GMM de sistema em dois passos (Tabela 6) — gmm.py. Explicado aqui; não refeito em fórmulas."
    ws["A1"].font = TIT
    linhas = [
        "Modelo: y_it = a·y_i,t−1 + Σ b_k·x_k,it + c + u_it, com y = EC, TC ou índice (8_Indices) e x = covariáveis (4_Covariaveis).",
        "Anos 2011–2017; cada coluna da Tabela 6 usa a lista de covariáveis em calcular.py (GMM_XS).",
        "1. Monta duas equações por banco: em diferenças (Δy_t sobre Δy_t−1, Δx_t) e em nível (y_t sobre y_t−1, x_t, constante).",
        "2. Instrumentos: y_t−2, y_t−3, … nas diferenças; Δy_t−1 no nível; as próprias covariáveis (Δx e x) e a constante.",
        "3. Passo 1: estimador GMM com matriz de pesos A1 = (Σ Z'HZ)⁻¹, H = estrutura do erro em diferença.",
        "4. Passo 2: refaz com A2 = (Σ Z'u u'Z)⁻¹ usando os resíduos do passo 1 → coeficientes finais.",
        "5. Erros-padrão com a correção de Windmeijer (2005) para amostra finita.",
        "6. Testes: AR(1), AR(2) de Arellano-Bond nos resíduos em diferença; Sargan e Hansen J (sobreidentificação); Wald χ².",
        "Por que não em Excel: são inversões de matrizes de dezenas de instrumentos por banco; ficaria ilegível.",
        "Resultado gravado pelo Python (data/saida/tabela6.xlsx):",
    ]
    textos(ws, 3, linhas)
    r0 = 3 + len(linhas) + 1
    cabecalho(ws, r0, list(t6.columns))
    for i, row in enumerate(t6.itertuples(index=False), r0 + 1):
        for j, v in enumerate(row, 1):
            ws.cell(i, j, None if (isinstance(v, float) and np.isnan(v)) else v)
    larguras(ws, [18, 12] + [12] * 6)


def aba_leiame(wb):
    ws = wb["0_LEIA-ME"]
    ws["A1"] = "Bansal et al. (2022) — os cálculos do app, passo a passo, em fórmulas do Excel"
    ws["A1"].font = TIT
    linhas = [
        "",
        "Cores: amarelo = entrada que você pode mudar; laranja = variável de decisão do Solver; verde = valor gravado pelo Python, para comparar.",
        "As fórmulas são vivas: mude um número em 1_Nominal e tudo abaixo recalcula (menos os β das LPs, que exigem o Solver).",
        "",
        "Aba | Etapa | Código Python",
        "1_Nominal | Itens contábeis brutos por banco e ano, já lidos das fontes (Rs lakh). | padronizar.py: montar",
        "1b_Deflator | Deflator do VAB, base 2011-12. | padronizar.py: deflator",
        "2_Variaveis | As 13 variáveis do paper, nominais. | padronizar.py: variaveis",
        "3_Painel | ÷ deflator ÷ agências → painel usado nos modelos. | padronizar.py: main; painel.py",
        "4_Covariaveis | 8 covariáveis do GMM. | padronizar.py: covariaveis",
        "5_Tabela2 | Estatística descritiva. | calcular.py: tabela2",
        "6_DDF_M1_D00..D11 | As 4 LPs da rede (M1) de um banco, prontas para o Solver. | models.py: direcoes_m1, ddf_rede; simplex.py",
        "7_DDF_ML_D00 | Uma LP do modelo caixa-preta. | models.py: ddf_caixa_preta",
        "6e_Indice_exemplo | Dos 4 β ao EC, TC e DMLPI do banco. | indices.py: componentes",
        "8_Indices | EC, TC e índice de todos os bancos, anos e modelos. | calcular.py: indices_banco_ano",
        "9_Tabela3 / 11_Tabela5 | Médias geométricas por ano e grupo. | calcular.py: tabela_ano",
        "10_Tabela4 | Médias geométricas por banco. | calcular.py: tabela4",
        "12_Li | Teste de Li para EC do DMLPI. | li_test.py",
        "13_GMM | Passos do GMM de sistema e resultado. | gmm.py",
        "",
        "O que fica fora: a leitura dos arquivos brutos (padronizar.py: ler_b1, ler_measure, ler_npa_liquido_strbi) — a aba 1_Nominal",
        "já é o resultado dela —, o algoritmo simplex em si (simplex.py; no Excel o Solver faz esse papel) e as LPs do M2/SMLPI,",
        "que têm variáveis demais para o Solver padrão (limite de 200).",
        "",
        "Regerar esta planilha: $env:PYTHONPATH=\"src\"; python -m bansal.planilha_passo_a_passo",
    ]
    textos(ws, 2, linhas)
    larguras(ws, [140])


FUNCOES_NOVAS = ("STDEV.S", "MAXIFS", "MINIFS", "NORM.S.DIST")


def novas(wb):
    """Prefixo _xlfn. que o Excel exige no arquivo para funções posteriores ao Excel 2007."""
    def troca(t):
        for f in FUNCOES_NOVAS:
            t = t.replace(f + "(", "_xlfn." + f + "(").replace("_xlfn._xlfn.", "_xlfn.")
        return t
    for ws in wb:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, ArrayFormula):
                    c.value.text = troca(c.value.text)
                elif isinstance(c.value, str) and c.value.startswith("="):
                    c.value = troca(c.value)


def main():
    xl = pd.ExcelFile(PAD)
    nom = xl.parse("nominal")
    defl = xl.parse("deflator")
    det = pd.read_excel(SAIDA / "indices_detalhe.xlsx")
    painel, _, meta = carregar()
    ids = meta["ids"]
    n = len(nom)

    wb = Workbook()
    wb.active.title = "0_LEIA-ME"
    cn = aba_nominal(wb, nom)
    aba_deflator(wb, defl)
    aba_variaveis(wb, nom, cn)
    pc = aba_painel(wb, n, cn)
    aba_covariaveis(wb, n, cn)
    aba_tabela2(wb, n, pc, pd.read_excel(SAIDA / "tabela2.xlsx"))

    banco, t = "SBI", 2010
    o = ids.index(banco)
    linha = det[(det["indice"] == "DMLPI") & (det["bank_id"] == banco) & (det["ano"] == t + 1)].iloc[0]
    refs = {}
    for d, (F, E) in {"D00": (t, t), "D01": (t, t + 1), "D10": (t + 1, t), "D11": (t + 1, t + 1)}.items():
        beta, x = resolver_python(painel, F, E, o)
        nome = f"6_DDF_M1_{d}"
        aba_ddf_m1(wb, nome, n, pc, ids, banco, F, E, f"{d}: fronteira {F}, dados {E}", beta, x)
        refs[d] = nome
    aba_indice_exemplo(wb, banco, t, refs, linha)
    beta, x = resolver_python(painel, t, t, o, caixa_preta=True)
    aba_ddf_ml(wb, "7_DDF_ML_D00", n, pc, ids, banco, t, t, beta, x)

    ni = aba_indices(wb, det)
    aba_tabela_ano(wb, "9_Tabela3", ni, [("DMLPI", ("EC_M1", "TC_M1", "DMLPI")),
                                         ("DSMLPI", ("EC_M2", "TC_M2", "DSMLPI"))],
                   pd.read_excel(SAIDA / "tabela3.xlsx", dtype={"ano": str}),
                   "Tabela 3: DMLPI (M1) e DSMLPI (M2), médias geométricas por ano.")
    aba_tabela4(wb, ni, pd.read_excel(SAIDA / "tabela4.xlsx"), ids)
    aba_tabela_ano(wb, "11_Tabela5", ni, [("MLPI", ("EC_ML", "TC_ML", "MLPI")),
                                          ("SMLPI", ("EC_SML", "TC_SML", "SMLPI"))],
                   pd.read_excel(SAIDA / "tabela5.xlsx", dtype={"ano": str}),
                   "Tabela 5: MLPI e SMLPI (caixa-preta), médias geométricas por ano.")
    aba_li(wb, det, ni)
    aba_gmm(wb)
    aba_leiame(wb)

    novas(wb)
    wb.save(ARQ)
    print("Planilha gravada em", ARQ)


if __name__ == "__main__":
    main()
