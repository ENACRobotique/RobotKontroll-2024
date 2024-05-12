from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPainter, QColor, QPen, QTransform
from PyQt5.QtCore import QRectF, Qt, QObject, pyqtSignal, QLocale, QPointF
import math

import sys

from PyQt5.QtWidgets import QGraphicsSceneMouseEvent

import generated.robot_state_pb2 as hgpb
import ecal.core.core as ecal_core
from ecal.core.publisher import ProtoPublisher
from ecal.core.subscriber import ProtoSubscriber


Robot_diameter = 300 #mm
Map_height = 2000 #mm
Map_width = 3000 #mm
Scale = 0.43 # mm -> graphic_size


class Map_scene(QGraphicsScene):
    def __init__(self,x,y,w,h):
        super().__init__(x,y,w,h)
        self.background = QImage("table.png")
        self.pub_send_pos = ProtoPublisher("set_position",hgpb.Position)
        self.selectedRobotGraphic = None
        self.pressPoint = QPointF()
        self.orientation_line = QGraphicsLineItem(0,0,Map_width * Scale, Map_height * Scale)
        self.addItem(self.orientation_line)
        self.orientation_line.hide()
        self.orientation_line.setPen(QPen(Qt.blue, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        rect_image = QRectF(rect.topLeft().x() / (Map_width*Scale) * self.background.width() , rect.topLeft().y() / (Map_height*Scale) * self.background.height(), self.background.width() * rect.width() / (Map_width*Scale) ,self.background.height() * rect.height() / (Map_height*Scale))
        painter.drawImage(rect, self.background, rect_image)
    
    def addRobotGraphic(self, robot_graphic):
        self.addItem(robot_graphic)
    
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton :
            self.pressPoint = event.scenePos()
            self.orientation_line.show()
        elif event.button() == Qt.MouseButton.RightButton :
            items = self.items(event.scenePos(), order = Qt.SortOrder.AscendingOrder)
            try :
                self.selectedRobotGraphic = items[0]
            except IndexError :
                print("No robot at this place")
            if self.selectedRobotGraphic != None:
                print(f'{self.selectedRobotGraphic.name}_{self.selectedRobotGraphic.rep_name} selected')

    
    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.orientation_line.setLine(self.pressPoint.x(), self.pressPoint.y(), event.scenePos().x(), event.scenePos().y())
    
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.orientation_line.hide()

            def send_pos(x,y,theta):
                msg = hgpb.Position()
                msg.x = x
                msg.y = y
                msg.theta = theta
                self.pub_send_pos.send(msg)

            delta = event.scenePos()
            delta -= self.pressPoint
            distance = math.sqrt(QPointF.dotProduct(delta,delta))
            if distance < Scale * 10:
                if self.selectedRobotGraphic == None:
                    print("No selected Robot")
                else :
                    theta = self.selectedRobotGraphic.theta
                    send_pos(self.pressPoint.x() / Scale, (Map_height* Scale - self.pressPoint.y()) / Scale, theta)
                    print(self.pressPoint.x() / Scale, (Map_height* Scale - self.pressPoint.y()) / Scale)
            else:
                theta = math.acos(delta.x() / distance)
                if delta.y() > 0:
                    theta *= -1
                send_pos(self.pressPoint.x() / Scale, (Map_height* Scale - self.pressPoint.y()) / Scale, theta)
                print(self.pressPoint.x() / Scale, (Map_height* Scale - self.pressPoint.y()) / Scale,theta)
    

    
class Monitor_Command(QTabWidget):
    def __init__(self):
        super().__init__()
        self.robots = {}
    
    def addRobotGraphic(self, robot_name, robot_graphic):
        if not (robot_name in self.robots.keys()): # Vérification de l'existence d'un robot "robot_name"
            robot = Robot(robot_name)
            self.robots[robot_name] = robot
            self.addTab(robot.getPage(),robot_name)
        else:
            robot = self.robots[robot_name]
        robot.addRobotGraphic(robot_graphic)

        



class MySignalEmitter(QObject):
    pos_signal = pyqtSignal(float, float, float)

class Robot:
    def __init__(self, name):
        self.name = name
        self.robotGraphics = {}
        self.page = QFrame()
        self.page_layout = QVBoxLayout()
        self.page.setLayout(self.page_layout)

        ## commande de position
        self.addPosTypeCommand("set_position", "Goto pos (x,y,theta) [mm/°]")
        self.addPosTypeCommand("reset", "Reset pos (x,y,theta) [mm/°]")
        self.addSpeedTypeCommand("speed_cons","Speed control")
        self.page_layout.addStretch()


    def getPage(self):
        return self.page
    
    def addRobotGraphic(self, robot_graphic):
        self.robotGraphics[robot_graphic.name] = robot_graphic
        self.page_layout.addWidget(robot_graphic.getPosFrame())
    
    def addPosTypeCommand(self, ecal_topic_send, button_text):
        frame = QFrame()
        self.page_layout.addWidget(frame)
        frame_layout = QHBoxLayout()
        frame.setLayout(frame_layout)
        frame.setMaximumHeight(50)

        send = QPushButton(button_text)
        frame_layout.addWidget(send)

        x_send = QDoubleSpinBox()
        frame_layout.addWidget(x_send)
        x_send.setSingleStep(10)
        x_send.setRange(0, Map_width)
        x_send.setLocale(QLocale("en")) # utilise le . pour le séparateur de décimal

        y_send = QDoubleSpinBox()
        frame_layout.addWidget(y_send)
        y_send.setSingleStep(10)
        y_send.setRange(0, Map_height)
        y_send.setLocale(QLocale("en"))

        theta_send = QDoubleSpinBox()
        frame_layout.addWidget(theta_send)
        theta_send.setSingleStep(10)
        theta_send.setRange(0, 360)
        theta_send.setLocale(QLocale("en"))

        pub_send_pos = ProtoPublisher(ecal_topic_send,hgpb.Position)

        def send_pos(x,y,theta):
            msg = hgpb.Position()
            msg.x = x
            msg.y = y
            msg.theta = theta
            pub_send_pos.send(msg)
        
        send.clicked.connect(lambda : send_pos(x_send.value(), y_send.value(), math.radians(theta_send.value())))
    
    def addSpeedTypeCommand(self, ecal_topic_send, button_text):
        frame = QFrame()
        self.page_layout.addWidget(frame)
        frame_layout = QHBoxLayout()
        frame.setLayout(frame_layout)
        frame.setMaximumHeight(50)

        send = QPushButton(button_text)
        frame_layout.addWidget(send)

        x_send = QDoubleSpinBox()
        frame_layout.addWidget(x_send)
        x_send.setSingleStep(10)
        x_send.setRange(-1000, 1000)
        x_send.setLocale(QLocale("en")) # utilise le . pour le séparateur de décimal

        y_send = QDoubleSpinBox()
        frame_layout.addWidget(y_send)
        y_send.setSingleStep(10)
        y_send.setRange(-1000, 1000)
        y_send.setLocale(QLocale("en"))

        theta_send = QDoubleSpinBox()
        frame_layout.addWidget(theta_send)
        theta_send.setSingleStep(10)
        theta_send.setRange(-360, 360)
        theta_send.setLocale(QLocale("en"))

        pub_send_speed = ProtoPublisher(ecal_topic_send,hgpb.Position)

        def send_pos(x,y,theta):
            msg = hgpb.Speed()
            msg.vx = x
            msg.vy = y
            msg.vtheta = theta
            pub_send_speed.send(msg)
        
        send.clicked.connect(lambda : send_pos(x_send.value(), y_send.value(), math.radians(theta_send.value())))
    
    
    
class RobotGraphic(QGraphicsItemGroup):
    def __init__(self, name, rep_name, ecal_pos_topic, color = "darkblue") -> None:
        super().__init__()
        self.x = 0
        self.y = 0
        self.theta = 0
        self.color = color
        self.name = name
        self.rep_name = rep_name

        self.signal_emitter = MySignalEmitter() # Qt Signals

        ## Tab Page Frame
        self.pos_frame = QFrame()
        self.pos_frame_layout = QHBoxLayout()
        self.pos_frame.setLayout(self.pos_frame_layout)
        self.pos_frame.setMaximumHeight(50)
        self.pos_frame.setStyleSheet(f"QFrame {{ background : {color}; }}")
        name_label = QLabel(self.rep_name)
        self.pos_frame_layout.addWidget(name_label)
        self.x_label = QLabel("x: Na")
        self.pos_frame_layout.addWidget(self.x_label)
        self.y_label = QLabel("y: Na")
        self.pos_frame_layout.addWidget(self.y_label)
        self.theta_label = QLabel("theta: Na")
        self.pos_frame_layout.addWidget(self.theta_label)

        ## GraphicsItem
        body = QGraphicsEllipseItem((- Robot_diameter/2) * Scale, - Robot_diameter/2 * Scale, Robot_diameter * Scale, Robot_diameter * Scale)
        body.setBrush(QColor(self.color))
        self.addToGroup(body)

        orientation_pointer = QGraphicsLineItem(0,0,300*Scale,0)
        orientation_pointer.setPen(QPen(Qt.black, 10*Scale, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        self.addToGroup(orientation_pointer)

        self.name_text = QGraphicsTextItem(f'{self.name}\n{self.rep_name}', body)

        ## Ecal
        # Position
        def send_pos_signal(topic_name, hlm, time):
            #if hlm.name == self.name:
            #    self.signal_emitter.pos_signal.emit(hlm.x, hlm.y, hlm.theta)
            self.signal_emitter.pos_signal.emit(hlm.x, hlm.y, hlm.theta)

        pos_sub = ProtoSubscriber(ecal_pos_topic, hgpb.Position)
        pos_sub.set_callback(send_pos_signal)

        self.signal_emitter.pos_signal.connect(self.setPos)
        
    def getPosFrame(self):
        return self.pos_frame

    def setPos(self,x,y,theta):
        self.x = x
        self.y = y
        self.theta = theta

        ## Affichage graphique
        super().setPos(x * Scale ,(Map_height - y)* Scale)
        super().setRotation(math.degrees(-theta))
        self.name_text.setRotation(-math.degrees(-theta))


        ## Affichage Tabs
        self.x_label.setText("x: {:.3f}".format(x))
        self.y_label.setText("y: {:.3f}".format(y))
        self.theta_label.setText("theta: {:.3f}".format(theta))
    
        


def addRobot(scene, tabs, name, representation_name, ecal_pos_topic, color):
    robot_graphic = RobotGraphic(name, representation_name, ecal_pos_topic, color)
    scene.addRobotGraphic(robot_graphic)
    tabs.addRobotGraphic(name, robot_graphic)


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

    robot_repName_field = QLineEdit()
    tool_bar.addWidget(robot_repName_field)
    robot_repName_field.setPlaceholderText("Representation name")

    robot_ecal_pos_field = QLineEdit()
    tool_bar.addWidget(robot_ecal_pos_field)
    robot_ecal_pos_field.setPlaceholderText("Ecal pos topic")


    robot_color_field = QComboBox()
    tool_bar.addWidget(robot_color_field)
    colors = QColor.colorNames()
    for i in range(len(colors)):
        robot_color_field.insertItem(i, colors[i])
    robot_color_field.currentTextChanged.connect(lambda : robot_color_field.setStyleSheet(f"QComboBox {{ background : { robot_color_field.currentText()}}}"))
    robot_color_field.setCurrentText("red")


    add_robot_button.clicked.connect(lambda :addRobot(scene, robots_tabs, robot_name_field.text(), robot_repName_field.text(), robot_ecal_pos_field.text(), robot_color_field.currentText()))

    

    



    main_window.show()
    app.exec()