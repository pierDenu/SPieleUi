from PyQt6.QtWidgets import QWidget
from drop_down_list import DropDownList


class ThreatWidget(QWidget):
    def __init__(self, parent=None):
        super(ThreatWidget, self).__init__(parent)

        self.threats_dropdown_list = DropDownList(self)

        threats = ["Mavic", "Shahed", "DJI"]
        self.threats_dropdown_list.addItems(threats)
