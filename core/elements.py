import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict


@dataclass
class Node:
    number: int
    x: float
    y: float
    fixed_x: bool = False
    fixed_y: bool = False
    force_x: float = 0.0
    force_y: float = 0.0


class Rod:
    def __init__(self, number: int, node1: Node, node2: Node, E: float = 1.0, section: float = 1.0):
        self.number = number
        self.node1 = node1
        self.node2 = node2
        self.E = E
        self.section = section

    @property
    def length(self) -> float:
        dx = self.node2.x - self.node1.x
        dy = self.node2.y - self.node1.y
        return np.sqrt(dx**2 + dy**2)

    def cosines(self) -> Tuple[float, float]:
        dx = self.node2.x - self.node1.x
        dy = self.node2.y - self.node1.y
        L = self.length
        if L == 0:
            raise ValueError(f"Element {self.number} has zero length.")
        l = dx / L
        m = dy / L
        return l, m

    def local_stiffness(self) -> np.ndarray:
        """
        Локальная матрица жесткости стержня в оси элемента:
        k_local = EA/L * [[1, -1], [-1, 1]]
        """
        k = self.E * self.section / self.length
        return k * np.array([
            [1.0, -1.0],
            [-1.0, 1.0]
        ], dtype=float)

    def transformation_matrix(self) -> np.ndarray:
        """
        Матрица преобразования 2x4:
        [u1_local]   [ l  m  0  0 ] [u1x]
        [u2_local] = [ 0  0  l  m ] [u1y]
                                    [u2x]
                                    [u2y]
        """
        l, m = self.cosines()
        return np.array([
            [l, m, 0.0, 0.0],
            [0.0, 0.0, l, m]
        ], dtype=float)

    def global_stiffness(self) -> np.ndarray:
        """
        Глобальная матрица жесткости элемента 4x4:
        K_e = T^T * k_local * T
        """
        T = self.transformation_matrix()
        k_local = self.local_stiffness()
        return T.T @ k_local @ T

    def axial_force(self, U_global: np.ndarray, node_index_map: Dict[int, int]) -> float:
        """
        Усилие в стержне (положительное - растяжение).
        dof -  Degrees of Freedom - степени свободы 
        [u1x, u1y, u2x, u2y] - глобальные перемещения узлов стержня по x и y.
        """
        i = node_index_map[self.node1.number]
        j = node_index_map[self.node2.number]
        dof = np.array([2 * i, 2 * i + 1, 2 * j, 2 * j + 1], dtype=int)

        u_e = U_global[dof]                  # [u1x, u1y, u2x, u2y]
        T = self.transformation_matrix()
        u_local = T @ u_e                    # [u1_local, u2_local]

        N = (self.E * self.section / self.length) * (u_local[1] - u_local[0])
        return float(N)

    def __str__(self):
        return (
            f"Rode {self.number}: Node {self.node1.number} -> Node {self.node2.number}, "
            f"E={self.E}, section={self.section}"
        )
