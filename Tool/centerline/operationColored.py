import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PySide6.QtCore import Qt
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

class COperationSelectionCL(operation.COperationSelectionCL) :
    def _color_setting(self, listSelectionKey : list, rootColor : np.ndarray, _color : np.ndarray) :
        dataInst = self.Data
        skeleton = self.Skeleton
        if skeleton is None :
            return
        
        for selectionKey in listSelectionKey :
            id = data.CData.get_id_from_key(selectionKey)
            if id == skeleton.RootCenterline.ID :
                color = rootColor
            else :
                # color = _color
                # sally
                cl = skeleton.get_centerline(id)
                ##_color != self.m_mediator.m_
                if not np.array_equal(_color, dataInst.SelectionCLColor) :
                    if cl.Name != '':
                        color = self.m_mediator.get_cl_color(cl.Name)
                    else :
                        color = _color  
                else :
                    color = _color

            clObj = dataInst.find_obj_by_key(selectionKey)
            if clObj is not None :
                clObj.Color = color
class COperationSelectionBr(operation.COperationSelectionBr) :
    def _color_setting(self, listSelectionKey : list, color : np.ndarray) :
        dataInst = self.Data
        for selectionKey in listSelectionKey :
            clObj = dataInst.find_obj_by_key(selectionKey)
            if clObj is not None :
                clObj.Color = color
class COperationSelectionEP(operation.COperationSelectionEP) :
    def _color_setting(self, listSelectionKey : list, color : np.ndarray) :
        dataInst = self.Data
        for selectionKey in listSelectionKey :
            clObj = dataInst.find_obj_by_key(selectionKey)
            if clObj is not None :
                clObj.Color = color
class COperationDragSelectionCL(operation.COperationDragSelectionCL) :
    def _color_setting(self, listSelectionKey : list, rootColor : np.ndarray, _color : np.ndarray) :
        dataInst = self.Data
        skeleton = self.Skeleton
        if skeleton is None :
            return
        
        for selectionKey in listSelectionKey :
            id = data.CData.get_id_from_key(selectionKey)
            if id == skeleton.RootCenterline.ID :
                color = rootColor
            else :
                # color = _color
                # sally
                cl = skeleton.get_centerline(id)
                ##_color != self.m_mediator.m_
                if not np.array_equal(_color, dataInst.SelectionCLColor) :
                    if cl.Name != '':
                        color = self.m_mediator.get_cl_color(cl.Name)
                    else :
                        color = _color  
                else :
                    color = _color
                

            clObj = dataInst.find_obj_by_key(selectionKey)
            if clObj is not None :
                clObj.Color = color

if __name__ == '__main__' :
    pass


# print ("ok ..")