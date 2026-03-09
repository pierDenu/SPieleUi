from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout


class PanelWidget(QWidget):
    def __init__(self, parent=None, child_widgets_dict=None, layout_alignment=None):
        super().__init__(parent)

        self.child_widgets_dict = child_widgets_dict or {}

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

        for widget in child_widgets_dict.values():
            self.layout.addWidget(widget)
