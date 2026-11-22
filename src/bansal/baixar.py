"""Baixa as fontes cruas e grava cada uma como .xlsx em data/raw, sem mudar valores."""

import csv
import io
import json
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import openpyxl
import xlrd

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

MEASURE = "https://measure.thisindianlife.today/data/"
RBIDOCS = "https://rbidocs.rbi.org.in/rdocs/Publications/DOCs/"

FONTES_CSV = {
    "measure_credit_npa_movement.xlsx": MEASURE + "credit-npa-movement-banks.csv",
    "measure_banks_balance_sheet.xlsx": MEASURE + "banks-balance-sheet.csv",
    "measure_bank_earnings.xlsx": MEASURE + "credit-deep-bank-earnings.csv",
    "measure_bank_provisions.xlsx": MEASURE + "credit-deep-bank-provisions.csv",
    "measure_employees_banks.xlsx": MEASURE + "credit-deep-employees-banks.csv",
    "measure_offices_banks.xlsx": MEASURE + "credit-deep-offices-banks.csv",
    "measure_priority_sector_banks.xlsx": MEASURE + "credit-deep-priority-sector-banks.csv",
}

FONTES_XLS = {
    "strbi/b1_2010.xlsx": [RBIDOCS + "B1_AST020311.xls"],
    "strbi/b1_2011.xlsx": [RBIDOCS + "01BT_STI110311F.xls"],
    "strbi/b1_2013.xlsx": [RBIDOCS + "B01_ST191113F.xls"],
    # Tabelas por banco das mesmas edições: B2 (receitas e despesas), B13 (agências),
    # B15 (empregados), 6.1 (crédito prioritário). Sufixo = ano final da edição (2009-10 -> 2010).
    "strbi/b2_2010.xlsx": [RBIDOCS + "B2_AST020311.xls"],
    "strbi/b2_2011.xlsx": [RBIDOCS + "02BT_STI110311F.xls"],
    "strbi/b2_2013.xlsx": [RBIDOCS + "B02_ST191113F.xls"],
    "strbi/b13_2010.xlsx": [RBIDOCS + "B13_AST020311.xls"],
    "strbi/b13_2011.xlsx": [RBIDOCS + "13BT_STI110311F.xls"],
    "strbi/b13_2013.xlsx": [RBIDOCS + "B13_ST191113F.xls"],
    "strbi/b15_2010.xlsx": [RBIDOCS + "B15_AST020311.xls"],
    "strbi/b15_2011.xlsx": [RBIDOCS + "15BT_STI110311F.xls"],
    "strbi/b15_2013.xlsx": [RBIDOCS + "B15_ST191113F.xls"],
    "strbi/p61_2010.xlsx": [RBIDOCS + "61_AST020311.xls"],
    "strbi/p61_2011.xlsx": [RBIDOCS + "061_STI110311F.xls"],
    "strbi/p61_2013.xlsx": [RBIDOCS + "601T_STF181113.xls"],
    # B4 (provisões) traz um ano por edição.
    "strbi/b4_2009.xlsx": [RBIDOCS + "TB4_STST1118.xls"],
    "strbi/b4_2010.xlsx": [RBIDOCS + "B4_AST020311.xls"],
    "strbi/b4_2011.xlsx": [RBIDOCS + "04BT_STI110311F.xls"],
    "strbi/b4_2012.xlsx": [RBIDOCS + "04TB_TSTR071112.xls"],
    "strbi/b4_2013.xlsx": [RBIDOCS + "B04_ST191113F.xls"],
}


def _curl(url: str) -> bytes:
    return subprocess.run(
        ["curl", "-sSfL", "-m", "120", "-A", UA["User-Agent"], url], capture_output=True, check=True
    ).stdout


def _wayback(url: str) -> str:
    resp = json.loads(_curl("https://archive.org/wayback/available?url=" + url.split("://", 1)[1]))
    snap = resp["archived_snapshots"]["closest"]
    return f"https://web.archive.org/web/{snap['timestamp']}id_/{url}"


def baixar(url: str) -> tuple[bytes, str]:
    """Conteúdo e URL efetivamente usada (a original ou a cópia idêntica no Internet Archive)."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            return r.read(), url
    except (urllib.error.URLError, TimeoutError):
        pass
    try:
        return _curl(url), url
    except subprocess.CalledProcessError:
        copia = _wayback(url)
        return _curl(copia), copia


def numero(texto: str):
    try:
        return float(texto)
    except ValueError:
        return texto


def aba_fonte(wb, urls):
    ws = wb.create_sheet("fonte")
    ws.append(["url", "baixado_em"])
    for u in urls:
        ws.append([u, date.today().isoformat()])


def csv_para_xlsx(url: str, destino: Path):
    conteudo, usada = baixar(url)
    texto = conteudo.decode("utf-8-sig")
    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet("dados")
    for i, linha in enumerate(csv.reader(io.StringIO(texto))):
        ws.append(linha if i == 0 else [numero(c) if c != "" else None for c in linha])
    aba_fonte(wb, [usada])
    wb.save(destino)


def xls_para_xlsx(urls: list[str], destino: Path):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    usadas = []
    with tempfile.TemporaryDirectory() as tmp:
        for k, url in enumerate(urls, 1):
            arq = Path(tmp) / f"{k}.xls"
            conteudo, usada = baixar(url)
            usadas.append(usada)
            arq.write_bytes(conteudo)
            livro = xlrd.open_workbook(arq)
            for folha in livro.sheets():
                nome = folha.name[:28] if len(urls) == 1 else f"P{k} {folha.name}"[:31]
                ws = wb.create_sheet(nome)
                for r in range(folha.nrows):
                    ws.append([c.value if c.ctype != xlrd.XL_CELL_EMPTY else None for c in folha.row(r)])
    aba_fonte(wb, usadas)
    wb.save(destino)


def main(nomes=None):
    (RAW / "strbi").mkdir(parents=True, exist_ok=True)
    for nome, url in FONTES_CSV.items():
        if nomes and nome not in nomes:
            continue
        print("baixando", nome, flush=True)
        csv_para_xlsx(url, RAW / nome)
    for nome, urls in FONTES_XLS.items():
        if nomes and nome not in nomes:
            continue
        print("baixando", nome, flush=True)
        try:
            xls_para_xlsx(urls, RAW / nome)
        except Exception as e:  # noqa: BLE001 - segue para o próximo arquivo
            print("  FALHOU", nome, type(e).__name__, e, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
