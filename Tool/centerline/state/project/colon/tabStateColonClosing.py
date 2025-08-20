import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math

from scipy.spatial import KDTree
from scipy.ndimage import label, generate_binary_structure

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStateProjectPath = os.path.dirname(fileAbsPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import data as data

import operation as operation

import tabState as tabState

import state.project.colon.userDataColon as userDataColon

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK
import AlgUtil.algImage as algImage

import Block.reconstruction as reconstruction

import VtkObj.vtkObjVertex as vtkObjVertex
import VtkObj.vtkObjLine as vtkObjLine
import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideMeshBound as vtkObjGuideMeshBound

import command.commandTerritory as commandTerritory


class CTabStateColonClosing(tabState.CTabState) : 
    s_closingType = "Closing"


    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        
    def clear(self) :
        # input your code
        super().clear()

    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        
        
        self.m_mediator.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Colon Closing Test --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        btn = QPushButton("Save")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_save)
        tabLayout.addWidget(btn)


        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)


    def clicked_mouse_rb(self, clickX, clickY) :
        dataInst = self.get_data()
        userData = self._get_userdata()
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        self.m_mediator.update_viewer()
    def release_mouse_rb(self) :
        self.m_mediator.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            userData = self._get_userdata()
            self.m_mediator.update_viewer()

    # protected
    def _get_userdata(self) -> userDataColon.CUserDataColon :
        return self.get_data().find_userdata(userDataColon.CUserDataColon.s_userDataKey)

    
    # ui event 
    def _on_btn_save(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        if userData is None :
            return
        
        savePath, _ = QFileDialog.getSaveFileName(
            self.get_main_widget(),
            "Save Mesh File", 
            "", 
            "STL Files (*.stl)"
        )
        if savePath == "" :
            return
        
        # key = data.CData.make_key(CTabStateColonMerge.s_colonKeyType, 0, 0)
        # obj = dataInst.find_obj_by_key(key)
        # if obj is None :
        #     print("not found merged colon")
        #     return
        # polyData = obj.PolyData
        # algVTK.CVTK.save_poly_data_stl(savePath, polyData)
        # print("vessel file saved successfully.")


    # private

if __name__ == '__main__' :
    pass


# print ("ok ..")

