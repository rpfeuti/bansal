"""SBH, CSB e NAIN: sem relatório de 31/03/2014.
Por decisão do usuário, os 9 itens de 2014 = média simples dos balanços de
31/03/2013 (RBI STRBI, Tabela B1, Rs milhões -> crore) e 31/03/2015 (Measure, global, Rs crore).
"""
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1]
AQUI = Path(__file__).parent
COLS = ["capital", "reservas", "depositos", "emprestimos_tomados",
        "caixa_rbi", "investimentos", "adiantamentos", "ativo_fixo", "ativo_total"]

# banco -> (aba STRBI, nome no STRBI, nome no Measure)
BANCOS = {
    "SBH": ("SBI&A", "State Bank of Hyderabad", "State Bank of Hyderabad"),
    "CSB": ("OPB", "Catholic Syrian Bank", "CSB Bank Limited"),
    "NAIN": ("OPB", "Nainital Bank", "Nainital Bank Ltd"),
}


def col_2013(t, nome):
    hdr = t.iloc[2]
    for j, v in enumerate(hdr):
        if str(v).strip().lower().startswith(nome.lower()):
            return j + 1          # (2012, 2013): 2013 é a segunda coluna do par
    raise KeyError(nome)


def linha(t, inicio):
    for i in range(len(t)):
        if str(t.iloc[i, 0]).strip().startswith(inicio):
            return i
    raise KeyError(inicio)


def strbi_2013(aba, nome):
    xl = pd.ExcelFile(RAW / "strbi" / "b1_2013.xlsx")
    L = xl.parse(f"{aba} - I", header=None)
    A = xl.parse(f"{aba} - II", header=None)
    jl, ja = col_2013(L, nome), col_2013(A, nome)
    gl = lambda p: float(L.iloc[linha(L, p), jl])
    ga = lambda p: float(A.iloc[linha(A, p), ja])
    v = [gl("1.     Capital"), gl("2.     Reserves"), gl("3.     Deposits"),
         gl("4.     Borrowings"),
         ga("1.     Cash in hand") + ga("2.     Balances with RBI"),
         ga("6.     Investments"), ga("7.     Advances"), ga("8.     Fixed Assets"),
         ga("Total Assets")]
    return [x / 10 for x in v]    # Rs milhões -> crore


def measure_2015(nome):
    d = pd.read_excel(RAW / "measure_banks_balance_sheet.xlsx", sheet_name="dados")
    d["date"] = pd.to_datetime(d["date"])
    s = d.set_index("date").loc[pd.Timestamp("2015-03-01")]
    g = lambda item: float(s[f"{nome}, {item}, global operations"])
    return [g("paid-up share capital"), g("reserves and surplus"), g("total deposits"),
            g("total borrowings"), g("cash funds"),
            g("SLR/approved securities") + g("non-SLR investments"),
            g("net loans and advances"), g("fixed assets (net)"), g("total assets")]


linhas = []
for b, (aba, n_strbi, n_meas) in BANCOS.items():
    a13, a15 = strbi_2013(aba, n_strbi), measure_2015(n_meas)
    for rot, v in (("2013", a13), ("2015", a15), ("media", [(x + y) / 2 for x, y in zip(a13, a15)])):
        linhas.append({"bank_id": b, "versao": rot, **dict(zip(COLS, v))})
df = pd.DataFrame(linhas)
print(df.round(2).to_string())

fonte = pd.DataFrame([{
    "bank_id": b,
    "metodo": "média simples de 31/03/2013 (RBI STRBI B1, Rs milhões/10) e 31/03/2015 "
              "(Measure, global, Rs crore); decisão do usuário",
} for b in BANCOS])
saida = AQUI / "b1_2014_media.xlsx"
with pd.ExcelWriter(saida) as w:
    df.to_excel(w, sheet_name="b1_2014", index=False)
    fonte.to_excel(w, sheet_name="fonte", index=False)
print("gravado", saida)
