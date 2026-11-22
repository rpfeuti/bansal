# Regras do projeto

Réplica de Bansal, Kumar, Mehra & Gulati (2022), Omega 107, 102538 (`Bansal(2022).pdf`).

Estas regras consolidam as de `.cursor/rules/` (usadas pelo Cursor). Ao mudar uma regra, mudar nos dois lugares.

## 1. Fidelidade ao paper

O paper é a única especificação. O objetivo é entender o que os autores fizeram, reproduzindo os passos. Não é avaliar, auditar nem criticar o paper, os dados ou as fontes.

### Não inventar

- Modelos, variáveis, amostra, anos, deflator, escala, testes e especificações do GMM saem do paper.
- Não acrescentar variável, índice, modelo, teste, verificação, gráfico, tela ou opção que o paper não tenha.
- Não "melhorar" o método nem propor alternativas.
- Não comentar qualidade dos dados, auditoria, robustez, limitações ou divergências, nem nas respostas, nem nos planos, nem no app.
- Não preencher lacuna com suposição silenciosa.

### Quando o paper não diz

Perguntar ao usuário de forma curta, com o trecho do paper e as opções. Não decidir sozinho.

As decisões já tomadas pelo usuário estão registradas em `ROTEIRO_EXTRACAO.md`. Seguir o que está lá.

### Exemplos

- ERRADO: "o balanço 1221 não é auditado".
- ERRADO: bloquear uma etapa até a Tabela 2 "bater", ou mostrar coluna de erro e desvio.
- ERRADO: incluir bancos estrangeiros, interpolar agências faltantes, adicionar um índice clássico.
- CERTO: mostrar a tabela calculada ao lado da publicada, sem comentário.

## 2. Não baixar arquivos sem perguntar

Nunca baixar arquivos da internet sem perguntar antes ao usuário.

- Vale para qualquer meio: `curl`, `wget`, `Invoke-WebRequest`, `Invoke-RestMethod`, `git clone`, `pip`/`npm` que busquem pacotes, scripts que fazem download, `WebFetch` salvando em disco.
- Antes de baixar, perguntar de forma curta: o que será baixado, a URL de origem e onde será salvo.
- Só baixar depois de o usuário confirmar.
