"""Distribuições normal e qui-quadrado, para os p-valores."""

import math


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _gama_inferior_regularizada(a: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x < a + 1:
        soma = termo = 1.0 / a
        k = a
        for _ in range(1000):
            k += 1
            termo *= x / k
            soma += termo
            if abs(termo) < abs(soma) * 1e-15:
                break
        return soma * math.exp(-x + a * math.log(x) - math.lgamma(a))
    # fração contínua (Lentz) para a gama superior
    b = x + 1 - a
    c = 1e300
    d = 1 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return 1.0 - math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi2_sf(x: float, gl: int) -> float:
    """P(Qui2(gl) > x)."""
    if gl <= 0:
        return float("nan")
    return 1.0 - _gama_inferior_regularizada(gl / 2.0, x / 2.0)
