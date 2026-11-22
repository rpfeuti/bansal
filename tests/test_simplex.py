import numpy as np
import pytest

from src.bansal.simplex import Ilimitado, Inviavel, inversa, maximizar


def test_inversa():
    rng = np.random.default_rng(0)
    B = rng.normal(size=(6, 6))
    assert np.allclose(inversa(B) @ B, np.eye(6))


def test_classico():
    # max 3x + 5y; x <= 4; 2y <= 12; 3x + 2y <= 18  -> (2, 6), 36
    v, x = maximizar([3, 5], A_ub=[[1, 0], [0, 2], [3, 2]], b_ub=[4, 12, 18])
    assert v == pytest.approx(36)
    assert x == pytest.approx([2, 6])


def test_igualdade_e_lado_direito_negativo():
    # max x + y; x - y = -1; x + 2y <= 8  -> x=2, y=3
    v, x = maximizar([1, 1], A_ub=[[1, 2]], b_ub=[8], A_eq=[[1, -1]], b_eq=[-1])
    assert v == pytest.approx(5)
    assert x == pytest.approx([2, 3])


def test_variavel_livre_negativa():
    # max b; b <= -0.5 (via x - b >= 0.5 com x = 0)
    v, x = maximizar([0, 1], A_ub=[[0, 1]], b_ub=[-0.5], A_eq=[[1, 0]], b_eq=[0], livres=[1])
    assert v == pytest.approx(-0.5)


def test_inviavel():
    with pytest.raises(Inviavel):
        maximizar([1], A_ub=[[1], [-1]], b_ub=[1, -2])


def test_ilimitado():
    with pytest.raises(Ilimitado):
        maximizar([1, 1], A_ub=[[1, -1]], b_ub=[1])


def test_ddf_dois_dmus():
    # Um insumo, um produto, VRS. DMU A (x=1, y=1), DMU B (x=2, y=1).
    # Para B com direção (x, y): max beta s.a. l1 + 2 l2 <= 2 - 2 beta; l1 + l2 >= 1 + beta; l1 + l2 = 1
    # beta = 0 na convexidade? y: 1 >= 1 + beta -> beta <= 0; x: l1=1 -> 1 <= 2 - 2 beta -> beta <= 0.5. Ótimo 0.
    v, x = maximizar([0, 0, 1], A_ub=[[1, 2, 2], [-1, -1, 1]], b_ub=[2, -1], A_eq=[[1, 1, 0]], b_eq=[1], livres=[2])
    assert v == pytest.approx(0.0, abs=1e-9)
    # Sem convexidade (CRS): l1 <= 2 - 2b e l1 >= 1 + b -> b = 1/3
    v, x = maximizar([0, 0, 1], A_ub=[[1, 2, 2], [-1, -1, 1]], b_ub=[2, -1], livres=[2])
    assert v == pytest.approx(1 / 3)


def test_degenerado_aleatorio_contra_vertices():
    rng = np.random.default_rng(1)
    for _ in range(30):
        A = rng.integers(-3, 5, size=(5, 3)).astype(float)
        b = rng.integers(0, 6, size=5).astype(float)
        c = rng.integers(-2, 4, size=3).astype(float)
        A = np.vstack([A, np.ones((1, 3))])
        b = np.append(b, 10.0)
        # força bruta: vértices de {Ax<=b, x>=0}
        G = np.vstack([A, -np.eye(3)])
        h = np.concatenate([b, np.zeros(3)])
        melhor = -np.inf
        from itertools import combinations
        for idx in combinations(range(len(h)), 3):
            M = G[list(idx)]
            if abs(np.linalg.det(M)) < 1e-9:
                continue
            p = np.linalg.solve(M, h[list(idx)])
            if np.all(G @ p <= h + 1e-9):
                melhor = max(melhor, c @ p)
        if melhor == -np.inf:
            with pytest.raises(Inviavel):
                maximizar(c, A_ub=A, b_ub=b)
        else:
            v, _ = maximizar(c, A_ub=A, b_ub=b)
            assert v == pytest.approx(melhor, abs=1e-7)
