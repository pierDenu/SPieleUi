from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout

from freq_input_widget import FreqInputWidget
from drop_down_list import DropDownList


class UI(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.toggle_controls_button = QPushButton("Toggle UI", parent=self)

        self.controls = QWidget(self)
        controls_layout = QVBoxLayout(self.controls)

        threats_dropdown_list = DropDownList(self)
        threats = ["Mavic", "Shahed", "DJI"]
        threats_dropdown_list.addItems(threats)

        freq_input_field = FreqInputWidget()
        scan_button = QPushButton("Scan")

        controls_layout.addWidget(freq_input_field)
        controls_layout.addWidget(scan_button)
        controls_layout.addWidget(threats_dropdown_list)


        self.toggle_controls_button.setGeometry(900, 450, 100, 100)
        self.toggle_controls_button.clicked.connect(self.toggle_visibility)

        self.is_visible = True

    def toggle_visibility(self):
        self.is_visible = not self.is_visible
        self.controls.setVisible(self.is_visible)


