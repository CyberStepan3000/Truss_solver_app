import sys
from PyQt5.QtWidgets import QApplication
from core.solver import FermaSolver
from gui.main_window import MainWindow
from controllers.app_controller import AppController


def main():
    app = QApplication(sys.argv)

    # 1. Инициализируем математическую модель
    solver = FermaSolver()

    # 2. Инициализируем графический интерфейс (пока без логики)
    window = MainWindow()

    # 3. Создаем "мозг" и передаем ему ссылки на оба слоя
    controller = AppController(view=window, model=solver)

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
