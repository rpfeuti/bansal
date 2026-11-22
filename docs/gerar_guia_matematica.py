"""Gera docs/guia_matematica_bansal.pdf: os conceitos matemáticos, do zero, com exemplos e simulações.

Rodar da raiz:  $env:PYTHONPATH="src"; python docs/gerar_guia_matematica.py

Complementa docs/guia_excel_bansal.pdf (que não é alterado). Os números são calculados aqui, com o próprio
motor (src/bansal) quando o exemplo é do projeto. Nada é gravado fora de docs/.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, PolyLine, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer,
                                Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from bansal import gmm, indices
from bansal.estatistica import chi2_sf, normal_cdf
from bansal.simplex import maximizar

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "data" / "saida"
ARQ = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "docs" / "guia_matematica_bansal.pdf"

# ------------------------------------------------------------------ estilo (o mesmo do primeiro guia)
FONTES = Path("C:/Windows/Fonts")
for nome, arq in (("Arial", "arial.ttf"), ("Arial-B", "arialbd.ttf"), ("Arial-I", "ariali.ttf"),
                  ("Arial-BI", "arialbi.ttf"), ("Consolas", "consola.ttf"), ("Consolas-B", "consolab.ttf")):
    pdfmetrics.registerFont(TTFont(nome, str(FONTES / arq)))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-B", italic="Arial-I", boldItalic="Arial-BI")
pdfmetrics.registerFontFamily("Consolas", normal="Consolas", bold="Consolas-B", italic="Consolas",
                              boldItalic="Consolas-B")

AZUL = colors.HexColor("#1F4E79")
AZUL_CLARO = colors.HexColor("#DDEBF7")
CINZA = colors.HexColor("#F2F2F2")
VERDE = colors.HexColor("#E2EFDA")
AMARELO = colors.HexColor("#FFF2CC")
LARANJA_ESC = colors.HexColor("#C55A11")

S = {
    "titulo": ParagraphStyle("titulo", fontName="Arial-B", fontSize=26, leading=32, textColor=AZUL,
                             alignment=TA_CENTER, spaceAfter=14),
    "subtitulo": ParagraphStyle("subtitulo", fontName="Arial", fontSize=13, leading=18, alignment=TA_CENTER,
                                textColor=colors.HexColor("#404040")),
    "h1": ParagraphStyle("h1", fontName="Arial-B", fontSize=18, leading=23, textColor=AZUL, spaceBefore=6,
                         spaceAfter=10),
    "h1sum": ParagraphStyle("h1sum", fontName="Arial-B", fontSize=18, leading=23, textColor=AZUL, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName="Arial-B", fontSize=13.5, leading=18, textColor=AZUL, spaceBefore=12,
                         spaceAfter=6, keepWithNext=1),
    "h3": ParagraphStyle("h3", fontName="Arial-B", fontSize=11, leading=15, spaceBefore=8, spaceAfter=4,
                         keepWithNext=1),
    "p": ParagraphStyle("p", fontName="Arial", fontSize=10, leading=14.2, alignment=TA_JUSTIFY, spaceAfter=6),
    "item": ParagraphStyle("item", fontName="Arial", fontSize=10, leading=14, leftIndent=14, bulletIndent=3,
                           spaceAfter=2),
    "caixa": ParagraphStyle("caixa", fontName="Arial", fontSize=9.6, leading=13.4),
    "form": ParagraphStyle("form", fontName="Consolas", fontSize=9, leading=12.4),
    "cel": ParagraphStyle("cel", fontName="Arial", fontSize=8.6, leading=11),
    "celc": ParagraphStyle("celc", fontName="Consolas", fontSize=8.2, leading=10.4),
    "legenda": ParagraphStyle("legenda", fontName="Arial-I", fontSize=8.8, leading=12, alignment=TA_CENTER,
                              textColor=colors.HexColor("#404040"), spaceAfter=8),
    "toc1": ParagraphStyle("toc1", fontName="Arial-B", fontSize=10.5, leading=15),
    "toc2": ParagraphStyle("toc2", fontName="Arial", fontSize=9.5, leading=13, leftIndent=16),
}


def br(x, d=3):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "—"
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


story = []


def H1(t, nova_pagina=False):
    story.append(PageBreak() if nova_pagina else CondPageBreak(9 * cm))
    story.append(Paragraph(t, S["h1"]))


def H2(t):
    story.append(Paragraph(t, S["h2"]))


def H3(t):
    story.append(Paragraph(t, S["h3"]))


def P(*ts):
    for t in ts:
        story.append(Paragraph(t, S["p"]))


def L(*itens):
    for t in itens:
        story.append(Paragraph(t, S["item"], bulletText="•"))
    story.append(Spacer(1, 4))


def N(*itens):
    for k, t in enumerate(itens, 1):
        story.append(Paragraph(t, S["item"], bulletText=f"{k}."))
    story.append(Spacer(1, 4))


def _caixa(conteudo, fundo, borda):
    t = Table([[conteudo]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fundo), ("BOX", (0, 0), (-1, -1), 0.6, borda),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(t)
    story.append(Spacer(1, 8))


def F(texto):
    _caixa(Preformatted(texto.strip("\n"), S["form"]), CINZA, colors.HexColor("#BFBFBF"))


def NOPROJETO(texto, titulo="No projeto"):
    _caixa(Paragraph(f"<b>{titulo}:</b> {texto}", S["caixa"]), VERDE, colors.HexColor("#A9D18E"))


def IDEIA(texto, titulo="Em uma frase"):
    _caixa(Paragraph(f"<b>{titulo}:</b> {texto}", S["caixa"]), AMARELO, colors.HexColor("#FFD966"))


def T(linhas, larguras, cabecalho=True, mono=False):
    est = S["celc"] if mono else S["cel"]
    dados = [[c if not isinstance(c, str) else Paragraph(c, est) for c in lin] for lin in linhas]
    t = Table(dados, colWidths=[w * cm for w in larguras], repeatRows=1 if cabecalho else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFBFBF")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
          ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if cabecalho:
        st.append(("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO))
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 8))


def LEG(t):
    story.append(Paragraph(t, S["legenda"]))


def mat(M, d=3, nomes_lin=None):
    """Matriz em texto alinhado (para caixas F)."""
    M = np.atleast_2d(np.asarray(M, float))
    cel = [[br(v, d) for v in lin] for lin in M]
    w = max(len(c) for lin in cel for c in lin)
    linhas = []
    for i, lin in enumerate(cel):
        pre = f"{nomes_lin[i]:<10}" if nomes_lin else ""
        linhas.append(pre + "[ " + "  ".join(c.rjust(w) for c in lin) + " ]")
    return "\n".join(linhas)


def seta(d, x1, y1, x2, y2, cor=colors.black):
    d.add(Line(x1, y1, x2, y2, strokeColor=cor, strokeWidth=1))
    a = math.atan2(y2 - y1, x2 - x1)
    d.add(Polygon([x2, y2, x2 + 7 * math.cos(a + 2.7), y2 + 7 * math.sin(a + 2.7),
                   x2 + 7 * math.cos(a - 2.7), y2 + 7 * math.sin(a - 2.7)], fillColor=cor, strokeColor=cor))


def grafico(pontos=(), linhas=(), poligono=None, eixo_x="x", eixo_y="y", xmax=10, ymax=9, legendas=(),
            setas=()):
    esc, ox, oy = 26, 40, 30
    d = Drawing(330, 290)
    if poligono:
        xy = []
        for x, y in poligono:
            xy += [ox + x * esc, oy + y * esc]
        d.add(Polygon(xy, fillColor=AZUL_CLARO, strokeColor=AZUL, strokeWidth=1.2))
    d.add(Line(ox, oy, ox + xmax * esc, oy))
    d.add(Line(ox, oy, ox, oy + ymax * esc))
    for k in range(0, xmax + 1, 2 if xmax > 6 else 1):
        d.add(String(ox + k * esc - 3, oy - 12, str(k), fontName="Arial", fontSize=8))
    for k in range(0, ymax + 1, 2 if ymax > 6 else 1):
        d.add(String(ox - 14, oy + k * esc - 3, str(k), fontName="Arial", fontSize=8))
    d.add(String(ox + xmax * esc / 2 - 30, oy - 25, eixo_x, fontName="Arial", fontSize=8.5))
    d.add(String(ox - 30, oy + ymax * esc + 6, eixo_y, fontName="Arial", fontSize=8.5))
    for pts, cor, tracejado in linhas:
        xy = []
        for x, y in pts:
            xy += [ox + x * esc, oy + y * esc]
        d.add(PolyLine(xy, strokeColor=cor, strokeWidth=1.5, strokeDashArray=tracejado))
    for (x1, y1), (x2, y2), cor in setas:
        seta(d, ox + x1 * esc, oy + y1 * esc, ox + x2 * esc, oy + y2 * esc, cor)
    for nome, x, y, cor in pontos:
        d.add(Circle(ox + x * esc, oy + y * esc, 3.5, fillColor=cor, strokeColor=cor))
        d.add(String(ox + x * esc + 5, oy + y * esc + 4, nome, fontName="Arial-B", fontSize=8.5, fillColor=cor))
    for k, (txt, cor) in enumerate(legendas):
        d.add(String(ox + xmax * esc * 0.55, oy + ymax * esc - 12 * (k + 1), txt, fontName="Arial", fontSize=8,
                     fillColor=cor))
    story.append(d)


# ------------------------------------------------------------------ ferramentas extras de desenho e simulação

def barras_lado_a_lado(series, largura=470, altura=150):
    """series: lista de (titulo, rotulos, probabilidades)."""
    d = Drawing(largura, altura + 30)
    k = len(series)
    w = largura / k
    for s_i, (tit, rot, pr) in enumerate(series):
        x0 = s_i * w + 12
        pm = max(pr)
        bw = (w - 30) / len(pr)
        d.add(Line(x0, 20, x0 + w - 24, 20))
        for j, (r, p) in enumerate(zip(rot, pr)):
            h = (altura - 25) * p / pm
            d.add(Polygon([x0 + j * bw, 20, x0 + (j + 0.85) * bw, 20, x0 + (j + 0.85) * bw, 20 + h, x0 + j * bw, 20 + h],
                          fillColor=AZUL, strokeColor=AZUL))
        for j in (0, len(rot) // 2, len(rot) - 1):
            d.add(String(x0 + (j + 0.4) * bw, 8, rot[j], fontName="Arial", fontSize=7, textAnchor="middle"))
        d.add(String(x0 + (w - 24) / 2, altura + 10, tit, fontName="Arial-B", fontSize=8.5, textAnchor="middle"))
    story.append(d)


def figura_normal():
    d = Drawing(440, 200)
    ox, oy, ex, ey = 220, 30, 52, 380

    def f(z):
        return math.exp(-z * z / 2) / math.sqrt(2 * math.pi)

    zs = np.linspace(-3.6, 3.6, 181)
    for lado in (-1, 1):
        pts = [z for z in zs if lado * z >= 1.96]
        xy = [ox + pts[0] * ex, oy] if lado > 0 else [ox + pts[0] * ex, oy]
        for z in pts:
            xy += [ox + z * ex, oy + f(z) * ey]
        xy += [ox + pts[-1] * ex, oy]
        d.add(Polygon(xy, fillColor=colors.HexColor("#F4B183"), strokeColor=None))
    xy = []
    for z in zs:
        xy += [ox + z * ex, oy + f(z) * ey]
    d.add(PolyLine(xy, strokeColor=AZUL, strokeWidth=1.6))
    d.add(Line(ox - 3.7 * ex, oy, ox + 3.7 * ex, oy))
    for z in (-3, -2, -1.96, -1, 0, 1, 1.96, 2, 3):
        if z in (-2, 2):
            continue
        d.add(Line(ox + z * ex, oy - 3, ox + z * ex, oy + 3))
        d.add(String(ox + z * ex, oy - 14, br(z, 2 if abs(z) == 1.96 else 0), fontName="Arial", fontSize=7.5,
                     textAnchor="middle"))
    d.add(String(ox + 2.6 * ex, oy + 30, "2,5%", fontName="Arial-B", fontSize=8, textAnchor="middle",
                 fillColor=LARANJA_ESC))
    d.add(String(ox - 2.6 * ex, oy + 30, "2,5%", fontName="Arial-B", fontSize=8, textAnchor="middle",
                 fillColor=LARANJA_ESC))
    d.add(String(ox, oy + 70, "95%", fontName="Arial-B", fontSize=10, textAnchor="middle", fillColor=AZUL))
    story.append(d)


def painel_sim(N, T, a, rng, rho=0.0, queima=30):
    """Painel dinâmico simulado: y[t] = a·y[t−1] + η + e[t], com e[t] = ρ·e[t−1] + v[t]."""
    eta = rng.normal(0, 1, N)
    y = np.zeros((N, T + queima))
    e = np.zeros((N, T + queima))
    y[:, 0] = eta / (1 - a) + rng.normal(0, 1, N) / math.sqrt(1 - a * a)
    for t in range(1, T + queima):
        e[:, t] = rho * e[:, t - 1] + rng.normal(0, 1, N)
        y[:, t] = a * y[:, t - 1] + eta + e[:, t]
    return y[:, queima:]


def ep_sem_correcao(y):
    """Erro-padrão do passo 2 do GMM de sistema SEM a correção de Windmeijer (mesmas contas de gmm.py)."""
    dados, H, _ = gmm._montar(y, [])
    A1 = np.linalg.pinv(sum(Z.T @ H @ Z for _, _, Z, _ in dados))
    b1, _, _ = gmm._estimar(dados, A1)
    u1 = [Y - X @ b1 for X, Y, _, _ in dados]
    S1 = sum(Z.T @ np.outer(u, u) @ Z for (_, _, Z, _), u in zip(dados, u1))
    _, V2, _ = gmm._estimar(dados, np.linalg.pinv(S1))
    return math.sqrt(V2[0, 0])


def gmm_dois_instr(y, x, Z):
    """GMM de 1 parâmetro (y = b·x + u): passo 1, passo 2, Sargan e Hansen."""
    n = len(y)
    Szx, Szy = Z.T @ x / n, Z.T @ y / n
    W1 = np.linalg.inv(Z.T @ Z / n)
    b1 = (Szx @ W1 @ Szy) / (Szx @ W1 @ Szx)
    u1 = y - b1 * x
    g1 = Z.T @ u1 / n
    sargan = n * g1 @ np.linalg.inv((u1 @ u1 / n) * Z.T @ Z / n) @ g1
    S_ = (Z * (u1 ** 2)[:, None]).T @ Z / n
    W2 = np.linalg.inv(S_)
    b2 = (Szx @ W2 @ Szy) / (Szx @ W2 @ Szx)
    g2 = Z.T @ (y - b2 * x) / n
    return {"b1": b1, "b2": b2, "W1": W1, "W2": W2, "g2": g2, "sargan": sargan, "J": n * g2 @ W2 @ g2}


def faixa(v):
    p25, p75 = np.percentile(v, [25, 75])
    return f"{br(p25, 2)} a {br(p75, 2)}"


# ------------------------------------------------------------------ CAPA E SUMÁRIO

story.append(Spacer(1, 4 * cm))
story.append(Paragraph("A matemática por trás do Excel", S["titulo"]))
story.append(Paragraph("Álgebra de matrizes, programação linear, DEA, probabilidade, regressão e GMM,<br/>"
                       "explicados do zero, com exemplos numéricos e simulações", S["subtitulo"]))
story.append(Spacer(1, 1.2 * cm))
story.append(Paragraph("Versão 2 — reescrita: cada conceito é explicado antes de ser usado", S["subtitulo"]))
story.append(PageBreak())
story.append(Paragraph("Sumário", S["h1sum"]))
toc = TableOfContents()
toc.levelStyles = [S["toc1"], S["toc2"]]
story.append(toc)

# ================================================================== COMO LER
H1("Como ler este guia", nova_pagina=True)
P("Este guia explica os conceitos matemáticos usados nos cálculos — não o paper. A regra seguida em todo o texto "
  "é: <b>nenhum conceito aparece antes de ser explicado</b>. Quando um termo novo surge, ele está em <b>negrito</b> "
  "e é definido ali mesmo. Por isso a ordem dos capítulos importa: cada um usa só o que veio antes.")
P("A notação é a mesma do primeiro guia:")
F("""SOMA( x[i] )            para i = 1 até n   =  x[1] + x[2] + ... + x[n]
SOMA( a[i] × b[i] )     para i = 1 até n   =  a[1]×b[1] + ... + a[n]×b[n]
MÉDIA( x[i] )                              =  SOMA( x[i] ) / n""")
P("Muitos capítulos usam <b>simulações</b>: o computador gera dados artificiais seguindo uma regra que nós "
  "escolhemos (por exemplo, \"o coeficiente verdadeiro é 0,5\"). Como sabemos a resposta certa, dá para ver o que "
  "cada método faz: se acerta, se erra para cima, quanto oscila. Todos os números foram calculados pelo script que "
  "gera este PDF.")
DUV = [
    ("1", "Programação linear", "5"), ("2", "GMM", "23"), ("3", "DEA", "10"), ("4", "VRS", "10"),
    ("5", "ξ = 3 e π = 1", "11"), ("6", "Simplex passo a passo", "6"), ("7", "Malmquist-Luenberger", "12"),
    ("8", "Mínimos quadrados", "18"), ("9", "Arellano-Bond e Blundell-Bond", "27 e 28"),
    ("10", "Windmeijer", "30"), ("11", "AR(1) e AR(2)", "26 e 29"), ("12", "Sargan e Hansen J", "24"),
    ("13", "Wald", "20"), ("14", "coef / ep e teste z", "16 e 19"), ("15", "Regra de Dantzig", "7"),
    ("16", "Pivotar / Gauss", "3"), ("17", "Simplex revisado", "9"), ("18", "O @ do código", "2"),
    ("19", "Gauss-Jordan com pivoteamento parcial", "4"),
]
T([["Dúvida", "Assunto", "Capítulo"]] + [list(r) for r in DUV], [2, 11.4, 3])

# ================================================================== PARTE I
H1("1. Vetores e matrizes")
P("Um <b>vetor</b> é uma lista ordenada de números. Uma <b>matriz</b> é uma tabela de números com linhas e colunas. "
  "\"Matriz 3×2\" quer dizer 3 linhas e 2 colunas. A <b>posição [i, j]</b> é o número na linha i, coluna j. Uma "
  "matriz com o mesmo número de linhas e colunas é <b>quadrada</b>.")
F("""c = [3, 2]                 vetor com 2 números

A = [ 1  1 ]               matriz 3×2;   A[2, 2] = 3
    [ 1  3 ]
    [ 1  0 ]""")
P("A <b>transposta</b> de A, escrita A', troca linhas por colunas: a linha 1 de A vira a coluna 1 de A'. A "
  "<b>identidade</b> I é a matriz quadrada com 1 na diagonal (posições [1,1], [2,2], ...) e 0 no resto.")
F("""A' = [ 1  1  1 ]           I (3×3) = [ 1  0  0 ]
     [ 1  3  0 ]                     [ 0  1  0 ]
                                     [ 0  0  1 ]""")

H1("2. Multiplicação de matrizes e o @ do código (dúvida 18)")
P("Em Python com numpy, <b>@</b> é o operador de <b>multiplicação de matrizes</b> (criado em 2015, Python 3.5, "
  "PEP 465). Ele não multiplica elemento por elemento — isso é o <font name='Consolas'>*</font>. Há três casos.")
H2("Vetor @ vetor: o produto escalar")
F("""a = [1, 2, 3]   b = [4, 5, 6]

a @ b = SOMA( a[i] × b[i] ) = 1×4 + 2×5 + 3×6 = 32          → um número
a * b = [1×4, 2×5, 3×6]     = [4, 10, 18]                  → um vetor""")
P("O <b>produto escalar</b> é o SUMPRODUCT do Excel: multiplica par a par e soma.")
H2("Matriz @ vetor")
P("Cada número do resultado é o produto escalar de uma <b>linha</b> da matriz com o vetor:")
F("""A = [ 1  1 ]   v = [ 2 ]       A @ v = [ 1×2 + 1×1 ] = [ 3 ]
    [ 1  3 ]       [ 1 ]               [ 1×2 + 3×1 ]   [ 5 ]

regra:  (A @ v)[i] = SOMA( A[i, j] × v[j] )   somando em j""")
H2("Vetor @ matriz")
P("Cada número do resultado é o produto escalar do vetor com uma <b>coluna</b> da matriz. É o caso da linha "
  "<font name='Consolas'>y = c[base] @ Binv</font> do simplex:")
cb = np.array([0.0, -1.0])
Bi = np.array([[1.0, -1.0 / 3], [0.0, 1.0 / 3]])
y_ = cb @ Bi
F(f"""c = [0, −1]       M = [ 1  −0,333 ]
                      [ 0   0,333 ]

(c @ M)[k] = SOMA( c[j] × M[j, k] )   somando em j
   k = 1:  0×1 + (−1)×0           = {br(y_[0], 3)}
   k = 2:  0×(−0,333) + (−1)×0,333 = {br(y_[1], 3)}""")
H2("Matriz @ matriz")
F("""(A @ B)[i, k] = SOMA( A[i, j] × B[j, k] )
              = produto escalar da linha i de A com a coluna k de B

A = [ 1  2 ]   B = [ 5  6 ]    A @ B = [ 1×5 + 2×7   1×6 + 2×8 ] = [ 19  22 ]
    [ 3  4 ]       [ 7  8 ]            [ 3×5 + 4×7   3×6 + 4×8 ]   [ 43  50 ]""")
P("Só funciona se o número de colunas de A for igual ao número de linhas de B. A ordem importa: em geral "
  "A @ B é diferente de B @ A. Multiplicar pela identidade não muda nada: A @ I = A.")

H1("3. Sistemas de equações, eliminação de Gauss e pivotar (dúvida 16)")
P("Um <b>sistema linear</b> é um conjunto de equações em que as incógnitas aparecem só multiplicadas por números "
  "e somadas. Em forma de matriz: A @ v = b (A = coeficientes, v = incógnitas, b = lado direito).")
P("A <b>eliminação de Gauss</b> resolve qualquer sistema usando três <b>operações de linha</b>, que não mudam a "
  "solução: (1) trocar duas equações de lugar; (2) multiplicar ou dividir uma equação inteira por um número "
  "diferente de zero; (3) somar a uma equação um múltiplo de outra. Para não reescrever as letras, trabalha-se "
  "com a <b>matriz aumentada</b> [A | b].")
P("<b>Pivotar</b> é: escolher um número da matriz (o <b>pivô</b>), dividir a linha dele pelo próprio pivô (o "
  "pivô vira 1) e usar a operação (3) para zerar todos os outros números da coluna do pivô.")
F("""  2x +  y +  z = 5           L1 [ 2  1  1 |  5 ]
  4x + 3y + 3z = 13    →     L2 [ 4  3  3 | 13 ]
  8x + 7y + 9z = 33          L3 [ 8  7  9 | 33 ]

Pivô = 2 (linha 1, coluna 1):
  L1 ← L1 / 2       [ 1  0,5  0,5 | 2,5 ]
  L2 ← L2 − 4×L1    [ 0  1    1   | 3   ]     4−4×1=0; 3−4×0,5=1; 3−4×0,5=1; 13−4×2,5=3
  L3 ← L3 − 8×L1    [ 0  3    5   | 13  ]     8−8×1=0; 7−8×0,5=3; 9−8×0,5=5; 33−8×2,5=13

Pivô = 1 (linha 2, coluna 2):
  L1 ← L1 − 0,5×L2  [ 1  0    0   | 1   ]
  L3 ← L3 − 3×L2    [ 0  0    2   | 4   ]

Pivô = 2 (linha 3, coluna 3):
  L3 ← L3 / 2       [ 0  0    1   | 2   ]
  L2 ← L2 − 1×L3    [ 0  1    0   | 1   ]

Lado esquerdo virou a identidade → x = 1, y = 1, z = 2""")
P("Zerando a coluna inteira (acima e abaixo do pivô), como aqui, o método se chama <b>Gauss-Jordan</b>. O simplex "
  "(capítulo 6) faz exatamente um pivô destes a cada passo.")

H1("4. A inversa por Gauss-Jordan, com pivoteamento parcial (dúvida 19)")
P("A <b>inversa</b> de uma matriz quadrada B, escrita B<super>−1</super> (no código, Binv), é a matriz tal que "
  "B @ Binv = I. Ela \"desfaz\" B, como 1/4 desfaz 4. Com ela, resolver B @ v = b vira simplesmente "
  "v = Binv @ b. Uma matriz sem inversa se chama <b>singular</b> — acontece quando uma linha é combinação das "
  "outras (o sistema não tem solução única).")
H2("O método: Gauss-Jordan em [B | I]")
P("Escreve-se B e, ao lado, a identidade. Aplicam-se as operações de linha até o lado esquerdo virar I. As mesmas "
  "operações, aplicadas à identidade, constroem a inversa.")


def gauss_jordan_passos(B):
    m = B.shape[0]
    M = np.hstack([B.astype(float), np.eye(m)])
    passos = [("início [B | I]", M.copy())]
    for k in range(m):
        p = k + int(np.argmax(np.abs(M[k:, k])))
        if p != k:
            M[[k, p]] = M[[p, k]]
            passos.append((f"coluna {k + 1}: o maior |valor| está na linha {p + 1} → troca L{k + 1} e L{p + 1}",
                           M.copy()))
        piv = M[k, k]
        M[k] /= piv
        col = M[:, k].copy()
        col[k] = 0.0
        M -= np.outer(col, M[k])
        passos.append((f"coluna {k + 1}: divide L{k + 1} por {br(piv, 3)} e zera o resto da coluna", M.copy()))
    return passos


Bex = np.array([[2.0, 1.0], [4.0, 3.0]])
for txt, M in gauss_jordan_passos(Bex):
    F(txt + "\n" + mat(M, 3))
P("A inversa é [[1,5; −0,5]; [−2; 1]]. Conferindo uma posição de B @ Binv: linha 1 de B × coluna 1 de Binv = "
  "2×1,5 + 1×(−2) = 1.")
H2("O atalho para 2×2")
P("Para matrizes 2×2 há uma fórmula direta, que será usada nos capítulos de regressão. O número ad − bc se chama "
  "<b>determinante</b>; se for zero, a matriz é singular.")
F("""[ a  b ]^(−1)  =  1/(ad − bc) × [  d  −b ]
[ c  d ]                         [ −c   a ]

B = [ 2  1 ]:  ad − bc = 2×3 − 1×4 = 2   →  Binv = 1/2 × [  3  −1 ] = [ 1,5  −0,5 ]
    [ 4  3 ]                                            [ −4   2 ]   [ −2    1   ]""")
H2("Por que o pivoteamento parcial")
P("O <b>valor absoluto</b> |x| é o número sem o sinal: |−5| = 5, |3| = 3. "
  "Antes de usar a coluna k, o código procura, da linha k para baixo, o número de <b>maior valor absoluto</b> e "
  "o traz para a posição do pivô (foi o que aconteceu acima: o 4 subiu). O motivo é o <b>arredondamento</b>: o "
  "computador guarda cerca de 16 algarismos de cada número, e dividir por um pivô muito pequeno multiplica os "
  "erros. O efeito aparece claramente numa calculadora que guarda só 3 algarismos:")
F("""0,0001 x + y = 1
1      x + y = 2          solução verdadeira: x = 1,0001…, y = 0,9998…

SEM pivoteamento (pivô = 0,0001):
   L2 ← L2 − 10000×L1:  −9999 y = −9998   → com 3 algarismos: −10000 y = −10000 → y = 1
   L1:  0,0001 x = 1 − 1 = 0              → x = 0                         (errado)

COM pivoteamento (troca as linhas; pivô = 1):
   L2 ← L2 − 0,0001×L1:  0,9999 y = 0,9998 → com 3 algarismos: y = 1
   L1:  x = 2 − 1                          → x = 1                         (certo)""")
F("""def inversa(B):                                   # o código do projeto, em palavras
    M = [B | I]
    para cada coluna k:
        p = linha, de k para baixo, com o maior |M[p, k]|     ← pivoteamento parcial
        se |M[p, k]| < 1e-13: erro \"base singular\"
        troca as linhas k e p
        M[k] = M[k] / M[k, k]                                ← pivô vira 1
        para cada outra linha i:  M[i] = M[i] − M[i, k] × M[k] ← zera a coluna
    devolve a metade direita de M""")

# ================================================================== PARTE II — OTIMIZAÇÃO
H1("5. Programação linear (dúvida 1)")
P("Uma <b>programação linear (PL)</b> escolhe valores para <b>variáveis de decisão</b> de modo a maximizar (ou "
  "minimizar) uma <b>função objetivo</b>, obedecendo a <b>restrições</b>. \"Linear\" quer dizer que objetivo e "
  "restrições só somam variáveis multiplicadas por números (nada de x², x×y, raízes).")
F("""maximizar   3x + 2y               (lucro: 3 por unidade de x, 2 por unidade de y)
sujeito a    x +  y ≤ 4            (matéria-prima)
             x + 3y ≤ 6            (horas de máquina)
             x      ≤ 2            (demanda de x)
             x ≥ 0,  y ≥ 0""")
H2("A geometria")
P("No plano (x, y), cada restrição \"≤\" deixa de um lado de uma reta os pontos permitidos. Os pontos que obedecem "
  "a todas as restrições formam a <b>região viável</b>. Os cantos dessa região são os <b>vértices</b>. As retas "
  "3x + 2y = constante (mesmo lucro) são paralelas; aumentar o lucro é empurrá-las para cima e para a direita, até "
  "o último ponto da região que elas tocam.")
grafico(pontos=[("(0;0)", 0, 0, AZUL), ("(2;0)", 2, 0, AZUL), ("ótimo (2; 1,33)", 2, 4 / 3, colors.HexColor("#C00000")),
                ("(0;2)", 0, 2, AZUL)],
        linhas=[([(0, 4), (4, 0)], colors.HexColor("#7F7F7F"), [3, 3]),
                ([(0, 2), (6, 0)], colors.HexColor("#7F7F7F"), [3, 3]),
                ([(2, 0), (2, 4.2)], colors.HexColor("#7F7F7F"), [3, 3]),
                ([(0.5, 3.583), (2.889, 0)], colors.HexColor("#C00000"), None)],
        poligono=[(0, 0), (2, 0), (2, 4 / 3), (0, 2)], eixo_x="x", eixo_y="y", xmax=6, ymax=5)
LEG("Figura 1. Região viável (azul), retas das restrições (cinza) e a reta de lucro 8,67 (vermelha), que toca a "
    "região só no vértice ótimo.")
T([["Vértice", "x + y ≤ 4", "x + 3y ≤ 6", "x ≤ 2", "Lucro 3x + 2y"],
   ["(0; 0)", "0", "0", "0", "0"], ["(2; 0)", "2", "2", "2", "6"],
   ["(2; 1,333)", "3,333", "6 (justa)", "2 (justa)", "<b>8,667</b>"], ["(0; 2)", "2", "6 (justa)", "0", "4"]],
  [3, 3, 3, 3, 4.4])
P("Uma restrição é <b>justa</b> quando vale com igualdade. Propriedade central: <b>se uma PL tem ótimo, um vértice "
  "é ótimo</b>. Basta procurar entre os vértices. Com 2 variáveis dá para listá-los; com centenas, o número de "
  "vértices é astronômico, e por isso existe o simplex, que visita só alguns.")
H2("Os três desfechos")
L("<b>Ótimo</b>: existe um melhor ponto.",
  "<b>Inviável</b>: as restrições se contradizem (x ≥ 3 e x ≤ 2); a região viável é vazia.",
  "<b>Ilimitado</b>: o objetivo pode crescer sem fim (maximizar x sem nenhuma restrição limitando x).")

H1("6. O método simplex, passo a passo (dúvida 6)")
H2("Passo 0: folgas e a forma padrão")
P("Cada \"≤\" vira \"=\" somando uma <b>folga</b> ≥ 0, que mede quanto sobra da restrição:")
F("""x +  y + s1           = 4
x + 3y      + s2      = 6            todas as variáveis ≥ 0
x                + s3 = 2            lucro z = 3x + 2y""")
P("São 3 equações e 5 incógnitas. Escolhendo 3 variáveis para serem calculadas pelas equações (as <b>básicas</b>) "
  "e fixando as outras 2 em zero (as <b>não básicas</b>), obtém-se um ponto chamado <b>solução básica</b>. Se as "
  "básicas saírem ≥ 0, esse ponto é um <b>vértice</b> da região viável. O conjunto das básicas é a <b>base</b>. "
  "O simplex anda de base em base.")
P("Começo: base = {s1, s2, s3}, x = y = 0. As equações dão s1 = 4, s2 = 6, s3 = 2. É o vértice (0; 0), z = 0.")
H2("Passo 1: quem entra — os custos reduzidos")
P("Escreve-se o lucro usando só as não básicas: <b>z = 0 + 3x + 2y</b>. O coeficiente de cada não básica diz "
  "quanto z muda se ela aumentar uma unidade (com as básicas se ajustando pelas equações). Esse coeficiente se chama "
  "<b>custo reduzido</b>. Coeficiente positivo = vale a pena aumentar aquela variável. Entre x (3) e y (2), "
  "escolhe-se o maior: <b>x entra na base</b> (regra de Dantzig, capítulo 7).")
H2("Passo 2: quem sai — o teste da razão")
P("Aumentando x (com y = 0), cada básica muda segundo sua equação, e nenhuma pode ficar negativa:")
F("""s1 = 4 − x ≥ 0  →  x ≤ 4
s2 = 6 − x ≥ 0  →  x ≤ 6
s3 = 2 − x ≥ 0  →  x ≤ 2          ← o limite mais apertado""")
P("x sobe até 2, que é a <b>menor razão</b> entre o lado direito e o coeficiente de x em cada equação (só onde o "
  "coeficiente é positivo; se ele for zero ou negativo, aumentar x não aproxima aquela básica de zero). Em x = 2, "
  "s3 chega a zero: <b>s3 sai da base</b>. Se nenhum coeficiente fosse positivo, x poderia crescer para sempre: o "
  "problema seria ilimitado.")
H2("Passo 3: pivotar")
P("Reescrevem-se as equações para que x apareça só na equação que era de s3. É um pivô de Gauss-Jordan (capítulo "
  "3) no coeficiente de x da linha 3:")
F("""L3 (pivô):        x               + s3 = 2      →  x  = 2 − s3
L1 ← L1 − L3:          y + s1     − s3 = 2      →  s1 = 2 − y + s3
L2 ← L2 − L3:         3y     + s2 − s3 = 4      →  s2 = 4 − 3y + s3
lucro: z = 3(2 − s3) + 2y = 6 + 2y − 3s3""")
P("Novo vértice: (x; y) = (2; 0), z = 6. Base = {s1, s2, x}.")
H2("Passo 4: repetir")
P("z = 6 + 2y − 3s3: só y tem custo reduzido positivo → <b>y entra</b>. Teste da razão (s3 fica em 0):")
F("""s1 = 2 − y   ≥ 0 → y ≤ 2
s2 = 4 − 3y  ≥ 0 → y ≤ 4/3       ← mais apertado: s2 sai
x  = 2       (não depende de y)

Pivô no 3 da linha de s2:
   y  = 4/3 − s2/3 + s3/3
   s1 = 2 − y + s3 = 2/3 + s2/3 + 2·s3/3
   z  = 6 + 2y − 3s3 = 26/3 − (2/3)·s2 − (7/3)·s3""")
H2("Passo 5: parar — por que é o ótimo")
P("Em z = 8,667 − 0,667·s2 − 2,333·s3, as não básicas s2 e s3 só podem aumentar (são ≥ 0) e ambas têm coeficiente "
  "negativo: qualquer movimento a partir deste vértice <b>diminui</b> o lucro. Numa PL, a região viável não tem "
  "\"reentrâncias\" e o objetivo é uma reta (um plano); por isso, se nenhum vizinho melhora, nenhum ponto da região "
  "melhora. Ótimo: x = 2, y = 4/3, z = 26/3 = 8,667.")
H2("Bônus: os preços-sombra")
P("Os coeficientes finais têm um significado útil. s2 é a folga da restrição 2 (horas de máquina). Forçar s2 = 1 é "
  "o mesmo que ter uma hora a menos; o lucro cai 2/3. Ao contrário, <b>uma hora a mais</b> aumenta o lucro em 2/3. "
  "Esse valor se chama <b>preço-sombra</b> da restrição. Conferindo, resolvendo de novo com 7 horas em vez de 6:")
v6, _ = maximizar(np.array([3, 2.]), np.array([[1, 1], [1, 3], [1, 0.]]), np.array([4, 6, 2.]))
v7, _ = maximizar(np.array([3, 2.]), np.array([[1, 1], [1, 3], [1, 0.]]), np.array([4, 7, 2.]))
F(f"""lucro com 6 horas = {br(v6, 4)}      lucro com 7 horas = {br(v7, 4)}      diferença = {br(v7 - v6, 4)} = 2/3""")
P("A restrição 1 tem preço-sombra 0: ela tem folga (s1 = 2/3), então mais matéria-prima não ajudaria.")
H2("Os mesmos passos em forma de quadro")
P("O <b>quadro</b> (tableau) guarda só os coeficientes. Cada linha é uma equação; a última linha é o objetivo "
  "escrito como z − 3x − 2y = 0, por isso os custos reduzidos aparecem com o sinal trocado (negativo = vale a pena "
  "entrar). A coluna \"valor\" tem os valores das básicas e, na última linha, o lucro.")


def quadros(A, b, c):
    m, n = A.shape
    Q = np.zeros((m + 1, n + m + 1))
    Q[:m, :n], Q[:m, n:n + m], Q[:m, -1] = A, np.eye(m), b
    Q[m, :n] = -np.asarray(c, float)
    base = [n + i for i in range(m)]
    out = [(Q.copy(), list(base), None, None)]
    while True:
        neg = [j for j in range(n + m) if Q[m, j] < -1e-12]
        if not neg:
            break
        j = min(neg, key=lambda k: Q[m, k])
        raz = [Q[i, -1] / Q[i, j] if Q[i, j] > 1e-12 else np.inf for i in range(m)]
        r = int(np.argmin(raz))
        Q[r] /= Q[r, j]
        for i in range(m + 1):
            if i != r:
                Q[i] -= Q[i, j] * Q[r]
        sai = base[r]
        base[r] = j
        out.append((Q.copy(), list(base), j, sai))
    return out


NOMES = ["x", "y", "s1", "s2", "s3"]
Aq, bq, cq = np.array([[1, 1], [1, 3], [1, 0.]]), np.array([4, 6, 2.]), [3, 2]
QUADROS = quadros(Aq, bq, cq)


def mostra(Q, base):
    lin = [["básica"] + NOMES + ["valor"]]
    for i, bi in enumerate(base):
        lin.append([NOMES[bi]] + [br(v, 3) for v in Q[i]])
    lin.append(["objetivo"] + [br(v, 3) for v in Q[-1]])
    T(lin, [2.0] + [1.9] * 5 + [2.0], mono=True)


for k, (Qk, bk, ent, sai) in enumerate(QUADROS):
    H3("Quadro inicial" if k == 0 else f"Depois da iteração {k}: entrou {NOMES[ent]}, saiu {NOMES[sai]}")
    mostra(Qk, bk)
P("No quadro final, os números da linha do objetivo sob s2 e s3 (0,667 e 2,333) são os preços-sombra.")
H2("Degeneração: quando o passo é zero")
P("Troque a terceira restrição para x ≤ 3. Depois que x entra (x = 3), y entra e o teste da razão <b>empata</b>: "
  "s1 = 1 − y e s2 = 3 − 3y chegam a zero juntos, em y = 1. Uma sai da base e a outra continua básica <b>com valor "
  "0</b>. Uma base com uma básica igual a zero é <b>degenerada</b>. Num vértice degenerado, o próximo pivô pode "
  "ter passo zero: a base muda, mas o ponto (e o lucro) não. Isso é comum em DEA, onde muitas restrições passam "
  "pelo mesmo vértice.")

H1("7. A regra de Dantzig e a regra de Bland (dúvida 15)")
P("Quando várias variáveis têm custo reduzido favorável, é preciso escolher uma. A <b>regra de Dantzig</b> "
  "(George Dantzig, criador do simplex, 1947) escolhe a de custo reduzido mais favorável — a que melhora o objetivo "
  "mais depressa <b>por unidade</b>. No exemplo, x (3 por unidade) ganhou de y (2 por unidade).")
P("É uma regra \"gulosa\": olha a taxa, não o tamanho do passo. x rende 3 por unidade mas só pode subir até 2 "
  "(ganho 6); y rende 2 por unidade e, se entrasse primeiro, subiria até 2 (ganho 4). Aqui a escolha gulosa coincidiu "
  "com o maior ganho, mas nem sempre é assim. Na prática, Dantzig costuma precisar de poucas iterações e é barato de "
  "calcular.")
H2("Um cuidado: a taxa depende da unidade de medida")
P("Se y fosse medido em centenas, seu coeficiente seria 200 em vez de 2, e Dantzig passaria a preferir y. Por "
  "isso o simplex do projeto <b>muda a escala</b> do problema antes (capítulo 9): divide cada linha e cada coluna "
  "pelo seu maior valor absoluto, deixando todos os números entre −1 e 1.")
H2("Ciclagem e a regra de Bland")
P("Com degeneração (capítulo 6), pode acontecer uma sequência de pivôs de passo zero que volta a uma base já "
  "visitada; a partir daí o algoritmo repete o mesmo ciclo para sempre. Isso se chama <b>ciclagem</b>. É raro, mas "
  "possível. A <b>regra de Bland</b> (1977) evita: entra a candidata de <b>menor índice</b> (a primeira na ordem das "
  "colunas) e, se o teste da razão empatar, sai a básica de menor índice. Está provado que, com ela, o simplex nunca "
  "cicla; em compensação, costuma ser mais lento.")
P("O código do projeto usa Dantzig e troca para Bland depois de 50 passos degenerados seguidos.")

H1("8. Duas fases e variáveis livres")
P("Até aqui o ponto inicial (tudo zero) era viável. Nem sempre é: com uma igualdade como SOMA(λ) = 1, tudo zero "
  "dá 0 ≠ 1. Não há uma base inicial óbvia. O <b>simplex de duas fases</b> resolve isso.")
N("<b>Fase 1</b>: em cada restrição põe-se uma variável <b>artificial</b> ≥ 0 (uma \"folga de mentira\" que torna o "
  "ponto inicial viável) e minimiza-se a soma das artificiais com o próprio simplex. Se o mínimo for 0, achou-se um "
  "ponto viável do problema original. Se for maior que 0, não existe ponto viável: o problema é <b>inviável</b>.",
  "<b>Fase 2</b>: parte-se da base encontrada e maximiza-se o objetivo verdadeiro, com as artificiais proibidas de "
  "voltar.")
F("""maximizar 2x + y    sujeito a   x + y = 1     e     x ≤ 0,6

FASE 1: x + y + a = 1 (a = artificial);  minimizar a.  Início: a = 1, s = 0,6.
  x entra. Razões: 1/1 = 1 (igualdade) e 0,6/1 = 0,6 (linha de s) → s sai.
     agora x = 0,6 e a = 0,4
  y entra. Razão: 0,4/1 na igualdade → a sai.
     agora y = 0,4 e a = 0  → ponto viável: x = 0,6, y = 0,4
FASE 2: maximizar 2x + y a partir daí: lucro = 1,6; nenhum vizinho melhora → ótimo.""")
H2("Variáveis que podem ser negativas")
P("O simplex exige variáveis ≥ 0. Se uma variável pode ter qualquer sinal (uma <b>variável livre</b>, como o β do "
  "DEA), escreve-se β = β+ − β−, com β+ ≥ 0 e β− ≥ 0. β = −0,01 vira β+ = 0 e β− = 0,01.")

H1("9. O simplex revisado (dúvida 17)")
P("No simplex de quadro, cada pivô reescreve todos os números do quadro. O <b>simplex revisado</b> parte de uma "
  "observação: todo o quadro pode ser recalculado, quando preciso, a partir da matriz original A (com as folgas), "
  "dos custos c e de uma única matriz que muda — a inversa das colunas básicas.")
H2("A matriz base B e sua inversa")
P("<b>B</b> é a matriz formada pelas colunas de A que correspondem às variáveis básicas. Como as equações são "
  "A @ (todas as variáveis) = b e as não básicas valem zero, sobra B @ (básicas) = b. Logo, <b>básicas = Binv @ b</b>.")
A_ful = np.array([[1, 1, 1, 0, 0], [1, 3, 0, 1, 0], [1, 0, 0, 0, 1.]])
Qf, basef = QUADROS[-1][0], QUADROS[-1][1]
Bf = A_ful[:, basef]
Bfi = np.linalg.inv(Bf)
F(f"""Base final = ({', '.join(NOMES[i] for i in basef)}).  B = colunas dessas variáveis em A:
{mat(Bf, 0)}
Binv (capítulo 4):
{mat(Bfi, 3)}
Colunas de s1, s2, s3 no quadro final:
{mat(Qf[:3, 2:5], 3)}""")
P("As colunas das folgas no quadro final <b>são</b> a Binv. Não é coincidência: no início elas eram a identidade, e "
  "todo pivô aplica a elas as mesmas operações de linha; o acumulado dessas operações é justamente a inversa da "
  "base (capítulo 4: Gauss-Jordan em [B | I]). O quadro inteiro é Binv @ A.")
H2("O que o revisado calcula em cada iteração")
F("""xB = Binv @ b                 valores das básicas              (coluna \"valor\")
y  = c[base] @ Binv           um número por restrição: os preços-sombra (cap. 6)
d  = c − y @ A                custo reduzido de cada coluna      (linha do objetivo)
j  = coluna que entra (Dantzig ou Bland)
a  = Binv @ A[:, j]           a coluna j no quadro atual
teste da razão com xB / a ; atualiza Binv com um pivô (m × m) ; troca base[r] = j""")
H2("É mais leve? Depende do problema")
P("Contando multiplicações por iteração, com m restrições e n colunas: o quadro atualiza m × n números; o "
  "revisado gasta m × m para atualizar Binv, m × m para y, m × n para os custos d e m × m para a coluna a. Num "
  "problema com m = 19 e n ≈ 197 (o DEA do projeto), dá cerca de 3,7 mil contra 4,8 mil — o revisado <b>não</b> é "
  "mais leve em aritmética neste tamanho. (O primeiro guia dizia que era; esta conta corrige.)")
P("O revisado ganha em velocidade quando há muito mais colunas que linhas e a matriz A tem muitos zeros, porque "
  "então y @ A é barato, ou quando só uma parte das colunas é examinada por iteração. As vantagens que valem em "
  "qualquer caso são:")
L("<b>Precisão</b>: a matriz A nunca é reescrita, então os erros de arredondamento não se acumulam nela. Só Binv "
  "acumula erro, e pode ser <b>recalculada do zero</b> a partir de A (o código faz isso a cada 40 iterações).",
  "<b>Memória</b>: guarda-se Binv (m × m) em vez do quadro (m × n).",
  "<b>As duas fases</b> usam a mesma A e a mesma base; muda só o vetor de custos c.")

# ================================================================== PARTE III — DEA
H1("10. DEA e retornos de escala (dúvidas 3 e 4)")
P("<b>DEA</b> (Data Envelopment Analysis; Charnes, Cooper e Rhodes, 1978) mede a eficiência de unidades que "
  "transformam <b>insumos</b> (o que se gasta) em <b>produtos</b> (o que se gera) — bancos, hospitais, escolas. "
  "Cada unidade é uma <b>DMU</b> (decision-making unit). Não se supõe nenhuma fórmula de produção: as DMUs são "
  "comparadas umas com as outras.")
H2("O conjunto de possibilidades e a fronteira")
P("Uma <b>média ponderada</b> multiplica cada valor por um peso e soma, com os pesos somando 1: 30% de 10 mais 70% "
  "de 20 dá 0,3×10 + 0,7×20 = 17. Supõe-se que, se duas DMUs foram observadas, qualquer média ponderada delas "
  "(dos insumos e dos produtos) também seria possível. Os pesos λ (lambda) são ≥ 0. Também se supõe que é possível desperdiçar: usar mais insumo ou produzir menos "
  "que uma média observada. Tudo o que pode ser feito forma o <b>conjunto de possibilidades de produção</b>; sua "
  "borda de cima (as melhores práticas) é a <b>fronteira</b>.")
X4, Y4 = [2, 4, 8, 6], [2, 6, 8, 4]
P("Exemplo: 4 bancos, insumo = funcionários, produto = empréstimos: A (2; 2), B (4; 6), C (8; 8), D (6; 4).")
H2("A eficiência de Farrell: andar na horizontal até a fronteira")
P("A primeira forma de medir \"quão longe da fronteira\" está uma DMU foi proposta por Farrell (1957). A pergunta é: "
  "<b>mantendo a produção, com que fração dos seus insumos a DMU conseguiria trabalhar, se fizesse tão bem quanto as "
  "melhores?</b>")
P("Veja D no gráfico: 6 funcionários, 4 de empréstimos. Fixamos a produção em 4 e andamos para a <b>esquerda</b> "
  "(menos funcionários) até bater na fronteira. A fronteira, na altura 4, está no segmento entre A (2; 2) e B (4; 6). "
  "Esse segmento é a reta empréstimos = 2 × funcionários − 2; para empréstimos = 4, funcionários = 3. O ponto (3; 4) "
  "é a média 50% A + 50% B: 0,5×2 + 0,5×4 = 3 funcionários e 0,5×2 + 0,5×6 = 4 de empréstimos.")
grafico(pontos=[("A", 2, 2, AZUL), ("B", 4, 6, AZUL), ("C", 8, 8, AZUL), ("D", 6, 4, AZUL),
                ("(3; 4)", 3, 4, colors.HexColor("#C00000"))],
        linhas=[([(2, 0), (2, 2), (4, 6), (8, 8), (10, 8)], AZUL, None)],
        setas=[((6, 4), (3.1, 4), colors.HexColor("#C00000"))],
        eixo_x="insumo (funcionários)", eixo_y="produto (empréstimos)")
LEG("Figura 2. A fronteira (azul) liga A, B e C. A seta parte de D e anda na horizontal: mesma produção, menos "
    "funcionários, até a fronteira em (3; 4).")
P("Resultado: D poderia produzir o mesmo com 3 funcionários em vez de 6, ou seja, com a fração <b>θ = 3/6 = 0,5</b> "
  "dos seus insumos. θ (teta) = 1 significa que a DMU já está na fronteira (eficiente); θ = 0,5 significa que metade "
  "do insumo bastaria.")
H2("A mesma conta escrita como programação linear")
P("Com muitas DMUs e muitos insumos não dá para olhar o gráfico; escreve-se a mesma pergunta como uma PL (capítulo "
  "5). As incógnitas são θ e os pesos λ da média ponderada que serve de referência:")
F("""minimizar θ                                    (a menor fração possível dos insumos)
sujeito a
   SOMA( λ[j] × insumo[j] )  ≤ θ × insumo_o     a média usa no máximo θ × insumo de o
   SOMA( λ[j] × produto[j] ) ≥ produto_o        e produz pelo menos o que o produz
   SOMA( λ[j] ) = 1                             é uma média ponderada (ver abaixo)
   λ[j] ≥ 0
(o = DMU avaliada; j percorre todas as DMUs)""")
P("Para D, o simplex encontra θ = 0,5 com λA = 0,5 e λB = 0,5, exatamente o ponto (3; 4) do gráfico.")


def farrell(o, vrs):
    n = 4
    A = np.zeros((2, n + 1))
    A[0, :n], A[0, n] = X4, -X4[o]
    A[1, :n] = [-v for v in Y4]
    c = np.zeros(n + 1)
    c[n] = -1
    if vrs:
        v, x = maximizar(c, A, [0, -Y4[o]], np.array([[1, 1, 1, 1, 0.]]), [1])
    else:
        v, x = maximizar(c, A, [0, -Y4[o]])
    return -v, x


th = {(k, v): farrell(i, v)[0] for i, k in enumerate("ABCD") for v in (False, True)}
H2("Retornos de escala")
P("<b>Retornos de escala</b> descrevem o que acontece com a produção quando todos os insumos aumentam na mesma "
  "proporção: <b>constantes</b> (dobrar insumos dobra a produção), <b>crescentes</b> (mais que dobra), "
  "<b>decrescentes</b> (menos que dobra). Em DEA isso se traduz numa única restrição sobre os pesos:")
L("<b>CRS</b> (retornos constantes): retira-se a linha SOMA(λ) = 1; os pesos podem somar qualquer valor. O modelo pode comparar uma DMU com \"o dobro "
  "de B\" (λ = 2) ou \"metade de B\" (λ = 0,5). A fronteira vira uma reta saindo da origem e passando pela DMU de "
  "maior produto ÷ insumo (B: 6/4 = 1,5).",
  "<b>VRS</b> (retornos variáveis): é o modelo usado até aqui, com SOMA(λ) = 1. Só médias ponderadas são "
  "permitidas; uma DMU pequena é comparada com DMUs de tamanho parecido. A fronteira liga A, B e C.")
grafico(pontos=[("A", 2, 2, AZUL), ("B", 4, 6, AZUL), ("C", 8, 8, AZUL), ("D", 6, 4, AZUL)],
        linhas=[([(0, 0), (6, 9)], LARANJA_ESC, [4, 3]), ([(2, 0), (2, 2), (4, 6), (8, 8), (10, 8)], AZUL, None)],
        eixo_x="insumo (funcionários)", eixo_y="produto (empréstimos)",
        legendas=[("— fronteira VRS", AZUL), ("- - fronteira CRS", LARANJA_ESC)])
LEG("Figura 3. Fronteira CRS (laranja, pela origem e por B) e fronteira VRS (azul, ligando A, B e C).")
T([["DMU", "θ CRS", "θ VRS", "Leitura (VRS)"]] +
  [[k, br(th[k, False], 3), br(th[k, True], 3),
    "eficiente" if th[k, True] > 0.999 else f"produziria o mesmo com {br(th[k, True] * 100, 0)}% dos insumos"]
   for k in "ABCD"], [2, 2.6, 2.6, 9.2])
P("D no VRS: θ = 0,5. A média 50% A + 50% B usa 0,5×2 + 0,5×4 = 3 funcionários (metade dos 6 de D) e produz "
  "0,5×2 + 0,5×6 = 4, o mesmo que D. A no CRS: θ = 0,667, porque A produz 1 por funcionário e B produz 1,5; no VRS "
  "A é eficiente, porque nenhuma <i>média</i> de bancos faz melhor no tamanho de A. A razão θ CRS ÷ θ VRS é a "
  f"<b>eficiência de escala</b> (D: {br(th['D', False], 3)} ÷ {br(th['D', True], 3)} = "
  f"{br(th['D', False] / th['D', True], 3)}): a parte da ineficiência que se deve ao tamanho.")

H1("11. Medir andando numa direção: a função distância direcional e as constantes ξ e π (dúvida 5)")
P("No capítulo 10, a distância de D até a fronteira foi medida andando <b>só na horizontal</b>: reduzindo "
  "funcionários sem mexer nos empréstimos. Mas pode-se andar em qualquer outra direção — por exemplo, reduzir "
  "funcionários <b>e ao mesmo tempo</b> aumentar empréstimos. Este capítulo explica, em ordem:")
N("o que é andar numa direção e o que é o β;",
  "por que o β muda quando a direção muda;",
  "a direção mais natural (\"o próprio tamanho do banco\") e quando ela quebra (valores zero ou negativos);",
  "como as constantes ξ e π consertam isso, e o que o paper diz sobre os valores 3 e 1.")
IDEIA("ξ é a letra grega \"csi\" e π é a letra grega \"pi\". Aqui as duas são apenas <b>nomes de constantes</b> "
      "escolhidas por quem aplica o método. Este π <b>não</b> é o número 3,14159.", titulo="Atenção")
H2("11.1 O que é uma direção e o que é o β")
P("Uma <b>direção</b> é um par de números g = (g_x; g_y) que diz quanto se anda em cada eixo a cada \"passo\": g_x "
  "unidades de insumo a menos e g_y unidades de produto a mais. Dar β passos a partir de D (6; 4) leva ao ponto:")
F("""( 6 − β × g_x  ;  4 + β × g_y )""")
P("Com g = (6; 4) — os próprios valores de D —, um passo inteiro zeraria os 6 funcionários e dobraria os 4 de "
  "empréstimos; passos fracionários andam uma parte disso. A tabela testa alguns valores de β. Um ponto é "
  "<b>possível</b> se alguma média de bancos usa no máximo aquele insumo e produz pelo menos aquele produto, ou seja, "
  "se o ponto está abaixo da fronteira:")


def fronteira_toy(x):
    if x < 2:
        return None
    return 2 * x - 2 if x <= 4 else (0.5 * x + 4 if x <= 8 else 8.0)


lin = [["β", "ponto (funcionários; empréstimos)", "fronteira com esse número de funcionários", "possível?"]]
for b in (0, 0.1, 0.2, 0.3, 0.375, 0.4):
    xx, yy = 6 - 6 * b, 4 + 4 * b
    fr = fronteira_toy(xx)
    lin.append([br(b, 3), f"({br(xx, 2)}; {br(yy, 2)})", br(fr, 2), "sim" if yy <= fr + 1e-12 else "<b>não</b>"])
T(lin, [2, 5.4, 6, 3])
P("Até β = 0,375 o ponto continua possível; em 0,375 ele toca a fronteira (5,5 = 5,5); depois sai. O maior β "
  "possível é a <b>função distância direcional</b> de D na direção g (Chambers, Chung e Färe, 1996). Leitura: D "
  "poderia andar 0,375 passo, isto é, reduzir 0,375 × 6 = 2,25 funcionários e aumentar 0,375 × 4 = 1,5 de "
  "empréstimos <b>ao mesmo tempo</b>. β = 0 quer dizer que a DMU já está na fronteira.")
P("Como PL, é a mesma ideia do capítulo 10, trocando θ pelo passo β:")
F("""maximizar β
   SOMA( λ × insumo )  ≤ insumo_o  − β × g_x      (insumo reduzido em β passos)
   SOMA( λ × produto ) ≥ produto_o + β × g_y      (produto aumentado em β passos)
   SOMA( λ ) = 1 ;  λ ≥ 0 ;  β pode ter qualquer sinal""")


def ddf_toy(gx, gy):
    A = np.array([[2, 4, 8, 6, gx], [-2, -6, -8, -4, gy]], float)
    return maximizar(np.array([0, 0, 0, 0, 1.]), A, [6, -4], np.array([[1, 1, 1, 1, 0.]]), [1], livres=[4])


DIRS = [((6, 0), "só reduz insumo (é a direção de Farrell)"), ((0, 4), "só aumenta produto"),
        ((6, 4), "os próprios valores de D"), ((1, 1), "um de cada"),
        ((30, 3), "a regra do paper com ξ = 3, π = 1 (ver 11.7)")]
CORES_D = [colors.HexColor("#C00000"), colors.HexColor("#548235"), LARANJA_ESC, colors.HexColor("#7030A0"),
           colors.HexColor("#404040")]
RD = {g: ddf_toy(*g) for g, _ in DIRS}
H2("11.2 O β depende da direção")
P("A mesma DMU D, medida em direções diferentes, tem β diferentes — e chega a pontos diferentes da fronteira:")
grafico(pontos=[("A", 2, 2, AZUL), ("B", 4, 6, AZUL), ("C", 8, 8, AZUL), ("D", 6, 4, AZUL)],
        linhas=[([(2, 0), (2, 2), (4, 6), (8, 8), (10, 8)], AZUL, None)],
        setas=[((6, 4), (6 - RD[g][0] * g[0], 4 + RD[g][0] * g[1]), cor) for (g, _), cor in zip(DIRS, CORES_D)],
        eixo_x="insumo (funcionários)", eixo_y="produto (empréstimos)")
LEG("Figura 4. Cinco direções a partir de D (cores na ordem da tabela). Cada seta termina onde a direção toca a "
    "fronteira.")
T([["direção g", "o que é", "β", "ponto de chegada", "leitura"]] +
  [[f"({g[0]}; {g[1]})", txt, br(RD[g][0], 4),
    f"({br(6 - RD[g][0] * g[0], 2)}; {br(4 + RD[g][0] * g[1], 2)})",
    f"{br(RD[g][0], 3)} passo(s) de {g[0]} func. a menos e {g[1]} empr. a mais"] for g, txt in DIRS],
  [2.2, 4.4, 1.8, 3, 5])
P("Três lições:")
L("<b>β conta passos do tamanho da direção.</b> Com g = (1; 1), β = 2: dois passos de \"1 funcionário a menos e 1 "
  "de empréstimo a mais\" levam D exatamente até B (4; 6). Com g = (30; 3), cada passo é enorme, e β fica pequeno "
  "(0,095).",
  "<b>A medida de Farrell é um caso particular.</b> Com g = (6; 0) anda-se só na horizontal: β = 0,5, e "
  "θ = 1 − β = 0,5, o mesmo resultado do capítulo 10.",
  "<b>β só é comparável entre DMUs (ou entre anos) se a direção seguir a mesma regra para todas.</b> Por isso o "
  "método precisa de uma regra que funcione para qualquer DMU — e é aí que entram as constantes.")
H2("11.3 A direção natural e quando ela quebra")
P("A escolha mais natural é g = os próprios valores da DMU: g_x = insumo_o, g_y = produto_o. Assim cada passo é "
  "proporcional ao tamanho da DMU, e β vira um percentual (β = 0,375 = \"37,5% menos insumo e 37,5% mais produto\"). "
  "Isso funciona enquanto todos os valores forem positivos. Com dados reais de bancos, nem sempre são:")
F("""Problema 1 — valor ZERO. Lucro = 0 → g_y = 0.
   Depois de β passos: 0 + β × 0 = 0. O passo não mexe no lucro:
   o método fica \"cego\" para essa variável.

Problema 2 — PRODUTO negativo. Lucro = −5 (prejuízo) → g_y = −5.
   Depois de β = 0,2:  −5 + 0,2 × (−5) = −6.
   \"Aumentar o produto\" virou piorar o prejuízo.

Problema 3 — INSUMO negativo. Algumas variáveis tratadas como insumo podem ser
   negativas (por exemplo, o lucro do ano anterior, que entra como recurso herdado).
   x = −4 → g_x = −4.  Depois de β = 0,2:  −4 − 0,2 × (−4) = −3,2.
   \"Reduzir o insumo\" virou aumentá-lo.""")
P("A solução usada por Bansal et al. (seguindo Lin e Chen) é trocar a direção natural por uma versão <b>deslocada</b>, "
  "que é sempre positiva. Há uma regra para produtos e outra para insumos.")
H2("11.4 O conserto para produtos: medir a partir do pior banco, mais uma margem π")
F("""g_y = y_o − ν        com   ν = min(y) − π
   (min(y) = menor valor entre todas as DMUs)

Substituindo ν:  g_y = y_o − min(y) + π
                     = (distância do banco até o pior banco do setor) + π""")
P("Como nenhum banco está abaixo do mínimo, a distância até o pior banco é sempre ≥ 0; somando π > 0, a direção fica "
  "sempre positiva, mesmo para o pior banco e mesmo com valores negativos. Exemplo com o lucro de 5 bancos:")
luc = np.array([-5.0, 0, 3, 8, 12])
T([["lucro do banco"] + [br(v, 0) for v in luc],
   ["g_y com π = 0  (ν = −5)"] + [br(v + 5, 0) for v in luc],
   ["g_y com π = 1  (ν = −6)"] + [br(v + 6, 0) for v in luc],
   ["g_y com π = 0,01 (ν = −5,01)"] + [br(v + 5.01, 2) for v in luc]], [5.4] + [2.2] * 5)
L("Com π = 0, o pior banco (lucro −5) tem direção 0: volta o problema 1.",
  "Com π = 1, todos têm direção positiva; o pior banco anda 1 unidade de lucro por passo.",
  "Com π muito pequeno (0,01), o pior banco anda só 0,01 por passo: para melhorar 1 unidade de lucro precisaria de "
  "100 passos, e seu β ficaria enorme. O valor de π define o tamanho do passo do pior banco.")
H2("11.5 O conserto para insumos: somar ξ vezes o maior valor absoluto")
F("""g_x = x_o + μ        com   μ = ξ × max|x|
   (max|x| = maior valor absoluto entre as DMUs)

Como |x_o| ≤ max|x|, o pior caso é x_o = −max|x|:
   g_x ≥ −max|x| + ξ × max|x| = (ξ − 1) × max|x|
   ξ = 1 → g_x ≥ 0 (pode dar exatamente zero)
   ξ = 3 → g_x ≥ 2 × max|x| > 0""")
xin = np.array([-10.0, -4, 1, 3, 10])
T([["valor do insumo"] + [br(v, 0) for v in xin],
   ["g_x com ξ = 1  (μ = 10)"] + [br(v + 10, 0) for v in xin],
   ["g_x com ξ = 3  (μ = 30)"] + [br(v + 30, 0) for v in xin]], [5.4] + [2.2] * 5)
P("Com ξ = 1, o banco no extremo negativo (−10) fica com direção zero. Com ξ = 3 todos ficam positivos e com folga. "
  "Repare também que, com ξ = 3, as direções de insumo ficam parecidas entre os bancos (de 20 a 40): o passo reduz "
  "aproximadamente a mesma quantidade de insumo de todos.")
H2("11.6 Por que a margem: comparações entre anos")
P("O índice de produtividade (capítulo 12) mede um banco de um ano contra a fronteira de <b>outro</b> ano. Nessas "
  "contas \"cruzadas\", a direção é calculada com o mínimo e o máximo do ano da fronteira, mas o valor do banco vem do "
  "outro ano — e pode estar <b>fora</b> da faixa do ano da fronteira. É para esses casos que a margem serve:")
F("""PRODUTO. Ano da fronteira: min(y) = 2.
   Banco, no outro ano, com y = 1,5 (abaixo do mínimo).
   π = 0:  g_y = 1,5 − 2       = −0,5   (quebra)
   π = 1:  g_y = 1,5 − 2 + 1   =  0,5   (funciona)
   Se o banco tivesse y = 0,5:  g_y = 0,5 − 2 + 1 = −0,5 → nem π = 1 bastaria.

INSUMO. Ano da fronteira: max|x| = 10.
   Banco, no outro ano, com x = −15.
   ξ = 1:  g_x = −15 + 10 = −5   (quebra)
   ξ = 3:  g_x = −15 + 30 = 15   (funciona)""")
P("Por isso o paper diz que as constantes devem ser escolhidas \"appropriately\": grandes o bastante para que todas "
  "as direções, inclusive as dos casos cruzados, fiquem positivas.")
H2("11.7 O efeito das constantes no β")
P("Voltando ao brinquedo: max|funcionários| = 8 e min(empréstimos) = 2. Para D (6; 4), as direções são "
  "g_x = 6 + ξ × 8 e g_y = 4 − (2 − π) = 2 + π. Variando as constantes:")
lin = [["ξ", "π", "direção (g_x; g_y)", "β", "funcionários a menos (β × g_x)", "empréstimos a mais (β × g_y)"]]
for xi, pi_ in ((1, 1), (3, 1), (5, 1), (3, 0.5), (3, 2)):
    gx, gy = 6 + 8 * xi, 2 + pi_
    b, _ = ddf_toy(gx, gy)
    lin.append([br(xi, 0), br(pi_, 1), f"({br(gx, 0)}; {br(gy, 1)})", br(b, 4), br(b * gx, 3), br(b * gy, 3)])
T(lin, [1.2, 1.2, 3, 2, 4.4, 4.6])
P("O β muda bastante com as constantes, porque muda o tamanho do passo. Também muda a proporção entre reduzir "
  "insumo e aumentar produto: quanto maior ξ (passo de insumo maior em relação ao de produto), mais a melhora de D "
  "aparece como redução de funcionários. O que o índice de produtividade usa é a comparação entre β's calculados "
  "<b>com a mesma regra</b>.")
H2("11.8 O que o paper diz sobre ξ = 3 e π = 1")
P("O paper tem seis constantes, uma para cada tipo de variável, todas com o mesmo papel visto acima:")
T([["tipo de variável", "direção", "constante", "valor no M1"],
   ["insumo", "x_o + μ,  μ = ξ × max|x|", "ξ", "3"],
   ["produto indesejável (NPL do ano)", "u_o + ω,  ω = ξ' × max|u|", "ξ'", "3"],
   ["carryover do ano anterior", "c_o + α,  α = ξ'' × max|c|", "ξ''", "3"],
   ["insumo indesejável (NPL do ano anterior)", "w_o − ρ,  ρ = min(w) − π", "π", "1"],
   ["produto", "y_o − ν,  ν = min(y) − π'", "π'", "1"],
   ["carryover do ano", "c_o − γ,  γ = min(c) − π''", "π''", "1"]], [5.4, 5, 2.2, 2.6])
L("Seção 3.2: as constantes são \"positive real constants\", escolhidas de modo que, nos casos cruzados, todas as "
  "direções sejam <b>positivas</b> (11.6).",
  "Seção 4.3.1: o M1 usa ξ = ξ' = ξ'' = 3 e π = π' = π'' = 1, \"following Lin and Chen\" (referência [62]). No M2 "
  "as constantes se chamam η e δ: η = 3 e δ = 1 quando a fronteira é do ano t; η = 1,5 e δ = 1 quando é do ano t+1.",
  "Ainda na seção 4.3.1, os autores afirmam que a escolha não influencia a inferência geral da análise, mas que os "
  "valores dos índices podem ser levemente afetados.")
P("Esse é todo o embasamento que o paper dá: os valores vêm de Lin e Chen, e a exigência matemática é a positividade "
  "das direções. O artigo de Lin e Chen não está no projeto, então este guia não vai além disso.")

H1("12. Índices de Malmquist e Malmquist-Luenberger (dúvida 7)")
H2("Produtividade entre dois anos")
P("Quer-se medir se uma DMU ficou mais produtiva de um ano (t) para o seguinte (t+1). Dois fenômenos se misturam: a "
  "DMU pode ter se <b>aproximado da fronteira</b> (mudança de eficiência, EC) e a <b>fronteira pode ter se "
  "deslocado</b> (mudança técnica, TC). O <b>índice de Malmquist</b> (Caves, Christensen e Diewert, 1982; "
  "decomposto por Färe et al., 1994) separa os dois usando quatro distâncias: DMU de t e de t+1, medidas contra as "
  "fronteiras de t e de t+1.")
H2("Bom e ruim: o Malmquist-Luenberger")
P("Chung, Färe e Grosskopf (1997) trataram produtos <b>indesejáveis</b> (poluição; crédito problemático) usando a "
  "função distância direcional com direção (produto bom, −produto ruim): aumenta o bom e reduz o ruim na mesma "
  "proporção β. O produto ruim entra com igualdade, que representa a ideia de <b>descarte fraco</b>: não se pode "
  "reduzir o ruim de graça; reduzi-lo exige reduzir também o bom.")
F("""maximizar β
   SOMA(λ × insumo)        ≤ insumo_o
   SOMA(λ × produto_bom)   ≥ (1 + β) × produto_bom_o
   SOMA(λ × produto_ruim)  = (1 − β) × produto_ruim_o
   SOMA(λ) = 1""")
mlt = [(2, 4, 1), (4, 6, 3), (4, 4, 3)]
mlt1 = [(2, 5, 1), (4, 8, 3), (4, 5, 3)]


def dml(Fr, o):
    n = len(Fr)
    A = np.zeros((2, n + 1))
    A[0, :n] = [f[0] for f in Fr]
    A[1, :n], A[1, n] = [-f[1] for f in Fr], o[1]
    eq = np.zeros((2, n + 1))
    eq[0, :n], eq[0, n] = [f[2] for f in Fr], o[2]
    eq[1, :n] = 1
    c = np.zeros(n + 1)
    c[n] = 1
    return maximizar(c, A, [o[0], -o[1]], eq, [o[2], 1], livres=[n])


r00, r01, r10, r11 = dml(mlt, mlt[2]), dml(mlt, mlt1[2]), dml(mlt1, mlt[2]), dml(mlt1, mlt1[2])
T([["DMU", "ano t: insumo; bom; ruim", "ano t+1: insumo; bom; ruim"],
   ["A", "2; 4; 1", "2; 5; 1"], ["B", "4; 6; 3", "4; 8; 3"], ["C", "4; 4; 3", "4; 5; 3"]], [2, 7, 7])
F(f"""C, fronteira de t, dados de t (D00):  λA = 3/7, λB = 4/7, β = 2/7 = {br(r00[0], 4)}
   insumo = 2×3/7 + 4×4/7 = 22/7 = 3,143 ≤ 4
   bom    = 4×3/7 + 6×4/7 = 36/7 = 5,143 = 4 × (1 + 2/7)
   ruim   = 1×3/7 + 3×4/7 = 15/7 = 2,143 = 3 × (1 − 2/7)

D00 = {br(r00[0], 4)} (fronteira t, dados t)      D01 = {br(r01[0], 4)} (fronteira t, dados t+1)
D10 = {br(r10[0], 4)} (fronteira t+1, dados t)    D11 = {br(r11[0], 4)} (fronteira t+1, dados t+1)""")
ecm, tcm, im = indices.componentes(r00[0], r01[0], r10[0], r11[0])
F(f"""EC = (1 + D00) / (1 + D11)                               = {br(ecm, 4)}
TC = RAIZ( (1 + D11)/(1 + D01) × (1 + D10)/(1 + D00) )   = {br(tcm, 4)}
ML = EC × TC                                             = {br(im, 4)}""")
L(f"<b>EC</b>: C estava a 0,286 da fronteira de t e ficou a 0,316 da fronteira de t+1 → se afastou um pouco "
  f"(EC = {br(ecm, 3)} < 1).",
  "<b>TC</b>: (1+D11)/(1+D01) compara a distância dos dados de t+1 às duas fronteiras; (1+D10)/(1+D00), a dos dados "
  "de t. Se a fronteira nova está mais longe dos mesmos dados, ela avançou. A <b>raiz</b> é a média geométrica das "
  "duas comparações (definida abaixo), para não escolher arbitrariamente um dos dois anos como referência.",
  f"<b>ML</b> = {br(im, 3)}: a produtividade de C subiu {br((im - 1) * 100, 1)}%, toda ela por avanço da fronteira.")
H2("Média geométrica")
P("A <b>média geométrica</b> de n números positivos é a raiz n-ésima do produto deles: de 1,10 e 0,90 é "
  "RAIZ(1,10 × 0,90) = 0,995. É a média certa para taxas que se multiplicam: subir 10% e cair 10% deixa 99% do "
  "valor inicial, ou seja, 0,995 por período. (A média aritmética diria 1,00.) Na prática calcula-se com logaritmos, "
  "porque o <b>logaritmo natural</b> LN transforma produto em soma (LN(a×b) = LN a + LN b) e EXP desfaz o LN: "
  "média geométrica = EXP( MÉDIA( LN(x) ) ).")

# ================================================================== PARTE IV — PROBABILIDADE
H1("13. Variáveis aleatórias, valor esperado e variância")
P("Uma <b>variável aleatória</b> é um número que depende do acaso — o resultado de um dado, o erro de uma medição. "
  "Sua <b>distribuição de probabilidade</b> diz quais valores ela pode assumir e com que probabilidade.")
H2("Valor esperado (média teórica)")
P("O <b>valor esperado</b> E[X] é a média ponderada dos valores possíveis, com pesos iguais às probabilidades. É a "
  "média que se obteria repetindo o experimento infinitas vezes.")
F("""Dado: valores 1..6, probabilidade 1/6 cada
E[X] = SOMA( valor × probabilidade ) = (1+2+3+4+5+6)/6 = 3,5""")
H2("Variância e desvio-padrão")
P("A <b>variância</b> mede o espalhamento: é o valor esperado do quadrado da distância até a média. O "
  "<b>desvio-padrão</b> é a raiz da variância (volta à unidade original).")
F("""Var(X) = E[ (X − E[X])² ]
Dado:  distâncias até 3,5:  −2,5  −1,5  −0,5  0,5  1,5  2,5
       quadrados:            6,25  2,25  0,25  0,25 2,25 6,25    média = 17,5/6 = 2,917
Var = 2,917      desvio-padrão = RAIZ(2,917) = 1,708""")
P("É costume escrever o desvio-padrão com a letra grega <b>σ</b> (sigma) e a variância como σ².")
P("Numa <b>amostra</b> de n valores observados, a variância se estima com SOMA((x − média)²)/(n − 1). Divide-se por "
  "n − 1, e não por n, porque a média usada foi calculada com os mesmos dados, o que \"gasta\" uma informação. O "
  "número n − 1 é chamado de <b>graus de liberdade</b>: quantos valores independentes sobram depois de estimar o que "
  "foi estimado.")
H2("Covariância, correlação e independência")
P("A <b>covariância</b> mede se duas variáveis andam juntas: Cov(X, Y) = E[(X − E[X]) × (Y − E[Y])]. Positiva: "
  "quando uma está acima da média, a outra tende a estar também. A <b>correlação</b> é a covariância dividida pelos "
  "dois desvios-padrão; fica entre −1 e +1. Duas variáveis são <b>independentes</b> quando saber o valor de uma não "
  "muda as probabilidades da outra (dois dados diferentes); variáveis independentes têm covariância zero.")
H2("As regras que serão usadas o tempo todo")
F("""(R1) E[a × X] = a × E[X]                    (R2) E[X + Y] = E[X] + E[Y]
(R3) Var(a × X) = a² × Var(X)
(R4) Var(X + Y) = Var(X) + Var(Y) + 2 × Cov(X, Y)
     se X e Y são independentes:  Var(X + Y) = Var(X) + Var(Y)""")
P("Conferindo (R4) com dois dados: a soma tem valores de 2 a 12, e a conta direta da variância dá 5,833 = "
  "2,917 + 2,917. Conferindo (R3): 3 × (um dado) tem variância 9 × 2,917 = 26,25 — o desvio-padrão triplica e a "
  "variância fica 9 vezes maior.")

H1("14. Amostras, estimadores e erro-padrão")
P("Na prática não conhecemos a distribuição; observamos uma <b>amostra</b> e queremos descobrir algo da "
  "<b>população</b> (o processo que gerou os dados). Um <b>parâmetro</b> é um número da população (a média "
  "verdadeira). Um <b>estimador</b> é uma receita para calcular, a partir da amostra, um palpite sobre o parâmetro "
  "(por exemplo, a média da amostra). O número que a receita produz numa amostra específica é a <b>estimativa</b>.")
P("Ponto-chave: <b>o estimador também é uma variável aleatória</b>. Outra amostra daria outra estimativa. A "
  "distribuição das estimativas ao longo de muitas amostras possíveis é a <b>distribuição amostral</b>. Duas "
  "perguntas sobre ela:")
L("<b>Viés</b>: em média (E[estimativa]), ela acerta o parâmetro? Se E[estimativa] ≠ parâmetro, o estimador é "
  "<b>viesado</b> — erra sistematicamente para um lado.",
  "<b>Erro-padrão</b>: quanto ela oscila de amostra para amostra? É o <b>desvio-padrão da distribuição amostral</b>. "
  "Ele mede a incerteza da estimativa.")
H2("O erro-padrão da média, deduzido com as regras")
F("""média = (X1 + ... + Xn) / n       (n valores independentes, cada um com variância σ²)
Var(X1 + ... + Xn) = n × σ²          (R4, independentes)
Var(média) = (1/n)² × n × σ² = σ²/n  (R3)
erro-padrão da média = σ / RAIZ(n)""")
rng = np.random.default_rng(1)
linhas = [["n (dados por amostra)", "σ/RAIZ(n) (fórmula)", "desvio-padrão das 20.000 médias (simulação)"]]
for n_ in (4, 25, 100):
    medias = rng.integers(1, 7, size=(20000, n_)).mean(axis=1)
    linhas.append([str(n_), br(math.sqrt(35 / 12) / math.sqrt(n_), 4), br(medias.std(), 4)])
P("Verificação por simulação: jogamos n dados, tiramos a média, e repetimos 20.000 vezes:")
T(linhas, [4.4, 4.6, 7.4])
P("Com amostras maiores a estimativa oscila menos. Um estimador cujas estimativas se concentram no valor verdadeiro "
  "quando a amostra cresce é chamado de <b>consistente</b>. O erro-padrão é sempre <b>estimado</b> com a própria "
  "amostra (trocando σ pelo desvio-padrão observado), porque σ é desconhecido.")

H1("15. A distribuição normal e o teorema central do limite")
P("A <b>distribuição normal</b> é a curva em forma de sino. É definida por dois números: a média (centro) e o "
  "desvio-padrão (largura). A <b>normal padrão</b> tem média 0 e desvio 1. Qualquer normal vira padrão com a "
  "<b>padronização</b>:")
F("""z = (x − média) / desvio-padrão      → \"quantos desvios-padrão x está acima da média\"
Ex.: média 50, desvio 5, x = 62  →  z = (62 − 50)/5 = 2,4""")
figura_normal()
LEG("Figura 5. Normal padrão. 95% da probabilidade fica entre −1,96 e 1,96; 2,5% em cada cauda.")
F(f"""Probabilidade de ficar ABAIXO de z, para a normal padrão (no código: normal_cdf):
   z = 0      → {br(normal_cdf(0), 4)}
   z = 1      → {br(normal_cdf(1), 4)}      (entre −1 e 1: 68%)
   z = 1,645  → {br(normal_cdf(1.645), 4)}      (5% acima)
   z = 1,96   → {br(normal_cdf(1.96), 4)}      (2,5% acima; 5% fora de ±1,96)
   z = 2,576  → {br(normal_cdf(2.576), 4)}      (0,5% acima; 1% fora de ±2,576)""")
H2("Por que a normal aparece em todo lugar")
P("O <b>teorema central do limite</b> diz: a média (ou a soma) de muitas variáveis aleatórias independentes tem "
  "distribuição aproximadamente normal, <b>qualquer que seja</b> a distribuição de cada uma. O dado tem distribuição "
  "plana; a média de 2 dados já tem forma de triângulo; a de 5 dados já parece um sino:")


def dist_media(k):
    p = np.ones(6) / 6
    out = p.copy()
    for _ in range(k - 1):
        out = np.convolve(out, p)
    somas = np.arange(k, 6 * k + 1)
    return [br(s / k, 1) for s in somas], list(out)


barras_lado_a_lado([("1 dado",) + dist_media(1), ("média de 2 dados",) + dist_media(2),
                    ("média de 5 dados",) + dist_media(5)])
LEG("Figura 6. Probabilidades exatas da média de 1, 2 e 5 dados.")
P("Como os estimadores (médias, coeficientes de regressão, médias de momentos) são somas de muitos termos, em amostras "
  "grandes eles têm distribuição aproximadamente normal, centrada no seu valor esperado e com desvio igual ao "
  "erro-padrão. Isso é o que permite os testes do próximo capítulo.")

H1("16. Teste de hipótese, teste z e p-valor (dúvida 14)")
P("Um <b>teste de hipótese</b> decide se os dados são compatíveis com uma afirmação. As peças:")
N("<b>Hipótese nula (H0)</b>: a afirmação testada, em geral \"não há efeito\" (a moeda é honesta; o coeficiente é "
  "zero). <b>Hipótese alternativa (H1)</b>: o contrário.",
  "<b>Estatística de teste</b>: um número calculado com os dados cuja distribuição é conhecida <b>se H0 for "
  "verdadeira</b>.",
  "<b>Nível de significância α</b> (alfa): a probabilidade de erro que se aceita, em geral 5%.",
  "<b>Decisão</b>: se a estatística cair numa região que, sob H0, só aconteceria com probabilidade α, rejeita-se "
  "H0.")
H2("O teste z")
P("Quando a estatística é uma estimativa com distribuição aproximadamente normal (capítulo 15), padroniza-se usando "
  "o valor afirmado por H0 e o erro-padrão:")
F("""z = (estimativa − valor sob H0) / erro-padrão
  = quantos erros-padrão a estimativa está longe do que H0 afirma.
Se H0 é verdadeira, z segue a normal padrão: |z| > 1,96 acontece só 5% das vezes.
Regra a 5%: rejeitar H0 se |z| > 1,96.""")
H2("Exemplo completo")
F(f"""Moeda lançada 100 vezes: 62 caras.   H0: a moeda é honesta (probabilidade 0,5).
Sob H0: número de caras = soma de 100 variáveis (1 = cara, 0 = coroa), cada uma com
   média 0,5 e variância 0,5 × 0,5 = 0,25.
   média da soma = 100 × 0,5 = 50              (R2)
   variância     = 100 × 0,25 = 25 → desvio 5  (R4, independentes)
   pelo teorema central do limite, a soma é aproximadamente normal.
z = (62 − 50)/5 = 2,4   → |z| > 1,96 → rejeita-se H0 a 5%.""")
H2("O p-valor")
P("Em vez de só dizer \"rejeita/não rejeita\", calcula-se o <b>p-valor</b>: a probabilidade, <b>supondo H0 "
  "verdadeira</b>, de obter um resultado pelo menos tão extremo quanto o observado. Rejeita-se H0 quando p-valor "
  "< α. As estrelas das tabelas (*, **, ***) marcam p < 10%, 5% e 1%.")
F(f"""p-valor (bilateral: extremo para cima ou para baixo) = 2 × (1 − Normal(|z|))
Moeda: 2 × (1 − Normal(2,4)) = 2 × (1 − {br(normal_cdf(2.4), 4)}) = {br(2 * (1 - normal_cdf(2.4)), 4)}""")
P("Um teste é <b>bilateral</b> quando valores extremos para os dois lados contam contra H0 (a moeda pode estar "
  "viciada para cara ou para coroa) e <b>unilateral</b> quando só um lado conta (aí p = 1 − Normal(z) e o limite a 5% "
  "é 1,645).")
H2("Os dois erros possíveis")
L("<b>Erro tipo I</b>: rejeitar H0 quando ela é verdadeira. Acontece com probabilidade α (5%) — é o que α controla.",
  "<b>Erro tipo II</b>: não rejeitar H0 quando ela é falsa. Fica menor com amostras maiores.",
  "<b>Não rejeitar H0 não prova H0</b>: só diz que os dados não são incompatíveis com ela.")

H1("17. A distribuição qui-quadrado")
P("Se z1, z2, …, zk são normais padrão independentes, a soma dos quadrados")
F("""Q = z1² + z2² + ... + zk²""")
P("tem a distribuição chamada <b>qui-quadrado com k graus de liberdade</b>, χ²(k). Como cada z² tem valor esperado 1 "
  "(é a variância de z), E[Q] = k. Ela aparece sempre que se quer testar <b>várias coisas ao mesmo tempo</b>: cada "
  "coisa vira um z, e soma-se os quadrados. Valores grandes de Q indicam que algum z está longe de zero.")
rng = np.random.default_rng(2)
crit = {}
for k in (1, 2, 5, 10):
    lo, hi = 0.0, 100.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if chi2_sf(mid, k) > 0.05 else (lo, mid)
    sim = (rng.normal(size=(50000, k)) ** 2).sum(axis=1)
    crit[k] = (lo, sim.mean(), (sim > lo).mean())
T([["k", "valor crítico a 5% (P(χ² > c) = 5%)", "média de 50.000 simulações", "fração simulada acima do crítico"]] +
  [[str(k), br(c, 2), br(m, 3), br(f * 100, 1) + "%"] for k, (c, m, f) in crit.items()], [1.4, 5.6, 4.6, 4.8])
P("Para testar com χ²: calcula-se Q; o p-valor é P(χ²(k) > Q) (no código, <font name='Consolas'>chi2_sf</font>). "
  "Com k = 1, Q = z² e o teste é o mesmo teste z bilateral (1,96² = 3,84).")

# ================================================================== PARTE V — REGRESSÃO
H1("18. Regressão linear e mínimos quadrados (dúvida 8)")
P("Um <b>modelo de regressão linear</b> supõe que y é uma reta em x mais um <b>erro</b> u, que reúne tudo o que "
  "afeta y e não está em x:")
F("""y[i] = a + b × x[i] + u[i]        a = intercepto, b = inclinação, u = erro (não observado)""")
P("a e b são parâmetros desconhecidos. Uma vez estimados (â, b_est), o <b>resíduo</b> de cada observação é "
  "û = y − (â + b_est x): a parte de y que a reta estimada não explica. O erro u é da população; o resíduo û é da "
  "amostra.")
H2("O critério: a menor soma dos quadrados dos resíduos")
P("<b>Mínimos quadrados ordinários (MQO)</b> escolhe a reta que minimiza SQR = SOMA(û²). O quadrado evita que "
  "resíduos positivos e negativos se cancelem e pune mais os erros grandes.")
H2("A conta, sem cálculo diferencial")
P("Comece pela reta sem intercepto, y = b × x. A soma dos quadrados é uma <b>parábola</b> em b:")
xs = np.array([1, 2, 3, 4.])
ys = np.array([2, 3, 5, 6.])
sxx, sxy, syy = (xs * xs).sum(), (xs * ys).sum(), (ys * ys).sum()
F(f"""Pontos: (1; 2) (2; 3) (3; 5) (4; 6)
SQR(b) = SOMA( (y − b x)² ) = SOMA(y²) − 2b × SOMA(x y) + b² × SOMA(x²)
       = {br(syy, 0)} − 2b × {br(sxy, 0)} + b² × {br(sxx, 0)}

Completando o quadrado (álgebra de escola):
   A b² − 2B b + C = A × (b − B/A)² + C − B²/A
   o termo A×(b − B/A)² é ≥ 0 e vale zero quando b = B/A  → esse é o mínimo.
b_est = SOMA(x y) / SOMA(x²) = {br(sxy, 0)} / {br(sxx, 0)} = {br(sxy / sxx, 4)}""")
T([["b", "1,40", "1,50", br(sxy / sxx, 3), "1,60", "1,70"],
   ["SQR(b)"] + [br(syy - 2 * b * sxy + b * b * sxx, 3) for b in (1.4, 1.5, sxy / sxx, 1.6, 1.7)]],
  [2.4, 2.8, 2.8, 2.8, 2.8, 2.8])
mx, my = xs.mean(), ys.mean()
Sxy, Sxx = ((xs - mx) * (ys - my)).sum(), ((xs - mx) ** 2).sum()
b_ = Sxy / Sxx
a_ = my - b_ * mx
res = ys - (a_ + b_ * xs)
SQR = (res ** 2).sum()
P("Com intercepto, a mesma ideia aplicada às variáveis <b>centradas</b> (subtraindo a média de cada uma) dá:")
F(f"""b_est = SOMA( (x − mx)(y − my) ) / SOMA( (x − mx)² )
â     = my − b_est × mx
mx = {br(mx, 1)}, my = {br(my, 1)}
numerador   = (−1,5)(−2) + (−0,5)(−1) + (0,5)(1) + (1,5)(2) = {br(Sxy, 1)}
denominador = 2,25 + 0,25 + 0,25 + 2,25                     = {br(Sxx, 1)}
b_est = {br(Sxy, 1)}/{br(Sxx, 1)} = {br(b_, 2)}
â = {br(my, 1)} − {br(b_, 2)} × {br(mx, 1)} = {br(a_, 2)}
resíduos: {', '.join(br(r, 1) for r in res)}    SQR = {br(SQR, 2)}""")
P("Note que b_est = Cov(x, y)/Var(x) da amostra (o denominador n − 1 se cancela). Essa forma será usada no capítulo 21.")
H2("A mesma conta com matrizes")
P("Com vários explicativos, monta-se a matriz X (uma coluna de 1 para o intercepto e uma coluna para cada "
  "explicativo) e a fórmula é b_est = (X' @ X)<super>−1</super> @ (X' @ y). Com os mesmos 4 pontos:")
X2 = np.c_[np.ones(4), xs]
XtX, Xty = X2.T @ X2, X2.T @ ys
F(f"""X = [1 1; 1 2; 1 3; 1 4]
X' @ X = {mat(XtX, 0).splitlines()[0]}      X' @ y = [{br(Xty[0], 0)}, {br(Xty[1], 0)}]
         {mat(XtX, 0).splitlines()[1]}
inversa 2×2 (cap. 4): determinante = 4×30 − 10×10 = 20
(X'X)^(−1) = 1/20 × [ 30 −10; −10 4 ]
b_est = 1/20 × [ 30×16 − 10×47 ; −10×16 + 4×47 ] = 1/20 × [10; 28] = [{br(a_, 2)}; {br(b_, 2)}]""")
P("Com vários explicativos, cada coeficiente mede o efeito daquele explicativo <b>mantendo os outros fixos</b>.")

H1("19. A precisão de um coeficiente: erro-padrão e coef / ep (dúvida 14)")
H2("As hipóteses do MQO")
L("<b>(H1)</b> o erro tem média zero e <b>não tem relação com x</b>: E[u | x] = 0 (saber x não ajuda a prever u).",
  "<b>(H2)</b> os erros de observações diferentes são independentes.",
  "<b>(H3) homocedasticidade</b>: todos os erros têm a mesma variância σ². O contrário se chama "
  "<b>heterocedasticidade</b> (a variância muda de uma observação para outra — por exemplo, bancos grandes com erros "
  "maiores).")
H2("A variância de b_est, deduzida")
F("""Substituindo y = a + b x + u na fórmula de b_est:
   b_est = b + SOMA( (x − mx) × u ) / SOMA( (x − mx)² )
   = valor verdadeiro + uma média ponderada dos erros.

Por (H1), o segundo termo tem valor esperado 0 → b_est não é viesado.
Por (H2), (H3) e as regras R3 e R4:
   Var(b_est) = SOMA( (x − mx)² × σ² ) / ( SOMA( (x − mx)² ) )² = σ² / SOMA( (x − mx)² )
   ep(b_est)  = RAIZ( σ² / SOMA( (x − mx)² ) )""")
s2_ = SQR / 2
ep_b = math.sqrt(s2_ / Sxx)
F(f"""σ² é estimado pelos resíduos:  s² = SQR / (n − 2)    (2 graus de liberdade gastos: a e b)
Exemplo: s² = {br(SQR, 2)}/2 = {br(s2_, 2)}     ep(b_est) = RAIZ({br(s2_, 2)} / {br(Sxx, 1)}) = {br(ep_b, 4)}""")
H2("coef / ep: o teste z de um coeficiente")
P("As tabelas de regressão mostram, para cada explicativo, o <b>coef</b> (b_est) e o <b>ep</b>. Com H0: \"o coeficiente "
  "verdadeiro é zero\" (o explicativo não tem efeito), o teste z do capítulo 16 é:")
F(f"""z = (coef − 0) / ep = coef / ep            p-valor = 2 × (1 − Normal(|z|))
Exemplo: z = {br(b_, 2)} / {br(ep_b, 4)} = {br(b_ / ep_b, 2)}  → p ≈ 0 → x tem efeito.
Outro: coef = 0,0076, ep = 0,0034 → z = 2,24 → p = {br(2 * (1 - normal_cdf(0.0076 / 0.0034)), 3)} → significativo a 5%.
       coef = −0,0044, ep = 0,0029 → z = −1,52 → p = {br(2 * (1 - normal_cdf(0.0044 / 0.0029)), 3)} → não significativo.""")
P("(Com amostras pequenas e erros normais usa-se a distribuição t, quase igual à normal com mais de umas 30 "
  "observações; a ideia é a mesma.)")
H2("Heterocedasticidade e o erro-padrão robusto")
P("A fórmula σ²/SOMA((x − mx)²) usou (H3). Se a variância muda entre observações, a conta correta (com R3 e R4) "
  "mantém cada variância separada, e cada uma é estimada pelo próprio resíduo ao quadrado. É o <b>erro-padrão "
  "robusto</b> (White, 1980), também chamado \"sanduíche\" pela forma da fórmula:")
F("""Var_robusta(b_est) = SOMA( (x − mx)² × û² ) / ( SOMA( (x − mx)² ) )²""")
rng = np.random.default_rng(9)
bs, epc, epr = [], [], []
for _ in range(4000):
    x = rng.uniform(0, 4, 100)
    y = 1 + 2 * x + rng.normal(0, 1, 100) * (0.2 + x)
    xm = x - x.mean()
    b = (xm * (y - y.mean())).sum() / (xm ** 2).sum()
    u = y - (y.mean() - b * x.mean()) - b * x
    bs.append(b)
    epc.append(math.sqrt((u @ u) / 98 / (xm ** 2).sum()))
    epr.append(math.sqrt(((xm ** 2) * u ** 2).sum()) / (xm ** 2).sum())
T([["Simulação: 4.000 amostras de 100 obs., erro com desvio crescente em x", "valor"],
   ["desvio-padrão real das 4.000 estimativas de b (o que o ep deveria medir)", br(np.std(bs), 4)],
   ["média do ep usual (supõe homocedasticidade)", br(np.mean(epc), 4)],
   ["média do ep robusto", br(np.mean(epr), 4)]], [12.4, 4])
P("Com heterocedasticidade, o ep usual erra (aqui, para baixo) e o robusto acerta. A mesma preocupação reaparece "
  "no GMM (Sargan × Hansen, capítulo 24).")

H1("20. O teste de Wald (dúvida 13)")
P("O teste z testa <b>um</b> coeficiente. O teste de <b>Wald</b> testa <b>vários ao mesmo tempo</b>, por exemplo "
  "H0: \"todos os coeficientes, exceto o intercepto, são zero\" (o modelo não explica nada).")
H2("Por que não basta somar os z²")
P("Se os coeficientes estimados fossem independentes, cada z² seria um χ²(1) e a soma seria χ²(k) (capítulo 17). "
  "Mas estimativas de uma mesma regressão costumam ser <b>correlacionadas</b> (quando dois explicativos andam juntos, "
  "superestimar um tende a vir com subestimar o outro). Essa informação está na <b>matriz de variância-covariância</b> "
  "V das estimativas: na diagonal, as variâncias (ep²); fora dela, as covariâncias entre pares de estimativas.")
F("""Wald = b' @ V^(−1) @ b        ~ χ²(k) sob H0
   (k = número de coeficientes testados)
com um coeficiente: V = ep²  →  Wald = b²/ep² = z²""")
P("Multiplicar pela inversa de V é \"padronizar\" o vetor b levando em conta as variâncias e as correlações. Com V "
  "diagonal (sem correlação), Wald = soma dos z².")


def wald(b, V):
    return float(np.asarray(b) @ np.linalg.inv(V) @ np.asarray(b))


V0 = np.array([[0.01, 0.0], [0.0, 0.01]])
V8 = np.array([[0.01, 0.008], [0.008, 0.01]])
F(f"""ep de cada coeficiente = 0,1 (variância 0,01).  b = [0,30 ; 0,20] → z = 3 e 2.

Sem correlação: V = [0,01 0; 0 0,01] → Wald = 3² + 2² = {br(wald([0.3, 0.2], V0), 2)}

Correlação 0,8: V = [0,01 0,008; 0,008 0,01]
   determinante = 0,01×0,01 − 0,008² = 0,000036
   V^(−1) = 1/0,000036 × [0,01 −0,008; −0,008 0,01]
   b = [0,30; 0,20]  → Wald = {br(wald([0.3, 0.2], V8), 2)}
   b = [0,30; −0,20] → Wald = {br(wald([0.3, -0.2], V8), 2)}""")
P(f"Com correlação positiva, é \"esperado\" que as duas estimativas errem para o mesmo lado. b = (0,3; 0,2) é "
  f"compatível com isso e o Wald cai de 13 para {br(wald([0.3, 0.2], V8), 1)}; b = (0,3; −0,2) contraria isso e o "
  f"Wald sobe para {br(wald([0.3, -0.2], V8), 1)}. O p-valor é P(χ²(2) > Wald): {br(chi2_sf(wald([0.3, 0.2], V8), 2), 4)} "
  f"e {br(chi2_sf(wald([0.3, -0.2], V8), 2), 6)}.")

H1("21. Quando o MQO falha: endogeneidade")
P("Um explicativo é <b>endógeno</b> quando está correlacionado com o erro u — viola (H1). O contrário é "
  "<b>exógeno</b>. Causas comuns: uma variável importante que ficou de fora e afeta x e y (<b>variável omitida</b>); "
  "x e y se determinam mutuamente (<b>simultaneidade</b>); e, em painéis, a defasagem de y junto com características "
  "fixas de cada unidade (capítulo 25).")
H2("Quanto o MQO erra")
F("""b_est = b + SOMA((x − mx) u) / SOMA((x − mx)²)        (capítulo 19)
dividindo em cima e em baixo por n − 1, com amostra grande:
   b_est ≈ b + Cov(x, u) / Var(x)
Se Cov(x, u) ≠ 0, o erro NÃO some com mais dados: o MQO é viesado e inconsistente.""")
rng = np.random.default_rng(3)
n_ = 100000
z_ = rng.normal(0, 1, n_)
v_ = rng.normal(0, 1, n_)
u_ = 0.8 * v_ + rng.normal(0, 0.6, n_)
x_ = z_ + v_
y_ = 2 * x_ + u_
bmqo = np.cov(x_, y_)[0, 1] / np.var(x_, ddof=1)
biv = np.cov(z_, y_)[0, 1] / np.cov(z_, x_)[0, 1]
F(f"""Simulação (100.000 obs.):  x = z + v ;  u = 0,8 v + ruído ;  y = 2x + u
   x e u compartilham v → Cov(x, u) = 0,8 × Var(v) = 0,8 ;  Var(x) = Var(z) + Var(v) = 2
   previsto: b_est_MQO ≈ 2 + 0,8/2 = 2,4
   MQO na simulação: {br(bmqo, 4)}""")

H1("22. Variáveis instrumentais")
P("Um <b>instrumento</b> z para o explicativo endógeno x é uma variável com duas propriedades:")
L("<b>Relevância</b>: z está correlacionado com x (Cov(z, x) ≠ 0).",
  "<b>Validade (exogeneidade)</b>: z não está correlacionado com o erro (Cov(z, u) = 0) — z só afeta y através de x.")
F(f"""Da validade:  Cov(z, u) = 0  e  u = y − b x  →  Cov(z, y) − b × Cov(z, x) = 0
   →  b = Cov(z, y) / Cov(z, x)         (estimador de variáveis instrumentais, VI)
Na simulação acima (z não aparece em u):  b_est_VI = {br(biv, 4)}   (verdadeiro: 2)""")
H2("Instrumento fraco")
P("Se Cov(z, x) é pequena, divide-se por um número perto de zero: pequenas oscilações da amostra viram grandes "
  "oscilações da estimativa. Diz-se que o instrumento é <b>fraco</b>. Simulação com 2.000 amostras de 200 obs. e "
  "x = força × z + v:")
rng = np.random.default_rng(6)
lin = [["força do instrumento", "correlação de z com x", "metade central das estimativas VI (25% a 75%)"]]
for f_ in (1.0, 0.3, 0.05):
    est, cr = [], []
    for _ in range(2000):
        z = rng.normal(0, 1, 200)
        v = rng.normal(0, 1, 200)
        u = 0.8 * v + rng.normal(0, 0.6, 200)
        x = f_ * z + v
        y = 2 * x + u
        est.append(np.cov(z, y)[0, 1] / np.cov(z, x)[0, 1])
        cr.append(np.corrcoef(z, x)[0, 1])
    lin.append([br(f_, 2), br(np.mean(cr), 3), faixa(est)])
T(lin, [4, 4.4, 8])
P("Com instrumento forte, metade das estimativas fica numa faixa estreita em volta de 2; com instrumento fraco, a "
  "faixa explode. A <b>metade central</b> é o intervalo entre o valor que deixa 25% das estimativas abaixo e o que "
  "deixa 25% acima.")

# ================================================================== PARTE VI — GMM E PAINEL
H1("23. O método generalizado dos momentos — GMM (dúvida 2)")
H2("Momentos e condições de momento")
P("Um <b>momento</b> é o valor esperado de alguma função dos dados (E[X], E[X²], E[z × u]...). Uma <b>condição de "
  "momento</b> é uma afirmação da teoria do tipo \"este valor esperado é zero\". O <b>método dos momentos</b> estima "
  "os parâmetros fazendo a <b>média da amostra</b> cumprir a condição:")
F("""média μ:  teoria E[y − μ] = 0     amostra MÉDIA(y − μ) = 0
          → μ_est = MÉDIA(y)
MQO:      teoria E[x × u] = 0     amostra MÉDIA(x × (y − b x)) = 0
          → b_est = SOMA(x y) / SOMA(x²)
VI:       teoria E[z × u] = 0     amostra MÉDIA(z × (y − b x)) = 0
          → b_est = SOMA(z y) / SOMA(z x)""")
P("Com tantas condições quantos parâmetros, a solução é exata. Quando há <b>mais condições que parâmetros</b> — "
  "por exemplo, dois instrumentos válidos z1 e z2 para um único b — diz-se que o modelo é <b>sobreidentificado</b>. "
  "Cada instrumento sozinho dá um b_est diferente (a amostra tem ruído), e nenhum b zera as duas médias ao mesmo tempo.")
H2("A ideia do GMM")
P("O GMM (Hansen, 1982) escolhe o b que deixa as médias <b>o mais perto possível de zero</b>, num sentido "
  "ponderado. Com g1(b) = MÉDIA(z1 (y − b x)) e g2(b) = MÉDIA(z2 (y − b x)), minimiza-se:")
F("""Q(b) = [g1 g2] @ W @ [g1 g2]'          W = matriz de pesos 2×2, escolhida por nós

Com W = identidade: Q = g1² + g2²   (soma simples dos quadrados)
Q(b) é uma parábola em b (cada g é uma reta em b) → mínimo pelo \"completar o quadrado\":
   b_est = (Szx' @ W @ Szy) / (Szx' @ W @ Szx)
   Szx = [MÉDIA(z1 x), MÉDIA(z2 x)]     Szy = [MÉDIA(z1 y), MÉDIA(z2 y)]""")
H2("Que pesos usar: a analogia dos termômetros")
P("Dois termômetros medem a mesma temperatura: o A marca 20,0 com variância de erro 1; o B marca 22,0 com variância "
  "4 (é menos preciso). Combinando com pesos w e 1 − w, a variância da combinação é (por R3 e R4, erros "
  "independentes) w² × 1 + (1 − w)² × 4. O menor valor acontece com <b>pesos proporcionais a 1/variância</b>:")
F("""pesos proporcionais a 1/1 e 1/4  →  w = 0,8 para A e 0,2 para B
combinação = 0,8 × 20 + 0,2 × 22 = 20,4
variância  = 0,8² × 1 + 0,2² × 4 = 0,80     (menor que a do melhor termômetro, 1)
com pesos iguais: 0,5² × 1 + 0,5² × 4 = 1,25 (pior)""")
P("No GMM é igual: as condições de momento mais ruidosas devem pesar menos. A matriz de pesos ótima é a "
  "<b>inversa da matriz de variância-covariância dos momentos</b>, S, onde S mede quanto cada MÉDIA(z (y − b x)) "
  "oscila e quanto elas oscilam juntas. Um estimador com a menor variância possível dentro de uma classe é chamado "
  "<b>eficiente</b>.")
H2("GMM em dois passos")
N("<b>Passo 1</b>: usa uma W inicial razoável — por exemplo W1 = inversa de MÉDIA(z z'), que é ótima se os erros "
  "forem homocedásticos (essa versão também se chama <b>mínimos quadrados em dois estágios</b>). Calcula b_est1 e os "
  "resíduos û1.",
  "<b>Passo 2</b>: estima S com os resíduos, S = MÉDIA(û1² × z z'), usa W2 = S<super>−1</super> e recalcula: b_est2.")
rng = np.random.default_rng(3)
n8 = 8
z1 = np.round(rng.uniform(1, 5, n8), 0)
z2 = np.round(rng.uniform(1, 5, n8), 0)
v8 = rng.normal(0, 1, n8)
x8 = np.round(z1 + 0.5 * z2 + v8, 1)
u8 = np.round(0.8 * v8 + rng.normal(0, 0.5, n8), 1)
y8 = np.round(2 * x8 + u8, 1)
G8 = gmm_dois_instr(y8, x8, np.c_[z1, z2])
T([["obs"] + [str(i + 1) for i in range(n8)],
   ["z1"] + [br(v, 0) for v in z1], ["z2"] + [br(v, 0) for v in z2],
   ["x"] + [br(v, 1) for v in x8], ["y"] + [br(v, 1) for v in y8]], [1.6] + [1.85] * 8, cabecalho=False)
F(f"""Dados gerados com b verdadeiro = 2 e x endógeno.
MQO:           SOMA(x y)/SOMA(x²)       = {br((x8 @ y8) / (x8 @ x8), 4)}
VI só com z1:  SOMA(z1 y)/SOMA(z1 x)    = {br((z1 @ y8) / (z1 @ x8), 4)}
VI só com z2:  SOMA(z2 y)/SOMA(z2 x)    = {br((z2 @ y8) / (z2 @ x8), 4)}
GMM passo 1:   W1 = {mat(G8['W1'], 4).splitlines()[0]}
                    {mat(G8['W1'], 4).splitlines()[1]}      b_est1 = {br(G8['b1'], 4)}
GMM passo 2:   W2 = {mat(G8['W2'], 4).splitlines()[0]}
                    {mat(G8['W2'], 4).splitlines()[1]}      b_est2 = {br(G8['b2'], 4)}""")
P("Com 8 observações os números servem só para acompanhar a conta. O capítulo seguinte usa simulações grandes.")

H1("24. Sobreidentificação: os testes de Sargan e Hansen J (dúvida 12)")
P("Num modelo sobreidentificado sobram condições: com L instrumentos e k parâmetros, o GMM só consegue \"ajustar\" k "
  "combinações das L médias; as outras <b>L − k</b> funcionam como checagem. Se todos os instrumentos forem válidos, "
  "as L médias g(b_est) devem ficar perto de zero, só não exatamente zero por ruído. Se algum instrumento for inválido, "
  "ele \"puxa\" uma média para longe de zero.")
H2("A estatística J")
F("""J = n × g(b_est)' @ W @ g(b_est)        H0: todos os instrumentos são válidos
sob H0, J ~ χ²(L − k)              (L − k = número de checagens que sobram)""")
P("Com W = inversa da variância dos momentos, n × g' W g é uma soma de quadrados de momentos padronizados — os z do "
  "capítulo 17 —, por isso a distribuição χ². J grande (p-valor pequeno) → rejeita-se a validade conjunta dos "
  "instrumentos. Atenção: o teste diz que <b>algum</b> instrumento é inválido, não qual; e não rejeitar não prova que "
  "são válidos.")
F(f"""Exemplo dos 8 pontos (L = 2, k = 1 → 1 grau de liberdade):
   g(b_est2) = [{br(G8['g2'][0], 4)} ; {br(G8['g2'][1], 4)}]   J = {br(G8['J'], 3)}   p = P(χ²(1) > J) = {br(chi2_sf(G8['J'], 1), 3)}""")
H2("Sargan × Hansen")
T([["Teste", "Calcula J com", "Supõe"],
   ["Sargan (1958)", "resíduos do passo 1 e W baseada numa variância comum σ² para todos os erros",
    "homocedasticidade"],
   ["Hansen J (1982)", "resíduos do passo 2 e a W ótima estimada (S<super>−1</super>)",
    "nada sobre a variância (robusto a heterocedasticidade)"]], [3, 8.4, 5])
rng = np.random.default_rng(4)
lin = [["Cenário (1.000 amostras de 200 obs.)", "Sargan rejeita", "Hansen rejeita", "média de b_est2"]]
for cen in ("instrumentos válidos", "z2 inválido (aparece no erro)", "válidos, mas heterocedástico"):
    rs_, rh_, bb_ = [], [], []
    for _ in range(1000):
        n = 200
        z1, z2, v, w = (rng.normal(0, 1, n) for _ in range(4))
        u = 0.8 * v + 0.6 * w
        if cen.startswith("z2"):
            u = u + 0.5 * z2
        if cen.startswith("válidos, mas"):
            u = u * np.exp(0.8 * z1)
        x = z1 + 0.7 * z2 + v
        y = 2 * x + u
        G = gmm_dois_instr(y, x, np.c_[z1, z2])
        rs_.append(chi2_sf(G["sargan"], 1) < 0.05)
        rh_.append(chi2_sf(G["J"], 1) < 0.05)
        bb_.append(G["b2"])
    lin.append([cen, br(np.mean(rs_) * 100, 1) + "%", br(np.mean(rh_) * 100, 1) + "%", br(np.mean(bb_), 3)])
T(lin, [6.8, 3, 3, 3.6])
P("Leitura: com instrumentos válidos, os dois rejeitam perto de 5% das vezes, como deve ser (é o erro tipo I, "
  "capítulo 16). Com um instrumento inválido, os dois detectam, e a estimativa fica viesada. Com heterocedasticidade e "
  "instrumentos válidos, o Sargan rejeita mais do que 5% — acusa um problema que não existe —, enquanto o Hansen "
  "continua correto.")

H1("25. Dados em painel, efeito fixo e o modelo dinâmico")
P("Dados em <b>painel</b> observam as mesmas unidades i (bancos) em vários períodos t (anos). Num <b>modelo "
  "dinâmico</b>, o valor do ano anterior (a <b>defasagem</b> y[t−1]) é um dos explicativos:")
F("""y[i, t] = a × y[i, t−1] + η[i] + e[i, t]
   η[i]    = efeito fixo: algo próprio de cada unidade, constante no tempo
             (ex.: qualidade da gestão)
   e[i, t] = erro do ano, sem relação com η nem com os erros de outros anos""")
H2("Por que o MQO superestima a")
F("""O explicativo é y[t−1] = a × y[t−2] + η + e[t−1]  → contém η.
O erro da equação é (η + e[t]) → também contém η.
Logo Cov(y[t−1], η + e[t]) > 0 → pelo capítulo 21, b_est_MQO ≈ a + (algo positivo).""")
H2("Tirar a média de cada unidade (\"within\") cria outro problema")
P("Subtrair de cada variável a média da própria unidade no período elimina η (que é constante). Mas a média de "
  "e[i, ·] inclui os erros de todos os anos, inclusive os que já afetaram y[t−1]; a correlação reaparece, agora "
  "negativa. É o <b>viés de Nickell</b> (1981), aproximadamente −(1 + a)/(T − 1): grande quando há poucos anos.")
rng = np.random.default_rng(7)
Nn, Tt, a_v = 300, 7, 0.5
ysim = painel_sim(Nn, Tt, a_v, rng)
Yp, Xp = ysim[:, 1:].ravel(), ysim[:, :-1].ravel()
b_mqo = np.linalg.lstsq(np.c_[Xp, np.ones_like(Xp)], Yp, rcond=None)[0][0]
Yw = ysim[:, 1:] - ysim[:, 1:].mean(1, keepdims=True)
Xw = ysim[:, :-1] - ysim[:, :-1].mean(1, keepdims=True)
b_within = (Xw * Yw).sum() / (Xw * Xw).sum()
dy = np.diff(ysim, axis=1)
zah = ysim[:, :-2].ravel()
b_ah = (zah @ dy[:, 1:].ravel()) / (zah @ dy[:, :-1].ravel())
RS = gmm.system_gmm(ysim, [], ["L.dep", "Constant"])
T([["Simulação: 300 unidades × 7 anos, a = 0,5", "â"],
   ["MQO", br(b_mqo, 3)],
   [f"Within (Nickell previsto: 0,5 − 1,5/6 = 0,25)", br(b_within, 3)],
   ["Diferença + instrumento y[t−2] (capítulo 27)", br(b_ah, 3)],
   ["GMM de sistema (capítulo 28)", br(RS["coef"][0], 3)]], [12, 4.4])

H1("26. Autocorrelação (dúvida 11, parte 1)")
P("<b>Autocorrelação de ordem k</b> é a correlação de uma série com ela mesma k períodos antes: entre e[t] e "
  "e[t−k]. Se é positiva, um erro alto tende a ser seguido de outro alto — a série \"tem memória\".")
serie = np.array([1.0, 3, 2, 4, 3, 5])
sc = serie - serie.mean()
r1 = (sc[1:] * sc[:-1]).sum() / (sc ** 2).sum()
F(f"""Série: 1, 3, 2, 4, 3, 5     média = {br(serie.mean(), 3)}
desvios da média: {', '.join(br(v, 2) for v in sc)}
autocorrelação de ordem 1 ≈ SOMA( desvio[t] × desvio[t−1] ) / SOMA( desvio² ) = {br(r1, 3)}""")
P("Um modelo simples de erro com memória é o <b>AR(1)</b> (autorregressivo de ordem 1): e[t] = ρ × e[t−1] + v[t], com "
  "v sem memória. ρ = 0: sem memória; ρ = 0,5: metade do erro passado continua presente. (Repare: \"AR(1)\" designa "
  "esse modelo; no capítulo 29, \"AR(1)\" e \"AR(2)\" são os nomes de dois <i>testes</i>, que verificam autocorrelação "
  "de ordem 1 e 2.)")
H2("A autocorrelação das diferenças")
P("No próximo capítulo as equações serão diferenciadas: Δe[t] = e[t] − e[t−1]. Mesmo que e não tenha memória, as "
  "diferenças vizinhas têm:")
F("""Δe[t]   = e[t]   − e[t−1]
Δe[t−1] = e[t−1] − e[t−2]          → as duas contêm e[t−1], com sinais opostos

Se e não tem memória (variância σ²):
   Cov(Δe[t], Δe[t−1]) = Cov(−e[t−1], e[t−1]) = −σ²
      (os outros pares de termos são independentes)
   Var(Δe) = σ² + σ² = 2σ²                                   (R4)
   correlação de ordem 1 = −σ² / 2σ² = −0,5

   Δe[t−2] = e[t−2] − e[t−3] não tem nenhum termo em comum com Δe[t]
   → correlação de ordem 2 = 0""")
rng = np.random.default_rng(8)
e_ = rng.normal(0, 1, 200000)
de = np.diff(e_)
P(f"Com 200.000 erros simulados sem memória: correlação de Δe com Δe de 1 período antes = "
  f"{br(np.corrcoef(de[1:], de[:-1])[0, 1], 3)}; de 2 períodos antes = {br(np.corrcoef(de[2:], de[:-2])[0, 1], 3)}.")

H1("27. Arellano-Bond: diferenças e instrumentos defasados (dúvida 9, parte 1)")
H2("Passo 1: diferenciar elimina o efeito fixo")
F("""y[t]   = a × y[t−1] + η + e[t]
y[t−1] = a × y[t−2] + η + e[t−1]
subtraindo:   Δy[t] = a × Δy[t−1] + Δe[t]          (η sumiu)""")
H2("Passo 2: o novo explicativo ainda é endógeno")
F("""Δy[t−1] = y[t−1] − y[t−2]   contém e[t−1]  (via y[t−1])
Δe[t]   = e[t] − e[t−1]     contém e[t−1]
→ correlacionados → MQO na diferença também é viesado.""")
H2("Passo 3: instrumentos que já existiam antes")
P("y[t−2] é <b>relevante</b> (faz parte de Δy[t−1]) e <b>válido</b>: y[t−2] depende de η e de e[t−2], e[t−3], …, mas "
  "não de e[t] nem de e[t−1], que são os termos de Δe[t] — desde que <b>e não tenha memória</b> (capítulo 26). "
  "y[t−3], y[t−4], … também valem. Usando só y[t−2] tem-se o estimador de Anderson e Hsiao (1981): "
  "â = SOMA(y[t−2] × Δy[t]) / SOMA(y[t−2] × Δy[t−1]).")
P("<b>Arellano e Bond (1991)</b> usam todas as defasagens disponíveis como condições de momento separadas e as "
  "combinam com GMM (capítulo 23). Cada ano tem um conjunto diferente de instrumentos:")
F("""painel 2011–2017 (7 anos); equação de cada ano: Δy(t) = a × Δy(t−1) + Δe(t)
   ano 2013 → instrumentos: y(2011)
   ano 2014 → instrumentos: y(2011), y(2012)
   ano 2015 → instrumentos: y(2011), y(2012), y(2013)
   ano 2016 → 4 instrumentos
   ano 2017 → 5 instrumentos
   total: 1 + 2 + 3 + 4 + 5 = 15 condições de momento para 1 parâmetro
   → sobreidentificado""")
P("No passo 1 desse GMM, a matriz de pesos já incorpora o fato do capítulo 26: erros em diferença de anos vizinhos "
  "têm correlação −0,5 (no código, a matriz H, com 2 na diagonal e −1 nas posições vizinhas).")

H1("28. Blundell-Bond: o GMM de sistema (dúvida 9, parte 2)")
H2("O problema dos instrumentos fracos")
P("Quando a série é muito persistente (a perto de 1), y[t−2] quase não ajuda a prever Δy[t−1]: o que acontece num "
  "ano quase não se desfaz no seguinte, e a diferença fica perto de puro ruído. O instrumento fica fraco (capítulo "
  "22). Simulação com 100 unidades × 7 anos, 200 repetições para cada a:")
lin = [["a verdadeiro", "correlação de y[t−2] com Δy[t−1]", "Anderson-Hsiao: metade central",
        "Sistema: metade central"]]
for a in (0.2, 0.5, 0.8, 0.95):
    rng = np.random.default_rng(2)
    cors, ah, sy = [], [], []
    for _ in range(200):
        y = painel_sim(100, 7, a, rng)
        d_ = np.diff(y, axis=1)
        z, x, yy = y[:, :-2].ravel(), d_[:, :-1].ravel(), d_[:, 1:].ravel()
        cors.append(np.corrcoef(z, x)[0, 1])
        ah.append((z @ yy) / (z @ x))
        sy.append(gmm.system_gmm(y, [], ["L", "C"])["coef"][0])
    lin.append([br(a, 2), br(np.mean(cors), 3), faixa(ah), faixa(sy)])
T(lin, [2.6, 4.6, 4.6, 4.6])
H2("A solução: acrescentar as equações em nível")
P("<b>Blundell e Bond (1998)</b> acrescentam as equações <b>em nível</b> (a original, com η) e usam como instrumento "
  "a <b>diferença</b> defasada Δy[t−1]:")
F("""y[t] = a × y[t−1] + constante + (η + e[t])          instrumento: Δy[t−1]""")
L("<b>Relevância</b>: Δy[t−1] é forte para y[t−1] mesmo quando a é perto de 1.",
  "<b>Validade</b>: Δy[t−1] não pode ter relação com η + e[t]. Com e sem memória, a parte com e[t] está ok. A parte "
  "com η exige uma condição sobre o começo da série: cada unidade já oscila em torno do seu próprio nível de longo "
  "prazo, sem uma tendência de aproximação que dependa de η. (O nível de longo prazo L é o valor que se repete "
  "quando não há choques: L = a × L + η, ou seja, L = η/(1 − a).) Assim, as <b>variações</b> de y não revelam "
  "o η da unidade.")
P("As equações em diferença (Arellano-Bond) e em nível são estimadas juntas, com todas as condições de momento num "
  "único GMM: é o <b>GMM de sistema</b>. Na tabela acima, quando a é alto, sua metade central fica bem mais "
  "estreita que a do Anderson-Hsiao; nestas amostras ela também fica um pouco acima do valor verdadeiro.")

H1("29. Os testes AR(1) e AR(2) de Arellano-Bond (dúvida 11, parte 2)")
H2("Para que servem")
P("Toda a validade dos instrumentos defasados depende de <b>e não ter memória</b> (capítulo 27). Se e tivesse "
  "memória — por exemplo e[t] = ρ e[t−1] + v[t] —, y[t−2] (que contém e[t−2]) estaria correlacionado com e[t−1], que "
  "está em Δe[t]: o instrumento seria inválido. Os testes verificam isso <b>nos resíduos</b> da equação em diferença.")
H2("O que se espera de cada um")
L("<b>AR(1)</b>: testa a correlação entre Δê[t] e Δê[t−1]. Pelo capítulo 26, ela é −0,5 <b>mesmo quando tudo está "
  "certo</b>. Por isso o esperado é rejeitar H0 (p-valor pequeno). Rejeitar o AR(1) não indica problema.",
  "<b>AR(2)</b>: testa a correlação entre Δê[t] e Δê[t−2]. Se e não tem memória, ela é zero (capítulo 26). H0: "
  "\"não há autocorrelação de ordem 2\". <b>p-valor grande</b> → não se rejeita → os instrumentos y[t−2], y[t−3], … "
  "são aceitáveis. p-valor pequeno → sinal de que e tem memória e os instrumentos estão comprometidos.")
H2("Como a estatística é montada")
F("""1. Calcula-se o resíduo em diferença de cada unidade e ano: Δê[i, t]
2. Soma-se o produto com o resíduo de m anos antes:    P = SOMA( Δê[i, t] × Δê[i, t−m] )
   (m = 1 para AR(1), m = 2 para AR(2); soma sobre unidades e anos)
3. Sob H0 (\"correlação de ordem m é zero\"), P tem média zero. Estima-se o desvio-padrão
   de P (levando em conta que os resíduos vêm de uma estimativa) e padroniza-se:
   z = P / desvio-padrão(P)  ~ normal padrão sob H0
4. p-valor = 2 × (1 − Normal(|z|))          (teste z, capítulo 16)""")
H2("Simulação: com e sem memória nos erros")
lin = [["Cenário (200 amostras, 100 unidades × 7 anos, a = 0,5)", "AR(1) rejeita", "AR(2) rejeita",
        "Hansen rejeita", "média de â"]]
for rho in (0.0, 0.5):
    rng = np.random.default_rng(5)
    ar1, ar2, es, hp = [], [], [], []
    for _ in range(200):
        y = painel_sim(100, 7, 0.5, rng, rho)
        r_ = gmm.system_gmm(y, [], ["L", "C"])
        ar1.append(r_["AR1"] < 0.05)
        ar2.append(r_["AR2"] < 0.05)
        es.append(r_["coef"][0])
        hp.append(r_["hansen_p"] < 0.05)
    nome = "erros sem memória (ρ = 0): tudo válido" if rho == 0 else "erros com memória (ρ = 0,5): inválido"
    lin.append([nome, br(np.mean(ar1) * 100, 0) + "%", br(np.mean(ar2) * 100, 0) + "%",
                br(np.mean(hp) * 100, 0) + "%", br(np.mean(es), 3)])
T(lin, [6.6, 2.4, 2.4, 2.4, 2.6])
P("Leitura: o AR(1) rejeita sempre, nos dois cenários — como previsto, ele não distingue nada. O AR(2) rejeita perto "
  "de 5% quando tudo está certo e rejeita muito mais quando os erros têm memória; nesse caso a estimativa de a fica "
  "muito longe de 0,5, e o Hansen (capítulo 24) também acusa o problema.")

H1("30. A correção de Windmeijer (dúvida 10)")
H2("O problema")
P("No GMM em dois passos (capítulo 23), a matriz de pesos W2 do passo 2 é calculada com os resíduos do passo 1 — é, "
  "ela mesma, uma <b>estimativa</b>, com sua própria oscilação de amostra para amostra. A fórmula usual do erro-padrão "
  "do passo 2 trata W2 como se fosse conhecida de antemão e ignora essa oscilação extra. Em amostras pequenas, e "
  "principalmente com muitos instrumentos (como no GMM de sistema), o resultado é um erro-padrão <b>pequeno demais</b>: "
  "os coeficientes parecem mais precisos — e os testes z mais significativos — do que são.")
H2("A correção")
P("Windmeijer (2005) calculou quanto b_est2 muda quando os resíduos do passo 1 (e, portanto, W2) mudam um pouco — uma "
  "medida de <b>sensibilidade</b>, a matriz D — e somou à variância o efeito dessa oscilação:")
F("""V_corrigida = V2 + D @ V2 + V2 @ D' + D @ V1r @ D'
   V2  = variância usual do passo 2 (a que ignora a oscilação de W2)
   V1r = variância robusta do passo 1 (quanto os resultados do passo 1 oscilam)
   D   = sensibilidade de b_est2 aos resultados do passo 1
Os termos extras levam a oscilação do passo 1, através de D, para o passo 2.""")
H2("Simulação: o erro-padrão deveria medir a oscilação real")
P("Pelo capítulo 14, o erro-padrão é uma estimativa do <b>desvio-padrão da distribuição amostral</b>. Numa "
  "simulação dá para medir esse desvio diretamente — gerando muitas amostras e vendo quanto â varia — e comparar com o "
  "que cada fórmula de erro-padrão diz, em média:")
lin = [["300 amostras, 7 anos, a = 0,5", "desvio-padrão real de â", "ep médio sem correção",
        "ep médio com Windmeijer", "média de â"]]
for N_ in (42, 100):
    rng = np.random.default_rng(11)
    est, es_, ec_ = [], [], []
    for _ in range(300):
        y = painel_sim(N_, 7, 0.5, rng)
        r_ = gmm.system_gmm(y, [], ["L", "C"])
        est.append(r_["coef"][0])
        ec_.append(r_["ep"][0])
        es_.append(ep_sem_correcao(y))
    lin.append([f"{N_} unidades", br(np.std(est), 3), br(np.mean(es_), 3), br(np.mean(ec_), 3), br(np.mean(est), 3)])
T(lin, [3.8, 3.2, 3.2, 3.4, 2.8])
P("Leitura: sem a correção, o erro-padrão diz menos da metade da oscilação real com 42 unidades; com a correção, "
  "fica perto do valor real. Com mais unidades a diferença diminui. A coluna da média mostra um outro efeito de "
  "amostra pequena: com 42 unidades a própria estimativa fica, em média, acima de 0,5 — a correção de Windmeijer não "
  "trata isso; ela corrige só o erro-padrão.")

story.append(PageBreak())
story.append(Paragraph("Glossário", S["h1"]))
GL = [
    ("@", "Multiplicação de matrizes em Python/numpy (cap. 2)."),
    ("Autocorrelação de ordem k", "Correlação de uma série com ela mesma k períodos antes (cap. 26)."),
    ("AR(1) — modelo", "Erro com memória: e[t] = ρ e[t−1] + v[t] (cap. 26)."),
    ("AR(1), AR(2) — testes", "Testes z da autocorrelação de ordem 1 e 2 dos resíduos em diferença (cap. 29)."),
    ("Base / básicas", "No simplex, as variáveis calculadas pelas equações num vértice (cap. 6)."),
    ("Binv", "Inversa da matriz das colunas básicas (cap. 4 e 9)."),
    ("Ciclagem", "Simplex voltando sempre às mesmas bases (cap. 7)."),
    ("Condição de momento", "Afirmação de que um valor esperado é zero (cap. 23)."),
    ("Consistente", "Estimador que se concentra no valor verdadeiro quando a amostra cresce (cap. 14)."),
    ("Covariância / correlação", "Medidas de quanto duas variáveis andam juntas (cap. 13)."),
    ("CRS / VRS", "Retornos constantes / variáveis de escala; VRS = SOMA(λ) = 1 (cap. 10)."),
    ("Custo reduzido", "Quanto o objetivo muda por unidade de uma não básica (cap. 6)."),
    ("Degeneração", "Base com uma básica igual a zero; pivô de passo zero (cap. 6)."),
    ("Descarte fraco", "O produto ruim só se reduz junto com o bom (cap. 12)."),
    ("Determinante 2×2", "ad − bc; zero = matriz singular (cap. 4)."),
    ("Efeito fixo", "Parte constante e própria de cada unidade num painel (cap. 25)."),
    ("Eficiente (estimador)", "O de menor variância dentro de uma classe (cap. 23)."),
    ("Endógeno / exógeno", "Correlacionado / não correlacionado com o erro (cap. 21)."),
    ("Erro / resíduo", "Parte não explicada na população / na amostra (cap. 18)."),
    ("Erro tipo I / II", "Rejeitar H0 verdadeira / não rejeitar H0 falsa (cap. 16)."),
    ("Erro-padrão (ep)", "Desvio-padrão da distribuição amostral de uma estimativa (cap. 14)."),
    ("Estimador / estimativa", "Receita de cálculo / número que ela produz numa amostra (cap. 14)."),
    ("Graus de liberdade", "Quantas informações independentes sobram (cap. 13 e 17)."),
    ("Heterocedasticidade", "Erros com variâncias diferentes entre observações (cap. 19)."),
    ("Instrumento", "Variável relevante (ligada a x) e válida (não ligada ao erro) (cap. 22)."),
    ("Instrumento fraco", "Instrumento pouco correlacionado com x (cap. 22)."),
    ("Matriz de pesos W", "Quanto cada condição de momento pesa no GMM (cap. 23)."),
    ("Matriz de variância-covariância", "Variâncias (diagonal) e covariâncias das estimativas (cap. 20)."),
    ("Normal padrão", "Sino com média 0 e desvio 1 (cap. 15)."),
    ("p-valor", "Probabilidade, sob H0, de um resultado tão extremo quanto o observado (cap. 16)."),
    ("Pivotar", "Pivô vira 1 e zera-se o resto da coluna (cap. 3)."),
    ("Preço-sombra", "Ganho no objetivo por unidade a mais no lado direito de uma restrição (cap. 6)."),
    ("Qui-quadrado χ²(k)", "Soma de k normais padrão ao quadrado (cap. 17)."),
    ("Sobreidentificado", "Mais condições de momento que parâmetros (cap. 23)."),
    ("Teorema central do limite", "Médias de muitas variáveis independentes ficam aproximadamente normais (cap. 15)."),
    ("Valor esperado E[X]", "Média teórica de uma variável aleatória (cap. 13)."),
    ("Viés", "Diferença entre o valor esperado da estimativa e o valor verdadeiro (cap. 14)."),
    ("Viés de Nickell", "Viés do estimador within em painéis dinâmicos curtos (cap. 25)."),
    ("Wald", "Teste de vários coeficientes ao mesmo tempo: b' @ V^(−1) @ b (cap. 20)."),
]
T([["Termo", "Significado"]] + [[a, b] for a, b in GL], [4.6, 11.8])


class Doc(SimpleDocTemplate):
    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name in ("h1", "h2"):
            nivel = 0 if fl.style.name == "h1" else 1
            texto = fl.getPlainText()
            chave = f"h{id(fl)}"
            self.canv.bookmarkPage(chave)
            self.canv.addOutlineEntry(texto, chave, level=nivel, closed=nivel > 0)
            self.notify("TOCEntry", (nivel, texto, self.page, chave))


def rodape(canv, doc):
    canv.saveState()
    canv.setFont("Arial", 8)
    canv.setFillColor(colors.HexColor("#7F7F7F"))
    if doc.page > 1:
        canv.drawString(2.2 * cm, 1.2 * cm, "A matemática por trás do Excel — réplica de Bansal et al. (2022)")
        canv.drawRightString(A4[0] - 2.2 * cm, 1.2 * cm, f"página {doc.page}")
    canv.restoreState()


def main():
    doc = Doc(str(ARQ), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2 * cm,
              bottomMargin=2 * cm, title="A matemática por trás do Excel", author="Projeto bansal")
    doc.multiBuild(story, onFirstPage=rodape, onLaterPages=rodape)
    print("Guia gravado em", ARQ)


if __name__ == "__main__":
    main()
