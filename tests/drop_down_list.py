from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QComboBox, QAbstractItemView


class DropDownList(QComboBox):
    def __init__(self, *args, scroll_to_top_on_open: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.scroll_to_top_on_open = scroll_to_top_on_open

    def showPopup(self):
        # показати стандартний popup
        super().showPopup()

        view = self.view()
        popup = view.window()  # popup-вікно зі списком

        # (опційно) щоб список починався зверху, а не "навколо" поточного елемента
        if self.scroll_to_top_on_open:
            idx0 = view.model().index(0, 0)
            if idx0.isValid():
                view.scrollTo(idx0, QAbstractItemView.ScrollHint.PositionAtTop)

        # позиція строго під комбобоксом
        below = self.mapToGlobal(QPoint(0, self.height()))

        # обмежити висоту, щоб popup все одно відкривався ВНИЗ і не виліз за екран
        screen = QGuiApplication.screenAt(below) or self.screen()
        if screen:
            avail = screen.availableGeometry()
            max_h = max(50, avail.bottom() - below.y() - 2)
            popup.resize(popup.width(), min(popup.height(), max_h))

        # примусово поставити popup під комбобокс
        popup.move(below)