import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QStackedLayout, QPushButton
from PyQt6.QtCore import QTimer, Qt
from fb0_video_widget import FB0VideoWidget
from ui import UI
from PyQt6.QtGui import QImage, QPixmap


class MainWindow(QMainWindow):
    def __init__(self, width, height):
        super().__init__()
        self.setWindowTitle("Spiel")
        self.resize(width, height)

        container = QWidget(self)
        self.fb0_video = FB0VideoWidget()
        self.ui = UI()
        self.ui.raise_()

        stack = QStackedLayout(container)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        stack.addWidget(self.ui)    # передній шар
        stack.addWidget(self.fb0_video)  # задній шар

        self.setCentralWidget(container)

        self.w = width
        self.h = height

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fb0_video.update)
        self.timer.start(3)

def main():
    app = QApplication(sys.argv)
    win = MainWindow(1024, 600)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
