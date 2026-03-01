import cv2
from PyQt6.QtCore import QTimer, QRect
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QWidget

class Video0Widget(QWidget):
    def __init__(self):
        super().__init__()
        self.video_capture = cv2.VideoCapture("/dev/video0", cv2.CAP_V4L2)
        self.current_frame = QImage()

    def grab(self):
        ok, frame_bgr = self.video_capture.read()
        if not ok:
            return
        # BGR -> RGB
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        self.current_frame = QImage(frame_rgb.data, w, h, w*ch, QImage.Format.Format_RGB888)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.drawImage(QRect(0, 0, self.width(), self.height()), self.current_frame)

    def closeEvent(self, e):
        self.video_capture.release()
        super().closeEvent(e)