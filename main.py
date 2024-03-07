from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPainter, QColor, QPen, QResizeEvent
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtWidgets import QGraphicsItem, QWidget
import math

Robot_diameter = 30 #cm
Map_height = 200 #cm
Map_width = 300 #cm
Scale = 4 # cm -> graphic_size


class Map_scene(QGraphicsScene):
    def __init__(self,x,y,w,h):
        super().__init__(x,y,w,h)
        self.background = QImage("table.png")

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.drawImage(rect,self.background)


class Robot(QGraphicsItemGroup):
    def __init__(self, color = QColor("blue")) -> None:
        super().__init__()
        self.x = 0
        self.y = 0
        self.theta = 0
        self.color = color
        body = QGraphicsEllipseItem((- Robot_diameter/2) * Scale, - Robot_diameter/2 * Scale, Robot_diameter * Scale, Robot_diameter * Scale)
        body.setBrush(self.color)
        self.addToGroup(body)

        orientation_pointer = QGraphicsLineItem(0,0,30*Scale,0)
        orientation_pointer.setPen(QPen(Qt.black, Scale, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        self.addToGroup(orientation_pointer)

    def setPos(self,x,y,theta):
        super().setPos(x * Scale ,(Map_height - y)* Scale)
        super().setRotation(math.degrees(-theta))
        self.x = x
        self.y = y
        self.theta = theta



if __name__ == "__main__":
    app = QApplication([])
    scene = Map_scene(0,0,Map_width * Scale, Map_height * Scale)

    robot = Robot()
    
    scene.addItem(robot)

    view = QGraphicsView(scene)

    ######
    main_window = QMainWindow()
    #tool_bar = QToolBar("tools")
    #tool_bar.addWidget(QPushButton("tool test"))
    #main_window.addToolBar(Qt.ToolBarArea.TopToolBarArea,tool_bar)

    central_frame = QFrame()
    main_window.setCentralWidget(central_frame)
    central_frame_layout = QHBoxLayout()
    central_frame.setLayout(central_frame_layout)

    central_frame_layout.addWidget(view)

    robots_tabs = QTabWidget()
    central_frame_layout.addWidget(robots_tabs)

    #page = QFrame()
    #page_layout = QVBoxLayout()
    #page.setLayout(page_layout)
    #page_layout.addWidget(QPushButton("button 1"))
    #page_layout.addWidget(QPushButton("button 2"))
    #robots_tabs.addTab(page,"Robot 1")



    main_window.show()
    app.exec()