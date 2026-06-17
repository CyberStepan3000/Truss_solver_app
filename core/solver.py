import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from .elements import Node, Rod


@dataclass
class SolutionResult:
    # Перемещения узлов {node_id: (dx, dy)}
    displacements: Dict[int, Tuple[float, float]]
    # Усилия в стержнях {rod_id: force}
    forces: Dict[int, float]


class FermaSolver:  # Переименовали для ясности
    def __init__(self):
        self.nodes: Dict[int, Node] = {}
        self.rods: List[Rod] = []

    def add_node(self, number: int, x: float, y: float, fixed_x: bool = False, fixed_y: bool = False):
        if number in self.nodes:
            raise ValueError(f"Node {number} already exists.")
        self.nodes[number] = Node(number, x, y, fixed_x, fixed_y)

    def add_rod(self, number: int, node1_number: int, node2_number: int, E: float = 1.0, section: float = 1.0):
        if node1_number not in self.nodes or node2_number not in self.nodes:
            raise KeyError("One of the node numbers does not exist.")
        rod = Rod(number, self.nodes[node1_number],
                  self.nodes[node2_number], E, section)
        self.rods.append(rod)
        return rod

    def add_force(self, node_number: int, fx: float = 0.0, fy: float = 0.0):
        if node_number not in self.nodes:
            raise KeyError(f"Node {node_number} does not exist.")
        self.nodes[node_number].force_x += fx
        self.nodes[node_number].force_y += fy

    def _node_index_map(self) -> Dict[int, int]:
        """
        Отображение: номер узла -> индекс в глобальном векторе
        Узлы сортируются по номеру.
        """
        ordered_node_numbers = sorted(self.nodes.keys())
        return {node_number: i for i, node_number in enumerate(ordered_node_numbers)}

    def assemble_global_stiffness(self) -> np.ndarray:
        node_index_map = self._node_index_map()
        n_nodes = len(self.nodes)
        K = np.zeros((2 * n_nodes, 2 * n_nodes), dtype=float)

        for rod in self.rods:
            k_e = rod.global_stiffness()

            i = node_index_map[rod.node1.number]
            j = node_index_map[rod.node2.number]

            dof = [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]

            for a in range(4):
                for b in range(4):
                    K[dof[a], dof[b]] += k_e[a, b]

        return K

    def assemble_load_vector(self) -> np.ndarray:
        node_index_map = self._node_index_map()
        n_nodes = len(self.nodes)
        F = np.zeros(2 * n_nodes, dtype=float)

        for node_number, node in self.nodes.items():
            i = node_index_map[node_number]
            F[2 * i] = node.force_x
            F[2 * i + 1] = node.force_y

        return F

    def apply_boundary_conditions(self, K: np.ndarray, F: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Жесткое задание закреплений:
        фиксированная степень свободы -> строка/столбец зануляются,
        на диагонали ставится 1, нагрузка = 0.
        """
        node_index_map = self._node_index_map()

        K = K.copy()
        F = F.copy()

        for node_number, node in self.nodes.items():
            i = node_index_map[node_number]

            if node.fixed_x:
                dof = 2 * i
                K[dof, :] = 0.0
                K[:, dof] = 0.0
                K[dof, dof] = 1.0
                F[dof] = 0.0

            if node.fixed_y:
                dof = 2 * i + 1
                K[dof, :] = 0.0
                K[:, dof] = 0.0
                K[dof, dof] = 1.0
                F[dof] = 0.0

        return K, F

    def solve(self) -> SolutionResult:
        """
        Выполняет расчет и возвращает объект с результатами: перемещениями и усилиями.
        """
        K = self.assemble_global_stiffness()
        F = self.assemble_load_vector()
        K_bc, F_bc = self.apply_boundary_conditions(K, F)

        try:
            U = np.linalg.solve(K_bc, F_bc)
        except np.linalg.LinAlgError as e:
            raise np.linalg.LinAlgError(
                "Global stiffness matrix is singular. Check supports and connectivity of the truss."
            ) from e

        node_index_map = self._node_index_map()
        displacements = {}
        for node_number in sorted(self.nodes.keys()):
            i = node_index_map[node_number]
            ux, uy = U[2 * i], U[2 * i + 1]
            displacements[node_number] = (float(ux), float(uy))

        # Сразу считаем усилия в стержнях
        forces = {}
        for rod in self.rods:
            forces[rod.number] = rod.axial_force(U, node_index_map)

        return SolutionResult(displacements=displacements, forces=forces)
