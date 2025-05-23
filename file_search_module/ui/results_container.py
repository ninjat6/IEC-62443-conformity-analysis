from PyQt6.QtWidgets import QWidget, QSizePolicy

class ResultsContainer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.layout():
            container_width = self.width()
            for i in range(self.layout().count()):
                widget = self.layout().itemAt(i).widget()
                if widget:
                    widget.setMaximumWidth(container_width)
                    widget.updateGeometry()
