import re, sys
from pathlib import Path
from pypdf import PdfReader
out = Path("texto_pdf")
for p in sorted(Path(".").glob("*.pdf")):
    try:
        r = PdfReader(str(p))
        n = len(r.pages)
        cand = []
        txts = []
        for i, pg in enumerate(r.pages):
            try: t = pg.extract_text() or ""
            except Exception: t = ""
            txts.append(t)
            tl = t.lower()
            if all(k in tl for k in ["reserves", "deposits", "borrowings", "advances", "fixed assets"]) and ("capital" in tl):
                cand.append(i + 1)
        (out / (p.stem + ".txt")).write_text("\n\f".join(txts), encoding="utf8")
        print(p.stem, n, cand[:8], sum(len(t) for t in txts))
    except Exception as e:
        print(p.stem, "ERRO", e)
