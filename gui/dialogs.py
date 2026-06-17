import math
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QRadioButton,
    QDialogButtonBox, QLabel, QCheckBox, QDoubleSpinBox, QFormLayout,
    QTextEdit, QPushButton, QComboBox, QGroupBox, QStackedWidget, QWidget
)


class SettingsDialog(QDialog):
    def __init__(self, parent=None, current_theme="system"):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setModal(True)  # Окно блокирует остальной интерфейс, пока открыто
        self.resize(300, 150)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Выбор темы оформления:"))

        # Создаем радио-кнопки
        self.radio_system = QRadioButton("Системная (по умолчанию)")
        self.radio_light = QRadioButton("Светлая")
        self.radio_dark = QRadioButton("Темная")

        # Отмечаем текущую
        if current_theme == "dark":
            self.radio_dark.setChecked(True)
        elif current_theme == "light":
            self.radio_light.setChecked(True)
        else:
            self.radio_system.setChecked(True)

        layout.addWidget(self.radio_system)
        layout.addWidget(self.radio_light)
        layout.addWidget(self.radio_dark)

        # Стандартные кнопки ОК / Отмена
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_selected_theme(self) -> str:
        if self.radio_dark.isChecked():
            return "dark"
        if self.radio_light.isChecked():
            return "light"
        return "system"


class SupportDialog(QDialog):
    def __init__(self, parent=None, current_fix_x=False, current_fix_y=False):
        super().__init__(parent)
        self.setWindowTitle("Настройки опоры")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Выберите закрепления узла:"))

        self.cb_x = QCheckBox("Зафиксировать по X (Горизонтально)")
        self.cb_x.setChecked(current_fix_x)

        self.cb_y = QCheckBox("Зафиксировать по Y (Вертикально)")
        self.cb_y.setChecked(current_fix_y)

        layout.addWidget(self.cb_x)
        layout.addWidget(self.cb_y)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_values(self):
        return self.cb_x.isChecked(), self.cb_y.isChecked()


class ForceDialog(QDialog):
    def __init__(self, parent=None, current_fx=0.0, current_fy=0.0):
        super().__init__(parent)
        self.setWindowTitle("Задать нагрузку")
        self.setModal(True)

        # QFormLayout автоматически красиво выравнивает подписи и поля ввода
        layout = QFormLayout(self)

        self.spin_fx = QDoubleSpinBox()
        # Задаем огромный диапазон
        self.spin_fx.setRange(-1000000.0, 1000000.0)
        self.spin_fx.setDecimals(2)  # Две цифры после запятой
        self.spin_fx.setValue(current_fx)

        self.spin_fy = QDoubleSpinBox()
        self.spin_fy.setRange(-1000000.0, 1000000.0)
        self.spin_fy.setDecimals(2)
        self.spin_fy.setValue(current_fy)

        layout.addRow("Сила по X (Fx) (Н):", self.spin_fx)
        layout.addRow("Сила по Y (Fy) (Н):", self.spin_fy)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_values(self):
        return self.spin_fx.value(), self.spin_fy.value()


class LogDialog(QDialog):
    def __init__(self, parent=None, logs_text="", restore_callback=None):
        super().__init__(parent)
        self.setWindowTitle("Логи сессии")
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        # Многострочное текстовое поле (только для чтения)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setText(logs_text)
        # Прокручиваем ползунок в самый низ (к последним логам)
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().maximum()
        )
        layout.addWidget(self.text_edit)

        # Кнопка восстановления
        self.btn_restore = QPushButton("Восстановить ферму до очистки")
        self.btn_restore.setStyleSheet(
            "background-color: #f39c12; color: white; font-weight: bold; padding: 8px;")
        if restore_callback:
            # Если нажали восстановить, закрываем окно логов и вызываем функцию
            self.btn_restore.clicked.connect(
                lambda: [restore_callback(), self.accept()])
        layout.addWidget(self.btn_restore)

        # Стандартная кнопка закрытия
        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)


class RodPropertyDialog(QDialog):  # возможно не используется.
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Свойства стержня")
        self.setModal(True)
        self.resize(350, 300)

        layout = QVBoxLayout(self)

        # --- БЛОК 1: МАТЕРИАЛ (Модуль упругости E) ---
        group_mat = QGroupBox("Материал (E, МПа)")
        layout_mat = QFormLayout(group_mat)

        self.combo_mat = QComboBox()
        self.combo_mat.addItems([
            "Сталь 45 (200 000 МПа)",
            "Алюминий Д16 (72 000 МПа)",
            "Титан ВТ1-0 (112 000 МПа)",
            "Свой материал..."
        ])

        self.spin_e = QDoubleSpinBox()
        self.spin_e.setRange(0.1, 1e9)
        self.spin_e.setDecimals(0)  # Убираем копейки для МПа

        self.combo_mat.currentIndexChanged.connect(self._update_mat)

        layout_mat.addRow("Сплав:", self.combo_mat)
        layout_mat.addRow("Модуль E:", self.spin_e)
        layout.addWidget(group_mat)

        # --- БЛОК 2: ПОПЕРЕЧНОЕ СЕЧЕНИЕ (A) ---
        group_sec = QGroupBox("Поперечное сечение (A, мм²)")
        layout_sec = QFormLayout(group_sec)

        self.combo_sec = QComboBox()
        self.combo_sec.addItems(
            ["Труба круглая", "Труба квадратная", "Своя площадь..."])

        # QStackedWidget позволяет "листать" виджеты как страницы
        self.stacked_sec = QStackedWidget()

        # Страница 1: Круглая труба
        w_round = QWidget()
        l_round = QFormLayout(w_round)
        l_round.setContentsMargins(0, 0, 0, 0)
        self.spin_r_d = QDoubleSpinBox()
        self.spin_r_d.setRange(1.0, 10000.0)
        self.spin_r_d.setValue(50.0)
        self.spin_r_t = QDoubleSpinBox()
        self.spin_r_t.setRange(0.1, 5000.0)
        self.spin_r_t.setValue(2.0)
        l_round.addRow("Наруж. диаметр (мм):", self.spin_r_d)
        l_round.addRow("Толщина стенки (мм):", self.spin_r_t)
        self.stacked_sec.addWidget(w_round)

        # Страница 2: Квадратная труба
        w_sq = QWidget()
        l_sq = QFormLayout(w_sq)
        l_sq.setContentsMargins(0, 0, 0, 0)
        self.spin_s_b = QDoubleSpinBox()
        self.spin_s_b.setRange(1.0, 10000.0)
        self.spin_s_b.setValue(50.0)
        self.spin_s_t = QDoubleSpinBox()
        self.spin_s_t.setRange(0.1, 5000.0)
        self.spin_s_t.setValue(2.0)
        l_sq.addRow("Сторона (мм):", self.spin_s_b)
        l_sq.addRow("Толщина стенки (мм):", self.spin_s_t)
        self.stacked_sec.addWidget(w_sq)

        # Страница 3: Ручной ввод площади
        w_custom = QWidget()
        l_custom = QFormLayout(w_custom)
        l_custom.setContentsMargins(0, 0, 0, 0)
        self.spin_c_a = QDoubleSpinBox()
        self.spin_c_a.setRange(0.01, 1e9)
        self.spin_c_a.setValue(300.0)
        l_custom.addRow("Площадь A (мм²):", self.spin_c_a)
        self.stacked_sec.addWidget(w_custom)

        self.lbl_area = QLabel("Итоговая площадь: 0.00 мм²")
        self.lbl_area.setStyleSheet("font-weight: bold; color: #4CAF50;")

        self.combo_sec.currentIndexChanged.connect(
            self.stacked_sec.setCurrentIndex)
        self.combo_sec.currentIndexChanged.connect(self._calc_area)

        # Привязываем пересчет площади к изменению любых размеров
        self.spin_r_d.valueChanged.connect(self._calc_area)
        self.spin_r_t.valueChanged.connect(self._calc_area)
        self.spin_s_b.valueChanged.connect(self._calc_area)
        self.spin_s_t.valueChanged.connect(self._calc_area)
        self.spin_c_a.valueChanged.connect(self._calc_area)

        layout_sec.addRow("Профиль:", self.combo_sec)
        layout_sec.addRow(self.stacked_sec)
        layout_sec.addRow(self.lbl_area)
        layout.addWidget(group_sec)

        # --- КНОПКИ ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        # Инициализация начальных значений
        self.calculated_area = 0.0
        self._update_mat()
        self._calc_area()

    def _update_mat(self):
        """Устанавливает модуль упругости в зависимости от сплава"""
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
            self.spin_e.setEnabled(True)  # Свой материал

    def _calc_area(self):
        """Математика профилей"""
        idx = self.combo_sec.currentIndex()
        a = 0.0
        if idx == 0:  # Круглая: A = (pi/4) * (D^2 - d^2)
            D = self.spin_r_d.value()
            t = self.spin_r_t.value()
            if D > 2 * t:
                a = (math.pi / 4) * (D**2 - (D - 2 * t)**2)
        elif idx == 1:  # Квадратная: A = B^2 - b^2
            B = self.spin_s_b.value()
            t = self.spin_s_t.value()
            if B > 2 * t:
                a = B**2 - (B - 2 * t)**2
        else:  # Своя
            a = self.spin_c_a.value()

        self.calculated_area = a
        self.lbl_area.setText(f"Итоговая площадь: {a:.2f} мм²")

    def get_values(self):
        return self.spin_e.value(), self.calculated_area
