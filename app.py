"""App Streamlit: tabelas calculadas ao lado das publicadas no paper.

Rodar da raiz: $env:PYTHONPATH='src'; streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "data" / "saida"
ARTIGO = RAIZ / "data" / "raw" / "artigo_tabelas.xlsx"
PAD = RAIZ / "data" / "padronizada" / "painel.xlsx"

st.set_page_config(page_title="Bansal et al. (2022)", layout="wide")
st.title("Bansal, Kumar, Mehra & Gulati (2022)")
st.caption("Réplica em Python. Calculado ao lado do publicado.")


@st.cache_data
def ler_xlsx(caminho):
    return pd.read_excel(caminho)


@st.cache_data
def artigo():
    return pd.read_excel(ARTIGO, sheet_name=None)


def comparar(calc, pub, chaves, metricas, casas=3):
    """Uma linha por observação, com cada métrica em duas colunas: calculado e paper."""
    metricas = [m for m in metricas if m in calc.columns and m in pub.columns]
    a = calc[chaves + metricas].copy()
    b = pub[chaves + metricas].copy()
    for k in chaves:
        a[k] = a[k].map(lambda v: str(v).strip())
        b[k] = b[k].map(lambda v: str(v).strip())
    m = a.merge(b, on=chaves, how="outer", suffixes=(" · calculado", " · paper"))
    ordem = b[chaves].drop_duplicates()
    ordem.insert(0, "_ord", range(len(ordem)))
    m = ordem.merge(m, on=chaves, how="right").sort_values("_ord", na_position="last")
    cols = [(k, "") for k in chaves]
    dados = {k: m[k] for k in chaves}
    for met in metricas:
        dados[(met, "calculado")] = pd.to_numeric(m[f"{met} · calculado"], errors="coerce")
        bruto = m[f"{met} · paper"]
        num = pd.to_numeric(bruto, errors="coerce")
        # Mantém o texto do paper quando a célula não é número (ex.: "-").
        dados[(met, "paper")] = num.where(num.notna(), bruto.where(bruto.notna(), pd.NA))
        cols += [(met, "calculado"), (met, "paper")]
    out = pd.DataFrame(dados)
    out.columns = pd.MultiIndex.from_tuples(cols)

    def _fmt(v):
        if isinstance(v, str):
            return v
        if pd.isna(v):
            return ""
        return f"{v:.{casas}f}"

    for col in out.columns:
        if col[1] in ("calculado", "paper"):
            out[col] = out[col].map(_fmt)
    return out


def _tabela4(calc, pub, t3):
    """As duas médias geométricas do paper (públicos e privados) saem da Tabela 3, 2010-17."""
    calc = calc.drop(columns=["grupo"], errors="ignore")
    calc = calc[calc["banco"] != "Geometric mean"]
    medias = []
    for painel, rotulo in (("publico", "Geometric mean · públicos"),
                           ("privado", "Geometric mean · privados")):
        row = t3[(t3["painel"] == painel) & (t3["ano"].astype(str) == "2010-17")].iloc[0]
        medias.append({"banco": rotulo, **{c: row[c] for c in row.index if c not in ("painel", "ano")}})
    calc = pd.concat([calc, pd.DataFrame(medias)], ignore_index=True)
    n = 0
    rotulos = []
    for nome in pub["banco"]:
        if nome == "Geometric mean":
            n += 1
            rotulos.append("Geometric mean · públicos" if n == 1 else "Geometric mean · privados")
        else:
            rotulos.append(nome)
    pub = pub.copy()
    pub["banco"] = rotulos
    return calc, pub


def mostrar(titulo, tabela):
    st.subheader(titulo)
    st.dataframe(tabela, width="stretch", hide_index=True)


def main():
    if not SAIDA.exists() or not any(SAIDA.glob("*.xlsx")):
        st.warning("Não há resultados em data/saida/. Rode: python -m bansal.calcular")
        return
    art = artigo()
    pag = st.sidebar.radio("Tela", ["Dados", "Índices", "Segunda etapa"])

    if pag == "Dados":
        st.header("Dados")
        painel = ler_xlsx(PAD)
        st.markdown("Painel padronizado (13 variáveis, deflacionadas e por agência)")
        st.dataframe(painel, width="stretch", hide_index=True)
        if (SAIDA / "tabela2.xlsx").exists():
            mets = ["mean", "sd", "kurtosis", "skewness", "median", "max", "min"]
            mostrar("Tabela 2 — estatísticas descritivas",
                    comparar(ler_xlsx(SAIDA / "tabela2.xlsx"), art["tabela2"], ["variavel"], mets, casas=2))

    elif pag == "Índices":
        st.header("Índices")
        m3 = ["EC_M1", "TC_M1", "DMLPI", "EC_M2", "TC_M2", "DSMLPI"]
        mostrar("Tabela 3 — DMLPI e DSMLPI (médias geométricas)",
                comparar(ler_xlsx(SAIDA / "tabela3.xlsx"), art["tabela3"], ["painel", "ano"], m3))
        if (SAIDA / "tabela3_li.xlsx").exists():
            li = ler_xlsx(SAIDA / "tabela3_li.xlsx").set_index("componente")[["teste_li", "p_valor"]].T
            li.index.name = "estatistica"
            li = li.reset_index()
            mostrar("Tabela 3, painel D — teste de Li",
                    comparar(li, art["tabela3_li"], ["estatistica"], m3))
        mostrar("Tabela 4 — por banco (2010–2017)",
                comparar(*_tabela4(ler_xlsx(SAIDA / "tabela4.xlsx"), art["tabela4"],
                                   ler_xlsx(SAIDA / "tabela3.xlsx")),
                         ["banco"], m3))
        m5 = ["EC_ML", "TC_ML", "MLPI", "EC_SML", "TC_SML", "SMLPI"]
        mostrar("Tabela 5 — MLPI e SMLPI",
                comparar(ler_xlsx(SAIDA / "tabela5.xlsx"), art["tabela5"], ["painel", "ano"], m5))
        mb = ["EC", "TC", "IDX"]
        with st.expander("Apêndice B1 (bancos públicos)"):
            mostrar("Tabela B1", comparar(ler_xlsx(SAIDA / "tabelaB1.xlsx"), art["tabelaB1"],
                                          ["indice", "banco", "ano"], mb))
        with st.expander("Apêndice B2 (bancos privados)"):
            mostrar("Tabela B2", comparar(ler_xlsx(SAIDA / "tabelaB2.xlsx"), art["tabelaB2"],
                                          ["indice", "banco", "ano"], mb))

    else:
        st.header("Segunda etapa")
        if (SAIDA / "tabela6.xlsx").exists():
            m6 = ["EC_M1", "TC_M1", "DMLPI", "EC_M2", "TC_M2", "DSMLPI"]
            pub6 = art["tabela6"]
            calc6 = ler_xlsx(SAIDA / "tabela6.xlsx")
            # A Tabela 6 do paper traz coeficiente e erro-padrão. O p-valor numérico
            # só aparece em AR(1), AR(2), Sargan e Hansen J.
            publicados = pub6[["regressor", "estatistica"]].drop_duplicates()
            calc6 = calc6.merge(publicados, on=["regressor", "estatistica"])
            mostrar("Tabela 6 — GMM de sistema em dois passos",
                    comparar(calc6, pub6, ["regressor", "estatistica"], m6, casas=4))
        else:
            st.info("Tabela 6 ainda não foi gerada.")


if __name__ == "__main__":
    main()
