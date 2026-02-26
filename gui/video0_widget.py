import cv2
from PyQt6.QtCore import QTimer, QRect
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QWidget

class Video0Widget(QWidget):
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture("/dev/video0", cv2.CAP_V4L2)
        self.frame = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.grab)
        self.timer.start(0)  # якнайчастіше

    def grab(self):
        ok, frame_bgr = self.cap.read()
        if not ok:
            return
        # BGR -> RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        self.qimg = QImage(frame_rgb.data, w, h, w*ch, QImage.Format.Format_RGB888)
        self.update()

    def paintEvent(self, e):
        if hasattr(self, "qimg"):
            p = QPainter(self)
            p.drawImage(QRect(0, 0, self.width(), self.height()), self.qimg)

    def closeEvent(self, e):
        self.cap.release()
        super().closeEvent(e)