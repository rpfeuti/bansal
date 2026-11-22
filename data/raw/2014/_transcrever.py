"""Transcreve para b1_2014.xlsx o balanço de 31/03/2014 (standalone) dos bancos
cujo relatório foi lido em texto (data/raw/2014/texto/*.txt).

Valores exatamente como impressos no relatório, convertidos para Rs crore.
Os bancos com PDF em data/raw/2014/{ID}.pdf entram em outra etapa.
"""
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).parent
COLS = ["capital", "reservas", "depositos", "emprestimos_tomados",
        "caixa_rbi", "investimentos", "adiantamentos", "ativo_fixo", "ativo_total"]


def mil(*v):      # Rs '000 -> crore
    return [x / 1e4 for x in v]


def lakh(*v):     # Rs lakh -> crore
    return [x / 100 for x in v]


def c4(*v):       # "crore,milhar,unidade" impresso como 624 58 46 (000s omitted)
    return [x for x in v]


L = {}
fonte = {}

# --- Rs '000 (milhares) ---
L["ALB"] = mil(5446093, 112561241, 1908428083, 121307715, 88344455,
               639605322, 1380065727, 13096934, 2204342831)
fonte["ALB"] = ("Allahabad Bank, AR 2013-14, Balance Sheet standalone (Rs '000)", "texto/ALB.txt")

L["DENA"] = mil(5378164, 66046729, 1100276878, 51609309, 62439503,
                366120731, 775537748, 11448139, 1248634900)
fonte["DENA"] = ("Dena Bank, AR 2013-14, Schedules 1-11 (Rs '000); ativo total 124863.49 crore "
                 "(Pillar 3 do mesmo relatório)", "texto/DENA.txt")

L["TMB"] = mil(2845, 22693122, 226456831, 2595817, 10339027,
               67718908, 171438500, 1168840, 263982345)
fonte["TMB"] = ("Tamilnad Mercantile Bank, coluna 31.03.2014 do balanço de 31.03.2015 (Rs '000)",
                "texto/TMB_comparativo_AR2015.txt")

# --- Rs crore (000s omitted, formato crore,milhar,unidade) ---
L["SYND"] = [624.5846, 11219.6104, 212343.3045, 19224.5130, 12711.9920,
             55539.3802, 173912.4079, 1468.8351, 251861.4738]
fonte["SYND"] = ("Syndicate Bank, AR 2013-14, Balance Sheet standalone", "texto/SYND.txt")

L["VIJB"] = [859.1194, 5028.8044, 124296.1593, 4744.7986, 5540.2076,
             42585.3848, 81504.0321, 528.9455, 137358.6128]
fonte["VIJB"] = ("Vijaya Bank, AR 2013-14, Balance Sheet", "texto/VIJB.txt")

L["RBL"] = [272.0402, 1613.2172, 11598.6021, 3895.5438, 980.7335,
            6518.0386, 9835.0473, 134.3485, 18198.1328]
fonte["RBL"] = ("RBL Bank, AR 2013-14, Balance Sheet (capital exclui share application money)",
                "texto/RBL.txt")

L["OBC"] = [299.8487, 13130.8217, 193488.9605, 7863.6100, 9981.1523,
            61472.2287, 139079.8404, 1255.5762, 220302.5038]
fonte["OBC"] = ("Oriental Bank of Commerce, coluna 31.03.2014 do balanço de 31.03.2015; "
                "confere com o Pillar 3 de 2013-14", "texto/OBC_comparativo_AR2015.txt")

# --- Rs crore, 2 casas ---
L["ANDB"] = [589.61, 8147.84, 141845.12, 13185.09, 7912.06,
             45356.62, 107644.20, 433.93, 167340.92]
fonte["ANDB"] = ("Andhra Bank, AR 2013-14, Balance Sheet (Rs crore)", "texto/ANDB.txt")

L["SBP"] = [367.85, 5763.56, 89673.16, 12386.23, 8145.77,
            24581.11, 75936.56, 410.67, 114120.73]
fonte["SBP"] = ("State Bank of Patiala, balanço de 31.03.2014 publicado com os resultados auditados "
                "(Rs crore)", "")

# --- Rs lakh ---
sbt_res = 156758.62 + 10401.65 + 14250.00 + 270769.57 + 301.85
sbt_dep = 276961.17 + 2193262.82 + 6463444.19
sbt_bor = 79000.00 + 22500.00 + 520422.48 + 59915.00
sbt_inv = 2352257.32 + 15843.16 + 57231.79 + 368804.26
sbt_adv = 418381.46 + 3042015.40 + 3480064.57
L["SBT"] = lakh(5000.00, sbt_res, sbt_dep, sbt_bor, 445856.84,
                sbt_inv, sbt_adv, 33901.18, 10528541.79)
fonte["SBT"] = ("State Bank of Travancore, AR 2013-14, balanço abreviado (Rs lakh; "
                "share application money de 385 crore fora do capital)", "texto/SBT.txt")

linhas = []
for b, v in L.items():
    d = {"bank_id": b, **dict(zip(COLS, v))}
    d["fonte"], d["arquivo"] = fonte[b]
    linhas.append(d)

df = pd.DataFrame(linhas)
soma_passivo = df[["capital", "reservas", "depositos", "emprestimos_tomados"]].sum(axis=1)
saida = AQUI / "b1_2014_texto.xlsx"
with pd.ExcelWriter(saida) as w:
    df.to_excel(w, sheet_name="b1_2014", index=False)
print(df.drop(columns=["fonte", "arquivo"]).round(2).to_string())
print("gravado", saida)
