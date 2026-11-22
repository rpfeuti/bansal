"""GMM de sistema em dois passos (Blundell e Bond 1998) com correção de Windmeijer (2005).

Instrumentos como no padrão do xtabond2: y defasado endógeno, com y_{t-2}, y_{t-3}, ... na equação em
diferenças e Δy_{t-1} na equação em nível; covariáveis exógenas como instrumento próprio (Δx nas
diferenças, x e a constante no nível); sem collapse.
"""

import numpy as np

from .estatistica import chi2_sf, normal_cdf


def _montar(y, xs):
    """Matrizes por banco: regressores, dependente, instrumentos e H (erro em diferença e em nível)."""
    N, T = y.shape
    K = len(xs)
    d_rows = list(range(2, T))
    l_rows = list(range(1, T))
    n_gd = sum(t - 1 for t in d_rows)
    n_gl = len(d_rows)
    L = n_gd + n_gl + K + K + 1
    R = len(d_rows) + len(l_rows)

    M = np.zeros((R, T))
    for r, t in enumerate(d_rows):
        M[r, t], M[r, t - 1] = 1.0, -1.0
    for r, t in enumerate(l_rows):
        M[len(d_rows) + r, t] = 1.0
    H = M @ M.T

    dados = []
    for i in range(N):
        X = np.zeros((R, K + 2))
        Y = np.zeros(R)
        Z = np.zeros((R, L))
        ok = np.zeros(R, bool)
        col = 0
        for r, t in enumerate(d_rows):
            v = [y[i, t] - y[i, t - 1], y[i, t - 1] - y[i, t - 2]] + [x[i, t] - x[i, t - 1] for x in xs]
            insts = y[i, :t - 1]
            if np.all(np.isfinite(v)) and np.all(np.isfinite(insts)):
                ok[r] = True
                Y[r] = v[0]
                X[r, :K + 1] = v[1:]
                Z[r, col:col + t - 1] = insts
                Z[r, n_gd + n_gl:n_gd + n_gl + K] = v[2:]
            col += t - 1
        for r, t in enumerate(l_rows):
            rr = len(d_rows) + r
            v = [y[i, t], y[i, t - 1]] + [x[i, t] for x in xs]
            if not np.all(np.isfinite(v)):
                continue
            ok[rr] = True
            Y[rr] = v[0]
            X[rr, :K + 1] = v[1:]
            X[rr, K + 1] = 1.0
            if t >= 2 and np.isfinite(y[i, t - 1] - y[i, t - 2]):
                Z[rr, n_gd + (t - 2)] = y[i, t - 1] - y[i, t - 2]
            Z[rr, n_gd + n_gl + K:n_gd + n_gl + 2 * K] = v[2:]
            Z[rr, -1] = 1.0
        X[~ok], Y[~ok], Z[~ok] = 0.0, 0.0, 0.0
        dados.append((X, Y, Z, ok))
    usados = np.abs(sum(np.abs(Z).sum(axis=0) for _, _, Z, _ in dados)) > 0
    dados = [(X, Y, Z[:, usados], ok) for X, Y, Z, ok in dados]
    return dados, H, len(d_rows)


def _estimar(dados, A):
    ZX = sum(Z.T @ X for X, _, Z, _ in dados)
    Zy = sum(Z.T @ Y for _, Y, Z, _ in dados)
    V = np.linalg.pinv(ZX.T @ A @ ZX)
    b = V @ ZX.T @ A @ Zy
    return b, V, ZX


def system_gmm(y, xs, nomes):
    """y: N x T; xs: lista de matrizes N x T. Devolve dict com coeficientes, erros-padrão e testes."""
    dados, H, nd = _montar(y, xs)
    N = len(dados)

    A1 = np.linalg.pinv(sum(Z.T @ H @ Z for _, _, Z, _ in dados))
    b1, V1, ZX = _estimar(dados, A1)
    u1 = [Y - X @ b1 for X, Y, _, _ in dados]
    S1 = sum(Z.T @ np.outer(u, u) @ Z for (_, _, Z, _), u in zip(dados, u1))
    V1r = V1 @ ZX.T @ A1 @ S1 @ A1 @ ZX @ V1

    A2 = np.linalg.pinv(S1)
    b2, V2, _ = _estimar(dados, A2)
    u2 = [Y - X @ b2 for X, Y, _, _ in dados]
    Zu2 = sum(Z.T @ u for (_, _, Z, _), u in zip(dados, u2))

    k = b2.size
    D = np.zeros((k, k))
    for j in range(k):
        dS = -sum(Z.T @ (np.outer(X[:, j], u) + np.outer(u, X[:, j])) @ Z
                  for (X, _, Z, _), u in zip(dados, u1))
        D[:, j] = -V2 @ ZX.T @ A2 @ dS @ A2 @ Zu2
    Vc = V2 + D @ V2 + V2 @ D.T + D @ V1r @ D.T
    ep = np.sqrt(np.diag(Vc))

    L = A2.shape[0]
    gl = L - k
    hansen = float(Zu2 @ A2 @ Zu2)
    Zu1 = sum(Z.T @ u for (_, _, Z, _), u in zip(dados, u1))
    niv = [u[nd:][ok[nd:]] for u, (_, _, _, ok) in zip(u1, dados)]
    s2 = float(sum((e ** 2).sum() for e in niv) / sum(e.size for e in niv))
    sargan = float(Zu1 @ A1 @ Zu1) / s2

    sem_const = slice(0, k - 1)
    bw = b2[sem_const]
    wald = float(bw @ np.linalg.pinv(Vc[sem_const, sem_const]) @ bw)

    def ar(m):
        num, var1 = 0.0, 0.0
        ex = np.zeros(k)
        cruz = np.zeros(L)
        for (X, _, Z, ok), u in zip(dados, u2):
            e = np.where(ok[:nd], u[:nd], 0.0)
            em = np.zeros(nd)
            em[m:] = e[:-m] if m < nd else 0.0
            em[~ok[:nd]] = 0.0
            w = em @ e
            num += w
            var1 += w * w
            ex += em @ X[:nd]
            cruz += Z.T @ u * w
        var = var1 - 2 * ex @ V2 @ ZX.T @ A2 @ cruz + ex @ Vc @ ex
        z = num / np.sqrt(var)
        return 2 * (1 - normal_cdf(abs(z)))

    return {
        "nomes": nomes,
        "coef": b2,
        "ep": ep,
        "p": [2 * (1 - normal_cdf(abs(c / s))) for c, s in zip(b2, ep)],
        "AR1": ar(1),
        "AR2": ar(2),
        "sargan_p": chi2_sf(sargan, gl),
        "hansen_p": chi2_sf(hansen, gl),
        "wald": wald,
        "wald_p": chi2_sf(wald, k - 1),
        "instrumentos": L,
        "bancos": N,
        "obs": int(sum(ok[nd:].sum() for _, _, _, ok in dados)),
    }
