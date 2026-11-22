"""Simplex revisado de duas fases, escrito no projeto. Numpy só como aritmética de vetores."""

import numpy as np

TOL = 1e-9
REFATORAR = 40
MAX_DEGENERADOS = 50


class Inviavel(Exception):
    pass


class Ilimitado(Exception):
    pass


def inversa(B: np.ndarray) -> np.ndarray:
    """Inversa por Gauss-Jordan com pivoteamento parcial."""
    m = B.shape[0]
    M = np.hstack([B.astype(float), np.eye(m)])
    for k in range(m):
        p = k + int(np.argmax(np.abs(M[k:, k])))
        if abs(M[p, k]) < 1e-13:
            raise np.linalg.LinAlgError("base singular")
        if p != k:
            M[[k, p]] = M[[p, k]]
        M[k] /= M[k, k]
        col = M[:, k].copy()
        col[k] = 0.0
        M -= np.outer(col, M[k])
    return M[:, m:]


def _simplex(A, b, c, base, proibidas):
    """Minimiza c'x com Ax = b, x >= 0, partindo da base viável `base`."""
    m, n = A.shape
    base = list(base)
    Binv = inversa(A[:, base])
    xB = Binv @ b
    permitida = np.ones(n, bool)
    permitida[list(proibidas)] = False
    degenerados = 0
    it = 0
    while True:
        it += 1
        if it % REFATORAR == 0:
            Binv = inversa(A[:, base])
            xB = Binv @ b
        y = c[base] @ Binv
        d = c - y @ A
        d[base] = 0.0
        candidatas = np.where((d < -TOL) & permitida)[0]
        if candidatas.size == 0:
            break
        if degenerados >= MAX_DEGENERADOS:
            j = int(candidatas[0])  # regra de Bland contra ciclagem
        else:
            j = int(candidatas[np.argmin(d[candidatas])])
        a = Binv @ A[:, j]
        pos = a > TOL
        if not pos.any():
            raise Ilimitado()
        razoes = np.full(m, np.inf)
        razoes[pos] = np.maximum(xB[pos], 0.0) / a[pos]
        theta = razoes.min()
        empates = np.where(razoes <= theta + 1e-12)[0]
        r = int(min(empates, key=lambda i: base[i]))
        degenerados = degenerados + 1 if theta <= 1e-12 else 0
        xB = xB - theta * a
        xB[r] = theta
        piv = Binv[r] / a[r]
        Binv -= np.outer(a, piv)
        Binv[r] = piv
        base[r] = j
    return base, Binv, xB


def maximizar(c, A_ub=None, b_ub=None, A_eq=None, b_eq=None, livres=()):
    """max c'x s.a. A_ub x <= b_ub, A_eq x = b_eq, x >= 0 exceto as variáveis em `livres`.

    Devolve (valor ótimo, x).
    """
    c = np.asarray(c, float)
    n = c.size
    blocos, rhs, folgas = [], [], 0
    if A_ub is not None and len(A_ub):
        blocos.append(np.asarray(A_ub, float))
        rhs.append(np.asarray(b_ub, float))
        folgas = blocos[-1].shape[0]
    if A_eq is not None and len(A_eq):
        blocos.append(np.asarray(A_eq, float))
        rhs.append(np.asarray(b_eq, float))
    A = np.vstack(blocos)
    b = np.concatenate(rhs)
    m = A.shape[0]

    livres = list(livres)
    A = np.hstack([A, -A[:, livres]]) if livres else A
    custo = np.concatenate([-c, c[livres]]) if livres else -c
    nv = A.shape[1]
    S = np.zeros((m, folgas))
    S[np.arange(folgas), np.arange(folgas)] = 1.0
    A = np.hstack([A, S])
    custo = np.concatenate([custo, np.zeros(folgas)])

    escala_l = np.abs(A).max(axis=1)
    escala_l[escala_l == 0] = 1.0
    A = A / escala_l[:, None]
    b = b / escala_l
    escala_c = np.abs(A).max(axis=0)
    escala_c[escala_c == 0] = 1.0
    A = A / escala_c
    custo = custo / escala_c

    sinal = np.where(b < 0, -1.0, 1.0)
    A = A * sinal[:, None]
    b = b * sinal

    nt = A.shape[1]
    A1 = np.hstack([A, np.eye(m)])
    art = list(range(nt, nt + m))
    c1 = np.concatenate([np.zeros(nt), np.ones(m)])
    base, Binv, xB = _simplex(A1, b, c1, art, [])
    if c1[base] @ xB > 1e-7 * max(1.0, np.abs(b).max()):
        raise Inviavel()

    for r in range(m):
        if base[r] >= nt:
            linha = Binv[r] @ A1[:, :nt]
            linha[[j for j in base if j < nt]] = 0.0
            js = np.where(np.abs(linha) > 1e-9)[0]
            if js.size:
                j = int(js[np.argmax(np.abs(linha[js]))])
                a = Binv @ A1[:, j]
                piv = Binv[r] / a[r]
                Binv -= np.outer(a, piv)
                Binv[r] = piv
                base[r] = j
                xB = Binv @ b

    c2 = np.concatenate([custo, np.zeros(m)])
    base, Binv, xB = _simplex(A1, b, c2, base, art)

    x = np.zeros(nt + m)
    x[base] = xB
    x = x[:nt] / escala_c
    xo = x[:n].copy()
    if livres:
        xo[livres] -= x[n:nv]
    return float(c @ xo), xo
