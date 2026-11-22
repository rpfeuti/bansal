# Roteiro para continuar a extração e gerar a base padronizada

Este documento é para outra IA (ou pessoa) continuar o trabalho sem depender do histórico das conversas. Leia tudo antes de escrever código.

---

## 1. Contexto do projeto

- Projeto: réplica em Python de Bansal, Kumar, Mehra & Gulati (2022), *Omega* 107, 102538. O PDF está na raiz: `Bansal(2022).pdf`.
- Pasta do projeto: `c:\Users\rpfeu\OneDrive\Projects\bansal` (Windows, PowerShell, Python 3.11).
- O cálculo (DDF por programação linear própria, índices DMLPI/DSMLPI/MLPI/SMLPI e GMM de sistema) já existe em `src/bansal/`:
  - `models.py`: modelos (M1), (M2) e caixa-preta. Define os **nomes das variáveis** que o painel precisa ter.
  - `simplex.py`: simplex próprio (sem biblioteca de PL).
  - `indices.py`: índices e decomposição EC/TC.
  - `gmm.py`, `estatistica.py`, `li_test.py`: segunda etapa e testes.
  - `nomes.py`: lista dos 42 bancos (`BANCOS`) e função `bank_id(nome)` que mapeia qualquer grafia de nome para o código do banco.
  - `baixar.py`: script de download já executado (não rodar de novo).
- **Ainda não existe** a base padronizada nem o app Streamlit.

### Estrutura de pastas combinada com o usuário

- `data/raw/`: somente arquivos crus, todos em `.xlsx`. Não alterar.
- `data/padronizada/`: um estágio que padroniza tudo, deixando só o que entra no cálculo, já normalizado (nomes, unidades, deflator, divisão por agências).
- `data/saida/`: resultados calculados para o Streamlit (etapa posterior).

---

## 2. Regras obrigatórias do usuário (em `.cursor/rules/`)

1. **Não baixar nada da internet sem perguntar antes** (curl, wget, Invoke-WebRequest, pip, navegador salvando arquivo, etc.). Perguntar o que, de qual URL e onde salvar. Nesta etapa a ordem é: **não baixar mais nada**, usar só o que está em `data/raw/`.
2. **Fidelidade ao paper**: o paper é a única especificação.
   - Não inventar variável, modelo, teste, índice, gráfico ou opção.
   - Não comentar qualidade dos dados, auditoria, robustez ou divergências (nem em respostas, nem no código, nem no app).
   - Não "bater" com a Tabela 2 como critério de bloqueio; no máximo mostrar calculado ao lado do publicado, sem comentário.
   - Quando o paper não diz algo, perguntar ao usuário de forma curta com o trecho do paper e as opções. Não decidir sozinho em silêncio.
3. Estilo com o usuário: respostas curtas, diretas, em português. Ele se irrita com rodeios, com perguntas repetidas e com a IA dizendo que "terminou" quando não terminou. Seja exato sobre o que existe e o que falta.

---

## 3. O que o paper especifica (seção 4)

### Amostra e período
- 42 bancos (25 públicos e 17 privados) listados em `src/bansal/nomes.py` na ordem da Tabela 4.
- Período do estudo: 2010 a 2017. Como há variáveis em t-1 (NPL, ativos não usados, lucro), a base precisa de **2009 a 2017**.
- Ano t = posição em 31 de março de t (ano fiscal indiano (t-1)-t).
- Fonte declarada: *Statistical Tables Relating to Banks in India* (STRBI, RBI).

### Tabela 1 (variáveis da rede em três divisões)

| Papel | Variável no paper | Nome em `models.py` |
|---|---|---|
| Insumo desejável div. 1 | Labor | `labor` |
| Insumo desejável div. 1 | Fixed assets | `fixed_assets` |
| Quase-fixo div. 1 | Equity | `equity` |
| Elo div. 1 para 2 | Deposits | `deposits` |
| Insumo desejável div. 2 | Inter-bank borrowings | `borrowings` |
| Insumo indesejável div. 2 (t-1) e produto indesejável (t) | NPLs | `npl` |
| Carryover div. 2 (t-1) | Unused assets | `unused_assets` |
| Carryover div. 2 (t-1) | Net profit | `net_profit` |
| Elo div. 2 para 3 | Performing loans | `performing_loans` |
| Elo div. 2 para 3 | Investments | `investments` |
| Insumo div. 3 | Loan loss provisions | `provision` |
| Produto div. 3 | Net-interest income | `net_interest_income` |
| Produto div. 3 | Non-interest income | `non_interest_income` |

Definições textuais do paper:
- Performing loans = total loans − non-performing loans.
- Unused assets = total assets − (required reserves + fixed capital + loans + securities investments) (seguindo Fukuyama e Weber).

### Transformações
- Todas as variáveis em valor corrente, **exceto labor**, são deflacionadas pelo deflator implícito do PIB a custo de fatores, base 2011-12 = 100.
- **Todas** as variáveis (inclusive labor) são divididas pelo número de agências do banco.
- Tabela 2: tudo em INR lakh, exceto labor. 1 crore = 100 lakh; 1 milhão = 10 lakh.

### Covariáveis da segunda etapa (texto da seção 4.4 e Tabela 6)

| Covariável | Definição no paper |
|---|---|
| `G_NPLs` | crescimento dos NPLs |
| `SIZE` | log natural do ativo total |
| `IC` | custo de intermediação / ativo total |
| `EQTA` | patrimônio / ativo total |
| `LIQUIDITY` | empréstimos / depósitos |
| `BME` | salários / despesas não financeiras (non-interest expenses) |
| `PRIORITY` | crédito ao setor prioritário / ativo total |
| `DIVERSIFICATION` | índice de Stiroh e Rumble com as participações da receita líquida de juros e da receita não financeira: 1 − s_NII² − s_NON² |

---

## 4. Inventário do que já está em `data/raw/` (tudo `.xlsx`)

### 4.1 Measure (measure.thisindianlife.today), republica as séries do RBI/DBIE
Cada arquivo tem aba `dados` (1ª coluna = data, demais = séries) e aba `fonte` (URL e data do download).

| Arquivo | Frequência | Uso |
|---|---|---|
| `measure_banks_balance_sheet.xlsx` | trimestral, dez/2013 a mar/2026 | balanço 2015 a 2017 (março de 2014 vem **vazio** nos itens "global operations") |
| `measure_bank_earnings.xlsx` | anual (março), 2005 a 2025 | receitas, despesas, lucro, provisões |
| `measure_bank_provisions.xlsx` | anual, 2005 a 2025 | provisões por tipo (NPA etc.) |
| `measure_credit_npa_movement.xlsx` | anual, 2005 a 2025 | NPA bruto |
| `measure_employees_banks.xlsx` | anual, 2005 a 2025 | empregados |
| `measure_offices_banks.xlsx` | trimestral, 2006 a 2026 | agências |
| `measure_priority_sector_banks.xlsx` | anual, 2005 a 2025 | crédito prioritário |

**Unidade do Measure: Rs crore** (verificado: Allahabad Bank, juros recebidos 2013 = 17.435,69; ativo total mar/2015 = 227.394,31). Multiplicar por 100 para lakh. Antes de fechar, confirmar com a tabela B2 de 2013 do STRBI (em Rs milhão), comparando um ou dois bancos.

**Formatos dos nomes de coluna** (cuidado, variam por arquivo):
- Balanço: `"Allahabad Bank, total assets, global operations"` → banco, item, escopo. Usar só `global operations`.
- Earnings, provisions, employees, offices, priority: `"Nationalised banks, Allahabad bank, Earnings, Total (I)"` → grupo, banco, item.
- NPA: `"AB BANK (foreign banks): gross NPAs at the end of the year"` → `BANCO (grupo): item`.
- O mesmo banco aparece com **mais de um rótulo de grupo** (ex.: "Nationalised banks" e "Public sector banks"), cada um preenchido em anos diferentes. Juntar pegando o primeiro valor não nulo por banco, ano e item.
- Nomes antigos e novos do mesmo banco (Ratnakar/RBL, Catholic Syrian/CSB, Development Credit/DCB, Dhanlakshmi/Dhanlaxmi) já estão em `GRAFIAS` de `nomes.py`. Para identificar o banco: tentar `bank_id()` no texto antes de `" ("`, ou em cada parte separada por vírgula.
- Datas: pegar só as linhas de **mês 3** (março). Ano da data = ano t.

**Itens a usar no Measure** (comparar o final do nome da coluna, com igualdade exata do item):

| Variável | Arquivo | Item |
|---|---|---|
| juros recebidos | earnings | `Earnings, Total (I)` |
| receita não financeira | earnings | `Earnings, Total (II)` |
| juros pagos | earnings | `Expenses, Total (III)` |
| despesas operacionais | earnings | `Expenses, Total (IV)` |
| salários | earnings | `Expenses, Payments to and provisions for employees` |
| provisões e contingências | earnings | `Expenses, Provisions and Contingencies` |
| lucro líquido | earnings | `Expenses, Profit (Loss) during the year` |
| provisão para NPA (alternativa) | provisions | item `NPA` (faltam de 1 a 4 bancos por ano) |
| NPA bruto | npa_movement | `gross NPAs at the end of the year` |
| empregados | employees | `Total` |
| agências | offices | soma de todas as colunas terminadas em `, Branch` (Metropolitan, Urban, Semi-urban, Rural) |
| crédito prioritário 2013 a 2015 | priority | `Total Priority Sector Advances (PSA), Priority Sector, Amount Outstanding` |
| crédito prioritário 2016 a 2017 | priority | `Priority Sector, Amount Outstanding` (cuidado: não confundir com `... Loans to Weaker Sections under Priority Sector, Amount Outstanding`) |
| balanço 2015 a 2017 | balance_sheet | `paid-up share capital`, `reserves and surplus`, `total deposits`, `total borrowings`, `cash funds`, `SLR/approved securities` + `non-SLR investments`, `net loans and advances`, `fixed assets (net)`, `total assets` (todos com `, global operations`) |

Observação: confirmar se `cash funds` = caixa + saldo no RBI (equivalente a "Cash in hand" + "Balances with RBI" do B1). Se houver dúvida, perguntar ao usuário.

Cobertura já verificada para os 42 bancos, 2009 a 2017: earnings, NPA, empregados e agências completos. Crédito prioritário no Measure: completo de 2013 a 2017; de 2009 a 2012 só os 25 públicos (os privados vêm do B1, ver abaixo).

### 4.2 STRBI do RBI (`data/raw/strbi/`)
Sufixo do arquivo = ano final da edição. Cada edição do B1 e do B2 traz **dois anos**.

| Arquivo | Conteúdo | Anos | Unidade |
|---|---|---|---|
| `b1_2010.xlsx` | B1 balanço por banco | 2009 e 2010 | Rs lakh |
| `b1_2011.xlsx` | B1 | 2010 e 2011 | Rs lakh |
| `b1_2013.xlsx` | B1 | 2012 e 2013 | Rs milhão (×10 para lakh) |
| `b2_2010/2011/2013` | B2 receitas e despesas | dois anos cada | lakh / lakh / milhão |
| `b4_2010..2013` | B4 provisões | um ano cada (b4_2009 não foi baixado) | ver cabeçalho |
| `b13_2010/2011/2013` | B13 agências | | |
| `b15_2010/2011/2013` | B15 empregados | | |
| `p61_2010/2011/2013` | Tabela 6.1 crédito prioritário **por estado** (não por banco) | não serve para PRIORITY | |

**Layout do B1** (as três edições diferem, mas seguem o mesmo padrão):
- Abas por grupo (SBI e associados, nacionalizados, outros públicos, privados antigos, privados novos, estrangeiros). Em 2011 e 2013 cada grupo é dividido em passivo (Liab, "- I") e ativo (Assets, "- II").
- Há uma **linha de anos** (células com "2009", "2010" etc., às vezes com espaço na frente).
- Acima dela, uma **linha com o nome do banco** na primeira coluna do par de anos (fazer forward-fill para a direita).
- O **rótulo do item** fica numa coluna à esquerda da primeira coluna de ano (coluna 1 ou 2 conforme a aba).
- Abaixo de vários itens há uma linha só com percentuais entre parênteses, ex.: `( 5.5)`. Ignorar (linha sem rótulo).
- Valores vêm como texto com espaços; `-` significa zero.
- Unidade no cabeçalho: "(Amount in Rs. lakh)" ou "(Amount in ` Million)".
- Na aba `SBI&A - II` de 2013 a ordem dos bancos é diferente da aba I. Por isso, ler o nome do banco em cada aba.
- Ignorar State Bank of Indore, que não está na amostra (`bank_id` devolve None).

Rótulos a capturar (normalizar espaços; usar regex no início do rótulo):

| Item | Rótulo |
|---|---|
| capital | `1. Capital` |
| reservas | `2. Reserves and Surplus` |
| depósitos | `3. Deposits` |
| empréstimos tomados | `4. Borrowings` |
| caixa | `1. Cash in hand` |
| saldo no RBI | `2. Balances with RBI` |
| investimentos | `6. Investments` (o total, não `6.1`) |
| adiantamentos | `7. Advances` (o total) |
| crédito prioritário | `(i) Priority sectors` (dentro de `7C.I. Advances in India`) |
| ativo fixo | `8. Fixed Assets` |
| ativo total | `Total Assets` |

Ano repetido entre edições (2010 aparece em b1_2010 e b1_2011): usar a edição mais recente.

### 4.3 Balanço de 31/03/2014 (`data/raw/2014/`)
- Março de 2014 não existe no Measure nem nas edições do STRBI baixadas. Foi montado a partir dos relatórios anuais dos bancos.
- **Arquivo final: `data/raw/2014/b1_2014.xlsx`**, aba `b1_2014`, 42 bancos, sem vazios, **em Rs crore**. Colunas: `bank_id, capital, reservas, depositos, emprestimos_tomados, caixa_rbi, investimentos, adiantamentos, ativo_fixo, ativo_total`. Aba `fonte` com a origem de cada banco.
- `caixa_rbi` já é caixa + saldo no RBI somados.
- SBH: média de 31/03/2013 (B1) e 31/03/2015 (Measure), por decisão do usuário (nenhum relatório de 2013-14 ou 2014-15 localizado).
- CSB e NAIN: valores publicados, lidos de `CSB.pdf` (p.37) e `NAIN.pdf` (p.46, imagem), baixados com autorização do usuário.
- Os demais `.xlsx`, `.txt`, `.png` e `_*.py` dessa pasta são intermediários da extração. Não usar diretamente.
- Crédito prioritário de 2014 vem do Measure.

### 4.4 Deflator (`data/raw/mospi_gva.xlsx`)
- Colunas: `ano_fiscal`, `gva_corrente_crore`, `gva_constante_2011_12_crore`, `indice_implicito_2011_12`, `fonte`.
- De 2008-09 a 2011-12: índice = corrente / constante × 100.
- De 2012-13 a 2016-17: usar `indice_implicito_2011_12`.
- Ano t (31 de março de t) usa o ano fiscal "(t-1)-(t mod 100)", ex.: 2014 → "2013-14".

### 4.5 Tabelas do paper (`data/raw/artigo_tabelas.xlsx`)
Tabelas 2, 3, 3 (teste de Li), 4, 5, 6, B1 e B2 transcritas. Só para exibir ao lado do calculado.

---

## 5. Decisões já tomadas e decisões abertas

Já decididas pelo usuário:
- 2014 montado pelos relatórios anuais; só o SBH pela média de 2013 e 2015.
- Tudo em `.xlsx`; `raw` só com arquivos crus.
- Não baixar mais nada nesta etapa.

Propostas no último plano (o usuário aprovou o plano para executar, mas confirme se houver dúvida):
- **Loan loss provisions** = `Provisions and Contingencies` (completo). Alternativa: provisões para NPA do arquivo de provisões.
- **Resultado, empregados e agências de 2009 a 2013** vêm do Measure (contínuo de 2009 a 2017). B2, B4, B13 e B15 do STRBI ficam sem uso.
- **Reservas obrigatórias** (para unused assets) = caixa + saldo no RBI.
- **Performing loans** = adiantamentos do balanço − NPA líquido (decisão do usuário em 22/11/2026).
- **NPL** = NPA líquido no fim do ano (decisão do usuário em 22/11/2026). Fonte: Measure (`net NPAs at the end of the year`); onde o Measure não tem valor (NAIN 2009–2015), o STRBI: B6 (`strbi/b6_*.xlsx`, 2009–2013) e Tabela 6 do DBIE (`strbi/dbie_t06_2015_2025.xlsx`, 2014–2017). No STRBI o NPA líquido do NAIN de 2009 a 2015 é zero. O Measure foi conferido banco a banco contra essas tabelas do STRBI.
- **Borrowings** = total de empréstimos tomados (item 4 do B1).
- **Equity** = capital + reservas.
- **Net-interest income** = Total (I) − Total (III).
- **IC**: custo de intermediação = despesas operacionais (Total IV).
- **BME** = salários / despesas operacionais (Total IV).
- **SIZE** = ln do ativo total deflacionado.
- Covariáveis em razão calculadas com valores nominais (a razão não muda com deflator nem com a divisão por agências).

---

## Estado atual (base gerada)

- `src/bansal/padronizar.py` está implementado e gera `data/padronizada/painel.xlsx`. Rodar da raiz com `$env:PYTHONPATH="src"; python -m bansal.padronizar`.
- Resultado: as 13 variáveis estão completas para os 42 bancos de 2009 a 2017. Covariáveis completas, exceto G_NPLs de 2009 (vazio por definição) e G_NPLs do NAIN: vazio de 2010 a 2015 (0/0) e infinito em 2016 (NPL líquido de 2015 = 0); essas observações ficam fora do GMM.
- Unidade do Measure confirmada como Rs crore: Allahabad 2013, juros recebidos 174.357 (B2, Rs milhão) = 17.435,69 (Measure).
- Investimentos do Measure (SLR + non-SLR) conferidos: a soma dos ativos fecha com o ativo total (Allahabad 2016).
- Painel, índices, Tabelas 2–6 / B1 / B2, teste de Li e GMM gravados em `data/saida/`.
- App: `app.py` (Streamlit). Rodar: `$env:PYTHONPATH='src'; python -m streamlit run app.py`
- Recalcular: `$env:PYTHONPATH='src'; python -m bansal.calcular`

## 6. Passo a passo da implementação

Criar `src/bansal/padronizar.py`, executável com `python -m bansal.padronizar` a partir da raiz (o pacote está em `src/`, então rodar com `$env:PYTHONPATH="src"` ou ajustar `sys.path`).

1. **Leitor B1** `ler_b1(arquivo) -> DataFrame(bank_id, ano, item, valor_lakh, fonte)`
   - Abrir todas as abas (exceto `fonte`) com `header=None`.
   - Detectar a unidade pelo texto do cabeçalho (lakh = ×1; Million = ×10).
   - Encontrar a linha de anos (pelo menos 2 células que casam `^\s*20\d\d\s*$`).
   - Nas até 3 linhas acima, achar os nomes dos bancos e fazer forward-fill por coluna.
   - Para cada linha abaixo, pegar o rótulo na primeira célula de texto à esquerda da primeira coluna de ano; casar com os rótulos da seção 4.2.
   - Converter valores: tirar espaços; `-` vira 0; percentuais entre parênteses são ignorados porque essas linhas não têm rótulo.
   - Aplicar `bank_id()` ao nome e descartar None.
2. **Leitor b1_2014**: ler a aba `b1_2014`, ×100, `ano = 2014`.
3. **Leitor Measure** `ler_measure(arquivo, itens) -> DataFrame(bank_id, ano, item, valor_lakh)`
   - Filtrar linhas de março; identificar banco e item pelo nome da coluna (seção 4.1); juntar grupos duplicados pelo primeiro não nulo; ×100 (exceto empregados e agências, que são contagens).
4. **Confirmar a unidade do Measure** comparando 2013 de `measure_bank_earnings` com `b2_2013` (convertido para lakh) para 2 ou 3 bancos. Se não bater em fator 100, parar e avisar o usuário.
5. **Montar o painel nominal** (bank_id × ano, 2009 a 2017):
   - Balanço: B1 para 2009 a 2013, b1_2014 para 2014, Measure para 2015 a 2017.
   - Crédito prioritário: B1 para 2009 a 2013, Measure para 2014 a 2017.
   - Resto: Measure.
   - Calcular `equity`, `unused_assets`, `performing_loans`, `net_interest_income`.
6. **Deflacionar**: dividir por (índice do ano fiscal / 100) todas as variáveis monetárias; `labor` não.
7. **Normalizar por agências**: dividir todas as 13 variáveis (inclusive labor) pelo número de agências do banco no ano.
8. **Covariáveis**: calcular as 8 da seção 3. `G_NPLs` de 2009 fica vazio (não há 2008).
9. **Gravar `data/padronizada/painel.xlsx`** com as abas:
   - `painel`: `bank_id, nome, grupo, ano` + 13 variáveis (deflacionadas e por agência).
   - `covariaveis`: `bank_id, ano` + 8 covariáveis.
   - `nominal`: níveis em Rs lakh antes de deflacionar e dividir, mais `agencias` e `prioritario`.
   - `fonte`: variável, ano, arquivo, item.
   - `faltantes`: banco, ano, variável de cada célula vazia.
10. **Imprimir no terminal**: número de bancos com dados completos por ano e a lista detalhada de faltantes. Essa lista é o que o usuário chama de "o que falta baixar".

---

## 7. Como o resto do código consome a base

- `models.py` espera `painel[ano][variavel]` como vetor numpy com um valor por banco, **na mesma ordem dos bancos em todos os anos** (usar a ordem de `BANCOS`).
- Os índices usam pares de anos (t, t+1) de 2010 a 2017; `npl` e os carryovers também são lidos em t-1, por isso 2009 é necessário.
- Depois da base: gerar `data/saida/` (índices, Tabelas 3, 4, 5, B1, B2, teste de Li, GMM da Tabela 6) e montar o app Streamlit mostrando calculado ao lado do publicado (`artigo_tabelas.xlsx`), sem colunas de erro e sem comentários.

---

## 8. Armadilhas conhecidas

- Não usar `p61_*.xlsx` para PRIORITY (é por estado).
- O balanço do Measure em março de 2014 está vazio: não confundir com cobertura (outras colunas, como "domestic operations", podem ter valor).
- Comparar itens do Measure por igualdade exata do sufixo; `Priority Sector, Amount Outstanding` também é sufixo de outros itens.
- No B1 de 2010, as abas de grupos têm muitas colunas vazias entre os bancos; o forward-fill do nome deve parar na próxima coluna com nome.
- Itens com subitens (ex.: `2.1 Statutory Reserves`) não podem ser capturados por um regex frouxo como "Reserves"; ancorar no número do item.
- Não alterar nada em `data/raw/`.
- Não rodar `baixar.py` nem qualquer download.
