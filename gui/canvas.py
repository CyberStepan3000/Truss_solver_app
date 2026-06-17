import math
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem
from PyQt5.QtGui import QPen, QBrush, QColor, QPainter, QPolygonF
from PyQt5.QtCore import Qt, pyqtSignal, QPointF


class TrussCanvas(QGraphicsView):
    canvas_clicked = pyqtSignal(float, float)
    # НОВЫЙ СИГНАЛ: передает координаты мыши при простом движении
    canvas_mouse_moved = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.Antialiasing)
        self.scene.setSceneRect(-1000, -1000, 2000, 2000)
        self.scale(40, -40)

        # ВАЖНО: Включаем отслеживание мыши без зажатой кнопки
        self.setMouseTracking(True)

        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._is_panning = False
        self._pan_start_pos = None

        self.grid_step = 1.0
        self.node_radius = 0.15

        self.is_dark_theme = False
        self._last_nodes = {}
        self._last_rods = []
        self._last_displacements = None  # Добавили
        self._last_forces = None

        # Создаем линию предпросмотра
        self._create_preview_line()

    def _create_preview_line(self):
        """Создает зеленую полупрозрачную линию для предпросмотра стержня"""
        preview_pen = QPen(QColor(46, 204, 113, 180))
        preview_pen.setWidth(3)            # Толщина 3 пикселя на экране
        # Запрещаем линии "толстеть" при зуме
        preview_pen.setCosmetic(True)
        preview_pen.setStyle(Qt.DashLine)  # Пунктир

        self.preview_line = self.scene.addLine(0, 0, 0, 0, preview_pen)
        self.preview_line.hide()
        self.preview_line.setZValue(5)

    def show_preview_rod(self, x1, y1, x2, y2):
        self.preview_line.setLine(x1, y1, x2, y2)
        self.preview_line.show()

    def hide_preview_rod(self):
        self.preview_line.hide()

    def set_theme(self, is_dark: bool):
        self.is_dark_theme = is_dark
        if is_dark:
            self.setBackgroundBrush(QBrush(QColor("#1e1e1e")))
        else:
            self.setBackgroundBrush(QBrush(QColor("#ffffff")))
        self.scene.invalidate()
        # Передаем все 4 параметра
        self.draw_model(self._last_nodes, self._last_rods,
                        self._last_displacements, self._last_forces)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)

        # 1. Защита от инверсии осей: находим реальные границы видимой области
        x_min = min(rect.left(), rect.right())
        x_max = max(rect.left(), rect.right())
        y_min = min(rect.top(), rect.bottom())
        y_max = max(rect.top(), rect.bottom())

        # 2. Настраиваем цвета с прозрачностью (Альфа-канал 0-255)
        # 20 - это очень прозрачная линия, 120 - хорошо видимая ось
        if self.is_dark_theme:
            grid_color = QColor(255, 255, 255, 20)  # Белая прозрачная сетка
            axis_color = QColor(255, 255, 255, 120)  # Главные оси
        else:
            grid_color = QColor(0, 0, 0, 50)        # Черная прозрачная сетка
            axis_color = QColor(0, 0, 0, 120)       # Главные оси

        grid_pen = QPen(grid_color, 0)
        painter.setPen(grid_pen)

        # Вычисляем стартовые точки, кратные шагу сетки
        start_x = math.floor(x_min / self.grid_step) * self.grid_step
        start_y = math.floor(y_min / self.grid_step) * self.grid_step

        # 3. Рисуем ВЕРТИКАЛЬНЫЕ линии (используем QPointF для точности)
        x = start_x
        while x <= x_max:
            if abs(x) > 1e-5:  # Пропускаем координату 0, там будет главная ось
                painter.drawLine(QPointF(x, y_min), QPointF(x, y_max))
            x += self.grid_step

        # 4. Рисуем ГОРИЗОНТАЛЬНЫЕ линии
        y = start_y
        while y <= y_max:
            if abs(y) > 1e-5:  # Пропускаем координату 0, там будет главная ось
                painter.drawLine(QPointF(x_min, y), QPointF(x_max, y))
            y += self.grid_step

        # 5. Рисуем главные оси (X и Y) более жирным/непрозрачным пером
        axis_pen = QPen(axis_color, 0)
        painter.setPen(axis_pen)
        painter.drawLine(QPointF(x_min, 0), QPointF(
            x_max, 0))  # Горизонтальная ось X
        painter.drawLine(QPointF(0, y_min), QPointF(
            0, y_max))  # Вертикальная ось Y

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        self.scale(zoom_factor, zoom_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._pan_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            snap_x = round(scene_pos.x() / self.grid_step) * self.grid_step
            snap_y = round(scene_pos.y() / self.grid_step) * self.grid_step
            self.canvas_clicked.emit(snap_x, snap_y)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = event.pos() - self._pan_start_pos
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._pan_start_pos = event.pos()
            event.accept()
            return

        # НОВОЕ: Передаем координаты мыши при движении
        scene_pos = self.mapToScene(event.pos())
        self.canvas_mouse_moved.emit(scene_pos.x(), scene_pos.y())

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _draw_support(self, node, color):
        """Программная отрисовка условных обозначений опор по ГОСТу"""
        if not node.fixed_x and not node.fixed_y:
            return  # Опоры нет, узел свободен

        pen = QPen(color)
        pen.setWidth(2)
        pen.setCosmetic(True)

        L = 0.6  # Базовый размер опоры
        radius = 0.1  # Радиус катка

        if node.fixed_x and node.fixed_y:
            # НЕПОДВИЖНЫЙ ШАРНИР
            # Треугольник
            poly = QPolygonF([
                QPointF(node.x, node.y),
                QPointF(node.x - L/2, node.y - L),
                QPointF(node.x + L/2, node.y - L)
            ])
            self.scene.addPolygon(poly, pen, QBrush(Qt.NoBrush))

            # Площадка (земля)
            self.scene.addLine(node.x - L, node.y - L,
                               node.x + L, node.y - L, pen)

            # Штриховка
            for i in range(-2, 3):
                x_start = node.x + i * L/2.5
                self.scene.addLine(x_start, node.y - L,
                                   x_start - L/3, node.y - L - L/3, pen)

        elif node.fixed_y and not node.fixed_x:
            # ПОДВИЖНЫЙ ШАРНИР (Ездит по X, держит Y)
            # Треугольник чуть приподнят
            poly = QPolygonF([
                QPointF(node.x, node.y),
                QPointF(node.x - L/2, node.y - 0.8*L),
                QPointF(node.x + L/2, node.y - 0.8*L)
            ])
            self.scene.addPolygon(poly, pen, QBrush(Qt.NoBrush))

            # Катки (кругляшки)
            roller_y = node.y - 0.9 * L
            self.scene.addEllipse(node.x - L/4 - radius, roller_y -
                                  radius, radius*2, radius*2, pen, QBrush(Qt.NoBrush))
            self.scene.addEllipse(node.x + L/4 - radius, roller_y -
                                  radius, radius*2, radius*2, pen, QBrush(Qt.NoBrush))

            # Земля
            self.scene.addLine(node.x - L, node.y - 1.0 * L,
                               node.x + L, node.y - 1.0 * L, pen)

        elif node.fixed_x and not node.fixed_y:
            # ПОДВИЖНЫЙ ШАРНИР (Ездит по Y, держит X - опора на стену)
            # Повернут на 90 градусов
            poly = QPolygonF([
                QPointF(node.x, node.y),
                QPointF(node.x - 0.8*L, node.y + L/2),
                QPointF(node.x - 0.8*L, node.y - L/2)
            ])
            self.scene.addPolygon(poly, pen, QBrush(Qt.NoBrush))

            # Катки
            roller_x = node.x - 0.9 * L
            self.scene.addEllipse(roller_x - radius, node.y - L/4 -
                                  radius, radius*2, radius*2, pen, QBrush(Qt.NoBrush))
            self.scene.addEllipse(roller_x - radius, node.y + L/4 -
                                  radius, radius*2, radius*2, pen, QBrush(Qt.NoBrush))

            # Стена
            self.scene.addLine(node.x - 1.0 * L, node.y - L,
                               node.x - 1.0 * L, node.y + L, pen)

    def _draw_force(self, node, color):
        """Отрисовка вектора нагрузки в виде стрелки с подписью"""
        if abs(node.force_x) < 1e-5 and abs(node.force_y) < 1e-5:
            return  # Нагрузки нет

        pen = QPen(color)
        pen.setWidth(2)
        pen.setCosmetic(True)
        brush = QBrush(color)

        # 1. Вычисляем угол вектора силы (куда направлена стрелка)
        angle = math.atan2(node.force_y, node.force_x)

        # Визуальная длина стрелки (пусть будет 1.2 метра/единицы сетки)
        L = 1.2
        end_x = node.x + L * math.cos(angle)
        end_y = node.y + L * math.sin(angle)

        # Рисуем саму линию (древко) от узла наружу
        self.scene.addLine(node.x, node.y, end_x, end_y, pen)

        # 2. Рисуем наконечник стрелки (треугольник на конце)
        arrow_size = 0.3
        # Углы для "усов" стрелки (отгибаем на 150 градусов в обе стороны от направления вектора)
        angle1 = angle + math.pi * 5 / 6
        angle2 = angle - math.pi * 5 / 6

        p1 = QPointF(end_x + arrow_size * math.cos(angle1),
                     end_y + arrow_size * math.sin(angle1))
        p2 = QPointF(end_x + arrow_size * math.cos(angle2),
                     end_y + arrow_size * math.sin(angle2))

        poly = QPolygonF([QPointF(end_x, end_y), p1, p2])
        self.scene.addPolygon(poly, pen, brush)

        # 3. Добавляем текст со значениями сил
        text_str = f"({node.force_x:g}, {node.force_y:g})"
        text_item = self.scene.addText(text_str)
        text_item.setDefaultTextColor(color)

        # МАГИЯ Qt: Делаем так, чтобы текст не переворачивался из-за инверсии оси Y
        # и не менял свой физический размер при зуме колесиком мыши!
        text_item.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

        # Привязываем текст к концу стрелки
        text_item.setPos(end_x, end_y)

    def draw_model(self, nodes: dict, rods: list, displacements: dict = None, forces: dict = None):
        self._last_nodes = nodes
        self._last_rods = rods
        self._last_displacements = displacements
        self._last_forces = forces
        self.scene.clear()

        self._create_preview_line()

        if self.is_dark_theme:
            node_brush = QBrush(QColor("#00aaff"))
            default_rod_pen = QPen(QColor("#dddddd"))
            support_color = QColor("#ffaa00")
            force_color = QColor("#ff55ff")

            color_ghost = QPen(QColor(255, 255, 255, 40), 1, Qt.DashLine)
            color_zero = QColor(100, 100, 100)
            color_tension = QColor(0, 170, 255)
            color_compression = QColor(255, 60, 60)
        else:
            node_brush = QBrush(QColor("blue"))
            default_rod_pen = QPen(QColor("black"))
            support_color = QColor("red")
            force_color = QColor("#d32f2f")

            color_ghost = QPen(QColor(0, 0, 0, 40), 1, Qt.DashLine)
            color_zero = QColor(180, 180, 180)
            color_tension = QColor(0, 0, 255)
            color_compression = QColor(220, 0, 0)

        default_rod_pen.setWidth(3)
        default_rod_pen.setCosmetic(True)
        color_ghost.setCosmetic(True)
        node_pen = QPen(Qt.NoPen)

        scale = 1.0
        max_force = 1e-9

        if displacements and nodes:
            xs = [n.x for n in nodes.values()]
            ys = [n.y for n in nodes.values()]
            span = max(max(xs) - min(xs), max(ys) - min(ys))
            if span == 0:
                span = 1.0

            max_disp = max([0.0] + [max(abs(dx), abs(dy))
                           for dx, dy in displacements.values()])
            if max_disp > 0:
                scale = (0.1 * span) / max_disp

        if forces:
            max_force = max([abs(f) for f in forces.values()] + [1e-9])

        def blend_colors(c1: QColor, c2: QColor, factor: float) -> QColor:
            r = int(c1.red() + (c2.red() - c1.red()) * factor)
            g = int(c1.green() + (c2.green() - c1.green()) * factor)
            b = int(c1.blue() + (c2.blue() - c1.blue()) * factor)
            return QColor(r, g, b)

        # 1. Опоры
        for node in nodes.values():
            self._draw_support(node, support_color)

        # 2. Исходная схема (призрак)
        if displacements:
            for rod in rods:
                # Призракам тултипы не нужны, иначе они будут перебивать активные стержни
                self.scene.addLine(rod.node1.x, rod.node1.y,
                                   rod.node2.x, rod.node2.y, color_ghost)

        # 3. Стержни (Активные)
        for rod in rods:
            tooltip_text = f"Стержень {rod.number}"  # Базовый текст

            if displacements and forces:
                dx1, dy1 = displacements.get(rod.node1.number, (0.0, 0.0))
                dx2, dy2 = displacements.get(rod.node2.number, (0.0, 0.0))
                x1 = rod.node1.x + dx1 * scale
                y1 = rod.node1.y + dy1 * scale
                x2 = rod.node2.x + dx2 * scale
                y2 = rod.node2.y + dy2 * scale

                f = forces.get(rod.number, 0.0)
                # Считаем напряжение (Усилие / Площадь)
                stress = f / rod.section

                # Добавляем результаты в тултип
                tooltip_text += f"\nУсилие (N): {f:.3f} Н\nНапряжение (σ): {stress:.3f} МПа"

                intensity = abs(f) / max_force
                if abs(f) < 1e-6:
                    r_color = color_zero
                elif f > 0:
                    r_color = blend_colors(
                        color_zero, color_tension, intensity)
                else:
                    r_color = blend_colors(
                        color_zero, color_compression, intensity)

                active_pen = QPen(r_color)
                active_pen.setWidth(1 + int(3 * intensity))
                active_pen.setCosmetic(True)
            else:
                x1, y1 = rod.node1.x, rod.node1.y
                x2, y2 = rod.node2.x, rod.node2.y
                active_pen = default_rod_pen

            # Отрисовываем линию и сохраняем объект
            line_item = self.scene.addLine(x1, y1, x2, y2, active_pen)
            # Прикрепляем к линии всплывающую подсказку
            line_item.setToolTip(tooltip_text)

        # 4. Силы
        for node in nodes.values():
            self._draw_force(node, force_color)

        # 5. Узлы
        for node in nodes.values():
            tooltip_text = f"Узел {node.number}"  # Базовый текст

            if displacements:
                dx, dy = displacements.get(node.number, (0.0, 0.0))
                nx = node.x + dx * scale
                ny = node.y + dy * scale

                # Добавляем результаты в тултип (выводим в научном формате или 5 знаков)
                tooltip_text += f"\nΔx: {dx:.5f} мм\nΔy: {dy:.5f} мм"
            else:
                nx, ny = node.x, node.y

            ellipse_item = self.scene.addEllipse(
                nx - self.node_radius, ny - self.node_radius,
                self.node_radius * 2, self.node_radius * 2,
                node_pen, node_brush
            )
            ellipse_item.setToolTip(tooltip_text)

    def clear_canvas(self):
        """Очищает холст и восстанавливает служебные элементы"""
        self.scene.clear()
        # Заново создаем невидимую линию для предпросмотра стержней,
        # так как clear() удалил её вместе с остальной фермой
        self._create_preview_line()
