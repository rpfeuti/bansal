"""Teste de Li (1996) de igualdade entre duas densidades desconhecidas (Painel D da Tabela 3)."""

import math

import numpy as np

from .estatistica import normal_cdf

INT_K2 = 1.0 / (2.0 * math.sqrt(math.pi))  # integral do kernel gaussiano ao quadrado


def _k(u):
    return np.exp(-0.5 * u * u) / math.sqrt(2.0 * math.pi)


def li_teste(x, y):
    """Estatística T de Li (1996), kernel gaussiano e janela de Silverman na amostra conjunta.

    Devolve (T, p-valor unilateral da N(0, 1)).
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    x, y = x[np.isfinite(x)], y[np.isfinite(y)]
    n1, n2 = x.size, y.size
    z = np.concatenate([x, y])
    h = 1.06 * z.std(ddof=1) * z.size ** (-0.2)
    delta = n1 / n2

    kxx = _k((x[:, None] - x[None, :]) / h)
    kyy = _k((y[:, None] - y[None, :]) / h)
    kxy = _k((x[:, None] - y[None, :]) / h)

    np.fill_diagonal(kxx, 0.0)
    np.fill_diagonal(kyy, 0.0)
    I = (kxx.sum() / (n1 * (n1 - 1)) + kyy.sum() / (n2 * (n2 - 1)) - 2 * kxy.sum() / (n1 * n2)) / h

    np.fill_diagonal(kxx, _k(0.0))
    np.fill_diagonal(kyy, _k(0.0))
    s2 = 2 * INT_K2 * (kxx.sum() / (n1 ** 2 * h) + delta ** 2 * kyy.sum() / (n2 ** 2 * h)
                       + 2 * delta * kxy.sum() / (n1 * n2 * h))
    T = n1 * math.sqrt(h) * I / math.sqrt(s2)
    return T, 1.0 - normal_cdf(T)
