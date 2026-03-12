from PyQt6.QtWidgets import QPushButton

from freq_input_widget import FreqInputWidget
from side_panels_container import SidePanelsContainer


class ControlsContainer(SidePanelsContainer):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.style = self.load_qss("styles/button.qss")
        self.setStyleSheet(self.style)
        self.set_up()

    def set_up(self):
        left_controls_dict = {
            "scan_button": QPushButton("S"),
            "dji_button": QPushButton("D"),
        }

        right_controls_dict = {
            "freq_input_field": QPushButton("Custom"),
            "intercept_button": QPushButton("I"),
        }

        self.update_panels_widgets(left_controls_dict, right_controls_dict)
        self.set_default_widget_size(70, 70)
