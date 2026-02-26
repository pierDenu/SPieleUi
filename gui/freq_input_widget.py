from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel


class FreqInputWidget(QWidget):
    def __init__(self, parent=None):
        super(FreqInputWidget, self).__init__(parent)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        self.freq_input_field = QLineEdit()
        self.freq_input_field.setPlaceholderText("200–7200")
        self.unit_label = QLabel("МГц")

        row.addWidget(self.freq_input_field, 1)  # поле тягнеться
        row.addWidget(self.unit_label, 0)  # "МГц" фіксовано