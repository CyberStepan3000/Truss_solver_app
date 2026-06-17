import math
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QAction, QStatusBar, QMessageBox, QApplication,
    QButtonGroup, QComboBox, QStackedWidget, QDoubleSpinBox, QGroupBox, QFormLayout
)
from PyQt5.QtGui import QPalette
from PyQt5.QtCore import Qt
from .canvas import TrussCanvas
from .dialogs import SettingsDialog

# --- НОВЫЙ ВИДЖЕТ: ПАНЕЛЬ СВОЙСТВ СТЕРЖНЯ ---


class RodPropertyPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)  # Делаем компактнее

        group_mat = QGroupBox("Материал (E, МПа)")
        layout_mat = QFormLayout(group_mat)

        self.combo_mat = QComboBox()
        self.combo_mat.addItems(
            ["Сталь 45 (200 000)", "Алюминий Д16 (72 000)", "Титан ВТ1-0 (112 000)", "Свой материал..."])
        self.spin_e = QDoubleSpinBox()
        self.spin_e.setRange(0.1, 1e9)
        self.spin_e.setDecimals(0)
        self.combo_mat.currentIndexChanged.connect(self._update_mat)

        layout_mat.addRow("Сплав:", self.combo_mat)
        layout_mat.addRow("E:", self.spin_e)
        layout.addWidget(group_mat)

        group_sec = QGroupBox("Сечение (A, мм²)")
        layout_sec = QFormLayout(group_sec)

        self.combo_sec = QComboBox()
        self.combo_sec.addItems(
            ["Труба круглая", "Труба квадратная", "Своя площадь..."])
        self.stacked_sec = QStackedWidget()

        w_round = QWidget()
        l_round = QFormLayout(w_round)
        l_round.setContentsMargins(0, 0, 0, 0)
        self.spin_r_d = QDoubleSpinBox()
        self.spin_r_d.setRange(1.0, 10000.0)
        self.spin_r_d.setValue(50.0)
        self.spin_r_t = QDoubleSpinBox()
        self.spin_r_t.setRange(0.1, 5000.0)
        self.spin_r_t.setValue(2.0)
        l_round.addRow("D (мм):", self.spin_r_d)
        l_round.addRow("t (мм):", self.spin_r_t)
        self.stacked_sec.addWidget(w_round)

        w_sq = QWidget()
        l_sq = QFormLayout(w_sq)
        l_sq.setContentsMargins(0, 0, 0, 0)
        self.spin_s_b = QDoubleSpinBox()
        self.spin_s_b.setRange(1.0, 10000.0)
        self.spin_s_b.setValue(50.0)
        self.spin_s_t = QDoubleSpinBox()
        self.spin_s_t.setRange(0.1, 5000.0)
        self.spin_s_t.setValue(2.0)
        l_sq.addRow("Сторона:", self.spin_s_b)
        l_sq.addRow("Стенка t:", self.spin_s_t)
        self.stacked_sec.addWidget(w_sq)

        w_custom = QWidget()
        l_custom = QFormLayout(w_custom)
        l_custom.setContentsMargins(0, 0, 0, 0)
        self.spin_c_a = QDoubleSpinBox()
        self.spin_c_a.setRange(0.01, 1e9)
        self.spin_c_a.setValue(300.0)
        l_custom.addRow("Площадь:", self.spin_c_a)
        self.stacked_sec.addWidget(w_custom)

        self.lbl_area = QLabel("Итог A: 0.00 мм²")
        self.lbl_area.setStyleSheet("font-weight: bold; color: #4CAF50;")

        self.combo_sec.currentIndexChanged.connect(
            self.stacked_sec.setCurrentIndex)
        self.combo_sec.currentIndexChanged.connect(self._calc_area)
        self.spin_r_d.valueChanged.connect(self._calc_area)
        self.spin_r_t.valueChanged.connect(self._calc_area)
        self.spin_s_b.valueChanged.connect(self._calc_area)
        self.spin_s_t.valueChanged.connect(self._calc_area)
        self.spin_c_a.valueChanged.connect(self._calc_area)

        layout_sec.addRow("Профиль:", self.combo_sec)
        layout_sec.addRow(self.stacked_sec)
        layout_sec.addRow(self.lbl_area)
        layout.addWidget(group_sec)

        self.calculated_area = 0.0
        self._update_mat()
        self._calc_area()

    def _update_mat(self):
        idx = self.combo_mat.currentIndex()
        if idx == 0:
            self.spin_e.setValue(200000)
            self.spin_e.setEnabled(False)
        elif idx == 1:
            self.spin_e.setValue(72000)
            self.spin_e.setEnabled(False)
        elif idx == 2:
            self.spin_e.setValue(112000)
            self.spin_e.setEnabled(False)
        else:
            self.spin_e.setEnabled(True)

    def _calc_area(self):
        idx = self.combo_sec.currentIndex()
        a = 0.0
        if idx == 0:
            D, t = self.spin_r_d.value(), self.spin_r_t.value()
            if D > 2 * t:
                a = (math.pi / 4) * (D**2 - (D - 2 * t)**2)
        elif idx == 1:
            B, t = self.spin_s_b.value(), self.spin_s_t.value()
            if B > 2 * t:
                a = B**2 - (B - 2 * t)**2
        else:
            a = self.spin_c_a.value()

        self.calculated_area = a
        self.lbl_area.setText(f"Итог A: {a:.2f} мм²")

    def get_values(self):
        return self.spin_e.value(), self.calculated_area


# --- ГЛАВНОЕ ОКНО ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Plane Truss FEM - Расчет ферм")
        self.resize(1200, 800)
        self.current_theme = "system"
        self._init_ui()
        self.apply_theme(self.current_theme)

    def _init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.canvas = TrussCanvas()
        self.main_layout.addWidget(self.canvas, stretch=4)

        self.control_panel_layout = QVBoxLayout()

        top_right_layout = QHBoxLayout()
        top_right_layout.addStretch()
        self.btn_settings = QPushButton("⚙ Настройки")
        self.btn_settings.setStyleSheet(
            "padding: 5px 15px; font-weight: bold;")
        top_right_layout.addWidget(self.btn_settings)
        self.control_panel_layout.addLayout(top_right_layout)

        # --- СОЗДАЕМ КНОПКИ И ДЕЛАЕМ ИХ ЗАЛИПАЮЩИМИ ---
        self.btn_add_node = QPushButton("Добавить узел")
        self.btn_add_rod = QPushButton("Добавить стержень")
        self.btn_add_support = QPushButton("Задать опору")
        self.btn_add_force = QPushButton("Задать нагрузку")

        self.btn_add_node.setCheckable(True)
        self.btn_add_rod.setCheckable(True)
        self.btn_add_support.setCheckable(True)
        self.btn_add_force.setCheckable(True)

        # Группируем их, чтобы нажата могла быть только одна
        self.tool_group = QButtonGroup(self)
        self.tool_group.addButton(self.btn_add_node)
        self.tool_group.addButton(self.btn_add_rod)
        self.tool_group.addButton(self.btn_add_support)
        self.tool_group.addButton(self.btn_add_force)

        self.control_panel_layout.addWidget(self.btn_add_node)
        self.control_panel_layout.addWidget(self.btn_add_rod)
        self.control_panel_layout.addWidget(self.btn_add_support)
        self.control_panel_layout.addWidget(self.btn_add_force)

        # --- ДОБАВЛЯЕМ ПАНЕЛЬ СВОЙСТВ ПОД КНОПКИ ---
        self.rod_panel = RodPropertyPanel()
        self.rod_panel.hide()  # По умолчанию скрыта
        self.control_panel_layout.addWidget(self.rod_panel)

        self.control_panel_layout.addStretch()

        self.btn_calculate = QPushButton("РАССЧИТАТЬ")
        self._calc_style = "background-color: #4CAF50; color: white; font-weight: bold; font-size: 14px; padding: 10px;"
        self.btn_calculate.setStyleSheet(self._calc_style)

        self.btn_clear = QPushButton("Очистить схему")
        self.btn_clear.setStyleSheet("color: red;")

        self.control_panel_layout.addWidget(self.btn_calculate)
        self.control_panel_layout.addWidget(self.btn_clear)
        self.main_layout.addLayout(self.control_panel_layout, stretch=1)

        self._create_menus()
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _create_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Файл")

        self.action_logs = QAction("Логи сессии", self)
        self.action_logs.setShortcut("Ctrl+L")
        file_menu.addAction(self.action_logs)
        file_menu.addSeparator()
        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def apply_theme(self, theme: str):
        app = QApplication.instance()
        is_dark = False

        if theme == "system":
            bg_color = app.palette().color(QPalette.Window)
            is_dark = bg_color.lightness() < 128
        elif theme == "dark":
            is_dark = True
        else:
            is_dark = False

        if is_dark:
            app.setStyleSheet("""
                QMainWindow, QDialog, QMessageBox, QStackedWidget, QWidget { background-color: #2b2b2b; color: #ffffff; }
                QPushButton { background-color: #3c3c3c; color: white; border: 1px solid #555; padding: 6px; border-radius: 3px; }
                QPushButton:hover { background-color: #4c4c4c; }
                QPushButton:pressed { background-color: #222222; }
                /* СТИЛЬ НАЖАТОЙ КНОПКИ В ТЕМНОЙ ТЕМЕ */
                QPushButton:checked { background-color: #005c99; border: 1px solid #00aaff; color: white; }
                QLabel, QRadioButton, QCheckBox { color: #ffffff; }
                QDoubleSpinBox, QComboBox { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555; padding: 2px; }
                QComboBox::drop-down { border: 0px; }
                QGroupBox { color: #ffffff; border: 1px solid #555; margin-top: 10px; padding-top: 15px; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; color: #00aaff; }
                QTextEdit { background-color: #1e1e1e; color: #00ff00; font-family: Consolas, monospace; font-size: 13px; }
                QStatusBar { color: #aaaaaa; }
            """)
        else:
            app.setStyleSheet("""
                /* СТИЛЬ НАЖАТОЙ КНОПКИ В СВЕТЛОЙ ТЕМЕ */
                QPushButton:checked { background-color: #cce5ff; border: 1px solid #005c99; font-weight: bold; color: #000000; }
            """)

        self.btn_calculate.setStyleSheet(self._calc_style)
        self.canvas.set_theme(is_dark)

    def show_status_message(self, message: str, timeout_ms: int = 5000):
        self.status_bar.showMessage(message, timeout_ms)

    def show_error_dialog(self, message: str):
        QMessageBox.critical(self, "Ошибка", message)
