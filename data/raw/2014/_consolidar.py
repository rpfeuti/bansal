"""Junta os balanços de 31/03/2014 dos 42 bancos em b1_2014.xlsx (Rs crore).

Entradas:
  b1_2014_texto.xlsx       bancos lidos dos textos (_transcrever.py)
  b1_2014_pdf_parte1.xlsx  bancos lidos dos PDFs (_extrair.py)
  b1_2014_media.xlsx       SBH: média 2013/2015 (_media_adjacentes.py)
  manuais abaixo           SBI, CUB, UNTD, SBM, CSB, NAIN (PDF com layout próprio ou imagem)
"""
import sys
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parents[2] / "src"))
from bansal.nomes import BANCOS  # noqa: E402

COLS = ["capital", "reservas", "depositos", "emprestimos_tomados", "caixa_rbi",
        "investimentos", "adiantamentos", "ativo_fixo", "ativo_total"]

# SBI: demonstrações abreviadas do PDF, p.119-120, Rs crore (2 casas).
sbi = [746.57, 117535.68, 1394408.51, 183130.88, 84955.66, 398308.19, 1209828.72, 8002.16, 1792234.60]
# CUB: PDF p.42, Rs mil (layout em colunas).
cub = [x / 1e4 for x in (4744_46, 1593_22_39, 20304_75_52, 476_73_91, 1016_33_64, 5266_80_33,
                         15246_05_73, 141_27_93, 22977_08_22)]
# UNTD: PDF p.92-93, Rs mil (valor antes do rótulo).
untd = [x / 1e4 for x in (1354_74_81, 3927_90_61, 111509_70_86, 4460_23_61, 6269_77_72, 44876_34_13,
                          65767_51_14, 938_73_47, 125104_95_02)]

# SBM: PDF p.60 é imagem; valores lidos da imagem (milhares de Rs, 000s omitted).
sbm = [x / 1e4 for x in (48_01_34, 4500_58_57, 61560_32_43, 5473_96_52, 2858_84_23, 19190_19_79,
                         49481_94_89, 860_32_15, 73976_34_59)]

# CSB: PDF p.37, Rs mil (agrupamento indiano com vírgulas).
csb = [x / 1e4 for x in (41_89_94, 728_12_73, 13673_86_17, 555_54_30, 623_90_24, 5131_65_29,
                         8707_36_15, 173_33_50, 15315_54_75)]
# NAIN: PDF p.46 é imagem (relatório impresso p.42); valores lidos da imagem, Rs mil.
nain = [x / 1e4 for x in (675000, 3777843, 46495804, 1802, 2191796, 11397400,
                          24370425, 189125, 53425901)]

manual = pd.DataFrame([
    {"bank_id": "CSB", **dict(zip(COLS, csb)), "fonte": "CSB.pdf p.37 (milhares de Rs)"},
    {"bank_id": "NAIN", **dict(zip(COLS, nain)), "fonte": "NAIN.pdf p.46 (imagem, milhares de Rs)"},
    {"bank_id": "SBM", **dict(zip(COLS, sbm)), "fonte": "SBM.pdf p.60 (imagem, milhares de Rs)"},
    {"bank_id": "SBI", **dict(zip(COLS, sbi)), "fonte": "SBI.pdf p.119-120 (demonstração abreviada, Rs crore)"},
    {"bank_id": "CUB", **dict(zip(COLS, cub)), "fonte": "CUB.pdf p.42 (milhares de Rs)"},
    {"bank_id": "UNTD", **dict(zip(COLS, untd)), "fonte": "UNTD.pdf p.92-93 (milhares de Rs)"},
])

texto = pd.read_excel(AQUI / "b1_2014_texto.xlsx").rename(columns={"arquivo": "arquivo_texto"})
texto["fonte"] = texto["fonte"] + " | " + texto["arquivo_texto"].fillna("")
pdf = pd.read_excel(AQUI / "b1_2014_pdf_parte1.xlsx")
med = pd.read_excel(AQUI / "b1_2014_media.xlsx", sheet_name="b1_2014")
med = med[(med["versao"] == "media") & ~med["bank_id"].isin(manual["bank_id"])].drop(columns="versao")
med["fonte"] = "média de 31/03/2013 (RBI STRBI B1) e 31/03/2015 (Measure, global); decisão do usuário"

tudo = pd.concat([d[["bank_id", *COLS, "fonte"]] for d in (texto, pdf, manual, med)], ignore_index=True)
assert tudo["bank_id"].is_unique, tudo[tudo["bank_id"].duplicated()]

ids = [b[0] for b in BANCOS]
faltam = [b for b in ids if b not in set(tudo["bank_id"])]
tudo["bank_id"] = pd.Categorical(tudo["bank_id"], ids, ordered=True)
tudo = tudo.sort_values("bank_id").reset_index(drop=True)
with pd.ExcelWriter(AQUI / "b1_2014.xlsx") as w:
    tudo.drop(columns="fonte").to_excel(w, sheet_name="b1_2014", index=False)
    tudo[["bank_id", "fonte"]].assign(unidade="Rs crore").to_excel(w, sheet_name="fonte", index=False)
print(len(tudo), "bancos; faltam:", faltam)
