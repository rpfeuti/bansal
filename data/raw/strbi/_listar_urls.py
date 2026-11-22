"""Lista (sem baixar arquivos de dados) os links das tabelas por banco nas páginas-índice do STRBI."""
import re
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
PAT = re.compile(r"Table (B2|B4|B8|B13|B15|B12|6\.1)\b")


def pagina(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode("utf8", "ignore")


for u in sys.argv[1:]:
    print("##", u)
    try:
        h = pagina(u)
    except Exception as e:
        print("ERRO", e)
        continue
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r)).strip()
        if PAT.search(t):
            print(t[:100], re.findall(r"href=[\"']([^\"']+)", r))
