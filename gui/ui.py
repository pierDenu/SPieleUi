from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QHBoxLayout

from freq_input_widget import FreqInputWidget
from drop_down_list import DropDownList
from side_panels_container import SidePanelsContainer
from switch_toggle import SwitchToggle


class UI(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.layout = QVBoxLayout(self)

        self.controls_container = SidePanelsContainer(self)
        self.plus_minus_container = SidePanelsContainer(self)
        self.settings_container = SidePanelsContainer(self)

        self.set_up_controls_container()
        self.set_up_settings_container()
        self.set_up_plus_minus_container()

        self.layout.addWidget(self.settings_container, 1)
        self.layout.addWidget(self.controls_container, 5)
        self.layout.addWidget(self.plus_minus_container, 4)

        self.is_visible = True
        #self.controls_container.set_default_widget_size(100, 100)

    def set_up_controls_container(self):
        left_controls_dict = dict()
        left_controls_dict["threats_button"] = QPushButton()
        left_controls_dict["scan_button"] = QPushButton("S")
        left_controls_dict["dji_button"] = QPushButton("D")

        right_controls_dict = dict()
        right_controls_dict["freq_input_field"] = FreqInputWidget()
        right_controls_dict["intercept_button"] = QPushButton("I")
        self.controls_container.update_panels_widgets(left_controls_dict, right_controls_dict)
        self.controls_container.set_default_widget_size(100, 100)

        left_panel = self.controls_container.get_left_panel()
        left_panel.set_child_button_icon(widget_name="threats_button",
                                         icon_path="/home/bohdan/Documents/Study/DS/LAB3/SPIEL_UI/gui/gui_assets/ss_icon.png")

    def set_up_settings_container(self):
        right_settings_dict = dict()
        left_settings_dict = dict()
        toggle_controls_switch = SwitchToggle(parent=self, checked_color="#FFB000",
                                              pulse_checked_color="#44FFB000")
        exit_button = QPushButton("Exit")
        toggle_controls_switch.stateChanged.connect(self.toggle_visibility)

        right_settings_dict["toggle_controls_switch"] = toggle_controls_switch
        left_settings_dict["exit_button"] = exit_button
        self.settings_container.update_panels_widgets(right_panel_widgets=right_settings_dict, left_panel_widgets=left_settings_dict)

    def set_up_plus_minus_container(self):
        left_panel, right_panel = self.plus_minus_container.get_panels()

        minus_button = QPushButton("-")
        plus_button = QPushButton("+")

        left_panel.add_widget(widget=minus_button, widget_name="minus_button")
        right_panel.add_widget(widget=plus_button, widget_name="plus_button")
        self.plus_minus_container.set_default_widget_size(100, 100)


    def toggle_visibility(self):
        self.is_visible = not self.is_visible
        self.controls_container.setVisible(self.is_visible)
        self.plus_minus_container.setVisible(self.is_visible)


