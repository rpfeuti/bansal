"""Gera docs/guia_excel_bansal.pdf: guia detalhado para entender o Excel do projeto.

Rodar da raiz:  $env:PYTHONPATH="src"; python docs/gerar_guia.py

Todos os números do guia são calculados aqui, com o próprio motor (src/bansal), a partir de
data/padronizada/painel.xlsx e data/saida/. Nada é gravado fora de docs/.
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd
from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer,
                                Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from bansal import indices, li_test, models, simplex
from bansal.calcular import GMM_XS, _matriz
from bansal.gmm import system_gmm
from bansal.painel import carregar
from bansal.simplex import maximizar

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "data" / "saida"
PAD = RAIZ / "data" / "padronizada" / "painel.xlsx"
ARQ = RAIZ / "docs" / "guia_excel_bansal.pdf"

# ------------------------------------------------------------------ fontes e estilos
FONTES = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Arial", str(FONTES / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Arial-B", str(FONTES / "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Arial-I", str(FONTES / "ariali.ttf")))
pdfmetrics.registerFont(TTFont("Arial-BI", str(FONTES / "arialbi.ttf")))
pdfmetrics.registerFont(TTFont("Consolas", str(FONTES / "consola.ttf")))
pdfmetrics.registerFont(TTFont("Consolas-B", str(FONTES / "consolab.ttf")))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-B", italic="Arial-I", boldItalic="Arial-BI")
pdfmetrics.registerFontFamily("Consolas", normal="Consolas", bold="Consolas-B", italic="Consolas",
                              boldItalic="Consolas-B")

AZUL = colors.HexColor("#1F4E79")
AZUL_CLARO = colors.HexColor("#DDEBF7")
CINZA = colors.HexColor("#F2F2F2")
VERDE = colors.HexColor("#E2EFDA")
AMARELO = colors.HexColor("#FFF2CC")
LARANJA = colors.HexColor("#FCE4D6")

S = {
    "titulo": ParagraphStyle("titulo", fontName="Arial-B", fontSize=26, leading=32, textColor=AZUL,
                             alignment=TA_CENTER, spaceAfter=14),
    "subtitulo": ParagraphStyle("subtitulo", fontName="Arial", fontSize=13, leading=18, alignment=TA_CENTER,
                                textColor=colors.HexColor("#404040")),
    "h1": ParagraphStyle("h1", fontName="Arial-B", fontSize=18, leading=23, textColor=AZUL, spaceBefore=6,
                         spaceAfter=10),
    "h1sum": ParagraphStyle("h1sum", fontName="Arial-B", fontSize=18, leading=23, textColor=AZUL, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName="Arial-B", fontSize=13.5, leading=18, textColor=AZUL, spaceBefore=12,
                         spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName="Arial-B", fontSize=11, leading=15, spaceBefore=8, spaceAfter=4),
    "p": ParagraphStyle("p", fontName="Arial", fontSize=10, leading=14.2, alignment=TA_JUSTIFY, spaceAfter=6),
    "item": ParagraphStyle("item", fontName="Arial", fontSize=10, leading=14, leftIndent=14, bulletIndent=3,
                           spaceAfter=2),
    "caixa": ParagraphStyle("caixa", fontName="Arial", fontSize=9.6, leading=13.4),
    "form": ParagraphStyle("form", fontName="Consolas", fontSize=9, leading=12.4),
    "cel": ParagraphStyle("cel", fontName="Arial", fontSize=8.6, leading=11),
    "celc": ParagraphStyle("celc", fontName="Consolas", fontSize=8.2, leading=10.4),
    "legenda": ParagraphStyle("legenda", fontName="Arial-I", fontSize=8.8, leading=12, alignment=TA_CENTER,
                              textColor=colors.HexColor("#404040"), spaceAfter=8),
    "toc1": ParagraphStyle("toc1", fontName="Arial-B", fontSize=10.5, leading=15, leftIndent=0),
    "toc2": ParagraphStyle("toc2", fontName="Arial", fontSize=9.5, leading=13, leftIndent=16),
}


def br(x, d=3):
    """Número no formato brasileiro (vírgula decimal, ponto de milhar)."""
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "—"
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


story = []


def H1(t):
    story.append(CondPageBreak(9 * cm))
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


def N(*itens, start=1):
    for k, t in enumerate(itens, start):
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
    """Caixa de fórmula / código (texto pré-formatado)."""
    _caixa(Preformatted(texto.strip("\n"), S["form"]), CINZA, colors.HexColor("#BFBFBF"))


def EXCEL(texto, titulo="No Excel"):
    _caixa(Paragraph(f"<b>{titulo}:</b> {texto}", S["caixa"]), VERDE, colors.HexColor("#A9D18E"))


def IDEIA(texto, titulo="Em uma frase"):
    _caixa(Paragraph(f"<b>{titulo}:</b> {texto}", S["caixa"]), AMARELO, colors.HexColor("#FFD966"))


def T(linhas, larguras, cabecalho=True, mono=False, alinhar_dir=()):
    est = S["celc"] if mono else S["cel"]
    dados = [[c if not isinstance(c, str) else Paragraph(c, est) for c in lin] for lin in linhas]
    t = Table(dados, colWidths=[w * cm for w in larguras], repeatRows=1 if cabecalho else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFBFBF")),
          ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
          ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if cabecalho:
        st.append(("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO))
    t.setStyle(TableStyle(st))
    story.append(t)
    story.append(Spacer(1, 8))


def LEG(t):
    story.append(Paragraph(t, S["legenda"]))


# ------------------------------------------------------------------ desenhos

def seta(d, x1, y1, x2, y2, cor=colors.black, larg=1.0):
    d.add(Line(x1, y1, x2, y2, strokeColor=cor, strokeWidth=larg))
    ang = math.atan2(y2 - y1, x2 - x1)
    a, b = ang + 2.7, ang - 2.7
    d.add(Polygon([x2, y2, x2 + 7 * math.cos(a), y2 + 7 * math.sin(a), x2 + 7 * math.cos(b), y2 + 7 * math.sin(b)],
                  fillColor=cor, strokeColor=cor))


def figura_fronteira(pontos, fronteira, projecao=None, eixo_x="insumo (funcionários)", eixo_y="produto (empréstimos)",
                     pontos2=None, fronteira2=None, rot2=None, rot1=None):
    esc, ox, oy = 26, 40, 30
    d = Drawing(330, 290)
    d.add(Line(ox, oy, ox + 10 * esc, oy))
    d.add(Line(ox, oy, ox, oy + 9.5 * esc))
    for k in range(0, 11, 2):
        d.add(String(ox + k * esc - 3, oy - 12, str(k), fontName="Arial", fontSize=8))
    for k in range(0, 10, 2):
        d.add(String(ox - 14, oy + k * esc - 3, str(k), fontName="Arial", fontSize=8))
    d.add(String(ox + 3.2 * esc, oy - 25, eixo_x, fontName="Arial", fontSize=8.5))
    d.add(String(ox - 30, oy + 9.7 * esc, eixo_y, fontName="Arial", fontSize=8.5))

    def linha(pts, cor, tracejado=None):
        xy = []
        for x, y in pts:
            xy += [ox + x * esc, oy + y * esc]
        d.add(PolyLine(xy, strokeColor=cor, strokeWidth=1.6, strokeDashArray=tracejado))

    linha(fronteira, AZUL)
    if fronteira2:
        linha(fronteira2, colors.HexColor("#C55A11"), [4, 3])
    for nome, x, y in pontos:
        d.add(Circle(ox + x * esc, oy + y * esc, 3.5, fillColor=AZUL, strokeColor=AZUL))
        d.add(String(ox + x * esc + 5, oy + y * esc + 4, nome, fontName="Arial-B", fontSize=9))
    for nome, x, y in pontos2 or []:
        d.add(Circle(ox + x * esc, oy + y * esc, 3.5, fillColor=colors.HexColor("#C55A11"),
                     strokeColor=colors.HexColor("#C55A11")))
        d.add(String(ox + x * esc + 5, oy + y * esc - 10, nome, fontName="Arial-B", fontSize=9,
                     fillColor=colors.HexColor("#C55A11")))
    if projecao:
        (x1, y1), (x2, y2) = projecao
        seta(d, ox + x1 * esc, oy + y1 * esc, ox + x2 * esc, oy + y2 * esc, colors.HexColor("#C00000"))
    if rot1:
        d.add(String(ox + 6.2 * esc, oy + 1.6 * esc, rot1, fontName="Arial", fontSize=8, fillColor=AZUL))
    if rot2:
        d.add(String(ox + 6.2 * esc, oy + 1.0 * esc, rot2, fontName="Arial", fontSize=8,
                     fillColor=colors.HexColor("#C55A11")))
    story.append(d)


def figura_rede():
    d = Drawing(470, 270)
    caixas = [("Divisão 1", "captação de depósitos", 20), ("Divisão 2", "concessão de crédito", 180),
              ("Divisão 3", "geração de receita", 340)]
    for t, s, x in caixas:
        d.add(Rect(x, 105, 110, 55, fillColor=AZUL_CLARO, strokeColor=AZUL, strokeWidth=1.2))
        d.add(String(x + 55, 138, t, fontName="Arial-B", fontSize=10, textAnchor="middle"))
        d.add(String(x + 55, 122, s, fontName="Arial", fontSize=8, textAnchor="middle"))
    seta(d, 130, 140, 180, 140)
    d.add(String(155, 146, "depósitos", fontName="Arial", fontSize=7.5, textAnchor="middle"))
    seta(d, 290, 145, 340, 145)
    seta(d, 290, 125, 340, 125)
    d.add(String(315, 151, "empréstimos", fontName="Arial", fontSize=7, textAnchor="middle"))
    d.add(String(315, 129, "investimentos", fontName="Arial", fontSize=7, textAnchor="middle"))
    # insumos
    seta(d, 50, 215, 50, 160)
    d.add(String(50, 220, "labor, fixed assets", fontName="Arial", fontSize=7.5, textAnchor="middle"))
    seta(d, 100, 200, 100, 160, colors.HexColor("#7F6000"))
    d.add(String(100, 204, "equity (quase-fixo)", fontName="Arial", fontSize=7.5, textAnchor="middle",
                 fillColor=colors.HexColor("#7F6000")))
    seta(d, 205, 215, 205, 160)
    d.add(String(205, 220, "borrowings", fontName="Arial", fontSize=7.5, textAnchor="middle"))
    seta(d, 265, 215, 265, 160, colors.HexColor("#C00000"))
    d.add(String(265, 228, "NPL de t−1", fontName="Arial", fontSize=7.5, textAnchor="middle",
                 fillColor=colors.HexColor("#C00000")))
    d.add(String(265, 219, "(insumo indesejável)", fontName="Arial", fontSize=6.8, textAnchor="middle",
                 fillColor=colors.HexColor("#C00000")))
    seta(d, 395, 215, 395, 160)
    d.add(String(395, 220, "provision", fontName="Arial", fontSize=7.5, textAnchor="middle"))
    # saídas
    seta(d, 395, 105, 395, 55)
    d.add(String(395, 44, "net interest income", fontName="Arial", fontSize=7.5, textAnchor="middle"))
    d.add(String(395, 34, "non-interest income", fontName="Arial", fontSize=7.5, textAnchor="middle"))
    seta(d, 265, 105, 265, 55, colors.HexColor("#C00000"))
    d.add(String(265, 44, "NPL de t", fontName="Arial", fontSize=7.5, textAnchor="middle",
                 fillColor=colors.HexColor("#C00000")))
    d.add(String(265, 34, "(produto indesejável)", fontName="Arial", fontSize=6.8, textAnchor="middle",
                 fillColor=colors.HexColor("#C00000")))
    # carryovers
    seta(d, 150, 80, 200, 105, colors.HexColor("#548235"))
    d.add(String(120, 70, "carryovers de t−1:", fontName="Arial", fontSize=7.5, textAnchor="middle",
                 fillColor=colors.HexColor("#548235")))
    d.add(String(120, 61, "unused assets, net profit", fontName="Arial", fontSize=7.5, textAnchor="middle",
                 fillColor=colors.HexColor("#548235")))
    seta(d, 220, 105, 175, 25, colors.HexColor("#548235"))
    d.add(String(130, 14, "carryovers de t (vão para t+1)", fontName="Arial", fontSize=7.5, textAnchor="middle",
                 fillColor=colors.HexColor("#548235")))
    story.append(d)


# ------------------------------------------------------------------ cálculos usados no texto

PAINEL, COV, META = carregar()
IDS, NOMES = META["ids"], META["nomes"]
NB = len(IDS)
xl = pd.ExcelFile(PAD)
NOM = xl.parse("nominal")
DEFL = xl.parse("deflator")
DET = pd.read_excel(SAIDA / "indices_detalhe.xlsx")
T3 = pd.read_excel(SAIDA / "tabela3.xlsx", dtype={"ano": str})
T4 = pd.read_excel(SAIDA / "tabela4.xlsx")
T6 = pd.read_excel(SAIDA / "tabela6.xlsx")
LI = pd.read_excel(SAIDA / "tabela3_li.xlsx")


def lp_com_x(F, E, o, modelo="M1"):
    """Roda a LP do pacote e devolve (beta, x)."""
    guardado = {}
    original = models.maximizar

    def captura(*a, **k):
        v, x = original(*a, **k)
        guardado["x"] = x
        return v, x

    models.maximizar = captura
    try:
        if modelo == "M1":
            b = models.ddf_rede(PAINEL, [F], E, o, models.direcoes_m1(PAINEL, F))
        else:
            b = models.ddf_caixa_preta(PAINEL, [F], E, o)
    finally:
        models.maximizar = original
    return b, guardado["x"]


def dea_brinquedo(X, Y, o, mu=0.0, nu=0.0):
    n = len(X)
    A = np.zeros((2, n + 1))
    A[0, :n], A[0, n] = X, X[o] + mu
    A[1, :n], A[1, n] = -np.asarray(Y), Y[o] - nu
    eq = np.zeros((1, n + 1))
    eq[0, :n] = 1
    c = np.zeros(n + 1)
    c[n] = 1
    return maximizar(c, A, [X[o], -Y[o]], eq, [1], livres=[n])


# ------------------------------------------------------------------ CAPA E SUMÁRIO

story.append(Spacer(1, 4 * cm))
story.append(Paragraph("Entendendo o Excel da réplica de Bansal et al. (2022)", S["titulo"]))
story.append(Paragraph("Produtividade de bancos indianos com DEA dinâmico em rede:<br/>"
                       "teoria, exemplos numéricos, o simplex do projeto e o mapa da planilha", S["subtitulo"]))
story.append(Spacer(1, 1.2 * cm))
story.append(Paragraph("Bansal, Kumar, Mehra &amp; Gulati (2022), <i>Omega</i> 107, 102538", S["subtitulo"]))
story.append(Spacer(1, 5 * cm))
story.append(Paragraph("Arquivos explicados: <b>excel/motor_bansal.xlsx</b> (o motor rodando no Excel) e "
                       "<b>data/saida/planilha_passo_a_passo.xlsx</b> (as contas em fórmulas).", S["subtitulo"]))
story.append(Spacer(1, 0.4 * cm))
story.append(Paragraph("Todos os números deste guia foram calculados pelo próprio motor do projeto (src/bansal).",
                       S["subtitulo"]))
story.append(PageBreak())
story.append(Paragraph("Sumário", S["h1sum"]))
toc = TableOfContents()
toc.levelStyles = [S["toc1"], S["toc2"]]
story.append(toc)

# ================================================================== PARTE I
story.append(PageBreak())
H1("1. Como ler este guia")
P("Este guia explica, do zero, tudo o que o Excel calcula. Ele foi escrito para quem programa, mas nunca "
  "estudou a teoria do paper. Cada conceito aparece primeiro num <b>exemplo de brinquedo</b> (poucos bancos, "
  "números redondos, conta que dá para fazer à mão) e depois no <b>exemplo real</b> do projeto, com os números "
  "que você vai encontrar na planilha.")
P("As fórmulas usam notação simples, parecida com código. Em vez de símbolos de somatório com índices, "
  "escrevemos, por exemplo:")
F("SOMA( λ[j] × labor[j] )   para j = cada um dos 42 bancos\n\n"
  "= λ[1]×labor[1] + λ[2]×labor[2] + ... + λ[42]×labor[42]\n"
  "= SUMPRODUCT(coluna λ ; coluna labor)   (no Excel)")
P("Letras gregas aparecem só como <b>nomes de variáveis</b>, sempre definidas na hora: β (beta), λ (lambda), "
  "φ (phi), μ (mi), ν (ni), ρ (rô), ω (ômega), γ (gama), α (alfa), ξ (csi), π (pi), η (eta), δ (delta). "
  "Elas são as mesmas letras do paper e do código, para você poder ir e voltar entre os três.")
H2("Os dois arquivos Excel")
T([["Arquivo", "Para que serve", "Como calcula"],
   ["excel/motor_bansal.xlsx", "Rodar a réplica inteira dentro do Excel. Você muda a base e tudo recalcula.",
    "Células =PY() executam o código Python de src/bansal (o mesmo do app)."],
   ["data/saida/planilha_passo_a_passo.xlsx", "Ver cada conta aberta em fórmulas, linha por linha.",
    "Fórmulas comuns do Excel; 5 problemas de otimização prontos para o Solver."]],
  [4.6, 6.0, 5.8])
P("O guia segue a ordem do cálculo: <b>dados → variáveis → eficiência (DEA) → índices de produtividade → "
  "tabelas → testes estatísticos</b>. Depois vem o <b>simplex</b> (o algoritmo que resolve os problemas de "
  "otimização) e, no fim, o <b>mapa do Excel</b>, aba por aba.")
H2("O que o paper mede, em linguagem simples")
P("A pergunta do paper é: <b>a produtividade dos bancos indianos cresceu entre 2010 e 2017?</b> E, se cresceu, "
  "foi porque os bancos ficaram mais eficientes (se aproximaram dos melhores) ou porque os melhores ficaram "
  "ainda melhores (a tecnologia do setor avançou)?")
P("Para responder, o paper faz três coisas:")
N("Para cada banco e cada ano, mede <b>o quanto o banco está longe dos melhores</b> do setor. Essa distância "
  "se chama <b>β</b> (beta) e sai de um problema de otimização (programação linear). β = 0 significa que o "
  "banco é um dos melhores; β = 0,10 significa, grosso modo, que ele poderia melhorar 10% de uma vez em "
  "todos os seus números.",
  "Compara essas distâncias entre dois anos seguidos e monta um <b>índice de produtividade</b>. Índice "
  "maior que 1 = produtividade subiu; menor que 1 = caiu. O índice se divide em duas partes: <b>EC</b> "
  "(o banco se aproximou dos melhores?) e <b>TC</b> (os melhores avançaram?).",
  "Usa estatística para comparar bancos públicos e privados (<b>teste de Li</b>) e para ver que "
  "características dos bancos explicam o índice (<b>GMM de sistema</b>).")
P("A novidade do paper está no item 1: em vez de tratar o banco como uma caixa-preta (entra funcionário, sai "
  "receita), ele abre o banco em <b>três divisões</b> ligadas entre si e liga também <b>um ano ao seguinte</b>. "
  "Isso é o que \"DEA dinâmico em rede\" quer dizer. O paper também calcula a versão caixa-preta, para comparar.")
IDEIA("cada número de índice do Excel é uma razão entre quatro distâncias β, e cada β é a solução de uma "
      "programação linear que compara um banco com combinações dos 42 bancos.")

# ================================================================== PARTE II: DADOS
H1("2. A base: os dados contábeis (aba base)")
P("Tudo começa na aba <b>base</b> do motor (é a aba <b>nominal</b> de data/padronizada/painel.xlsx). Ela é o "
  "resultado do trabalho de ETL: os números lidos das fontes do Reserve Bank of India (STRBI, DBIE) e do "
  "Measure, já organizados com <b>uma linha por banco e ano</b> e <b>uma coluna por item contábil</b>. São "
  f"{NB} bancos × 9 anos (2009 a 2017) = {len(NOM)} linhas. Os valores estão em <b>Rs lakh</b> "
  "(1 lakh = 100.000 rúpias) e em preços correntes, sem nenhuma conta.")
P("O ano 2009 entra só porque algumas variáveis precisam do ano anterior (NPL de t−1, carryovers de t−1). "
  "Os índices de produtividade vão de 2010→2011 até 2016→2017.")
ITENS = [
    ("adiantamentos", "Empréstimos concedidos (advances), líquidos"),
    ("agencias", "Número de agências (branches) — usado para normalizar"),
    ("ativo_fixo", "Ativo imobilizado (fixed assets)"),
    ("ativo_total", "Ativo total"),
    ("caixa_rbi", "Caixa + saldo no Reserve Bank of India (reservas obrigatórias)"),
    ("capital", "Capital social"),
    ("depositos", "Depósitos"),
    ("despesas_operacionais", "Despesas operacionais (Total IV do demonstrativo)"),
    ("empregados", "Número de empregados"),
    ("emprestimos_tomados", "Empréstimos tomados (borrowings)"),
    ("investimentos", "Investimentos (títulos)"),
    ("juros_pagos", "Juros pagos (Total III)"),
    ("juros_recebidos", "Juros recebidos (Total I)"),
    ("lucro", "Lucro líquido do ano"),
    ("npa_bruto", "Crédito problemático bruto (gross NPA) — não entra nas contas"),
    ("npa_liquido", "Crédito problemático líquido (net NPA) — é o NPL usado"),
    ("outras_receitas", "Outras receitas (Total II), receita que não é de juros"),
    ("prioritario", "Crédito ao setor prioritário"),
    ("provisoes", "Provisões e contingências"),
    ("reservas", "Reservas e lucros acumulados"),
    ("salarios", "Salários e encargos com empregados"),
]
T([["Coluna da base", "O que é"]] + [[f"<font name='Consolas'>{a}</font>", b] for a, b in ITENS], [4.6, 11.8])
P("A escolha de usar o NPA <b>líquido</b> como NPL é uma decisão registrada em ROTEIRO_EXTRACAO.md.")
s9 = NOM[(NOM.bank_id == "SBI") & (NOM.ano == 2009)].iloc[0]
s10 = NOM[(NOM.bank_id == "SBI") & (NOM.ano == 2010)].iloc[0]
EXCEL("aba <b>base</b>, células amarelas. A primeira linha de dados é o State Bank of India (SBI) em 2009: "
      f"adiantamentos = {br(s9.adiantamentos, 0)}, depósitos = {br(s9.depositos, 0)}, empregados = "
      f"{br(s9.empregados, 0)}, agências = {br(s9.agencias, 0)}. A aba <b>deflator</b> tem o índice de preços de "
      "cada ano.")

H1("3. Das contas às 13 variáveis do paper")
P("O paper (Tabela 1) usa 13 variáveis. Cada uma sai de uma conta simples com os itens da base. O código "
  "está em <font name='Consolas'>padronizar.variaveis</font>:")
F("""labor               = empregados
fixed_assets        = ativo_fixo
equity              = capital + reservas
deposits            = depositos
borrowings          = emprestimos_tomados
npl                 = npa_liquido
unused_assets       = ativo_total − caixa_rbi − ativo_fixo − adiantamentos − investimentos
net_profit          = lucro
performing_loans    = adiantamentos − npa_liquido
investments         = investimentos
provision           = provisoes
net_interest_income = juros_recebidos − juros_pagos
non_interest_income = outras_receitas""")
P("Três delas merecem explicação:")
L("<b>unused_assets</b> (ativos não usados): o que sobra do ativo total depois de tirar caixa/reservas, imóveis, "
  "empréstimos e investimentos. O paper segue Fukuyama e Weber: são recursos parados.",
  "<b>performing_loans</b> (empréstimos bons): empréstimos totais menos os problemáticos.",
  "<b>net_interest_income</b> (margem de juros): juros recebidos menos juros pagos.")
H2("Exemplo real: SBI em 2009 (valores nominais, Rs lakh)")
v = {
    "equity": s9.capital + s9.reservas,
    "unused_assets": s9.ativo_total - s9.caixa_rbi - s9.ativo_fixo - s9.adiantamentos - s9.investimentos,
    "performing_loans": s9.adiantamentos - s9.npa_liquido,
    "net_interest_income": s9.juros_recebidos - s9.juros_pagos,
}
T([["Variável", "Conta com os números do SBI 2009", "Resultado"],
   ["equity", f"{br(s9.capital, 0)} + {br(s9.reservas, 0)}", br(v["equity"], 0)],
   ["unused_assets", f"{br(s9.ativo_total, 0)} − {br(s9.caixa_rbi, 0)} − {br(s9.ativo_fixo, 0)} − "
                     f"{br(s9.adiantamentos, 0)} − {br(s9.investimentos, 0)}", br(v["unused_assets"], 0)],
   ["performing_loans", f"{br(s9.adiantamentos, 0)} − {br(s9.npa_liquido, 0)}", br(v["performing_loans"], 0)],
   ["net_interest_income", f"{br(s9.juros_recebidos, 1)} − {br(s9.juros_pagos, 1)}",
    br(v["net_interest_income"], 1)]],
  [3.6, 9.6, 3.2])

H2("Deflacionar e dividir por agência")
P("O paper (seção 4.2) faz mais dois ajustes antes de comparar os bancos:")
N("<b>Deflacionar</b>: dividir os valores em dinheiro pelo índice de preços do ano (deflator implícito, base "
  "2011-12 = 100). Assim um valor de 2009 e um de 2017 ficam na mesma moeda (preços de 2011-12). "
  "<b>labor</b> não é dinheiro e não é deflacionado.",
  "<b>Dividir pelo número de agências</b> (Denizer et al.): todas as 13 variáveis, inclusive labor. "
  "Assim um banco gigante e um pequeno ficam comparáveis: o que se compara é \"por agência\".")
d09 = float(DEFL[DEFL.ano == 2009].iloc[0, 1])
F(f"""valor_no_painel = valor_nominal / (deflator_do_ano / 100) / agencias
labor_no_painel = empregados / agencias

SBI 2009:  deflator = {br(d09, 3)}  →  fator = {br(d09 / 100, 5)}     agências = {br(s9.agencias, 0)}

performing_loans = {br(v['performing_loans'], 0)} / {br(d09 / 100, 5)} / {br(s9.agencias, 0)} = {br(v['performing_loans'] / (d09 / 100) / s9.agencias, 3)}
labor            = {br(s9.empregados, 0)} / {br(s9.agencias, 0)} = {br(s9.empregados / s9.agencias, 3)} empregados por agência""")
P(f"Confira na aba <b>r_painel</b>: SBI 2009 tem performing_loans = {br(PAINEL[2009]['performing_loans'][0], 3)} "
  f"e labor = {br(PAINEL[2009]['labor'][0], 3)}. Esses são os números que entram nos modelos.")
EXCEL("o motor faz isso em <font name='Consolas'>padronizar.painel_de_nominal(NOM, DEFL)</font>, chamado na "
      "célula A3 da aba <b>r_painel</b>. Na planilha passo a passo, as mesmas contas estão abertas nas abas "
      "<b>2_Variaveis</b> (contas) e <b>3_Painel</b> (deflator e agências), com fórmulas comuns.")

H1("4. As covariáveis (variáveis explicativas do GMM)")
P("Além das 13 variáveis, o paper usa 8 <b>covariáveis</b> na última etapa (a regressão GMM da Tabela 6), "
  "para ver o que explica a produtividade. Elas são calculadas com os valores <b>nominais</b> (sem dividir por "
  "agência). Código: <font name='Consolas'>padronizar.covariaveis</font>.")
npl9 = s9.npa_liquido
npl10 = s10.npa_liquido
nii10 = s10.juros_recebidos - s10.juros_pagos
non10 = s10.outras_receitas
d10 = float(DEFL[DEFL.ano == 2010].iloc[0, 1])
T([["Covariável", "Conta", "SBI 2010"],
   ["G_NPLs", "(NPL do ano − NPL do ano anterior) / NPL do ano anterior",
    f"({br(npl10, 0)} − {br(npl9, 0)}) / {br(npl9, 0)} = {br((npl10 - npl9) / npl9, 4)}"],
   ["SIZE", "ln( ativo_total / (deflator/100) )", f"ln({br(s10.ativo_total, 0)} / {br(d10 / 100, 4)}) = "
                                                   f"{br(math.log(s10.ativo_total / (d10 / 100)), 4)}"],
   ["IC", "despesas_operacionais / ativo_total", br(s10.despesas_operacionais / s10.ativo_total, 4)],
   ["EQTA", "(capital + reservas) / ativo_total", br((s10.capital + s10.reservas) / s10.ativo_total, 4)],
   ["LIQUIDITY", "adiantamentos / depositos", br(s10.adiantamentos / s10.depositos, 4)],
   ["BME", "salarios / despesas_operacionais", br(s10.salarios / s10.despesas_operacionais, 4)],
   ["PRIORITY", "prioritario / ativo_total", br(s10.prioritario / s10.ativo_total, 4)],
   ["DIVERSIFICATION", "1 − (NII/(NII+NonII))² − (NonII/(NII+NonII))²",
    f"1 − ({br(nii10 / (nii10 + non10), 4)})² − ({br(non10 / (nii10 + non10), 4)})² = "
    f"{br(1 - (nii10 / (nii10 + non10)) ** 2 - (non10 / (nii10 + non10)) ** 2, 4)}"]],
  [3.0, 6.6, 6.8])
P("NII = net interest income, NonII = non-interest income. DIVERSIFICATION é um índice de concentração "
  "invertido: vale 0 se toda a receita vem de uma fonte só e 0,5 se vem metade de cada.")
P("G_NPLs fica vazio em 2009 (não há ano anterior) e quando o NPL do ano anterior é zero (divisão por zero). "
  "Essas observações não entram no GMM.")
EXCEL("aba <b>r_covariaveis</b> (motor) e <b>4_Covariaveis</b> (passo a passo, com as fórmulas visíveis).")

# ================================================================== PARTE III: DEA
H1("5. Eficiência e fronteira: o DEA em um exemplo de brinquedo")
P("DEA (Data Envelopment Analysis, análise envoltória de dados) responde: <b>dado o que os outros bancos "
  "conseguem fazer, quanto este banco poderia melhorar?</b> Não há fórmula de \"banco ideal\": o padrão de "
  "comparação são os próprios bancos observados e as <b>misturas</b> deles.")
H2("Quatro bancos, um insumo, um produto")
TOY = {"A": (2, 2), "B": (4, 6), "C": (8, 8), "D": (6, 4)}
T([["Banco", "Insumo: funcionários", "Produto: empréstimos"]] +
  [[k, str(a), str(b)] for k, (a, b) in TOY.items()], [3, 5, 5])
P("Olhando a tabela: D usa 6 funcionários e produz 4. B usa <b>menos</b> (4) e produz <b>mais</b> (6). D está "
  "claramente atrás. Mas e A e C? A é pequeno e C é grande; nenhum dos dois domina o outro. A, B e C formam a "
  "<b>fronteira</b>: a linha dos melhores. D fica abaixo dela.")
figura_fronteira([("A", 2, 2), ("B", 4, 6), ("C", 8, 8), ("D", 6, 4)],
                 [(2, 0), (2, 2), (4, 6), (8, 8), (10, 8)], projecao=((6, 4), (3.75, 5.5)))
LEG("Figura 1. A fronteira (azul) liga A, B e C. A seta vermelha leva D até a fronteira, "
    "reduzindo funcionários e aumentando empréstimos ao mesmo tempo.")
H2("Misturas de bancos: os pesos λ")
P("A fronteira não tem só os pontos A, B e C: tem também as <b>misturas</b> deles. Uma mistura é uma média "
  "ponderada com pesos λ (lambda). Exemplo: 50% de A e 50% de B:")
F("""λA = 0,5   λB = 0,5   λC = 0   λD = 0         (os pesos somam 1)

funcionários = 0,5×2 + 0,5×4 = 3
empréstimos  = 0,5×2 + 0,5×6 = 4

→ o \"banco virtual\" (3 ; 4) é possível: fica no meio do segmento A–B.""")
P("A regra <b>\"os pesos somam 1\"</b> se chama <b>retornos variáveis de escala</b> (VRS). Ela impede comparar "
  "um banco pequeno com uma versão \"ampliada\" de um banco grande: a mistura tem que ser uma média, não uma "
  "multiplicação. O paper usa VRS em todos os modelos.")
P("O conjunto de todos os bancos virtuais possíveis (misturas, e também qualquer banco que use mais insumo "
  "ou produza menos que uma mistura) é o <b>conjunto de possibilidades de produção</b>. A fronteira é a borda "
  "de cima desse conjunto.")
H2("Medindo a distância: a função distância direcional (β)")
P("Para medir o quanto D está longe, a ideia é andar a partir de D numa <b>direção</b> escolhida: "
  "diminuindo funcionários e aumentando empréstimos ao mesmo tempo, até bater na fronteira. O tamanho do passo "
  "é β. Na versão mais simples, a direção é o próprio tamanho de D: reduzir funcionários em β×6 e aumentar "
  "empréstimos em β×4. O problema é:")
F("""maximizar  β
sujeito a:
   SOMA(λ × funcionários) ≤ 6 − β × 6      (a mistura usa no máximo o insumo reduzido)
   SOMA(λ × empréstimos)  ≥ 4 + β × 4      (a mistura produz pelo menos o produto aumentado)
   λA + λB + λC + λD = 1                   (VRS)
   todos os λ ≥ 0;  β pode ser qualquer número""")
bD, xD = dea_brinquedo([2, 4, 8, 6], [2, 6, 8, 4], 3)
P("Isso é uma <b>programação linear</b> (PL): uma função linear a maximizar, restrições lineares. "
  f"Resolvendo (com o simplex do projeto, capítulo 13): <b>β = {br(bD, 3)}</b>, com λA = {br(xD[0], 3)} e "
  f"λB = {br(xD[1], 3)}. Vamos conferir à mão:")
F(f"""funcionários da mistura = {br(xD[0], 3)}×2 + {br(xD[1], 3)}×4 = {br(xD[0] * 2 + xD[1] * 4, 3)}
limite                  = 6 − {br(bD, 3)}×6 = {br(6 - bD * 6, 3)}          (bate exatamente)

empréstimos da mistura  = {br(xD[0], 3)}×2 + {br(xD[1], 3)}×6 = {br(xD[0] * 2 + xD[1] * 6, 3)}
mínimo exigido          = 4 + {br(bD, 3)}×4 = {br(4 + bD * 4, 3)}           (bate exatamente)""")
P(f"Leitura: <b>D poderia, ao mesmo tempo, usar {br(bD * 100, 1)}% menos funcionários e produzir "
  f"{br(bD * 100, 1)}% mais empréstimos</b>, se fizesse como a mistura de A e B. Por que não um β maior? "
  "Porque com β maior o ponto alvo sairia da fronteira (ficaria acima dela), e nenhuma mistura o alcança.")
bB, _ = dea_brinquedo([2, 4, 8, 6], [2, 6, 8, 4], 1)
P(f"Para B, o mesmo problema dá β = {br(bB, 3)}: B já está na fronteira, nenhuma mistura faz melhor. "
  "<b>β = 0 significa eficiente; β > 0 mede a ineficiência.</b>")
IDEIA("β é o maior passo que se pode dar, na direção escolhida, sem sair do que os bancos observados "
      "conseguem fazer.")

H1("6. As direções do paper (μ, ν, ρ, ω, γ, α)")
P("O paper não usa a direção \"o próprio tamanho do banco\". Ele usa direções com <b>constantes</b>, porque "
  "algumas variáveis podem ser <b>negativas</b> (lucro líquido, margem de juros, provisões). Veja o problema:")
F("""Banco com lucro = −5.  Direção \"o próprio valor\": aumentar o lucro em β × (−5).
Com β = 0,1:  −5 + 0,1×(−5) = −5,5   → \"melhorar\" virou piorar!""")
P("A solução do paper (seção 3.2, seguindo Lin e Chen) é somar ou subtrair uma constante que deixa a direção "
  "sempre positiva:")
T([["Tipo de variável", "Direção usada", "Constante (paper)", "Por que fica positiva"],
   ["insumo x (labor, fixed assets, borrowings, provision)", "x_o + μ", "μ = ξ × max|x| de todos os bancos",
    "μ ≥ |x_o|, então x_o + μ ≥ 0"],
   ["produto y (net interest income, non-interest income)", "y_o − ν", "ν = min y de todos − π",
    "ν < y_o, então y_o − ν > 0"],
   ["produto indesejável u (NPL de t)", "u_o + ω", "ω = ξ × max|u|", "igual ao insumo"],
   ["insumo indesejável w (NPL de t−1)", "w_o − ρ", "ρ = min w − π", "igual ao produto"],
   ["carryover do ano (unused assets, net profit em t)", "c_o − γ", "γ = min c − π", "igual ao produto"],
   ["carryover do ano anterior (os mesmos, em t−1)", "c_o + α", "α = ξ × max|c| (em t−1)", "igual ao insumo"]],
  [4.6, 2.4, 4.4, 5.0])
P("o = banco avaliado. Os máximos e mínimos são tomados sobre os 42 bancos <b>no ano da fronteira</b>. No "
  "modelo M1 o paper usa <b>ξ = 3</b> e <b>π = 1</b> (seção 4.3.1). Para os insumos, a direção fica bem maior que "
  "o próprio valor do banco (até 4 vezes o maior valor do setor); para os produtos, fica \"valor do banco "
  "menos o menor valor do setor, mais 1\".")
H2("O brinquedo com as direções do paper")
mu, nu = 3 * 8, 2 - 1
bDp, xDp = dea_brinquedo([2, 4, 8, 6], [2, 6, 8, 4], 3, mu=mu, nu=nu)
F(f"""μ = ξ × max|funcionários| = 3 × 8 = {mu}         ν = min(empréstimos) − π = 2 − 1 = {nu}

maximizar β
   SOMA(λ × funcionários) ≤ 6 − β × (6 + {mu})  = 6 − 30β
   SOMA(λ × empréstimos)  ≥ 4 + β × (4 − {nu})   = 4 + 3β
   SOMA(λ) = 1

Solução: β = {br(bDp, 4)}   λA = {br(xDp[0], 4)}   λB = {br(xDp[1], 4)}
   funcionários: {br(xDp[0], 4)}×2 + {br(xDp[1], 4)}×4 = {br(xDp[0] * 2 + xDp[1] * 4, 4)} = 6 − 30×{br(bDp, 4)} (ok)
   empréstimos:  {br(xDp[0], 4)}×2 + {br(xDp[1], 4)}×6 = {br(xDp[0] * 2 + xDp[1] * 6, 4)} = 4 + 3×{br(bDp, 4)} (ok)""")
P(f"O β mudou ({br(bD, 3)} → {br(bDp, 4)}) porque a direção mudou: agora o passo em funcionários é muito "
  "maior (30 por unidade de β) do que em empréstimos (3 por unidade). O β deixa de ser \"percentual\" e vira "
  "uma medida em unidades da direção. O que importa para o índice de produtividade é comparar β's calculados "
  "com as mesmas regras, e isso o paper garante.")
EXCEL("nas abas <b>6_DDF_M1_*</b> da planilha passo a passo, linhas 14 a 25, cada constante tem sua fórmula "
      "(MAXIFS/MINIFS sobre a aba 3_Painel). No código: <font name='Consolas'>models._direcoes</font>.")

H1("7. Insumos e produtos indesejáveis: o NPL")
P("NPL (non-performing loans, crédito problemático) é um <b>produto indesejável</b>: o banco produz NPL ao "
  "emprestar, mas quer produzir <b>menos</b>. Por isso, no problema, o NPL do ano é tratado como um insumo: "
  "a mistura de referência tem que ter <b>no máximo</b> o NPL reduzido do banco avaliado (equação 9 do paper):")
F("SOMA(λ2 × NPL_t) ≤ NPL_t do banco − β × (NPL_t do banco + ω)")
P("O NPL do ano anterior entra como <b>insumo indesejável</b> da divisão 2 (o crédito problemático herdado "
  "condiciona o crédito novo). Para ele o paper usa a desigualdade \"maior ou igual\" (equação 7):")
F("SOMA(λ2 × NPL_(t−1)) ≥ NPL_(t−1) do banco + β × (NPL_(t−1) do banco − ρ)")
P("Ou seja, a mistura de referência tem que ter herdado <b>pelo menos</b> tanto NPL quanto o banco avaliado "
  "(mais β vezes a direção). Na prática, o banco só é comparado com misturas que partiram de um fardo de "
  "crédito problemático pelo menos igual ao dele.")
H2("A regra dos sinais")
P("Todas as restrições do paper seguem o mesmo padrão. Vale a pena memorizar:")
T([["O banco quer…", "Exemplo", "Restrição", "β…"],
   ["menos (insumo)", "labor", "SOMA(λ×x) ≤ x_o − β×(direção)", "reduz o limite"],
   ["mais (produto)", "net interest income", "SOMA(λ×y) ≥ y_o + β×(direção)", "aumenta a exigência"],
   ["menos (produto indesejável)", "NPL de t", "SOMA(λ×u) ≤ u_o − β×(direção)", "reduz o limite"],
   ["(insumo indesejável)", "NPL de t−1", "SOMA(λ×w) ≥ w_o + β×(direção)", "aumenta a exigência"]],
  [3.6, 3.3, 6.2, 3.3])

H1("8. Abrindo a caixa-preta: a rede de três divisões")
P("O paper modela o banco como <b>três divisões</b> em sequência (seção 4.1, Figura 2):")
figura_rede()
LEG("Figura 2. A rede do paper. As setas entre as caixas são os elos (produtos intermediários). "
    "Em verde, os carryovers que ligam um ano ao seguinte.")
T([["Divisão", "Insumos", "Produtos", "Peso no problema"],
   ["1 — captação", "labor, fixed assets; equity (quase-fixo)", "deposits (vai para a divisão 2)", "λ1 e φ1"],
   ["2 — crédito", "deposits, borrowings, NPL de t−1, carryovers de t−1",
    "performing loans, investments (vão para a 3); NPL de t; carryovers de t", "λ2"],
   ["3 — receita", "performing loans, investments, provision", "net interest income, non-interest income", "λ3"]],
  [2.6, 5.2, 6.0, 2.6])
H2("Cada divisão tem seus próprios pesos")
P("Esta é a grande diferença: em vez de um único conjunto de pesos λ, há <b>um conjunto por divisão</b> "
  "(λ1, λ2, λ3, cada um com 42 valores somando 1). A divisão 1 de referência pode ser a mistura de uns bancos e "
  "a divisão 3 de referência, a mistura de outros. O que amarra as divisões são os <b>elos</b>:")
F("""SOMA(λ1 × deposits)         = SOMA(λ2 × deposits)           (eq. 12, elo 1→2)
SOMA(λ2 × performing_loans)  = SOMA(λ3 × performing_loans)   (eq. 12, elo 2→3)
SOMA(λ2 × investments)       = SOMA(λ3 × investments)        (eq. 12, elo 2→3)""")
P("Leitura: o que a divisão 1 virtual produz de depósitos é exatamente o que a divisão 2 virtual consome. "
  "O paper explica (equações 2 a 4) que o elo é produto de uma divisão (mais é melhor) e insumo da seguinte "
  "(menos é melhor), e por isso vira uma igualdade: nada se perde nem se cria na passagem.")
H2("Brinquedo: rede × caixa-preta")
P("Três bancos, duas divisões. Divisão 1: funcionários → depósitos. Divisão 2: depósitos → empréstimos.")
LR, DR, ER = [4, 2, 4], [6, 6, 6], [6, 3, 4]
T([["Banco", "Funcionários (insumo div. 1)", "Depósitos (elo)", "Empréstimos (produto div. 2)"],
   ["A", "4", "6", "6"], ["B", "2", "6", "3"], ["C", "4", "6", "4"]], [2, 4.6, 3.6, 5])
P("B é ótimo na divisão 1 (capta 6 com só 2 funcionários) mas fraco na divisão 2 (transforma 6 em só 3). "
  "A é o contrário. Avaliando C, com direção = valores de C:")
A_ = np.zeros((2, 7))
A_[0, :3], A_[0, 6] = LR, LR[2]
A_[1, 3:6], A_[1, 6] = -np.array(ER), ER[2]
eq_ = np.zeros((3, 7))
eq_[0, :3], eq_[0, 3:6] = DR, -np.array(DR)
eq_[1, :3] = 1
eq_[2, 3:6] = 1
c_ = np.zeros(7)
c_[6] = 1
bR, xR = maximizar(c_, A_, [LR[2], -ER[2]], eq_, [0, 1, 1], livres=[6])
bCP, xCP = dea_brinquedo(LR, ER, 2)
F(f"""CAIXA-PRETA (funcionários → empréstimos, um só λ):
   SOMA(λ×func) ≤ 4 − 4β ;  SOMA(λ×empr) ≥ 4 + 4β ;  SOMA(λ) = 1
   → β = {br(bCP, 3)}   (λA = {br(xCP[0], 2)}, λB = {br(xCP[1], 2)})

REDE (λ1 na divisão 1, λ2 na divisão 2):
   SOMA(λ1×func) ≤ 4 − 4β
   SOMA(λ2×empr) ≥ 4 + 4β
   SOMA(λ1×dep)  = SOMA(λ2×dep)          (elo)
   SOMA(λ1) = 1 ;  SOMA(λ2) = 1
   → β = {br(bR, 3)}   (λ1: B = {br(xR[1], 0)} ;  λ2: A = {br(xR[3], 0)})""")
P(f"Na rede, a referência para C é <b>a divisão 1 de B</b> (2 funcionários → 6 de depósitos) ligada <b>à "
  f"divisão 2 de A</b> (6 de depósitos → 6 de empréstimos). Esse banco virtual usa 2 funcionários e empresta 6. "
  f"C (4 → 4) poderia melhorar β = {br(bR, 1)}: 4 − 4×0,5 = 2 funcionários e 4 + 4×0,5 = 6 de empréstimos. A "
  f"caixa-preta, que só vê bancos inteiros, enxerga β = {br(bCP, 1)}. A rede olha o que acontece dentro do banco.")

H2("O insumo quase-fixo (equity) e o peso φ")
P("Equity (capital próprio) é um insumo que o banco não ajusta no curto prazo. O paper o trata como "
  "<b>quase-fixo</b> (equação 6, inspirada em Mehdiloo e Podinovski):")
F("SOMA( (λ1 + φ1) × equity ) ≤ equity do banco avaliado")
P("Repare: <b>não há β</b> nessa restrição — o banco não precisa reduzir o equity. E aparece um segundo peso, "
  "φ1 (phi), que é ≥ 0 e não precisa somar 1. Na prática, φ1 deixa \"sobrar\" equity: a mistura de referência "
  "pode usar menos equity do que o banco avaliado, e a folga é absorvida por φ1. No exemplo real (capítulo 10) "
  "φ1 aparece positivo no próprio SBI.")

H2("Os carryovers: ligando um ano ao seguinte")
P("Unused assets e net profit são <b>carryovers</b> (Tone e Tsutsui): o que sobra no fim do ano t passa para o "
  "ano t+1. Eles aparecem <b>duas vezes</b> em cada problema (equações 10 e 11):")
F("""como produto do ano (o banco quer mais):
   SOMA(λ2 × carryover_t)     ≥ c_o,t     + β × (c_o,t − γ)

como insumo herdado do ano anterior (o banco quer menos):
   SOMA(λ2 × carryover_(t−1)) ≤ c_o,(t−1) − β × (c_o,(t−1) + α)""")
P("É isso que torna o modelo <b>dinâmico</b>: a decisão de um ano depende do que veio do ano anterior.")

H1("9. O modelo M1 completo: as 19 restrições")
P("Juntando tudo, o problema que o Excel resolve para <b>um banco o</b>, com a <b>fronteira formada pelos 42 "
  "bancos no ano F</b> e os <b>dados do banco o no ano E</b>, tem 169 variáveis (42 λ1 + 42 φ1 + 42 λ2 + 42 λ3 "
  "+ β) e 19 restrições. É o modelo (M1) do paper, equações 5 a 13:")
REST = [
    ("1", "≤", "SOMA(λ1×labor_F) ≤ labor_o − β(labor_o + μ_labor)", "5"),
    ("2", "≤", "SOMA(λ1×fixed_F) ≤ fixed_o − β(fixed_o + μ_fixed)", "5"),
    ("3", "≤", "SOMA(λ2×borrowings_F) ≤ borr_o − β(borr_o + μ_borr)", "5"),
    ("4", "≤", "SOMA(λ3×provision_F) ≤ prov_o − β(prov_o + μ_prov)", "5"),
    ("5", "≤", "SOMA((λ1+φ1)×equity_F) ≤ equity_o", "6"),
    ("6", "≤", "SOMA(λ2×NPL_F) ≤ NPL_o − β(NPL_o + ω)", "9"),
    ("7", "≤", "SOMA(λ2×unused_(F−1)) ≤ unused_o,(E−1) − β(… + α_unused)", "11"),
    ("8", "≤", "SOMA(λ2×profit_(F−1)) ≤ profit_o,(E−1) − β(… + α_profit)", "11"),
    ("9", "≥", "SOMA(λ2×NPL_(F−1)) ≥ NPL_o,(E−1) + β(NPL_o,(E−1) − ρ)", "7"),
    ("10", "≥", "SOMA(λ2×unused_F) ≥ unused_o + β(unused_o − γ_unused)", "10"),
    ("11", "≥", "SOMA(λ2×profit_F) ≥ profit_o + β(profit_o − γ_profit)", "10"),
    ("12", "≥", "SOMA(λ3×NII_F) ≥ NII_o + β(NII_o − ν_NII)", "8"),
    ("13", "≥", "SOMA(λ3×NonII_F) ≥ NonII_o + β(NonII_o − ν_NonII)", "8"),
    ("14", "=", "SOMA(λ1×deposits_F) = SOMA(λ2×deposits_F)", "12"),
    ("15", "=", "SOMA(λ2×perf_loans_F) = SOMA(λ3×perf_loans_F)", "12"),
    ("16", "=", "SOMA(λ2×investments_F) = SOMA(λ3×investments_F)", "12"),
    ("17", "=", "SOMA(λ1) = 1", "13"),
    ("18", "=", "SOMA(λ2) = 1", "13"),
    ("19", "=", "SOMA(λ3) = 1", "13"),
]
T([["#", "tipo", "Restrição (o = banco avaliado, dados do ano E)", "eq. paper"]] +
  [[a, b, f"<font name='Consolas'>{c}</font>", d] for a, b, c, d in REST], [0.8, 1.0, 12.6, 2.0])
P("Mais: todos os λ e φ ≥ 0; β livre (pode ser negativo). <b>Objetivo: maximizar β.</b>")
P("No código, cada restrição é uma linha de uma matriz, montada em <font name='Consolas'>models.ddf_rede</font>. "
  "As restrições \"≥\" são escritas como \"≤\" multiplicando tudo por −1 (é o mesmo que trocar os sinais), "
  "porque o simplex do projeto recebe só \"≤\" e \"=\". Por exemplo, a restrição 12 vira:")
F("−SOMA(λ3 × NII_F) + β × (NII_o − ν) ≤ −NII_o")
EXCEL("na planilha passo a passo, abas <b>6_DDF_M1_D00</b> a <b>D11</b>, linhas 35 a 53: uma linha por "
      "restrição, na mesma ordem desta tabela (≤ nas linhas 35–42, ≥ em 43–47, = em 48–53). Coluna C = lado "
      "esquerdo (SUMPRODUCT), E = lado direito, F = folga. As colunas B a E das linhas 62–103 são os pesos "
      "λ1, φ1, λ2, λ3 de cada banco.")

H1("10. Exemplo real: SBI, fronteira 2010, dados 2010")
o = 0
dirs = models.direcoes_m1(PAINEL, 2010)
b00, x00 = lp_com_x(2010, 2010, o)
P("Vamos abrir o problema D00 do State Bank of India para o par 2010→2011: fronteira = 42 bancos em 2010, "
  "dados do SBI em 2010. É exatamente a aba <b>6_DDF_M1_D00</b> da planilha passo a passo.")
H2("Passo 1: as direções (ano F = 2010, ξ = 3, π = 1)")
T([["Constante", "Conta", "Valor"],
   ["μ labor", "3 × maior |labor| em 2010", br(dirs["mu", "labor"], 2)],
   ["μ fixed assets", "3 × maior |fixed assets| em 2010", br(dirs["mu", "fixed_assets"], 2)],
   ["μ borrowings", "3 × maior |borrowings| em 2010", br(dirs["mu", "borrowings"], 2)],
   ["μ provision", "3 × maior |provision| em 2010", br(dirs["mu", "provision"], 2)],
   ["ρ (NPL t−1)", "menor NPL em 2009 − 1", br(dirs["rho"], 2)],
   ["ω (NPL t)", "3 × maior |NPL| em 2010", br(dirs["omega"], 2)],
   ["ν net interest income", "menor NII em 2010 − 1", br(dirs["nu", "net_interest_income"], 2)],
   ["ν non-interest income", "menor NonII em 2010 − 1", br(dirs["nu", "non_interest_income"], 2)],
   ["γ unused assets", "menor unused em 2010 − 1", br(dirs["gamma", "unused_assets"], 2)],
   ["γ net profit", "menor net profit em 2010 − 1", br(dirs["gamma", "net_profit"], 2)],
   ["α unused assets", "3 × maior |unused| em 2009", br(dirs["alpha", "unused_assets"], 2)],
   ["α net profit", "3 × maior |net profit| em 2009", br(dirs["alpha", "net_profit"], 2)]], [4.2, 7.4, 3.4])
P("ρ = −1 porque algum banco tinha NPL líquido igual a zero em 2009. γ do net profit é negativo porque algum "
  "banco teve prejuízo em 2010 — é exatamente o caso que as constantes resolvem.")
H2("Passo 2: os dados do SBI")
VS = ["labor", "fixed_assets", "equity", "deposits", "borrowings", "npl", "unused_assets", "net_profit",
      "performing_loans", "investments", "provision", "net_interest_income", "non_interest_income"]
T([["Variável", "SBI 2009 (E−1)", "SBI 2010 (E)"]] +
  [[f"<font name='Consolas'>{v}</font>", br(PAINEL[2009][v][o], 3), br(PAINEL[2010][v][o], 3)] for v in VS],
  [5.4, 4, 4])
H2("Passo 3: a solução")
lam = {nm: x00[k * NB:(k + 1) * NB] for k, nm in enumerate(["λ1", "φ1", "λ2", "λ3"])}
linhas = [["Peso", "Bancos com peso positivo"]]
for nm, vv in lam.items():
    linhas.append([nm, ", ".join(f"{IDS[i]} = {br(vv[i], 3)}" for i in np.argsort(-vv) if vv[i] > 1e-6) or "—"])
T(linhas, [1.6, 14.8])
P(f"<b>β = {br(b00, 6)}</b>. O SBI poderia, ao mesmo tempo, reduzir cada insumo em β × (insumo + μ), reduzir o "
  "NPL e aumentar os produtos, se operasse como o banco virtual montado assim: divisão 1 como uma mistura de "
  "Corporation Bank, UCO e Nainital; divisão 2 como uma mistura de Canara, J&amp;K, HDFC, DCB e outros; divisão 3 "
  "como uma mistura de SBT, Karnataka, IndusInd e Dhanalakshmi. Cada divisão tem sua própria referência.")
P(f"Exemplo de conta: a restrição de net interest income exige da divisão 3 virtual pelo menos "
  f"{br(PAINEL[2010]['net_interest_income'][o], 3)} + {br(b00, 6)} × ({br(PAINEL[2010]['net_interest_income'][o], 3)} − "
  f"{br(dirs['nu', 'net_interest_income'], 3)}) = "
  f"{br(PAINEL[2010]['net_interest_income'][o] + b00 * (PAINEL[2010]['net_interest_income'][o] - dirs['nu', 'net_interest_income']), 3)}.")
P("Na solução ótima, algumas restrições ficam <b>justas</b> (folga zero): são elas que impedem β de crescer. "
  "As outras ficam com folga. Abra a coluna F da aba 6_DDF_M1_D00 para ver quais.")
EXCEL("abas <b>6_DDF_M1_D00..D11</b>: as células laranja (β em B9 e os pesos) já vêm com a solução do Python. "
      "Para resolver no próprio Excel: Dados > Solver, com as instruções do topo da aba. No motor, este β é a "
      "coluna D00 da linha SBI/2011 da aba <b>r_DMLPI</b>.")

# ================================================================== PARTE IV: ÍNDICES
H1("11. Os quatro β de cada par de anos")
P("Para medir a mudança de produtividade de t para t+1, o paper resolve <b>quatro</b> problemas por banco "
  "(seção 3.2). Os nomes no Excel são D00, D01, D10, D11 — o primeiro dígito diz o ano da fronteira e o segundo "
  "o ano dos dados (0 = t, 1 = t+1):")
T([["Nome", "Fronteira (tecnologia)", "Dados do banco", "Pergunta"],
   ["D00", "ano t", "ano t", "Quão longe o banco estava da fronteira do seu próprio ano?"],
   ["D11", "ano t+1", "ano t+1", "Quão longe ficou da fronteira do novo ano?"],
   ["D01", "ano t", "ano t+1", "O banco de t+1, medido contra a tecnologia antiga"],
   ["D10", "ano t+1", "ano t", "O banco de t, medido contra a tecnologia nova"]], [1.6, 3.6, 3.2, 8.0])
P("D01 e D10 são \"cruzados\": misturam anos. Neles <b>β pode ser negativo</b>: se o banco de 2011 já está "
  "além da fronteira de 2010, ele precisaria <b>piorar</b> para voltar à fronteira antiga, e β < 0 mede quanto. "
  "No exemplo do SBI, D01 é negativo.")
P("Em todos os quatro, as direções (μ, ν...) são calculadas com o <b>ano da fronteira</b>. No código "
  "(<font name='Consolas'>indices.calcular_ddfs</font>) cada problema é guardado num cache pela chave "
  "(fronteira, ano dos dados, banco): o D11 do par 2010→2011 é o mesmo problema que o D00 do par 2011→2012 e "
  "não é resolvido de novo. Por isso o cálculo inteiro é rápido.")

H1("12. Do β ao índice: EC, TC e DMLPI")
P("A equação 14 do paper monta o índice com os quatro β. Sempre aparece \"1 + β\" (o paper prova que "
  "1 + β > 0, então as divisões são seguras):")
F("""EC    = (1 + D00) / (1 + D11)

TC    = RAIZ( (1 + D11) / (1 + D01)  ×  (1 + D10) / (1 + D00) )

DMLPI = EC × TC""")
H2("Brinquedo")
d00, d01, d10, d11 = 0.10, -0.02, 0.15, 0.05
ecb, tcb, ib = indices.componentes(d00, d01, d10, d11)
F(f"""D00 = 0,10   D01 = −0,02   D10 = 0,15   D11 = 0,05

EC  = 1,10 / 1,05 = {br(ecb, 4)}
TC  = RAIZ( 1,05/0,98 × 1,15/1,10 ) = RAIZ( {br(1.05 / 0.98, 4)} × {br(1.15 / 1.10, 4)} ) = RAIZ({br(1.05 / 0.98 * 1.15 / 1.10, 4)}) = {br(tcb, 4)}
DMLPI = {br(ecb, 4)} × {br(tcb, 4)} = {br(ib, 4)}""")
P("Como ler cada pedaço:")
L(f"<b>EC (efficiency change, catching-up)</b>: o banco estava a 0,10 da fronteira em t e a 0,05 em t+1. Se "
  f"aproximou dos melhores → EC = {br(ecb, 3)} > 1.",
  "<b>TC (technical change, inovação)</b>: compara as duas fronteiras, olhando dos dois pontos de vista "
  "(dados de t e dados de t+1) e tirando a média geométrica (a raiz). (1+D11)/(1+D01): os dados de t+1 estão "
  "mais longe da fronteira nova do que da antiga → a fronteira avançou. O mesmo com os dados de t: "
  f"(1+D10)/(1+D00). TC = {br(tcb, 3)} > 1: a fronteira do setor andou para frente.",
  f"<b>DMLPI = EC × TC = {br(ib, 3)}</b>: produtividade subiu cerca de {br((ib - 1) * 100, 1)}%. "
  "Índice = 1: sem mudança; < 1: queda.")
H2("Real: SBI, 2010→2011")
r = DET[(DET.indice == "DMLPI") & (DET.bank_id == "SBI") & (DET.ano == 2011)].iloc[0]
F(f"""D00 = {br(r.D00, 6)}   D01 = {br(r.D01, 6)}   D10 = {br(r.D10, 6)}   D11 = {br(r.D11, 6)}

EC    = (1 + {br(r.D00, 6)}) / (1 + {br(r.D11, 6)}) = {br(r.EC, 6)}
TC    = RAIZ( (1 + {br(r.D11, 6)})/(1 + {br(r.D01, 6)}) × (1 + {br(r.D10, 6)})/(1 + {br(r.D00, 6)}) ) = {br(r.TC, 6)}
DMLPI = {br(r.EC, 6)} × {br(r.TC, 6)} = {br(r.IDX, 6)}""")
P(f"O SBI se afastou um pouco da fronteira (EC = {br(r.EC, 4)} < 1), a fronteira avançou (TC = {br(r.TC, 4)}) e a "
  f"produtividade subiu {br((r.IDX - 1) * 100, 2)}%.")
EXCEL("aba <b>r_DMLPI</b>, linha do SBI com ano = 2011 (o ano do índice é sempre t+1). Colunas EC, TC, IDX "
      "(o índice) e D00..D11. Na planilha passo a passo, aba <b>6e_Indice_exemplo</b> faz exatamente esta conta "
      "a partir dos β das abas 6_DDF_M1_*.")

H1("13. O modelo sequencial M2 (DSMLPI)")
P("No M1, a fronteira de um ano é formada só pelos bancos daquele ano. Se num ano o setor inteiro piora, a "
  "fronteira \"recua\" e TC < 1 (regresso técnico). O paper propõe também o modelo <b>sequencial</b> (seção 3.3): "
  "a fronteira do ano t é formada por <b>todos os bancos de todos os anos até t</b>. A ideia é que uma tecnologia "
  "que já foi usada continua disponível.")
H2("O que muda no problema")
L("Os pesos existem para cada banco <b>e cada ano</b> até F: para F = 2013, são 42 × 4 anos (2010 a 2013) "
  "de cada tipo de peso. A soma dos λ de cada divisão, somando todos os anos, é 1.",
  "Os máximos e mínimos das direções são tomados sobre todos os bancos e todos esses anos.",
  "As constantes mudam (seção 4.3.1): <b>η = 3 e δ = 1 quando a fronteira é t</b> (D00, D01) e "
  "<b>η = 1,5 e δ = 1 quando a fronteira é t+1</b> (D10, D11). No código: "
  "<font name='Consolas'>models.M2_ETA = {0: 3.0, 1: 1.5}</font>.",
  "EC, TC e o índice usam as mesmas fórmulas do capítulo 12.")
P("Com a fronteira acumulada, a fronteira de t+1 contém a de t, e o paper mostra que TC não pode ser menor que "
  "1 no DSMLPI (seção 3.3).")
H2("Brinquedo: contemporâneo × sequencial")
X1, Y1 = [2, 4, 8, 6], [2, 6, 8, 4]
X2, Y2 = [2, 4, 8, 6], [3, 5.5, 9, 5]
P("Ano 1: os bancos do capítulo 5. Ano 2: A2 (2; 3), B2 (4; 5,5), C2 (8; 9), D2 (6; 5). Note que B piorou "
  "(6 → 5,5). Para simplificar, aqui a direção é o próprio valor do banco (como no capítulo 5).")
figura_fronteira([("A1", 2, 2), ("B1", 4, 6), ("C1", 8, 8), ("D1", 6, 4)],
                 [(2, 0), (2, 2), (4, 6), (8, 8), (10, 8)],
                 pontos2=[("A2", 2, 3), ("B2", 4, 5.5), ("C2", 8, 9), ("D2", 6, 5)],
                 fronteira2=[(2, 0), (2, 3), (4, 5.5), (8, 9), (10, 9)], rot1="— fronteira ano 1",
                 rot2="- - fronteira ano 2")
LEG("Figura 3. Na região de B, a fronteira do ano 2 (laranja) ficou abaixo da do ano 1 (azul).")


def dd(Xf, Yf, xo, yo):
    n = len(Xf)
    A = np.zeros((2, n + 1))
    A[0, :n], A[0, n] = Xf, xo
    A[1, :n], A[1, n] = -np.array(Yf), yo
    eq = np.zeros((1, n + 1))
    eq[0, :n] = 1
    c = np.zeros(n + 1)
    c[n] = 1
    return maximizar(c, A, [xo, -yo], eq, [1], livres=[n])[0]


o1, o2 = (6, 4), (6, 5)
c00, c11 = dd(X1, Y1, *o1), dd(X2, Y2, *o2)
c01, c10 = dd(X1, Y1, *o2), dd(X2, Y2, *o1)
s00, s01 = c00, c01
s10, s11 = dd(X1 + X2, Y1 + Y2, *o1), dd(X1 + X2, Y1 + Y2, *o2)
ec_c, tc_c, i_c = indices.componentes(c00, c01, c10, c11)
ec_s, tc_s, i_s = indices.componentes(s00, s01, s10, s11)
T([["Banco D", "D00", "D01", "D10", "D11", "EC", "TC", "Índice"],
   ["contemporâneo (M1)"] + [br(x, 4) for x in (c00, c01, c10, c11, ec_c, tc_c, i_c)],
   ["sequencial (M2)"] + [br(x, 4) for x in (s00, s01, s10, s11, ec_s, tc_s, i_s)]],
  [3.4, 1.8, 1.8, 1.8, 1.8, 1.8, 1.8, 1.8])
P("No sequencial, a fronteira do ano 2 inclui os bancos do ano 1 (B1 continua lá), então D10 e D11 nunca "
  "ficam abaixo dos valores contemporâneos, e TC sai maior. O paper usa essa propriedade para interpretar "
  "o TC do DSMLPI como progresso técnico.")
EXCEL("aba <b>r_DSMLPI</b> do motor (mesmas colunas da r_DMLPI). Este modelo tem variáveis demais para o Solver "
      "do Excel (até 1.345), por isso não há aba de Solver para ele na planilha passo a passo; quem resolve é o "
      "simplex do projeto, dentro da célula =PY().")

H1("14. Os modelos caixa-preta: MLPI e SMLPI")
P("Para comparar, o paper calcula também o índice <b>Malmquist-Luenberger</b> clássico (Chung et al. 1997), "
  "sem rede e sem dinâmica (seção 4.3.2): insumos da divisão 1, produtos da divisão 3 e NPL como produto "
  "indesejável. É orientado a produto, com a direção igual aos valores observados:")
F("""maximizar β
   SOMA(λ × labor)        ≤ labor_o
   SOMA(λ × fixed_assets) ≤ fixed_o
   SOMA(λ × NII)          ≥ (1 + β) × NII_o
   SOMA(λ × NonII)        ≥ (1 + β) × NonII_o
   SOMA(λ × NPL)          = (1 − β) × NPL_o       (indesejável: reduz na mesma proporção)
   SOMA(λ) = 1""")
P("Os insumos não são reduzidos (só limitam a mistura). Os produtos bons crescem β% e o NPL cai β%. O NPL "
  "entra com igualdade, que é a forma de Chung et al. de dizer que o produto indesejável não pode ser "
  "descartado de graça.")
alb = IDS.index("ALB")
bA, xA = lp_com_x(2010, 2010, alb, "ML")
P(f"Exemplo real: Allahabad Bank, fronteira e dados de 2010: <b>β = {br(bA, 4)}</b>, com referência "
  + ", ".join(f"{IDS[i]} = {br(xA[i], 3)}" for i in np.argsort(-xA[:NB]) if xA[i] > 1e-6)
  + f". Ou seja, a mistura produz {br(bA * 100, 1)}% mais receita com no máximo os mesmos insumos e "
  f"{br(bA * 100, 1)}% menos NPL.")
P("O <b>SMLPI</b> é a versão sequencial (fronteira com todos os anos até F). EC, TC e o índice usam as "
  "fórmulas do capítulo 12. Em alguns casos cruzados o problema não tem solução (inviável); aí o D fica "
  "vazio e o EC/TC correspondente também.")
EXCEL("abas <b>r_MLPI</b> e <b>r_SMLPI</b>; na planilha passo a passo, aba <b>7_DDF_ML_D00</b> (um problema "
      "pronto para o Solver, com 43 variáveis).")

H1("15. As tabelas: médias geométricas")
P("As Tabelas 3, 4 e 5 do paper resumem os índices com <b>médias geométricas</b>, não aritméticas.")
H2("Por que geométrica")
F("""Um banco com índice 1,10 num ano e 0,90 no seguinte:
   produtividade: 100 → 110 → 99           (caiu 1% no total)
   média aritmética: (1,10 + 0,90)/2 = 1,000   → diria \"sem mudança\"  (errado)
   média geométrica: RAIZ(1,10 × 0,90) = RAIZ(0,99) = 0,99499   → 0,5% ao ano de queda (ok)""")
P("Índices são razões que se multiplicam ao longo do tempo; a média geométrica é a que respeita isso. No código "
  "(<font name='Consolas'>calcular._geo</font>) ela é feita como exp(média dos logaritmos), ignorando valores "
  "vazios:")
F("média_geométrica(v1, ..., vn) = EXP( (LN(v1) + ... + LN(vn)) / n )")
H2("O que cada tabela agrupa")
T([["Tabela", "Agrupa", "Aba no motor", "Função"],
   ["Tabela 3", "DMLPI e DSMLPI: por ano (2011..2017) e período todo, para todos / públicos / privados",
    "r_tabela3", "tabela_ano"],
   ["Tabela 4", "DMLPI e DSMLPI: por banco no período todo; última linha = média dos privados", "r_tabela4",
    "tabela4"],
   ["Tabela 5", "MLPI e SMLPI, como a Tabela 3", "r_tabela5", "tabela_ano"],
   ["B1 / B2", "Todos os valores banco × ano, públicos (B1) e privados (B2)", "r_tabelaB1 / B2", "tabela_b"]],
  [2.2, 8.4, 3.0, 2.8])
r3 = T3[(T3.painel == "todos") & (T3.ano == "2011")].iloc[0]
P(f"Exemplo: na Tabela 3, linha \"todos, 2011\", DMLPI = {br(r3.DMLPI, 6)}. É a média geométrica dos 42 "
  "valores de IDX da aba r_DMLPI com ano = 2011.")
EXCEL("na planilha passo a passo (abas 9_Tabela3, 10_Tabela4, 11_Tabela5) a conta está em fórmulas: "
      "=EXP(AVERAGEIFS(coluna ln, índice, \"DMLPI\", grupo, ..., ano, ...)), com o valor do Python ao lado.")

# ================================================================== PARTE V: ESTATÍSTICA
H1("16. O teste de Li: públicos e privados são diferentes?")
P("O Painel D da Tabela 3 compara bancos públicos e privados com o teste de Li (1996). Em vez de comparar só "
  "médias, ele compara <b>as distribuições inteiras</b>: a forma do histograma dos índices dos públicos contra "
  "a dos privados. A hipótese testada (H0) é \"as duas distribuições são iguais\".")
H2("A ideia em três passos")
N("<b>Suavizar cada amostra numa curva</b> (estimativa de densidade por kernel): cada observação vira um "
  "\"sininho\" (curva normal) centrado nela; somando os sininhos, sai uma curva que é um histograma suave. "
  "A largura do sininho é a <b>janela h</b>.",
  "<b>Medir a distância entre as duas curvas</b>: a área do quadrado da diferença entre elas (I). Se as curvas "
  "são iguais, I ≈ 0.",
  "<b>Padronizar</b>: dividir por um desvio-padrão (σ) para obter T, que segue aproximadamente uma normal "
  "padrão se H0 for verdade. T grande → as distribuições são diferentes.")
P("Tudo isso se reduz a somas de uma única função, o kernel gaussiano:")
F("""K(u) = EXP(−u²/2) / RAIZ(2π)          (a curva normal padrão; K(0) = 0,39894)

Para pares de valores a, b:   K( (a − b) / h )
   a e b próximos (em relação a h)  → K perto de 0,399
   a e b distantes                  → K perto de 0""")
H2("Brinquedo com 4 + 4 valores")
xl_ = np.array([0.98, 1.00, 1.03, 1.05])
yl_ = np.array([1.04, 1.07, 1.10, 1.12])
n1, n2 = len(xl_), len(yl_)
z = np.concatenate([xl_, yl_])
h = 1.06 * z.std(ddof=1) * z.size ** (-0.2)
K = li_test._k
kxx, kyy, kxy = K((xl_[:, None] - xl_[None, :]) / h), K((yl_[:, None] - yl_[None, :]) / h), \
    K((xl_[:, None] - yl_[None, :]) / h)
Sxx, Syy, Sxy = kxx.sum(), kyy.sum(), kxy.sum()
k0 = K(0.0)
I = ((Sxx - n1 * k0) / (n1 * (n1 - 1)) + (Syy - n2 * k0) / (n2 * (n2 - 1)) - 2 * Sxy / (n1 * n2)) / h
delta = n1 / n2
s2 = 2 * li_test.INT_K2 * (Sxx / (n1 ** 2 * h) + delta ** 2 * Syy / (n2 ** 2 * h) + 2 * delta * Sxy / (n1 * n2 * h))
Tli = n1 * math.sqrt(h) * I / math.sqrt(s2)
Tref, pref = li_test.li_teste(xl_, yl_)
assert abs(Tli - Tref) < 1e-9
F(f"""x (públicos) = 0,98  1,00  1,03  1,05          n1 = 4
y (privados) = 1,04  1,07  1,10  1,12          n2 = 4

1) janela de Silverman, na amostra conjunta dos 8 valores:
   h = 1,06 × desvio_padrão(8 valores) × 8^(−0,2) = 1,06 × {br(z.std(ddof=1), 5)} × {br(8 ** -0.2, 5)} = {br(h, 5)}

2) somas de K sobre todos os pares (inclusive cada valor com ele mesmo):
   Sxx = soma dos 16 K((xi − xj)/h) = {br(Sxx, 5)}
   Syy = soma dos 16 K((yi − yj)/h) = {br(Syy, 5)}
   Sxy = soma dos 16 K((xi − yj)/h) = {br(Sxy, 5)}

3) distância entre as curvas (tirando os pares de um valor com ele mesmo, que valem K(0)):
   I = [ (Sxx − 4×K(0))/(4×3) + (Syy − 4×K(0))/(4×3) − 2×Sxy/(4×4) ] / h = {br(I, 5)}

4) variância:   δ = n1/n2 = 1
   σ² = 2 × 0,28209 × [ Sxx/(n1²h) + δ²×Syy/(n2²h) + 2δ×Sxy/(n1×n2×h) ] = {br(s2, 5)}
   (0,28209 = 1/(2×RAIZ(π)) é a área do kernel ao quadrado)

5) T = n1 × RAIZ(h) × I / RAIZ(σ²) = {br(Tli, 4)}        p-valor = 1 − Normal(T) = {br(pref, 4)}""")
P("Exemplo do primeiro termo de Sxy: x1 = 0,98 e y1 = 1,04 estão a 0,06 de distância; "
  f"(0,98 − 1,04)/h = {br((0.98 - 1.04) / h, 4)}; K = {br(K((0.98 - 1.04) / h), 5)}.")
P("Leitura: o termo cruzado Sxy é pequeno quando as duas amostras estão em lugares diferentes, o que faz I "
  "crescer. O teste é unilateral: rejeita-se H0 a 5% quando T > 1,645. "
  + (f"Aqui T = {br(Tli, 2)} > 1,645: rejeita-se H0." if Tli > 1.645 else
     f"Aqui T = {br(Tli, 2)} < 1,645: com só 4 + 4 valores, não se rejeita H0."))
li_ec = LI[LI.componente == "EC_M1"].iloc[0]
P(f"No projeto, com os 175 pares banco-ano públicos e 119 privados do EC do DMLPI, T = {br(li_ec.teste_li, 3)} "
  "(p-valor ≈ 0). As somas têm 175 × 175, 119 × 119 e 175 × 119 termos.")
EXCEL("aba <b>r_li</b> (motor) traz T e o p-valor dos 6 componentes. Na planilha passo a passo, a aba "
      "<b>12_Li</b> refaz o teste do EC_M1 passo a passo com fórmulas matriciais "
      "(SUM(EXP(−0,5×((X−TRANSPOSE(X))/h)²))/RAIZ(2π)), na mesma ordem dos passos acima.")

H1("17. O GMM de sistema (Tabela 6)")
P("A última etapa do paper (seção 4.3.3) pergunta: <b>que características dos bancos explicam o índice de "
  "produtividade?</b> É uma regressão em painel (vários bancos, vários anos) com o índice do ano anterior "
  "entre os explicativos:")
F("""índice[banco, ano] = a × índice[banco, ano−1]
                   + b1 × G_NPLs + b2 × SIZE + b3 × IC + ... (covariáveis do capítulo 4)
                   + constante + efeito_fixo[banco] + erro""")
P("Cada coluna da Tabela 6 é uma regressão: a variável explicada é EC, TC ou o índice (M1 ou M2), com a lista "
  "de covariáveis definida em <font name='Consolas'>calcular.GMM_XS</font> (onde o paper tem hífen, a "
  "covariável não entra). Anos usados: 2011 a 2017.")
H2("Por que não basta uma regressão comum (mínimos quadrados)")
P("Dois problemas aparecem quando o valor do ano anterior é explicativo:")
L("<b>Efeito fixo</b>: cada banco tem algo próprio e constante (gestão, cultura) que afeta o índice em todos os "
  "anos. Ele está tanto no índice deste ano quanto no do ano anterior, então o explicativo \"índice de t−1\" "
  "fica correlacionado com o erro. A estimativa de a sai viesada.",
  "<b>Endogeneidade</b>: o explicativo depende de coisas que também estão no erro.")
H2("A solução de Arellano-Bond e Blundell-Bond")
P("<b>Passo 1 — diferenciar</b>: subtrair a equação do ano anterior elimina o efeito fixo, porque ele é igual "
  "nos dois anos:")
F("""índice[t] − índice[t−1] = a × (índice[t−1] − índice[t−2])
                        + b × (x[t] − x[t−1])
                        + (erro[t] − erro[t−1])

Exemplo de um banco: índices 2011..2015 = 1,00  1,02  0,99  1,01  1,03
   diferenças Δ:              —     0,02  −0,03  0,02  0,02
   equação de 2013:  −0,03 = a × 0,02 + b × Δx(2013) + Δerro(2013)""")
P("<b>Passo 2 — instrumentos</b>: ainda assim Δíndice[t−1] está correlacionado com Δerro[t] (ambos contêm "
  "erro[t−1]). A saída é usar <b>instrumentos</b>: variáveis correlacionadas com o explicativo, mas não com o "
  "erro. Valores mais antigos servem: o índice de t−2, t−3, ... não contém erro[t] nem erro[t−1].")
F("""Instrumentos da equação em diferenças de 2013: índice(2011)
Instrumentos da equação em diferenças de 2014: índice(2011), índice(2012)
Instrumentos da equação em diferenças de 2015: índice(2011), índice(2012), índice(2013)
... (cada ano ganha mais um; é o padrão do xtabond2, sem 'collapse')""")
P("<b>Passo 3 — sistema</b> (Blundell e Bond 1998): além das equações em diferença, usa também as equações em "
  "<b>nível</b> (a original), instrumentadas pela <b>diferença</b> do ano anterior, Δíndice[t−1]. As duas "
  "famílias de equações são estimadas juntas: daí \"sistema\". As covariáveis servem de instrumento para si "
  "mesmas (Δx nas diferenças, x no nível) e a constante entra no nível.")
P("<b>Passo 4 — dois passos</b>: o GMM escolhe os coeficientes que deixam os instrumentos o menos "
  "correlacionados possível com os erros, ponderando cada condição por uma matriz de pesos. No 1º passo os "
  "pesos são fixos (a estrutura de um erro em diferença); no 2º passo os pesos vêm dos resíduos do 1º passo, "
  "o que dá estimativas mais precisas.")
P("<b>Passo 5 — correção de Windmeijer (2005)</b>: os erros-padrão do 2º passo, em amostras pequenas, saem "
  "pequenos demais; a correção os ajusta.")
H2("Um exemplo de instrumento com números")
F("""Ideia do estimador com um instrumento z para um explicativo x (sem constante):
   a = SOMA(z × y) / SOMA(z × x)

Dados: z = 1, 2, 3     x = 2, 3, 5     y = 4, 7, 9
   SOMA(z×y) = 4 + 14 + 27 = 45      SOMA(z×x) = 2 + 6 + 15 = 23      a = 45/23 = 1,957
O GMM generaliza isto para muitos instrumentos e muitos explicativos, com a matriz de pesos.""")
H2("Os testes que aparecem na Tabela 6")
T([["Linha", "O que testa", "Como ler"],
   ["AR(1), AR(2)", "Autocorrelação dos resíduos em diferença, de ordem 1 e 2 (Arellano-Bond)",
    "AR(1) costuma ser significativo por construção; AR(2) com p-valor alto indica que os instrumentos "
    "de t−2 são válidos"],
   ["Sargan, Hansen J", "Se os instrumentos, em conjunto, são válidos (sobreidentificação)",
    "p-valor alto = não se rejeita a validade"],
   ["Wald Chi2", "Se os coeficientes (sem a constante) são todos zero ao mesmo tempo",
    "estatística grande = o modelo explica algo"],
   ["coef / ep", "Coeficiente estimado e erro-padrão (corrigido por Windmeijer)",
    "coef/ep grande em valor absoluto = significativo"]], [3.0, 6.4, 7.0])
dep = "DMLPI"
dmo = DET[DET.indice == "DMLPI"].set_index(["bank_id", "ano"])["IDX"]
anos6 = [a for a in META["anos"] if a >= 2011]
rg = system_gmm(_matriz(dmo, anos6, IDS), [_matriz(COV[x], anos6, IDS) for x in GMM_XS[dep]],
                ["L.dep", *GMM_XS[dep], "Constant"])
lin6 = T6.set_index(["regressor", "estatistica"])
P(f"Na coluna DMLPI do projeto: {rg['bancos']} bancos, {rg['obs']} observações na equação em nível, "
  f"{rg['instrumentos']} instrumentos. O coeficiente do índice defasado (L.dep) é "
  f"{br(lin6.loc[('L.dep', 'coef'), 'DMLPI'], 4)} com erro-padrão {br(lin6.loc[('L.dep', 'ep'), 'DMLPI'], 4)}; "
  f"AR(2) tem p-valor {br(lin6.loc[('AR(2)', 'p'), 'DMLPI'], 3)} e Hansen J, {br(lin6.loc[('Hansen J', 'p'), 'DMLPI'], 3)}.")
EXCEL("aba <b>r_tabela6</b>: uma linha por regressor e estatística, uma coluna por modelo. O código está na "
      "aba <b>m_gmm</b> (<font name='Consolas'>system_gmm</font>), e as contas com matrizes não estão abertas "
      "em fórmulas.")

# ================================================================== PARTE VI: SIMPLEX
H1("18. Programação linear e o método simplex")
P("Cada β do projeto é a solução de uma programação linear (PL). O projeto tem seu próprio resolvedor, "
  "escrito à mão em <font name='Consolas'>src/bansal/simplex.py</font> (aba <b>m_simplex</b> no motor). "
  "Este capítulo explica o método; o próximo, o código.")
H2("A geometria")
P("Numa PL, as restrições cortam o espaço em uma região de soluções possíveis, um poliedro (com 2 variáveis, "
  "um polígono). O melhor valor de uma função linear está sempre num <b>vértice</b> desse poliedro. O simplex "
  "anda de vértice em vértice, sempre melhorando o objetivo, até nenhum vizinho ser melhor.")
H2("Folgas: transformando ≤ em =")
F("""x + y ≤ 4      vira     x + y + s1 = 4,   com s1 ≥ 0
s1 é a \"folga\": quanto falta para a restrição ficar justa.""")
P("Com as folgas, um vértice corresponde a escolher <b>quais variáveis podem ser diferentes de zero</b> (as "
  "<b>básicas</b>, uma por restrição) e zerar as outras (as <b>não básicas</b>). As básicas são então "
  "determinadas pelas equações.")
H2("Exemplo resolvido à mão (método do quadro)")
P("Maximizar 3x + 2y, sujeito a: x + y ≤ 4;  x + 3y ≤ 6;  x ≤ 2;  x, y ≥ 0.")


def quadro_simplex(A, b, c, nomes):
    """Simplex de quadro (Dantzig), só para o exemplo. Devolve a lista de quadros."""
    m, n = A.shape
    Q = np.zeros((m + 1, n + m + 1))
    Q[:m, :n], Q[:m, n:n + m], Q[:m, -1] = A, np.eye(m), b
    Q[m, :n] = -np.asarray(c)
    base = [n + i for i in range(m)]
    todos = list(nomes) + [f"s{i + 1}" for i in range(m)]
    quadros = [(Q.copy(), list(base), None, None)]
    while True:
        j = int(np.argmin(Q[m, :-1]))
        if Q[m, j] >= -1e-12:
            break
        raz = [Q[i, -1] / Q[i, j] if Q[i, j] > 1e-12 else np.inf for i in range(m)]
        r = int(np.argmin(raz))
        Q[r] /= Q[r, j]
        for i in range(m + 1):
            if i != r:
                Q[i] -= Q[i, j] * Q[r]
        sai = todos[base[r]]
        base[r] = j
        quadros.append((Q.copy(), list(base), todos[j], sai))
    return quadros, todos


Aq = np.array([[1, 1], [1, 3], [1, 0.]])
quads, nomes_q = quadro_simplex(Aq, np.array([4, 6, 2.]), [3, 2], ["x", "y"])


def mostra_quadro(Q, base, todos):
    cab = ["básica"] + todos + ["valor"]
    lin = [cab]
    for i, bi in enumerate(base):
        lin.append([todos[bi]] + [br(v, 3) for v in Q[i]])
    lin.append(["objetivo"] + [br(v, 3) for v in Q[-1]])
    T(lin, [2.0] + [1.9] * (len(todos)) + [2.0], mono=True)


H3("Quadro inicial (vértice x = 0, y = 0)")
mostra_quadro(quads[0][0], quads[0][1], nomes_q)
P("Como ler: cada linha é uma equação (x + y + s1 = 4 etc.). A última linha é o objetivo escrito como "
  "z − 3x − 2y = 0. As básicas são s1, s2, s3 (as folgas), com valores 4, 6, 2; x = y = 0; z = 0.")
P("<b>Quem entra?</b> Um número negativo na linha do objetivo indica que aumentar aquela variável aumenta z. "
  "O mais negativo é −3 (x): x entra (regra de Dantzig).")
P("<b>Quem sai?</b> O <b>teste da razão</b>: até quanto x pode crescer sem nenhuma básica ficar negativa? "
  "Para cada linha com coeficiente positivo na coluna de x: valor ÷ coeficiente = 4/1 = 4; 6/1 = 6; 2/1 = 2. "
  "O menor é 2 (linha de s3): s3 sai, e x passa a valer 2.")
P("<b>Pivotar</b>: dividir a linha de s3 pelo coeficiente de x (1) e zerar a coluna de x nas outras linhas, "
  "subtraindo múltiplos da linha do pivô (como na eliminação de Gauss).")
for k in range(1, len(quads)):
    Qk, bk, ent, sai = quads[k]
    H3(f"Iteração {k}: entra {ent}, sai {sai}")
    mostra_quadro(Qk, bk, nomes_q)
    if k == 1:
        P("Agora x = 2, s1 = 2, s2 = 4, z = 6. Ainda há negativo na linha do objetivo (−2 em y): y entra. "
          "Razões: linha de s1: 2/1 = 2; linha de s2: 4/3 = 1,333; linha de x: coeficiente 0, não limita. "
          "Sai s2.")
Qf = quads[-1][0]
P(f"Não há mais negativos na linha do objetivo: <b>ótimo</b>. x = 2, y = {br(4 / 3, 3)}, z = {br(Qf[-1, -1], 3)}. "
  "Conferindo: x + 3y = 2 + 4 = 6 (justa), x = 2 (justa), x + y = 3,333 < 4 (s1 = 0,667 de folga).")
H2("Restrições ≥ e =: a fase 1")
P("No exemplo, o vértice inicial (tudo zero) era possível. Nas PLs do paper não é: há igualdades "
  "(SOMA(λ) = 1) e restrições que exigem produção mínima. Com tudo zero, SOMA(λ) = 0 ≠ 1. O simplex de "
  "<b>duas fases</b> resolve isso:")
N("<b>Fase 1</b>: acrescenta uma variável <b>artificial</b> em cada restrição (uma \"folga de mentira\" que "
  "torna o ponto inicial possível) e minimiza a soma das artificiais. Se o mínimo for 0, achou um vértice "
  "verdadeiro do problema original. Se não for 0, o problema é <b>inviável</b> (não tem solução).",
  "<b>Fase 2</b>: a partir desse vértice, otimiza o objetivo verdadeiro (maximizar β), proibindo as "
  "artificiais de voltar.")
H2("Variáveis livres")
P("O simplex exige variáveis ≥ 0, mas β pode ser negativo. O truque padrão: escrever β = β+ − β−, com as "
  "duas partes ≥ 0. Se β = −0,01, a solução terá β+ = 0 e β− = 0,01.")

H1("19. O simplex do projeto, linha por linha")
P("O arquivo <font name='Consolas'>simplex.py</font> tem três partes: <font name='Consolas'>inversa</font> "
  "(inverte uma matriz), <font name='Consolas'>_simplex</font> (o laço do método) e "
  "<font name='Consolas'>maximizar</font> (prepara o problema e chama as duas fases). Ele implementa o "
  "<b>simplex revisado</b>: a mesma lógica do quadro, mas em vez de atualizar o quadro inteiro, guarda só a "
  "<b>inversa da matriz das colunas básicas</b> (B<super>−1</super>, no código <font name='Consolas'>Binv</font>). Com 169 variáveis e 19 restrições, isso é bem mais leve.")
H2("maximizar: a preparação")
F("""def maximizar(c, A_ub, b_ub, A_eq, b_eq, livres):
    # max c·x  s.a.  A_ub·x ≤ b_ub ;  A_eq·x = b_eq ;  x ≥ 0 exceto 'livres'""")
N("<b>Empilha</b> as restrições: primeiro as \"≤\", depois as \"=\". A = [A_ub; A_eq], b = [b_ub; b_eq].",
  "<b>Variáveis livres</b>: para cada livre (β), acrescenta uma coluna com o sinal trocado (−A[:, β]) — é o β−. "
  "No custo, β+ tem custo −1 e β− tem +1 (o projeto <b>minimiza −β</b>, o que é o mesmo que maximizar β).",
  "<b>Folgas</b>: uma coluna identidade para cada restrição \"≤\".",
  "<b>Escala</b>: divide cada linha pelo seu maior valor absoluto e depois cada coluna pelo seu maior valor "
  "absoluto. Os dados do paper vão de 0,0001 a 20.000 (μ de borrowings ≈ 19.821); sem escala, os arredondamentos "
  "do computador estragariam as contas. No fim, os valores são desescalados.",
  "<b>Sinal</b>: multiplica por −1 as linhas com lado direito negativo, para que b ≥ 0 (exigência do ponto "
  "inicial da fase 1).",
  "<b>Fase 1</b>: acrescenta uma artificial por linha (identidade), custo 1 nas artificiais, e chama "
  "<font name='Consolas'>_simplex</font> com a base = artificiais. Se o mínimo > 10<super>−7</super> × (maior |b|), levanta "
  "<font name='Consolas'>Inviavel</font> (e o D vira vazio no Excel).",
  "<b>Retirar artificiais da base</b>: alguma artificial pode ter ficado na base com valor 0. Para cada uma, "
  "procura uma coluna verdadeira com coeficiente não nulo naquela linha e pivota para trocá-las.",
  "<b>Fase 2</b>: custo verdadeiro, mesma base, artificiais proibidas de entrar.",
  "<b>Desfaz</b> a escala e junta β = β+ − β−. Devolve (valor ótimo, x).")
H2("_simplex: o laço")
F("""Binv = inversa(A[:, base])          # inversa das colunas básicas
xB   = Binv @ b                     # valores das básicas
repetir:
    y = c[base] @ Binv              # \"preços-sombra\" das restrições
    d = c − y @ A                   # custo reduzido de cada coluna
    candidatas = colunas com d < −1e-9 (e permitidas)
    se não há candidatas: FIM (ótimo)
    j = candidata com o d mais negativo        (Dantzig)
        ... ou a de menor índice, após 50 passos degenerados seguidos (Bland)
    a = Binv @ A[:, j]              # a coluna j no quadro atual
    se nenhum a > 1e-9: problema ILIMITADO
    razões = xB / a  (só onde a > 0) ; θ = menor razão
    r = linha da menor razão (empate: a básica de menor índice)
    xB = xB − θ·a ;  xB[r] = θ      # anda até o novo vértice
    atualiza Binv (pivô na linha r) ; base[r] = j
    a cada 40 iterações: recalcula Binv do zero""")
P("Comparando com o quadro do capítulo 18:")
T([["No quadro", "No código"],
   ["linha do objetivo", "d = c − y·A (custos reduzidos). Negativo = vale a pena entrar"],
   ["coluna da variável que entra", "a = Binv × A[:, j]"],
   ["coluna \"valor\"", "xB = Binv × b"],
   ["teste da razão", "razões = xB / a, só onde a > 0"],
   ["pivotar o quadro inteiro", "atualizar só Binv: piv = Binv[r]/a[r]; Binv −= outer(a, piv); Binv[r] = piv"]],
  [5.0, 11.4])
H2("As proteções numéricas")
L("<b>Tolerância 10<super>−9</super></b>: um custo reduzido de −10<super>−12</super> é tratado como zero (é arredondamento, não melhora real).",
  "<b>Refatoração a cada 40 iterações</b>: Binv é atualizada a cada passo e acumula erros de arredondamento; "
  "de tempos em tempos é recalculada do zero com <font name='Consolas'>inversa</font> (Gauss-Jordan com "
  "pivoteamento parcial: em cada coluna, usa como pivô o maior valor absoluto, para não dividir por números "
  "pequenos).",
  "<b>Regra de Bland após 50 passos degenerados</b>: um passo \"degenerado\" é quando θ = 0 (troca a base sem "
  "sair do lugar). Em problemas como os do DEA isso é comum e, em tese, o método pode girar em círculo. A regra "
  "de Bland (entra a candidata de menor índice; empate na razão sai a básica de menor índice) garante que "
  "isso não acontece.")

H2("O simplex do projeto no brinquedo do capítulo 6")
traco = []
orig = simplex._simplex


def _simplex_rastreado(A, b, c, base, proibidas):
    m, n = A.shape
    base = list(base)
    Binv = simplex.inversa(A[:, base])
    xB = Binv @ b
    permitida = np.ones(n, bool)
    permitida[list(proibidas)] = False
    deg = 0
    it = 0
    fase = 1 if not proibidas else 2
    while True:
        it += 1
        if it % simplex.REFATORAR == 0:
            Binv = simplex.inversa(A[:, base])
            xB = Binv @ b
        y = c[base] @ Binv
        d = c - y @ A
        d[base] = 0.0
        cand = np.where((d < -simplex.TOL) & permitida)[0]
        if cand.size == 0:
            break
        j = int(cand[0]) if deg >= simplex.MAX_DEGENERADOS else int(cand[np.argmin(d[cand])])
        a = Binv @ A[:, j]
        pos = a > simplex.TOL
        raz = np.full(m, np.inf)
        raz[pos] = np.maximum(xB[pos], 0.0) / a[pos]
        th = raz.min()
        emp = np.where(raz <= th + 1e-12)[0]
        r = int(min(emp, key=lambda i: base[i]))
        deg = deg + 1 if th <= 1e-12 else 0
        sai = base[r]
        xB = xB - th * a
        xB[r] = th
        piv = Binv[r] / a[r]
        Binv -= np.outer(a, piv)
        Binv[r] = piv
        base[r] = j
        traco.append((fase, it, j, sai, th, float(c[base] @ xB)))
    return base, Binv, xB


simplex._simplex = _simplex_rastreado
try:
    bt, xt = dea_brinquedo([2, 4, 8, 6], [2, 6, 8, 4], 3, mu=24, nu=1)
finally:
    simplex._simplex = orig
assert abs(bt - bDp) < 1e-12
P("Rodando o problema do banco D com as direções do paper (β = 2/21) no simplex do projeto, com um registro "
  "de cada iteração. As colunas internas são, nesta ordem: λA, λB, λC, λD e β+ (colunas 0 a 4), β− (5), folgas das duas "
  "restrições ≤ (6, 7) e artificiais das 3 linhas (8, 9, 10).")
nomes_col = ["λA", "λB", "λC", "λD", "β+", "β−", "folga 1", "folga 2", "artif. 1", "artif. 2", "artif. 3"]
T([["Fase", "Iteração", "Entra", "Sai", "Passo θ", "Objetivo da fase"]] +
  [[str(f), str(i), nomes_col[j], nomes_col[s], br(th, 4), br(ob, 6)] for f, i, j, s, th, ob in traco],
  [1.6, 2.0, 2.6, 2.6, 3.0, 4.6])
P("Na fase 1 o objetivo é a soma das artificiais (na escala interna) e cai até 0: achou-se uma mistura "
  "possível. Na fase 2 o objetivo é −β; o último valor é −2/21 = −0,095238: β = 0,095238, como no capítulo 6.")
mr = models.ddf_rede
traco.clear()
simplex._simplex = _simplex_rastreado
try:
    bsbi = models.ddf_rede(PAINEL, [2010], 2010, 0, models.direcoes_m1(PAINEL, 2010))
finally:
    simplex._simplex = orig
it1 = sum(1 for t in traco if t[0] == 1)
it2 = sum(1 for t in traco if t[0] == 2)
P(f"No problema real do SBI (D00, 2010) o mesmo código faz {it1} iterações na fase 1 e {it2} na fase 2, sobre "
  f"uma matriz de 19 linhas e 169 + 1 + 8 + 19 colunas (variáveis, β−, folgas e artificiais), e chega a "
  f"β = {br(bsbi, 6)}.")
EXCEL("o código está na aba <b>m_simplex</b> do motor, uma linha de Python por linha da planilha. O Solver do "
      "Excel (usado na planilha passo a passo) resolve as mesmas PLs com outra implementação do simplex; o β "
      "ótimo é o mesmo. Os λ podem sair diferentes quando há mais de uma mistura ótima.")

# ================================================================== PARTE VII: EXCEL
H1("20. O motor no Excel: como funciona por dentro")
P("O arquivo <b>excel/motor_bansal.xlsx</b> usa o <b>Python no Excel</b> do Microsoft 365: uma célula com "
  "=PY(...) executa código Python (na nuvem da Microsoft) e pode devolver um valor ou uma tabela inteira, que "
  "\"derrama\" pelas células ao lado e abaixo.")
H2("As abas, na ordem")
T([["Aba", "O que tem"],
   ["LEIA-ME", "Instruções curtas."],
   ["base", "Entrada: itens contábeis nominais por banco e ano (amarelo = editável)."],
   ["deflator", "Entrada: índice de preços por ano."],
   ["m_setup", "A1 define registrar() e mostrar() — as duas funções de apoio."],
   ["m_nomes … m_calcular", "Uma aba por módulo de src/bansal. Coluna A = número da linha, coluna B = código. "
                            "A célula A1 carrega o módulo."],
   ["r_painel … r_tabela6", "Uma aba por resultado. A célula A3 chama o motor e derrama a tabela."]],
  [4.0, 12.4])
H2("Como um módulo é carregado (m_*)")
F("""Célula A1 da aba m_simplex:
    =PY( registrar("simplex", xl("m_simplex!B3:B153")) )

registrar(nome, tabela):
    1. junta as linhas de código lidas da coluna B num texto só
    2. cria um módulo vazio chamado bansal.simplex
    3. executa o texto dentro dele (exec)
    4. registra o módulo, para que 'from bansal import simplex' funcione nas outras células""")
P("O código nas abas m_* é cópia literal de src/bansal: não há uma versão \"para Excel\". As linhas em branco "
  "do arquivo viram células vazias e são recompostas como linhas vazias.")
H2("Como um resultado é calculado (r_*)")
F("""Célula A3 da aba r_painel (resumida):
    b    = xl("base!A1:Y379", headers=True)          # lê a base
    NOM  = b.set_index(["bank_id", "ano"])           # índice banco × ano
    DEFL = {ano: índice} lido de 'deflator'
    P_, C_ = padronizar.painel_de_nominal(NOM, DEFL) # cap. 3 e 4
    PAINEL, COV, META = painel.montar(...)          # formato usado pelos modelos
    RES = P_.reset_index()
    mostrar(RES)                                     # sem índice; vazio no lugar de NaN

Célula A3 da aba r_DMLPI:
    DET_DMLPI = calcular.indices_banco_ano(PAINEL, META, ["DMLPI"])   # caps. 9 a 12
    mostrar(DET_DMLPI)""")
P("As variáveis criadas numa célula (PAINEL, COV, DET_DMLPI…) ficam visíveis nas células seguintes. Por isso a "
  "<b>ordem</b> importa: o Excel calcula as células =PY() aba por aba, da esquerda para a direita, e dentro da "
  "aba linha por linha. As abas m_* precisam vir antes das r_*, e r_painel antes de todas as outras r_*.")
T([["Aba r_*", "Chama", "Capítulo"],
   ["r_painel", "padronizar.painel_de_nominal, painel.montar", "3"],
   ["r_covariaveis", "(resultado da mesma conta)", "4"],
   ["r_tabela2", "calcular.tabela2 (média, desvio, curtose+3, assimetria, mediana, máx., mín.; 2010–2017)", "—"],
   ["r_DMLPI / r_DSMLPI", "calcular.indices_banco_ano (modelos M1 / M2)", "9–13"],
   ["r_MLPI / r_SMLPI", "calcular.indices_banco_ano (caixa-preta)", "14"],
   ["r_tabela3, 4, 5, B1, B2", "calcular.tabela_ano, tabela4, tabela_b", "15"],
   ["r_li", "calcular.li_por_componente", "16"],
   ["r_tabela6", "calcular.tabela6 (GMM)", "17"]], [4.2, 9.6, 2.6])
H2("Colunas das abas de índices (r_DMLPI, r_DSMLPI, r_MLPI, r_SMLPI)")
T([["Coluna", "Significado"],
   ["indice", "DMLPI, DSMLPI, MLPI ou SMLPI"],
   ["bank_id, banco, grupo", "Código, nome e grupo (publico/privado)"],
   ["ano", "t+1 do par (2011 = par 2010→2011)"],
   ["EC, TC, IDX", "Componentes e índice (cap. 12)"],
   ["D00, D01, D10, D11", "Os quatro β (cap. 11); vazio = problema inviável"]], [4.4, 12.0])

H1("21. Seguindo um número da base até a Tabela 3")
P("Para fixar tudo, o caminho completo de um número: o DMLPI de todos os bancos em 2011 na Tabela 3.")
N("<b>base</b>: os itens do SBI (e dos outros 41 bancos) de 2009, 2010 e 2011.",
  "<b>r_painel</b>: viram as 13 variáveis, deflacionadas e por agência (cap. 3).",
  "<b>Direções</b> de 2010 e 2011 (cap. 6 e 10), calculadas dentro do motor.",
  "<b>Quatro PLs por banco</b> (cap. 9 a 11), resolvidas pelo simplex (cap. 18 e 19): D00, D01, D10, D11.",
  "<b>r_DMLPI</b>: EC, TC e IDX de cada banco, linha ano = 2011 (cap. 12). SBI: "
  f"IDX = {br(r.IDX, 6)}.",
  f"<b>r_tabela3</b>: média geométrica dos 42 IDX de 2011 (cap. 15) = {br(r3.DMLPI, 6)}.")
H2("Mudando a base")
P("Mude um número na aba base (por exemplo, os adiantamentos de um banco). O Excel recalcula todas as "
  "células =PY() que vêm depois: o painel, os quatro modelos, as tabelas, o teste de Li e o GMM. Leva cerca de "
  "25 segundos; enquanto isso, as células mostram #BUSY!.")
L("O Python roda na nuvem: precisa de internet.",
  "Na pasta do OneDrive o Excel salva sozinho (AutoSave): para testar sem perder a base original, trabalhe "
  "numa cópia ou desligue o AutoSave.",
  "Não reordene as abas.",
  "Se o código em src/bansal mudar, gere a pasta de novo: "
  "<font name='Consolas'>$env:PYTHONPATH=\"src\"; python -m bansal.planilha_motor</font>.")

H1("22. A planilha passo a passo")
P("O arquivo <b>data/saida/planilha_passo_a_passo.xlsx</b> refaz as mesmas contas com <b>fórmulas comuns</b> do "
  "Excel, para você clicar numa célula e ver a conta. Cores: amarelo = entrada; laranja = variável de decisão do "
  "Solver; verde = valor gravado pelo Python, ao lado, para comparar.")
T([["Aba", "Conteúdo", "Capítulo"],
   ["1_Nominal, 1b_Deflator", "A base e o deflator (valores)", "2"],
   ["2_Variaveis", "As 13 variáveis em fórmulas; a linha 3 mostra a fórmula de cada coluna", "3"],
   ["3_Painel", "Fator do deflator, agências e as variáveis no painel", "3"],
   ["4_Covariaveis", "As 8 covariáveis em fórmulas", "4"],
   ["5_Tabela2", "Estatística descritiva com fórmulas matriciais", "—"],
   ["6_DDF_M1_D00..D11", "As 4 PLs do SBI 2010→2011: direções, dados, 19 restrições, 42 × 4 pesos", "9–11"],
   ["6e_Indice_exemplo", "Dos 4 β ao EC, TC e DMLPI do SBI", "12"],
   ["7_DDF_ML_D00", "Uma PL caixa-preta para o Solver", "14"],
   ["8_Indices", "D00..D11 (do Python) e EC/TC/IDX em fórmulas, para todos os modelos", "12"],
   ["9_Tabela3, 10_Tabela4, 11_Tabela5", "Médias geométricas em fórmulas", "15"],
   ["12_Li", "Teste de Li do EC_M1 passo a passo", "16"],
   ["13_GMM", "Passos do GMM em texto e o resultado", "17"]], [4.6, 9.4, 2.4])
H2("Usando o Solver nas abas 6_DDF_M1_*")
N("Dados > Solver (se não aparecer: Arquivo > Opções > Suplementos > Suplementos do Excel > marcar Solver).",
  "Definir objetivo: $B$9 (β). Para: Máx.",
  "Alterando células variáveis: $B$9 e $B$62:$E$103.",
  "Restrições: $C$35:$C$42 &lt;= $E$35:$E$42;  $C$43:$C$47 &gt;= $E$43:$E$47;  $C$48:$C$53 = $E$48:$E$53;  "
  "$B$62:$E$103 &gt;= 0.",
  "Desmarcar \"Tornar Variáveis Irrestritas Não Negativas\" (β é livre). Método: LP Simplex. Resolver.",
  "Para outro banco ou ano: mude as células amarelas B3 (banco), B4 (fronteira), B5 (dados), zere β e os "
  "pesos e rode de novo.")
P("O Solver do Excel aceita até 200 variáveis; o M1 tem 169, por isso cabe. Os modelos sequenciais não cabem, "
  "e é por isso que eles só existem no motor.")

story.append(PageBreak())
H1("Glossário")
GLOS = [
    ("β (beta)", "Distância do banco até a fronteira, na direção escolhida. Resultado de cada PL."),
    ("λ (lambda)", "Peso de cada banco na mistura de referência. Um conjunto por divisão (λ1, λ2, λ3)."),
    ("φ (phi)", "Peso extra do insumo quase-fixo (equity) na divisão 1."),
    ("μ, ω, α", "Constantes de direção de insumos, NPL de t e carryovers de t−1: ξ × maior valor absoluto."),
    ("ν, ρ, γ", "Constantes de direção de produtos, NPL de t−1 e carryovers de t: menor valor − π."),
    ("ξ, π (M1); η, δ (M2)", "Parâmetros das direções: ξ = 3, π = 1; η = 3 (fronteira t) ou 1,5 (t+1), δ = 1."),
    ("DDF", "Função distância direcional: o β de um banco em relação a uma fronteira."),
    ("D00, D01, D10, D11", "Os quatro DDFs de um par de anos (fronteira, dados)."),
    ("EC", "Efficiency change: (1+D00)/(1+D11). Aproximação da fronteira."),
    ("TC", "Technical change: deslocamento da fronteira."),
    ("DMLPI", "Índice Malmquist-Luenberger dinâmico em rede (modelo M1). = EC × TC."),
    ("DSMLPI", "A versão sequencial (modelo M2)."),
    ("MLPI, SMLPI", "Versões caixa-preta (Chung et al.), contemporânea e sequencial."),
    ("VRS", "Retornos variáveis de escala: os pesos de cada divisão somam 1."),
    ("Elo / intermediário", "Produto de uma divisão que é insumo da seguinte (depósitos; empréstimos e "
                            "investimentos)."),
    ("Carryover", "Variável que passa de um ano ao seguinte (unused assets, net profit)."),
    ("Quase-fixo", "Insumo que não se ajusta no curto prazo (equity)."),
    ("Fronteira contemporânea", "Formada pelos bancos de um único ano (M1, MLPI)."),
    ("Fronteira sequencial", "Formada pelos bancos de todos os anos até o ano em questão (M2, SMLPI)."),
    ("PL", "Programação linear: maximizar uma função linear sujeito a restrições lineares."),
    ("Simplex", "Algoritmo que resolve PLs andando de vértice em vértice."),
    ("Base / básicas", "As variáveis que podem ser não nulas num vértice (uma por restrição)."),
    ("Custo reduzido", "Quanto o objetivo muda se uma variável não básica aumentar uma unidade."),
    ("Folga", "Variável que transforma ≤ em =; quanto falta para a restrição ficar justa."),
    ("Artificial", "Variável temporária da fase 1, para começar de um ponto possível."),
    ("Kernel / janela h", "A curva-sino usada no teste de Li e a largura dela."),
    ("GMM de sistema", "Regressão em painel com equações em diferença e em nível, estimada com instrumentos."),
    ("Instrumento", "Variável correlacionada com o explicativo e não com o erro."),
]
T([["Termo", "Significado"]] + [[a, b] for a, b in GLOS], [4.4, 12.0])


# ------------------------------------------------------------------ montagem

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
        canv.drawString(2.2 * cm, 1.2 * cm, "Entendendo o Excel da réplica de Bansal et al. (2022)")
        canv.drawRightString(A4[0] - 2.2 * cm, 1.2 * cm, f"página {doc.page}")
    canv.restoreState()


def main():
    ARQ.parent.mkdir(parents=True, exist_ok=True)
    doc = Doc(str(ARQ), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2 * cm,
              bottomMargin=2 * cm, title="Entendendo o Excel da réplica de Bansal et al. (2022)",
              author="Projeto bansal")
    doc.multiBuild(story, onFirstPage=rodape, onLaterPages=rodape)
    print("Guia gravado em", ARQ)


if __name__ == "__main__":
    main()
