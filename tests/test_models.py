import numpy as np

from src.bansal import indices, models

VARS = ["labor", "fixed_assets", "equity", "deposits", "borrowings", "npl", "unused_assets", "net_profit",
        "performing_loans", "investments", "provision", "net_interest_income", "non_interest_income"]


def painel_sintetico(n=8, anos=range(2009, 2014), semente=0):
    rng = np.random.default_rng(semente)
    base = {v: rng.uniform(50, 500, n) for v in VARS}
    p = {}
    for k, a in enumerate(anos):
        p[a] = {v: base[v] * rng.uniform(0.97, 1.06, n) * (1.03 ** k) for v in VARS}
        p[a]["equity"] = np.full(n, 100.0)  # (6) não tem beta: equity abaixo do mínimo da fronteira é inviável
        p[a]["net_profit"] = p[a]["net_profit"] - 150  # lucro pode ser negativo
        p[a]["provision"] = p[a]["provision"] - 60  # provisão pode ser negativa
    return p


def test_teoremas_1_e_2():
    p = painel_sintetico()
    anos = list(range(2010, 2014))
    for modelo in ("M1", "M2"):
        for r in indices.calcular_ddfs(p, anos, modelo):
            for k in ("D00", "D01", "D10", "D11"):
                assert r[k] > -1
            assert r["D00"] >= -1e-9 and r["D11"] >= -1e-9


def test_sequencial_contem_contemporanea():
    p = painel_sintetico()
    anos = list(range(2010, 2014))
    m2 = indices.calcular_ddfs(p, anos, "SML")
    ml = indices.calcular_ddfs(p, anos, "ML")
    for a, b in zip(m2, ml):
        assert a["D11"] >= b["D11"] - 1e-9  # tecnologia sequencial contém a do ano
        assert a["D00"] >= -1e-9 and b["D00"] >= -1e-9


def test_componentes():
    ec, tc, idx = indices.componentes(0.1, 0.2, 0.05, 0.0)
    assert np.isclose(idx, np.sqrt((1.1 / 1.2) * (1.05 / 1.0)))
    assert np.isclose(ec * tc, idx)
