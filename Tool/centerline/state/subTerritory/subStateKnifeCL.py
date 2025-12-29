import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStatePath = os.path.dirname(fileAbsPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import data as data
import clMask as clMask

import operation as operation

import tabState as tabState

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK

import VtkObj.vtkObjLine as vtkObjLine
import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideCLBound as vtkObjGuideCLBound

import command.commandTerritory as commandTerritory
import command.commandTerritoryVessel as commandTerritoryVessel

import subStateKnife as subStateKnife



class CSubStateKnifeCL(subStateKnife.CSubStateKnife) :
    s_dbgName = "a"


    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()

    def process_init(self) :
        self.App.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        self._set_whole_vessel(None)
        opSelectionCL = self._get_operator_selection_cl()
        opSelectionCL.process_reset()
        self.App.remove_key_type(data.CData.s_territoryType)

    def clicked_mouse_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_territoryType,
            data.CData.s_vesselType,
            data.CData.s_organType,
            data.CData.s_outsideKeyType
        ]
        key = self.App.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""

        opSelectionCL = self._get_operator_selection_cl()

        self._set_whole_vessel(None)
        self.App.remove_key_type(data.CData.s_territoryType)
        operation.COperationSelectionCL.clicked(opSelectionCL, key)
        self.App.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        super().clicked_mouse_rb_shift(clickX, clickY)
        self.App.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            opSelectionCL = self._get_operator_selection_cl()
            opSelectionCL.process_reset()
            self._set_whole_vessel(None)
            self.App.remove_key_type(data.CData.s_territoryType)
            self.App.update_viewer()

    def on_btn_view_territory(self) :
        self._command_territory()
    def on_btn_view_vessel(self) :
        self._command_vessel()

    



if __name__ == '__main__' :
    pass


# print ("ok ..")

