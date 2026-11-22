"""Pasta de trabalho do Excel que roda o próprio motor (src/bansal) com Python no Excel (=PY).

Rodar da raiz: $env:PYTHONPATH="src"; python -m bansal.planilha_motor
Saída: excel/motor_bansal.xlsx

- Aba `base`: a base nominal (a mesma de data/padronizada/painel.xlsx, aba nominal). É a entrada: mude aqui.
- Abas `m_*`: o código de cada módulo de src/bansal, uma linha por linha da planilha. A célula A1 de cada
  uma carrega esse código como módulo Python. Não há outra cópia do motor: é o mesmo código do app.
- Abas `r_*`: células =PY() que chamam o motor e despejam os resultados (as mesmas saídas de data/saida).

As fórmulas =PY() são gravadas pelo próprio Excel (via COM), porque o openpyxl não sabe gravá-las.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter as L

RAIZ = Path(__file__).resolve().parents[2]
SRC = RAIZ / "src" / "bansal"
PAD = RAIZ / "data" / "padronizada" / "painel.xlsx"
ARQ = RAIZ / "excel" / "motor_bansal.xlsx"

# Ordem de carga: cada módulo depois dos que ele importa.
MODULOS = ["nomes", "estatistica", "simplex", "models", "indices", "li_test", "gmm", "painel", "padronizar",
           "calcular"]

NEG = Font(bold=True)
CAB = PatternFill("solid", fgColor="DDEBF7")
ENTRADA = PatternFill("solid", fgColor="FFF2CC")

SETUP = '''import sys, types
import numpy as np
import pandas as pd

def registrar(nome, tabela):
    """Carrega o código lido de uma aba m_* (coluna B, uma linha por linha) como o módulo bansal.<nome>."""
    linhas = tabela.iloc[:, 0]
    codigo = "\\n".join("" if pd.isna(v) else str(v) for v in linhas)
    if "bansal" not in sys.modules:
        pacote = types.ModuleType("bansal")
        pacote.__path__ = []
        sys.modules["bansal"] = pacote
    m = types.ModuleType("bansal." + nome)
    m.__package__ = "bansal"
    m.__file__ = "/projeto/src/bansal/" + nome + ".py"
    sys.modules["bansal." + nome] = m
    exec(compile(codigo, m.__file__, "exec"), m.__dict__)
    setattr(sys.modules["bansal"], nome, m)
    return "bansal." + nome + " carregado"

def mostrar(df):
    """Prepara a tabela para a planilha: sem índice, vazio no lugar de NaN e infinito."""
    df = df.reset_index(drop=True).rename_axis(columns=None).replace([np.inf, -np.inf], np.nan)
    return df.astype(object).where(df.notna(), "")

"funções de carga definidas"'''

RESULTADOS = [
    ("r_painel", "Painel real por agência (as 13 variáveis do paper)", '''from bansal import padronizar, painel as mod_painel
b = xl("base!A1:{ULT}", headers=True)
b["ano"] = b["ano"].astype(int)
NOM = b.drop(columns=["nome", "grupo"]).set_index(["bank_id", "ano"]).astype(float)
d = xl("deflator!A1:B10", headers=True)
DEFL = {int(a): float(v) for a, v in zip(d.iloc[:, 0], d.iloc[:, 1])}
P_, C_ = padronizar.painel_de_nominal(NOM, DEFL)
PAINEL, COV, META = mod_painel.montar(P_.reset_index(), C_.reset_index())
RES = P_.reset_index()'''),
    ("r_covariaveis", "Covariáveis do GMM", '''import numpy as np
RES = C_.reset_index()'''),
    ("r_tabela2", "Tabela 2: estatística descritiva", '''from bansal import calcular
RES = calcular.tabela2(PAINEL, META)'''),
    ("r_DMLPI", "DMLPI (rede, M1): EC, TC, índice e os quatro DDFs por banco e ano", '''from bansal import calcular
DET_DMLPI = calcular.indices_banco_ano(PAINEL, META, ["DMLPI"])
RES = DET_DMLPI'''),
    ("r_DSMLPI", "DSMLPI (rede sequencial, M2)", '''from bansal import calcular
DET_DSMLPI = calcular.indices_banco_ano(PAINEL, META, ["DSMLPI"])
RES = DET_DSMLPI'''),
    ("r_MLPI", "MLPI (caixa-preta)", '''from bansal import calcular
DET_MLPI = calcular.indices_banco_ano(PAINEL, META, ["MLPI"])
RES = DET_MLPI'''),
    ("r_SMLPI", "SMLPI (caixa-preta sequencial)", '''from bansal import calcular
DET_SMLPI = calcular.indices_banco_ano(PAINEL, META, ["SMLPI"])
RES = DET_SMLPI'''),
    ("r_tabela3", "Tabela 3: médias geométricas por ano (DMLPI e DSMLPI)", '''import pandas as pd
from bansal import calcular
DET = pd.concat([DET_DMLPI, DET_DSMLPI, DET_MLPI, DET_SMLPI], ignore_index=True)
RES = calcular.tabela_ano(DET, "DMLPI", ("EC_M1", "TC_M1", "DMLPI")).merge(
    calcular.tabela_ano(DET, "DSMLPI", ("EC_M2", "TC_M2", "DSMLPI")), on=["painel", "ano"])'''),
    ("r_tabela4", "Tabela 4: médias geométricas por banco", '''from bansal import calcular
RES = calcular.tabela4(DET)'''),
    ("r_tabela5", "Tabela 5: MLPI e SMLPI por ano", '''from bansal import calcular
RES = calcular.tabela_ano(DET, "MLPI", ("EC_ML", "TC_ML", "MLPI")).merge(
    calcular.tabela_ano(DET, "SMLPI", ("EC_SML", "TC_SML", "SMLPI")), on=["painel", "ano"])'''),
    ("r_tabelaB1", "Tabela B1: bancos públicos", '''import pandas as pd
from bansal import calcular
from bansal.nomes import BANCOS
pub = [b for b, _, g in BANCOS if g == "publico"]
RES = pd.concat([calcular.tabela_b(DET, "DMLPI", pub), calcular.tabela_b(DET, "DSMLPI", pub)]).reset_index(drop=True)'''),
    ("r_tabelaB2", "Tabela B2: bancos privados", '''import pandas as pd
from bansal import calcular
from bansal.nomes import BANCOS
priv = [b for b, _, g in BANCOS if g == "privado"]
RES = pd.concat([calcular.tabela_b(DET, "DMLPI", priv), calcular.tabela_b(DET, "DSMLPI", priv)]).reset_index(drop=True)'''),
    ("r_li", "Tabela 3, Painel D: teste de Li", '''from bansal import calcular
RES = calcular.li_por_componente(DET)'''),
    ("r_tabela6", "Tabela 6: GMM de sistema", '''from bansal import calcular
RES = calcular.tabela6(DET, COV, META)'''),
]


def montar_xlsx(destino):
    """Grava dados, código e textos. Devolve a lista de fórmulas =PY() a inserir (aba, célula, código, tipo)."""
    xl = pd.ExcelFile(PAD)
    nom = xl.parse("nominal")
    defl = xl.parse("deflator")
    wb = Workbook()
    ws = wb.active
    ws.title = "LEIA-ME"
    textos = [
        "Bansal et al. (2022) — o motor de cálculo do app rodando dentro do Excel (Python no Excel, =PY)",
        "",
        "1. A entrada é a aba base (valores nominais, Rs lakh) e a aba deflator. Mude um número ali e o Excel recalcula tudo.",
        "2. As abas m_* trazem o código de src/bansal, linha por linha. A célula A1 de cada uma carrega esse módulo.",
        "   É o mesmo código que o app usa: nada foi reescrito para o Excel.",
        "3. As abas r_* chamam o motor e mostram os resultados (os mesmos arquivos de data/saida).",
        "",
        "Ordem de cálculo do Python no Excel: abas da esquerda para a direita, células linha a linha.",
        "Por isso as abas m_* vêm antes das r_*. Não reordene as abas.",
        "",
        "O Python roda na nuvem da Microsoft: precisa de internet. Enquanto calcula, as células mostram #BUSY!.",
        "Para recalcular tudo: Fórmulas > Calcular Agora (ou Ctrl+Alt+F9). Uma mudança na base leva cerca de 25 s.",
        "Atenção: na pasta do OneDrive o Excel salva sozinho (AutoSave). Para testar mudanças sem perder a base original,",
        "trabalhe numa cópia do arquivo ou desligue o AutoSave.",
        "",
        "Se o código em src/bansal mudar, gere esta pasta de novo:",
        '   $env:PYTHONPATH="src"; python -m bansal.planilha_motor',
    ]
    for i, t in enumerate(textos, 1):
        ws.cell(i, 1, t)
    ws["A1"].font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 120

    wb_base = wb.create_sheet("base")
    for j, c in enumerate(nom.columns, 1):
        cell = wb_base.cell(1, j, c)
        cell.font, cell.fill = NEG, CAB
    for i, row in enumerate(nom.itertuples(index=False), 2):
        for j, v in enumerate(row, 1):
            cell = wb_base.cell(i, j, None if (isinstance(v, float) and pd.isna(v)) else v)
            if j > 4:
                cell.fill = ENTRADA
    wb_base.freeze_panes = "E2"
    ult = f"{L(nom.shape[1])}{nom.shape[0] + 1}"

    wd = wb.create_sheet("deflator")
    wd.append(list(defl.columns))
    for r in defl.itertuples(index=False):
        wd.append([int(r[0]), float(r[1])])
    for row in wd.iter_rows(min_row=2, min_col=2, max_col=2):
        for c in row:
            c.fill = ENTRADA

    formulas = []
    ws = wb.create_sheet("m_setup")
    ws["A2"] = "Define registrar(): lê o código de uma aba m_* e o carrega como módulo do pacote bansal."
    formulas.append(("m_setup", "A1", SETUP, 0))  # tipo 0 = valor do Excel (tabela despejada); 1 = objeto Python

    for mod in MODULOS:
        linhas = (SRC / f"{mod}.py").read_text(encoding="utf-8").splitlines()
        ws = wb.create_sheet(f"m_{mod}")
        ws["B2"] = f"src/bansal/{mod}.py"
        ws["B2"].font = NEG
        for k, t in enumerate(linhas, 1):
            ws.cell(2 + k, 1, k)
            if t.strip():
                assert not t.startswith("="), (mod, k, t)
                ws.cell(2 + k, 2, t)
        ws.column_dimensions["A"].width = 6
        ws.column_dimensions["B"].width = 120
        n = 2 + len(linhas)
        formulas.append((f"m_{mod}", "A1", f'registrar("{mod}", xl("m_{mod}!B3:B{n}"))', 0))

    for aba, titulo, codigo in RESULTADOS:
        ws = wb.create_sheet(aba)
        ws["A1"] = titulo
        ws["A1"].font = NEG
        formulas.append((aba, "A3", codigo.replace("{ULT}", ult) + "\nmostrar(RES)", 0))

    wb.save(destino)
    return formulas


PS = r'''
param([string]$entrada, [string]$saida, [string]$json)
$f = Get-Content -Raw -Encoding UTF8 $json | ConvertFrom-Json
$x = New-Object -ComObject Excel.Application
$x.DisplayAlerts = $false
$wb = $x.Workbooks.Open($entrada)
foreach ($i in $f) {
  $ws = $wb.Worksheets.Item($i.aba)
  $ws.Range($i.cel).Formula2 = '=PY("' + $i.codigo.Replace('"', '""') + '",' + $i.tipo + ')'
}
$x.CalculateFull()
$fim = (Get-Date).AddMinutes(10)
do {
  Start-Sleep -Seconds 3
  $ocupado = @($f | Where-Object { $wb.Worksheets.Item($_.aba).Range($_.cel).Text -match "BUSY|CONNECT" }).Count
} while ($ocupado -gt 0 -and (Get-Date) -lt $fim)
foreach ($i in $f) { "{0}!{1}: {2}" -f $i.aba, $i.cel, $wb.Worksheets.Item($i.aba).Range($i.cel).Text }
$wb.SaveAs($saida, 51)
$wb.Close($false)
$x.Quit()
'''


def main():
    ARQ.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        bruto = tmp / "sem_py.xlsx"
        formulas = montar_xlsx(bruto)
        js = tmp / "formulas.json"
        js.write_text(json.dumps([{"aba": a, "cel": c, "codigo": t, "tipo": k} for a, c, t, k in formulas],
                                 ensure_ascii=False), encoding="utf-8")
        ps = tmp / "inserir_py.ps1"
        ps.write_text(PS, encoding="utf-8-sig")
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps),
                            str(bruto), str(ARQ), str(js)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        print(r.stdout)
        if r.returncode:
            print(r.stderr)
            raise SystemExit(r.returncode)
    print("Pasta gravada em", ARQ)


if __name__ == "__main__":
    main()
