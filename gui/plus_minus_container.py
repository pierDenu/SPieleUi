from pathlib import Path

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QPushButton

from side_panels_container import SidePanelsContainer


class PlusMinusContainer(SidePanelsContainer):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.style = self.load_qss("styles/button.qss")
        self.set_up()

    def set_up(self):
        left_panel, right_panel = self.get_panels()

        minus_button = QPushButton("-")
        plus_button = QPushButton("+")
        font = QFont("Arial", 24)
        for button in [minus_button, plus_button]:
            button.setFont(font)

        self.setStyleSheet(self.style)

        left_panel.add_widget(widget=minus_button, widget_name="minus_button")
        right_panel.add_widget(widget=plus_button, widget_name="plus_button")

        self.set_default_widget_size(80, 80)