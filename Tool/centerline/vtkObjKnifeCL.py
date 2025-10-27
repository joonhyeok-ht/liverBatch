import sys
import os
import numpy as np
import vtk

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PySide6.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileToolPath = os.path.dirname(fileAbsPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import VtkObj.vtkObj as vtkObj
import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjSphere as vtkObjSphere
import VtkObj.vtkObjPolyData as vtkObjPolyData

import VtkUI.vtkUI as vtkUI
import vtkObjInterface as vtkObjInterface

import operation as operation



class CVTKObjKnifeCL(vtkObjInterface.CVTKObjInterface) :
    def __init__(self, skeleton : algSkeletonGraph.CSkeleton, opSelectionCL : operation.COperationSelectionCL, knifeCLID : int, knifeIndex : int, clSize : float) -> None :
        super().__init__()
        # input your code
        self.m_skeleton = skeleton
        self.m_knifeCLID = knifeCLID
        self.m_knifeIndex = knifeIndex
        self.m_clSize = clSize

        retList = opSelectionCL.get_all_selection_cl()
        if retList is None :
            return
        
        appendFilter = vtk.vtkAppendPolyData()
        self._create_knifed_cl_sphere(appendFilter)
        for clID in retList :
            if clID == knifeCLID :
                continue
            self._create_cl_sphere(appendFilter, clID)

        appendFilter.Update()
        output = appendFilter.GetOutput()
        if output.GetNumberOfPoints() == 0 or output.GetNumberOfCells() == 0 :
            return
        
        self.PolyData = output
        appendFilter = None
        self.Ready = True
    def clear(self) :
        # input your code
        self.m_skeleton = None
        self.m_knifeCLID = -1
        self.m_knifeIndex = -1
        self.m_clSize = 0.0
        super().clear()
    
    
    # protected
    def _create_cl_sphere(self, appendFilter : vtk.vtkAppendPolyData, clID : int) :
        cl = self.m_skeleton.get_centerline(clID)
        clPtCnt = cl.get_vertex_count()
        if clPtCnt <= 0 :
            return
        
        for clPtInx in range(0, clPtCnt) :
            pos = cl.get_vertex(clPtInx)
            polyData = algVTK.CVTK.create_poly_data_sphere(pos, self.m_clSize)
            appendFilter.AddInputData(polyData)
    def _create_knifed_cl_sphere(self, appendFilter : vtk.vtkAppendPolyData) :
        if self.m_knifeCLID < 0 :
            return
        
        clID = self.m_knifeCLID
        cl = self.m_skeleton.get_centerline(clID)
        clPtCnt = cl.get_vertex_count()
        if clPtCnt <= 0 :
            return
        
        for clPtInx in range(self.m_knifeIndex, clPtCnt) :
            pos = cl.get_vertex(clPtInx)
            polyData = algVTK.CVTK.create_poly_data_sphere(pos, self.m_clSize)
            appendFilter.AddInputData(polyData)




if __name__ == '__main__' :
    pass


# print ("ok ..")

