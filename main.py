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
    
    def addRobot(self, name, ecal_pos_topic):
        robot = Robot(name, ecal_pos_topic)
        self.addItem(robot)
    



class MySignalEmitter(QObject):
    pos_signal = pyqtSignal(float, float, float)

class Robot(QGraphicsItemGroup):
    def __init__(self, name, ecal_pos_topic, color = QColor("blue")) -> None:
        super().__init__()
        self.x = 0
        self.y = 0
        self.theta = 0
        self.color = color
        self.name = name

        self.signal_emitter = MySignalEmitter() # Qt Signals

        ## GraphicsItem
        body = QGraphicsEllipseItem((- Robot_diameter/2) * Scale, - Robot_diameter/2 * Scale, Robot_diameter * Scale, Robot_diameter * Scale)
        body.setBrush(self.color)
        self.addToGroup(body)

        orientation_pointer = QGraphicsLineItem(0,0,300*Scale,0)
        orientation_pointer.setPen(QPen(Qt.black, 10*Scale, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        self.addToGroup(orientation_pointer)

        ## Ecal
        # Position
        def send_pos_signal(topic_name, hlm, time):
            if hlm.name == self.name:
                self.signal_emitter.pos_signal.emit(hlm.x, hlm.y, hlm.theta)

        pos_sub = ProtoSubscriber(ecal_pos_topic, hgpb.Position)
        pos_sub.set_callback(send_pos_signal)

        self.signal_emitter.pos_signal.connect(robot.setPos)
        

    def setPos(self,x,y,theta):
        super().setPos(x * Scale ,(Map_height - y)* Scale)
        super().setRotation(math.degrees(-theta))
        self.x = x
        self.y = y
        self.theta = theta



if __name__ == "__main__":
    ecal_core.initialize(sys.argv, "Robot2Kontroll")
    app = QApplication([])
    main_window = QMainWindow()

    ##### Container Principal
    central_frame = QFrame()
    main_window.setCentralWidget(central_frame)
    central_frame_layout = QHBoxLayout()
    central_frame.setLayout(central_frame_layout)


    ### Ajout de la map
    scene = Map_scene(0,0,Map_width * Scale, Map_height * Scale)

    view = QGraphicsView(scene)
    central_frame_layout.addWidget(view)

    ### Ajout de tab
    robots_tabs = QTabWidget()
    central_frame_layout.addWidget(robots_tabs)

    page = QFrame()
    page_layout = QVBoxLayout()
    page.setLayout(page_layout)
    page_layout.addWidget(QPushButton("TEST"))
    page_layout.addWidget(QPushButton("TEST"))
    robots_tabs.addTab(page,"TEST")



    ##### Tool bar
    tool_bar = QToolBar("tools")
    main_window.addToolBar(Qt.ToolBarArea.TopToolBarArea,tool_bar)
    
    add_robot_button = QPushButton("Add robot")
    tool_bar.addWidget(add_robot_button)
    add_robot_button.clicked.connect(scene.addRobot)

    robot_name_field = QLineEdit()
    tool_bar.addWidget(robot_name_field)
    robot_name_field.setPlaceholderText("Name")

    robot_ecal_pos_field = QLineEdit()
    tool_bar.addWidget(robot_ecal_pos_field)
    robot_ecal_pos_field.setPlaceholderText("Ecal pos topic")





    main_window.show()

    ##########
    ## Ecal ##
    ##########
    # temporaire
    



    ##### Launch the app
    app.exec()