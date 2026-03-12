from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from controls_container import ControlsContainer
from settings_container import SettingsContainer
from plus_minus_container import PlusMinusContainer


class UI(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.layout = QVBoxLayout(self)

        self.controls_container = ControlsContainer(self)
        self.plus_minus_container = PlusMinusContainer(self)
        self.settings_container = SettingsContainer(self, toggle_callback=self.toggle_visibility)

        self.layout.addWidget(self.settings_container, 1)
        self.layout.addWidget(self.controls_container, 5)
        self.layout.addWidget(self.plus_minus_container, 4)

        self.is_visible = True

    def toggle_visibility(self):
        self.is_visible = not self.is_visible
        self.controls_container.setVisible(self.is_visible)
        self.plus_minus_container.setVisible(self.is_visible)