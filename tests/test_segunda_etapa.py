import numpy as np

from src.bansal.estatistica import chi2_sf
from src.bansal.gmm import system_gmm
from src.bansal.li_test import li_teste


def test_chi2():
    assert abs(chi2_sf(3.841458820694124, 1) - 0.05) < 1e-9
    assert abs(chi2_sf(18.307038053275146, 10) - 0.05) < 1e-9


def test_li_iguais_e_diferentes():
    rng = np.random.default_rng(0)
    _, p_igual = li_teste(rng.normal(size=300), rng.normal(size=200))
    T, p_dif = li_teste(rng.normal(size=300), rng.normal(1.0, 1.0, size=200))
    assert p_igual > 0.05
    assert p_dif < 0.01 and T > 0


def test_system_gmm_recupera_coeficientes():
    rng = np.random.default_rng(3)
    N, T = 400, 7
    eta = rng.normal(size=N)
    x = rng.normal(size=(N, T))
    y = np.zeros((N, T))
    y[:, 0] = eta / (1 - 0.5) + rng.normal(size=N)
    for t in range(1, T):
        y[:, t] = 0.5 * y[:, t - 1] + 0.3 * x[:, t] + eta + rng.normal(size=N)
    r = system_gmm(y, [x], ["L.y", "x", "const"])
    assert abs(r["coef"][0] - 0.5) < 0.1
    assert abs(r["coef"][1] - 0.3) < 0.1
    assert r["AR2"] > 0.05
    assert r["AR1"] < 0.05
    assert r["hansen_p"] > 0.01
