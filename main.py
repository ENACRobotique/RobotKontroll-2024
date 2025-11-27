#!/usr/bin/env python3
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPainter, QColor, QPen, QTransform
from PyQt5.QtCore import QRectF, Qt, QObject, pyqtSignal, QLocale, QPointF, QLineF
import math
import numpy as np

import sys

from PyQt5.QtWidgets import QGraphicsSceneMouseEvent

import generated.common_pb2 as hgpb
import ecal.nanobind_core as ecal_core
from ecal.msg.proto.core import Subscriber as ProtoSubscriber
from ecal.msg.proto.core import Publisher as ProtoPublisher
from ecal.msg.common.core import ReceiveCallbackData


Robot_diameter = 300 #mm
Map_height = 2000 #mm
Map_width = 3000 #mm
Scale = 0.43 # mm -> graphic_size

class Map_view(QGraphicsView):
    def resizeEvent(self, event):
        self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)
        super().resizeEvent(event)

class Map_scene(QGraphicsScene):
    def __init__(self,x,y,w,h):
        super().__init__(x,y,w,h)
        self.background = QImage("table2025.png")
        self.pub_send_pos = ProtoPublisher(hgpb.Position,"set_position")
        self.pub_send_trajectoire = ProtoPublisher(hgpb.Trajectoire,"set_trajectoire")
        self.selectedRobotGraphic = None
        self.pressPoint = QPointF()
        self.orientation_line = QGraphicsLineItem(0,0,Map_width * Scale, Map_height * Scale)
        self.addItem(self.orientation_line)
        self.orientation_line.hide()
        self.orientation_line.setPen(QPen(Qt.blue, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

        self.trajectoire = []
        # self.last_trajectoire_line = QGraphicsLineItem(0,0,Map_width * Scale, Map_height * Scale)
        # self.addItem(self.last_trajectoire_line)
        # self.last_trajectoire_line.hide()
        self.last_trajectoire_line = None
        # self.last_trajectoire_line.setPen(QPen(Qt.green, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))


    def _to_table_ref(self,point:QPointF):
        return (point.x() / Scale, (Map_height* Scale - point.y()) / Scale)
    
    @staticmethod
    def center_rad(theta):
        while theta > math.pi:
            theta -= 2*math.pi
        while theta < -math.pi:
            theta += 2*math.pi
        return theta

    def drawBackground(self, painter, rect):
        painter.drawImage(self.sceneRect(), self.background)
    
    def addRobotGraphic(self, robot_graphic):
        self.addItem(robot_graphic)
    
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton :
            self.pressPoint = event.scenePos()
            self.orientation_line.show()
            if self.last_trajectoire_line is not None:
                p1 = self.last_trajectoire_line.line().p1()
                self.last_trajectoire_line.setLine(QLineF(p1,event.scenePos()))
                self.trajectoire.append(self.last_trajectoire_line)
                self.last_trajectoire_line = None
        elif event.button() == Qt.MouseButton.RightButton :
            items = self.items(event.scenePos(), order = Qt.SortOrder.AscendingOrder)
            try :
                self.selectedRobotGraphic = items[0]
            except IndexError :
                print("No robot at this place")
            if self.selectedRobotGraphic != None:
                print(f'{self.selectedRobotGraphic.name}_{self.selectedRobotGraphic.rep_name} selected')
        elif event.button() == Qt.MouseButton.MiddleButton :
            if self.last_trajectoire_line is not None:
                self.trajectoire.append(self.last_trajectoire_line)
            self.last_trajectoire_line = QGraphicsLineItem(QLineF(event.scenePos(),event.scenePos()))
            self.last_trajectoire_line.setPen(QPen(Qt.green, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            self.addItem(self.last_trajectoire_line)
            # print(self.trajectoire)
    
    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        self.orientation_line.setLine(self.pressPoint.x(), self.pressPoint.y(), event.scenePos().x(), event.scenePos().y())
        if self.last_trajectoire_line is not None:
            p1 = self.last_trajectoire_line.line().p1()
            self.last_trajectoire_line.setLine(QLineF(p1,event.scenePos()))
    
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.orientation_line.hide()
            if len(self.trajectoire) > 0: # Cas où on a une trajectoire
                def line_to_pos(ligne):
                    x,y = self._to_table_ref(ligne.line().p1()) 
                    theta = -math.atan2(ligne.line().dy(),ligne.line().dx())
                    return hgpb.Position(x=x,y=y,theta=theta)

                # Calcul du delta
                delta = event.scenePos() - self.trajectoire[-1].line().p2()
                distance = math.sqrt(QPointF.dotProduct(delta,delta))
                theta = -math.atan2(delta.y(),delta.x()) if distance > 0 else -math.atan2(self.trajectoire[-1].line().dy(),self.trajectoire[-1].line().dx())

                traj = hgpb.Trajectoire()
                for ligne in self.trajectoire:
                    traj.pos.append(line_to_pos(ligne))

                _x,_y = self._to_table_ref(self.trajectoire[-1].line().p2())
                traj.pos.append(hgpb.Position(x=_x,y=_y,theta=theta))

                self.pub_send_trajectoire.send(traj)
                print(traj)

                for ligne in self.trajectoire:
                    self.removeItem(ligne)
                self.trajectoire=[]

            else : # Cas destination = 1 seul point

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
    
    def addPosTypeCommand(self, ecal_topic_send, text):
        frame = QFrame()
        self.page_layout.addWidget(frame)
        frame_layout = QVBoxLayout()
        frame_buttons_layout = QHBoxLayout()
        frame_label_layout = QHBoxLayout()

        command_text = QLabel(text)
        frame_label_layout.addWidget(command_text)
        send = QPushButton("send")
        frame_label_layout.addWidget(send)
        
        frame_layout.addLayout(frame_label_layout)
        frame_layout.addLayout(frame_buttons_layout)
        frame.setLayout(frame_layout)
        frame.setMaximumHeight(100)

        x_send = QDoubleSpinBox()
        frame_buttons_layout.addWidget(x_send)
        x_send.setSingleStep(10)
        x_send.setRange(0, Map_width)
        x_send.setLocale(QLocale("en")) # utilise le . pour le séparateur de décimal

        y_send = QDoubleSpinBox()
        frame_buttons_layout.addWidget(y_send)
        y_send.setSingleStep(10)
        y_send.setRange(0, Map_height)
        y_send.setLocale(QLocale("en"))

        theta_send = QDoubleSpinBox()
        frame_buttons_layout.addWidget(theta_send)
        theta_send.setSingleStep(10)
        theta_send.setRange(0, 360)
        theta_send.setLocale(QLocale("en"))

        pub_send_pos = ProtoPublisher(hgpb.Position,ecal_topic_send)

        def send_pos(x,y,theta):
            msg = hgpb.Position()
            msg.x = x
            msg.y = y
            msg.theta = theta
            pub_send_pos.send(msg)
        
        send.clicked.connect(lambda : send_pos(x_send.value(), y_send.value(), math.radians(theta_send.value())))
    
    def addSpeedTypeCommand(self, ecal_topic_send, text):
        frame = QFrame()
        self.page_layout.addWidget(frame)
        frame_layout = QVBoxLayout()
        frame_buttons_layout = QHBoxLayout()
        frame_label_layout = QHBoxLayout()

        command_text = QLabel(text)
        frame_label_layout.addWidget(command_text)
        send = QPushButton("send")
        frame_label_layout.addWidget(send)
        
        frame_layout.addLayout(frame_label_layout)
        frame_layout.addLayout(frame_buttons_layout)
        frame.setLayout(frame_layout)
        frame.setMaximumHeight(100)

        x_send = QDoubleSpinBox()
        frame_buttons_layout.addWidget(x_send)
        x_send.setSingleStep(10)
        x_send.setRange(-1000, 1000)
        x_send.setLocale(QLocale("en")) # utilise le . pour le séparateur de décimal

        y_send = QDoubleSpinBox()
        frame_buttons_layout.addWidget(y_send)
        y_send.setSingleStep(10)
        y_send.setRange(-1000, 1000)
        y_send.setLocale(QLocale("en"))

        theta_send = QDoubleSpinBox()
        frame_buttons_layout.addWidget(theta_send)
        theta_send.setSingleStep(10)
        theta_send.setRange(-360, 360)
        theta_send.setLocale(QLocale("en"))

        #pub_send_speed = ProtoPublisher(hgpb.Position,ecal_topic_send)

        def send_pos(x,y,theta):
            msg = hgpb.Speed()
            msg.vx = x
            msg.vy = y
            msg.vtheta = theta
            pub_send_speed.send(msg)
        
        #send.clicked.connect(lambda : send_pos(x_send.value(), y_send.value(), math.radians(theta_send.value())))
    
def normalize_angle(a):
    while a > math.pi:
        a -= 2*math.pi
    while a < -math.pi:
        a+= 2*math.pi
    return a

    
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
        robot_color = QLabel()
        robot_color.setStyleSheet(f"QFrame {{ background : {color}; }}")
        robot_color.setFixedSize(50, 25)
        name_label = QLabel(self.rep_name)
        name_label.setStyleSheet("font-size:28px;")
        self.pos_frame_layout.addWidget(name_label)
        self.x_label = QLabel("x: Na")
        self.x_label.setStyleSheet("font-size:28px;")
        self.pos_frame_layout.addWidget(self.x_label)
        self.y_label = QLabel("y: Na")
        self.y_label.setStyleSheet("font-size:28px;")
        self.pos_frame_layout.addWidget(self.y_label)
        self.theta_label = QLabel("theta: Na")
        self.theta_label.setStyleSheet("font-size:28px;")
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
        def send_pos_signal( pub_id : ecal_core.TopicId, data : ReceiveCallbackData[hgpb.Position]):
            #if hlm.name == self.name:
            #    self.signal_emitter.pos_signal.emit(hlm.x, hlm.y, hlm.theta)
            self.signal_emitter.pos_signal.emit(data.message.x, data.message.y, data.message.theta)
            self.signal_emitter.pos_signal.emit(data.message.x, data.message.y, data.message.theta)

        self.pos_sub = ProtoSubscriber(hgpb.Position,ecal_pos_topic)
        self.pos_sub.set_receive_callback(send_pos_signal)

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
        self.theta_label.setText("theta: {:.3f}".format(math.degrees(normalize_angle(theta))))

class Tools(QToolBar):
    def __init__(self,scene,robots_tabs):
        super().__init__()
        add_robot_button = QPushButton("Add robot")
        self.addWidget(add_robot_button)

        robot_name_field = QLineEdit()
        robot_name_field.setPlaceholderText("Name")
        self.addWidget(robot_name_field)

        robot_repName_field = QLineEdit()
        robot_repName_field.setPlaceholderText("Representation name")
        self.addWidget(robot_repName_field)

        robot_ecal_pos_field = QLineEdit()
        robot_ecal_pos_field.setPlaceholderText("Ecal pos topic")
        self.addWidget(robot_ecal_pos_field)

        robot_color_field = QComboBox()
        colors = QColor.colorNames()
        for i in range(len(colors)):
            robot_color_field.insertItem(i, colors[i])
        robot_color_field.currentTextChanged.connect(lambda : robot_color_field.setStyleSheet(f"QComboBox {{ background : { robot_color_field.currentText()}}}"))
        robot_color_field.setCurrentText("red")
        self.addWidget(robot_color_field)
        add_robot_button.clicked.connect(lambda :addRobot(scene, robots_tabs, robot_name_field.text(), robot_repName_field.text(), robot_ecal_pos_field.text(), robot_color_field.currentText()))
        
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Robot Kontroll")

        # Sous-fenêtre à gauche
        scene = Map_scene(0,0,Map_width * Scale, Map_height * Scale)
        map_window = Map_view(scene)

        # Sous-fenêtre à droite
        command_window = Monitor_Command()

        # Sous-fenêtre en haut 
        communication_window = Tools(scene,command_window)

        # Création d'un splitter vertical
        splitterV = QSplitter(Qt.Vertical)
        # Création d'un splitter horizontal
        splitterH = QSplitter(Qt.Horizontal)

        # Ajout des widgets au splitter
        splitterH.addWidget(map_window)
        splitterH.addWidget(command_window)
        splitterV.addWidget(communication_window)
        splitterV.addWidget(splitterH)

        # Un widget container pour la fenêtre principale
        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(splitterV)
        ##layout.addWidget(splitterH)
        container.setLayout(layout)

        self.setCentralWidget(container)

        addRobot(scene, command_window, "Odom","Odom", "odom_pos", "red")
        addRobot(scene, command_window, "Lidar","Lidar", "lidar_pos", "blue")


def addRobot(scene, tabs, name, representation_name, ecal_pos_topic, color):
    robot_graphic = RobotGraphic(name, representation_name, ecal_pos_topic, color)
    scene.addRobotGraphic(robot_graphic)
    tabs.addRobotGraphic(name, robot_graphic)


if __name__ == "__main__":
    ecal_core.initialize("Robot2Kontroll")
    app = QApplication([])
    window = QMainWindow()
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec_())
