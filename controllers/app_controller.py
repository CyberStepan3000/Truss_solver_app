import math
import copy
import datetime
from PyQt5.QtWidgets import QMessageBox
# УБРАЛИ RodPropertyDialog ИЗ ИМПОРТА!
from gui.dialogs import SupportDialog, ForceDialog, LogDialog
from gui.main_window import SettingsDialog


class AppController:
    def __init__(self, view, model):
        self.view = view
        self.model = model
        self.current_mode = "VIEW"
        self.first_node_for_rod = None

        self.session_logs = []
        self.backup_model = None

        self._log_event("Инициализация программы. Сессия начата.")
        self._connect_signals()

    def _log_event(self, message: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.session_logs.append(f"[{timestamp}] {message}")

    def _connect_signals(self):
        self.view.btn_add_node.clicked.connect(
            lambda: self.set_mode("ADD_NODE"))
        self.view.btn_add_rod.clicked.connect(lambda: self.set_mode("ADD_ROD"))
        self.view.btn_add_support.clicked.connect(
            lambda: self.set_mode("ADD_SUPPORT"))
        self.view.btn_add_force.clicked.connect(
            lambda: self.set_mode("ADD_FORCE"))

        self.view.btn_clear.clicked.connect(self.handle_clear_all)
        self.view.btn_calculate.clicked.connect(self.handle_calculate)
        self.view.btn_settings.clicked.connect(self.open_settings)
        self.view.action_logs.triggered.connect(self.open_logs)

        self.view.canvas.canvas_clicked.connect(self.handle_canvas_click)
        self.view.canvas.canvas_mouse_moved.connect(self.handle_mouse_move)

    def open_settings(self):
        dialog = SettingsDialog(self.view, self.view.current_theme)
        if dialog.exec_():
            new_theme = dialog.get_selected_theme()
            if new_theme != self.view.current_theme:
                self.view.current_theme = new_theme
                self.view.apply_theme(self.view.current_theme)

    def open_logs(self):
        logs_text = "\n".join(self.session_logs)
        dialog = LogDialog(self.view, logs_text,
                           restore_callback=self.restore_backup)
        dialog.exec_()

    def restore_backup(self):
        if not self.backup_model:
            self.view.show_error_dialog(
                "Нет сохраненной копии фермы для восстановления!")
            return
        self.model = copy.deepcopy(self.backup_model)
        self.view.canvas.draw_model(self.model.nodes, self.model.rods)
        self._log_event("Ферма успешно восстановлена из резервной копии.")
        self.view.show_status_message("Ферма восстановлена!")

    def handle_clear_all(self):
        if not self.model.nodes and not self.model.rods:
            self.view.show_status_message("Схема уже пуста.")
            return

        reply = QMessageBox.question(
            self.view, "Подтверждение",
            "Вы уверены, что хотите очистить схему?\n(Её можно будет восстановить через Логи)",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.backup_model = copy.deepcopy(self.model)
            self.model.nodes.clear()
            self.model.rods.clear()
            self.view.canvas.clear_canvas()
            self.set_mode("VIEW")
            self._log_event("Схема очищена. Создана резервная копия.")
            self.view.show_status_message("Проект очищен.")

    def handle_calculate(self):
        if not self.model.nodes:
            self.view.show_error_dialog(
                "Схема пуста. Добавьте узлы и стержни перед расчетом!")
            return

        self.set_mode("VIEW")
        self._log_event(
            f"--- ЗАПУСК РАСЧЕТА (Узлов: {len(self.model.nodes)}, Стержней: {len(self.model.rods)}) ---")

        try:
            result = self.model.solve()

            self._log_event("РАСЧЕТ ВЫПОЛНЕН УСПЕШНО. Результаты:")
            self._log_event("ПЕРЕМЕЩЕНИЯ УЗЛОВ (dx, dy):")

            for node_id, (dx, dy) in result.displacements.items():
                # Добавили "мм"
                self._log_event(
                    f"  > Узел {node_id}: dx = {dx:.5e} мм, dy = {dy:.5e} мм")

            self._log_event("УСИЛИЯ И НАПРЯЖЕНИЯ В СТЕРЖНЯХ:")
            for rod in self.model.rods:
                force = result.forces.get(rod.number, 0.0)
                stress = force / rod.section
                if abs(force) < 1e-9:
                    state = "Нулевой элемент"
                elif force > 0:
                    state = "Растяжение"
                else:
                    state = "Сжатие   "

                # Добавили "Н" и "МПа"
                self._log_event(
                    f"  > Стержень {rod.number}: {state} | N = {force:>8.3f} Н | σ = {stress:>8.3f} МПа")

            self._log_event("-" * 40)
            self.view.canvas.draw_model(
                self.model.nodes, self.model.rods, displacements=result.displacements, forces=result.forces)
            self.view.show_status_message(
                "Расчет завершен! Проверьте логи и графику.")

        except Exception as e:
            self._log_event(f"ОШИБКА РАСЧЕТА СЛАУ: {str(e)}")
            self.view.show_error_dialog(f"Ошибка расчета матриц:\n{str(e)}")

    def set_mode(self, mode: str):
        self.current_mode = mode
        self.first_node_for_rod = None
        self.view.canvas.hide_preview_rod()

        # --- УПРАВЛЕНИЕ ВИДИМОСТЬЮ ПАНЕЛИ СТЕРЖНЯ ---
        if mode == "ADD_ROD":
            self.view.rod_panel.show()
        else:
            self.view.rod_panel.hide()

        # Если режим VIEW, программно "отжимаем" все кнопки
        if mode == "VIEW":
            self.view.tool_group.setExclusive(False)
            for btn in self.view.tool_group.buttons():
                btn.setChecked(False)
            self.view.tool_group.setExclusive(True)

        if mode == "ADD_NODE":
            self.view.show_status_message("Режим: Добавление узлов.")
        elif mode == "ADD_ROD":
            self.view.show_status_message("Режим: Добавление стержней.")
        elif mode == "ADD_SUPPORT":
            self.view.show_status_message("Режим: Опоры.")
        elif mode == "ADD_FORCE":
            self.view.show_status_message("Режим: Нагрузки.")
        else:
            self.view.show_status_message("Режим просмотра.")

    def _find_node_near(self, x: float, y: float, tolerance: float = 0.4):
        for node in self.model.nodes.values():
            if math.hypot(node.x - x, node.y - y) <= tolerance:
                return node
        return None

    def handle_mouse_move(self, x: float, y: float):
        if self.current_mode == "ADD_ROD" and self.first_node_for_rod is not None:
            hovered = self._find_node_near(x, y)
            if hovered and hovered.number != self.first_node_for_rod.number:
                self.view.canvas.show_preview_rod(
                    self.first_node_for_rod.x, self.first_node_for_rod.y, hovered.x, hovered.y)
            else:
                self.view.canvas.hide_preview_rod()

    def handle_canvas_click(self, x: float, y: float):
        if self.current_mode == "ADD_NODE":
            self._add_node_at(x, y)
        elif self.current_mode == "ADD_ROD":
            self._handle_rod_click(x, y)
        elif self.current_mode == "ADD_SUPPORT":
            self._handle_support_click(x, y)
        elif self.current_mode == "ADD_FORCE":
            self._handle_force_click(x, y)

    def _add_node_at(self, x: float, y: float):
        for node in self.model.nodes.values():
            if abs(node.x - x) < 1e-5 and abs(node.y - y) < 1e-5:
                return
        new_num = len(self.model.nodes) + 1
        self.model.add_node(new_num, x, y)

        # Добавили "мм"
        self._log_event(
            f"Добавлен узел {new_num} с координатами x={x} мм, y={y} мм")
        self.view.canvas.draw_model(self.model.nodes, self.model.rods)

    def _handle_rod_click(self, x: float, y: float):
        node = self._find_node_near(x, y)
        if not node:
            return

        if self.first_node_for_rod is None:
            self.first_node_for_rod = node
        else:
            if node.number == self.first_node_for_rod.number:
                return

            for rod in self.model.rods:
                if (rod.node1.number == self.first_node_for_rod.number and rod.node2.number == node.number) or \
                   (rod.node1.number == node.number and rod.node2.number == self.first_node_for_rod.number):
                    self.view.show_error_dialog(
                        "Такой стержень уже существует!")
                    self.first_node_for_rod = None
                    self.view.canvas.hide_preview_rod()
                    return

            # --- БЕРЕМ ЗНАЧЕНИЯ ПРЯМО ИЗ БОКОВОЙ ПАНЕЛИ ---
            E, A = self.view.rod_panel.get_values()

            if A <= 0:
                self.view.show_error_dialog(
                    "Ошибка: Площадь сечения (A) должна быть больше нуля!")
                self.first_node_for_rod = None
                self.view.canvas.hide_preview_rod()
                return

            new_rod_num = len(self.model.rods) + 1
            self.model.add_rod(
                new_rod_num, self.first_node_for_rod.number, node.number)

            # Назначаем свойства созданному стержню
            new_rod = self.model.rods[-1]
            new_rod.E = E
            new_rod.section = A

            self._log_event(
                f"Добавлен стержень {new_rod_num} (Узлы {self.first_node_for_rod.number} -> {node.number}) | E={E} МПа, A={A:.2f} мм²")

            self.first_node_for_rod = None
            self.view.canvas.hide_preview_rod()
            self.view.canvas.draw_model(self.model.nodes, self.model.rods)

    def _handle_support_click(self, x: float, y: float):
        node = self._find_node_near(x, y)
        if not node:
            return
        dialog = SupportDialog(self.view, node.fixed_x, node.fixed_y)
        if dialog.exec_():
            fix_x, fix_y = dialog.get_values()
            node.fixed_x, node.fixed_y = fix_x, fix_y
            self._log_event(
                f"Изменены опоры узла {node.number}: Фикс_X={fix_x}, Фикс_Y={fix_y}")
            self.view.canvas.draw_model(self.model.nodes, self.model.rods)

    def _handle_force_click(self, x: float, y: float):
        node = self._find_node_near(x, y)
        if not node:
            return
        dialog = ForceDialog(self.view, node.force_x, node.force_y)
        if dialog.exec_():
            fx, fy = dialog.get_values()
            node.force_x, node.force_y = fx, fy

            # Добавили "Н"
            self._log_event(
                f"К узлу {node.number} приложена сила: Fx={fx} Н, Fy={fy} Н")
            self.view.canvas.draw_model(self.model.nodes, self.model.rods)
