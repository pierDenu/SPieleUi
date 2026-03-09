from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout
from freq_input_widget import FreqInputWidget
from drop_down_list import DropDownList
from gui.panel_widget import PanelWidget
from switch_toggle import SwitchToggle


class UI(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.toggle_controls_switch = SwitchToggle(parent=self, checked_color="#FFB000",
                                                   pulse_checked_color="#44FFB000")

        self.left_panel_widget = PanelWidget(layout_alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.right_panel_widget = PanelWidget(layout_alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        self.controls_widget = QWidget(self)
        self.layout = QHBoxLayout(self.controls_widget)
        self.layout.setContentsMargins(10, 20, 10, 20)

        self.add_controls_for_left_panel_widget()
        self.add_controls_for_right_panel_widget()

        self.layout.addWidget(self.left_panel_widget)
        self.layout.addStretch(1)  # центральна порожня зона
        self.layout.addWidget(self.right_panel_widget)

        self.toggle_controls_switch.setGeometry(900, 500, 100, 70)
        self.toggle_controls_switch.stateChanged.connect(self.toggle_visibility)

        self.is_visible = True

    def add_controls_for_right_panel_widget(self):
        controls_dict = dict()
        controls_dict["freq_input_field"] = FreqInputWidget()
        controls_dict["intercept_button"] = QPushButton("I")

        self.right_panel_widget.update_child_widgets_dict(controls_dict)


    def add_controls_for_left_panel_widget(self):
        controls_dict = dict()
        controls_dict["scan_button"] = QPushButton("S")
        controls_dict["dji_button"] = QPushButton("D")
        controls_dict["threats_dropdown_list"] = DropDownList(items_list=["Mavic", "Shahed", "DJI"])

        self.left_panel_widget.update_child_widgets_dict(controls_dict)



    def toggle_visibility(self):
        self.is_visible = not self.is_visible
        self.controls_widget.setVisible(self.is_visible)

    def resizeEvent(self, e):
        bottom_gap = 100
        r = self.rect()
        r.setHeight(max(0, r.height() - bottom_gap))
        self.controls_widget.setGeometry(r)  # або self.controls.setGeometry(r)
        super().resizeEvent(e)

