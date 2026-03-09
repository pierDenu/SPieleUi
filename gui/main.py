import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QStackedLayout, QPushButton
from PyQt6.QtCore import QTimer, Qt
from video0_widget import Video0Widget
from ui import UI
from PyQt6.QtGui import QImage, QPixmap


class MainWindow(QMainWindow):
    def __init__(self, width, height):
        super().__init__()
        self.setWindowTitle("Spiel")
        self.resize(width, height)

        self.container = QWidget(self)
        self._init_widgets()
        self._create_layout()
        self._add_widgets_to_layout()

        self.setCentralWidget(self.container)

        self.w = width
        self.h = height

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.video0_widget.grab)
        self.timer.start(15)

    def _init_widgets(self):
        self.video0_widget = Video0Widget()
        self.ui = UI()

    def _create_layout(self):
        self.layout = QStackedLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setStackingMode(QStackedLayout.StackingMode.StackAll)

    def _add_widgets_to_layout(self):
        self.layout.addWidget(self.ui)  # передній шар
        self.layout.addWidget(self.video0_widget)  # задній шар



def main():
    app = QApplication(sys.argv)
    win = MainWindow(1024, 600)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
