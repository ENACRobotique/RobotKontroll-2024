from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPainter, QColor, QPen
from PyQt5.QtCore import QRectF, Qt, QObject, pyqtSignal
import math

import sys
import robot_state_pb2 as hgpb
import ecal.core.core as ecal_core
from ecal.core.publisher import ProtoPublisher
from ecal.core.subscriber import ProtoSubscriber


Robot_diameter = 300 #mm
Map_height = 2000 #mm
Map_width = 3000 #mm
Scale = 0.4 # mm -> graphic_size


class Map_scene(QGraphicsScene):
    def __init__(self,x,y,w,h):
        super().__init__(x,y,w,h)
        self.background = QImage("table.png")

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        rect_image = QRectF(rect.topLeft().x() / (Map_width*Scale) * self.background.width() , rect.topLeft().y() / (Map_height*Scale) * self.background.height(), self.background.width() * rect.width() / (Map_width*Scale) ,self.background.height() * rect.height() / (Map_height*Scale))
        painter.drawImage(rect, self.background, rect_image)


class MySignalEmitter(QObject):
    custom_signal = pyqtSignal(float, float, float)

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

        orientation_pointer = QGraphicsLineItem(0,0,300*Scale,0)
        orientation_pointer.setPen(QPen(Qt.black, 10*Scale, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        self.addToGroup(orientation_pointer)

    def setPos(self,x,y,theta):
        super().setPos(x * Scale ,(Map_height - y)* Scale)
        super().setRotation(math.degrees(-theta))
        self.x = x
        self.y = y
        self.theta = theta



if __name__ == "__main__":
    app = QApplication([])
    main_window = QMainWindow()

    ##### Tool bar
    #tool_bar = QToolBar("tools")
    #tool_bar.addWidget(QPushButton("tool test"))
    #main_window.addToolBar(Qt.ToolBarArea.TopToolBarArea,tool_bar)

    ##### Container Principal
    central_frame = QFrame()
    main_window.setCentralWidget(central_frame)
    central_frame_layout = QHBoxLayout()
    central_frame.setLayout(central_frame_layout)


    ##### Ajout de la map
    scene = Map_scene(0,0,Map_width * Scale, Map_height * Scale)

    robot = Robot()
    robot.setPos(1500,1000,math.pi/2)
    scene.addItem(robot)

    view = QGraphicsView(scene)
    central_frame_layout.addWidget(view)

    #####
    robots_tabs = QTabWidget()
    central_frame_layout.addWidget(robots_tabs)

    page = QFrame()
    page_layout = QVBoxLayout()
    page.setLayout(page_layout)
    page_layout.addWidget(QPushButton("button 1"))
    page_layout.addWidget(QPushButton("button 2"))
    robots_tabs.addTab(page,"Robot 1")



    main_window.show()

    ##########
    ## Ecal ##
    ##########
    # temporaire
    signal_emitter = MySignalEmitter()

    def send_signal(topic_name, hlm, time):
        signal_emitter.custom_signal.emit(hlm.x, hlm.y, hlm.theta)
    
    signal_emitter.custom_signal.connect(robot.setPos)

    ecal_core.initialize(sys.argv, "Robot2Kontroll")
    odom_pos_sub = ProtoSubscriber("odom_pos", hgpb.Position)
    odom_pos_sub.set_callback(send_signal)

    ##### Launch the app
    app.exec()