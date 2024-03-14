from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPainter, QColor, QPen
from PyQt5.QtCore import QRectF, Qt, QObject, pyqtSignal
import math

import sys

from PyQt5.QtWidgets import QWidget
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
    
    def addRobot(self, robot):
        self.addItem(robot)

    
class Monitor_Command(QTabWidget):
    
    def addRobot(self,robot):
        page = QFrame()
        self.addTab(page,robot.name)
        page_layout = QVBoxLayout()
        page.setLayout(page_layout)

        pos_frame = QFrame()
        page_layout.addWidget(pos_frame)
        pos_frame_layout = QHBoxLayout()
        pos_frame.setLayout(pos_frame_layout)
        self.x_label = QLabel("Na")
        pos_frame_layout.addWidget(self.x_label)
        self.y_label = QLabel("Na")
        pos_frame_layout.addWidget(self.y_label)
        self.theta_label = QLabel("Na")
        pos_frame_layout.addWidget(self.theta_label)

        robot.signal_emitter.pos_signal.connect(self.update_pos)
    
    def update_pos(self,x,y,theta):
        self.x_label.setText("x_odom:{:.3f}".format(x))
        self.y_label.setText("y_odom:{:.3f}".format(y))
        self.theta_label.setText("theta_odom:{:.3f}".format(theta))
        



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

        QGraphicsTextItem(self.name, body)

        ## Ecal
        # Position
        def send_pos_signal(topic_name, hlm, time):
            #if hlm.name == self.name:
            #    self.signal_emitter.pos_signal.emit(hlm.x, hlm.y, hlm.theta)
            self.signal_emitter.pos_signal.emit(hlm.x, hlm.y, hlm.theta)

        pos_sub = ProtoSubscriber(ecal_pos_topic, hgpb.Position)
        pos_sub.set_callback(send_pos_signal)

        self.signal_emitter.pos_signal.connect(self.setPos)
        
        

    def setPos(self,x,y,theta):
        super().setPos(x * Scale ,(Map_height - y)* Scale)
        super().setRotation(math.degrees(-theta))
        self.x = x
        self.y = y
        self.theta = theta


def addRobot(scene, tabs, name, ecal_pos_topic):
        robot = Robot(name, ecal_pos_topic)
        scene.addRobot(robot)
        tabs.addRobot(robot)


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
    robots_tabs = Monitor_Command()
    central_frame_layout.addWidget(robots_tabs)

    ##### Tool bar
    tool_bar = QToolBar("tools")
    main_window.addToolBar(Qt.ToolBarArea.TopToolBarArea,tool_bar)
    
    add_robot_button = QPushButton("Add robot")
    tool_bar.addWidget(add_robot_button)

    robot_name_field = QLineEdit()
    tool_bar.addWidget(robot_name_field)
    robot_name_field.setPlaceholderText("Name")

    robot_ecal_pos_field = QLineEdit()
    tool_bar.addWidget(robot_ecal_pos_field)
    robot_ecal_pos_field.setPlaceholderText("Ecal pos topic")

    add_robot_button.clicked.connect(lambda :addRobot(scene, robots_tabs, robot_name_field.text(), robot_ecal_pos_field.text()))

    

    



    main_window.show()
    app.exec()