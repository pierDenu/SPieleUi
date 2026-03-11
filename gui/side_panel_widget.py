import os.path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton


class SidePanelWidget(QWidget):
    def __init__(self, parent=None, child_widgets_dict=None, layout_alignment=None):
        super().__init__(parent)

        self.child_widgets_dict = child_widgets_dict or {}
        self.child_widgets_default_size = QSize(100, 100)

        self.layout = QVBoxLayout()

        if layout_alignment is not None:
            self.layout.setAlignment(layout_alignment)

        for widget in self.child_widgets_dict.values():
            self.layout.addWidget(widget)

        self.setLayout(self.layout)

    def add_widget(self, widget: QWidget, widget_name: str):
        self.child_widgets_dict[widget_name] = widget
        self.layout.addWidget(widget)

    def update_child_widgets_dict(self, child_widgets_dict):
        self.child_widgets_dict = child_widgets_dict
        self.clear_layout()

        for widget in child_widgets_dict.values():
            self.layout.addWidget(widget)

    def set_default_child_widgets_size(self, width, height):
        self.child_widgets_default_size = QSize(width, height)
        for widget in self.child_widgets_dict.values():
            widget.setFixedSize(self.child_widgets_default_size)


    def set_child_widget_size(self, widget_name, width, height):
        self.child_widgets_dict[widget_name].setFixedSize(width, height)

    def set_child_button_icon(self, widget_name, icon_path, target_size=None):
        button = self.child_widgets_dict[widget_name]

        if not target_size:
            target_size = self.child_widgets_default_size

        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            print(f"Не вдалося завантажити іконку: {icon_path}")
            return

        # масштабуємо іконку під потрібний розмір
        scaled = pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # створюємо прозоре полотно розміру кнопки
        canvas = QPixmap(target_size)
        canvas.fill(Qt.GlobalColor.transparent)

        # малюємо іконку по центру
        painter = QPainter(canvas)
        x = (target_size.width() - scaled.width()) // 2
        y = (target_size.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()

        button.setFixedSize(target_size)
        button.setIcon(QIcon(canvas))
        button.setIconSize(target_size)
        button.setMask(canvas.mask())

        button.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                padding: 0px;
            }
        """)

    def clear_layout(self):
        while self.layout.count():
            item = self.layout.takeAt(0)

            widget = item.widget()
            widget.deleteLater()


