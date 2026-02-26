import os
import mmap

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QWidget


class FB0VideoWidget(QWidget):
    def __init__(self):
        super().__init__()

        # Повідомляє Qt, що віджет повністю непрозорий і ти сам повністю перемальовуєш його у paintEvent
        # (Qt може пропустити зайві операції з фоном/прозорістю, часто менше мерехтіння і трохи швидше)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        # Забороняє Qt автоматично заливати фон віджета системним бекграундом перед paintEvent
        # (прибирає зайвий крок "очистити фон → потім намалювати кадр", корисно для відео/анімованих віджетів)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        # читаємо параметри fb0
        with open("/sys/class/graphics/fb0/virtual_size") as f:
            w, h = map(int, f.read().strip().split(","))
            print(w, h)
        with open("/sys/class/graphics/fb0/bits_per_pixel") as f:
            bpp = int(f.read().strip()) // 8
        with open("/sys/class/graphics/fb0/stride") as f:
            stride = int(f.read().strip())

        self.w = w
        self.h = h
        self.bpp = bpp
        self.stride = stride
        self.size = stride * h

        # відкриваємо та мапимо framebuffer
        self.fd = os.open("/dev/fb0", os.O_RDONLY)
        self.mm = mmap.mmap(self.fd, self.size, access=mmap.ACCESS_READ)

        self.img = QImage(self.mm, self.w, self.h, self.stride, QImage.Format.Format_ARGB32)


    def paintEvent(self, e):
        p = QPainter(self)
        p.drawImage(QRect(0, 0, self.w, self.h), self.img)


    def close(self):
        self.mm.close()
        os.close(self.fd)

