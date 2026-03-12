from PyQt6.QtWidgets import QPushButton, QApplication

from side_panels_container import SidePanelsContainer
from switch_toggle import SwitchToggle


class SettingsContainer(SidePanelsContainer):
    def __init__(self, parent=None, toggle_callback=None):
        super().__init__(parent)
        self.toggle_callback = toggle_callback
        self.style = self.load_qss("styles/button.qss")
        self.setStyleSheet(self.style)
        self.set_up()

    def set_up(self):
        toggle_controls_switch = SwitchToggle(
            parent=self,
            checked_color="#FFB000",
            pulse_checked_color="#44FFB000"
        )

        exit_button = QPushButton("Exit")

        if self.toggle_callback is not None:
            toggle_controls_switch.stateChanged.connect(self.toggle_callback)

        exit_button.clicked.connect(QApplication.instance().quit)

        right_settings_dict = {
            "toggle_controls_switch": toggle_controls_switch
        }

        left_settings_dict = {
            "exit_button": exit_button,
            "threats_button": QPushButton()
        }

        self.update_panels_widgets(
            right_panel_widgets=right_settings_dict,
            left_panel_widgets=left_settings_dict
        )
        self.set_default_widget_size(70, 70)

        left_panel = self.get_left_panel()
        left_panel.set_child_button_icon(
            widget_name="threats_button",
            icon_path="/home/bohdan/Documents/Study/DS/LAB3/SPIEL_UI/gui/gui_assets/ss_icon.png"
        )
