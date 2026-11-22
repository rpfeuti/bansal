"""Completa data/raw/2014 com a maior cópia arquivada de cada relatório 2013-14."""

import json
import subprocess
import urllib.parse
from pathlib import Path

from pypdf import PdfReader

DEST = Path(__file__).resolve().parent
CODIGOS = {
    "SBM": "532200",
    "ANDB": "532418",
    "AXIS": "532215",
    "BOB": "532134",
    "CUB": "532210",
    "SYND": "532276",
    "UCO": "532505",
    "SBT": "532191",
    "ALB": "532480",
    "BOI": "532149",
    "CAN": "532483",
    "DENA": "532121",
    "OBC": "500315",
    "VIJB": "532401",
    "KVB": "590003",
    "LVB": "534690",
    "RBL": "540065",
}
EXTRAS = {
    "KVB": ["https://www.bseindia.com/HIS_ANN_RPT/HISTANNR/2014/KARUR_VYSYA_BANK_LTD-590003-MARCH-2014.PDF"],
    "RBL": ["https://www.bseindia.com/HIS_ANN_RPT/HISTANNR/2014/RBL_BANKLTD-540065-MARCH-2014.PDF"],
}


def abre(caminho: Path) -> bool:
    if not caminho.exists() or caminho.stat().st_size < 150_000:
        return False
    try:
        return len(PdfReader(str(caminho)).pages) >= 15
    except Exception:
        return False


def cdx(url: str):
    consulta = (
        "https://web.archive.org/cdx/search/cdx?url="
        + urllib.parse.quote(url, safe="")
        + "&output=json&fl=timestamp,length,statuscode&filter=statuscode:200"
    )
    bruto = subprocess.run(["curl.exe", "-s", "-m", "45", consulta], capture_output=True).stdout
    try:
        linhas = json.loads(bruto)
    except json.JSONDecodeError:
        return []
    achados = []
    for ts, tamanho, status in linhas[1:]:
        if str(tamanho).isdigit() and int(tamanho) > 200_000:
            achados.append((int(tamanho), ts, url))
    return achados


def baixar(destino: Path, timestamp: str, original: str) -> bool:
    url = f"https://web.archive.org/web/{timestamp}id_/{original}"
    print("  ", timestamp, original, flush=True)
    subprocess.run(
        ["curl.exe", "-sL", "-m", "400", "--retry", "2", "-A", "Mozilla/5.0", "-o", str(destino), url],
        check=False,
    )
    return abre(destino)


def main():
    for banco, codigo in CODIGOS.items():
        destino = DEST / f"{banco}.pdf"
        if abre(destino):
            print(banco, "ok", destino.stat().st_size, flush=True)
            continue
        destino.unlink(missing_ok=True)
        candidatos = []
        for base in ("AnnualReport", "annualreport"):
            candidatos += cdx(
                f"https://www.bseindia.com/bseplus/{base}/{codigo}/{codigo}0314.pdf"
            )
        for extra in EXTRAS.get(banco, []):
            candidatos += cdx(extra)
        candidatos.sort(reverse=True)
        vistos = set()
        print(banco, len(candidatos), "copias", flush=True)
        for tamanho, ts, original in candidatos:
            chave = (ts, original)
            if chave in vistos:
                continue
            vistos.add(chave)
            if baixar(destino, ts, original):
                print(banco, "ok", destino.stat().st_size, "de", tamanho, flush=True)
                break
            destino.unlink(missing_ok=True)
        else:
            print(banco, "sem copia util", flush=True)


if __name__ == "__main__":
    main()
