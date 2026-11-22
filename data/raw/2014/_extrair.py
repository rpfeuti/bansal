"""Lê o balanço standalone de 31/03/2014 dos PDFs em data/raw/2014 e grava b1_2014_pdf.xlsx.
Valores como impressos (milhares de rupias, 000s omitted) -> crore (/1e4)."""
import re
from pathlib import Path
import pandas as pd
from _parse import parse, check

AQUI = Path(__file__).parent
COLS = ["capital","reservas","depositos","emprestimos_tomados","caixa_rbi","investimentos","adiantamentos","ativo_fixo","ativo_total"]
KEYS = ["capital","reservas","depositos","borrow","cash","invest","adv","fixed"]
PAGINAS = {"AXIS":[52],"BOB":[214],"BOI":[92],"BOM":[124],"CAN":[134],"CBI":[265],"CORP":[130],"DCB":[42],"DHAN":[52],
           "FED":[74],"HDFC":[38],"ICICI":[107],"IIB":[82],"INDB":[162],"IOB":[101],"JK":[36],"KTK":[52],"KVB":[40],
           "LVB":[19],"PNB":[198],"PSB":[206],"SBBJ":[170],"SIB":[41],"UBI":[197],"UCO":[80,81]}

def totais(t):
    out = []
    for line in t.split("\n"):
        m = re.match(r"(?i)\W*total\b[^0-9]{0,40}?(\d[\d,]*(?: \d\d \d\d)?)\s+(\d[\d,]*(?: \d\d \d\d)?)", line.strip())
        if m: out.append(float(re.sub(r"[,\s]", "", m.group(1))))
    return out

linhas, diag = [], []
for b, pgs in PAGINAS.items():
    pages = (AQUI / "texto_pdf" / f"{b}.txt").read_text(encoding="utf8").split("\n\f")
    t = "\n".join(pages[p-1] for p in pgs)
    r, _ = parse(t)
    a, l = check(r, [])
    toks = [float(re.sub(r"[,\s]", "", x)) for x in re.findall(r"\d[\d,]*(?: \d\d \d\d)?", t)]
    ativo_total = next((x for x in toks if abs(x-a) <= max(2, 1e-6*a)), None)
    if ativo_total is None:
        ativo_total = next((x for x in toks if abs(x-l) <= max(2, 1e-6*l)), float("nan"))
    v = [r[k][0] for k in KEYS] + [r["fixed"][0]] if False else None
    vals = {"capital": r["capital"][0], "reservas": r["reservas"][0], "depositos": r["depositos"][0],
            "emprestimos_tomados": r["borrow"][0], "caixa_rbi": r["cash"][0], "investimentos": r["invest"][0],
            "adiantamentos": r["adv"][0], "ativo_fixo": r["fixed"][0], "ativo_total": ativo_total}
    linhas.append({"bank_id": b, **{k: x/1e4 for k, x in vals.items()}, "fonte": f"{b}.pdf p.{'+'.join(map(str,pgs))} (milhares de Rs)"})
    diag.append((b, len(r), a-ativo_total, l-ativo_total))
df = pd.DataFrame(linhas)
print("diag (banco, itens lidos, soma ativos - total, soma passivos - total [milhares]):")
for d in diag: print(" ", d)
df.to_excel(AQUI / "b1_2014_pdf_parte1.xlsx", index=False)
print(df.drop(columns="fonte").round(2).to_string())
