from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout

from side_panel_widget import SidePanelWidget


class SidePanelsContainer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.left_panel = SidePanelWidget(
            layout_alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.right_panel = SidePanelWidget(
            layout_alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 20, 10, 20)

        self.layout.addWidget(self.left_panel)
        self.layout.addStretch(1)  # центральна порожня зона
        self.layout.addWidget(self.right_panel)

    def set_default_widget_size(self, width, height):
        self.left_panel.set_default_child_widgets_size(width, height)
        self.right_panel.set_default_child_widgets_size(width, height)

    def get_panels(self):
        return self.left_panel, self.right_panel

    def get_left_panel(self):
        return self.left_panel

    def get_right_panel(self):
        return self.right_panel

    def update_panels_widgets(self, left_panel_widgets=None, right_panel_widgets=None):
        if left_panel_widgets:
            print()
            self.left_panel.update_child_widgets_dict(left_panel_widgets)

        if right_panel_widgets:
            self.right_panel.update_child_widgets_dict(right_panel_widgets)
