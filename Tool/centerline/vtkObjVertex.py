import sys
import os
import numpy as np
import vtk
from vtkmodules.util import numpy_support as nps

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


class CVTKObjVertex(vtkObjInterface.CVTKObjInterface) :
    def __init__(self, CL : algSkeletonGraph.CSkeletonCenterline, vertexSize : float, vertexColor) -> None:
        super().__init__()
        # input your code
        self.m_keyType = "vertex"
        self.m_CL = CL
        self.m_points = vtk.vtkPoints()
        
        vn = self.m_CL.get_vertex_count()
        
        if vn <= 0:
            return
        
        verts = np.empty((vn, 3), dtype=np.float64)
        for i in range(vn):
            verts[i] = self.m_CL.get_vertex(i).flatten()
        pts_vtk = vtk.vtkPoints()
        pts_vtk.SetData(nps.numpy_to_vtk(verts, deep=True))

        poly = vtk.vtkPolyData()
        poly.SetPoints(pts_vtk)

        # 2) per-vertex ID (버그 수정: vid 사용)
        ids = vtk.vtkUnsignedIntArray()
        ids.SetName("VertexID")
        ids.SetNumberOfTuples(vn)
        for vid in range(vn):
            ids.SetValue(vid, vid)
        poly.GetPointData().AddArray(ids)

        colors = vtk.vtkUnsignedCharArray()
        colors.SetName("RGB")
        colors.SetNumberOfComponents(3)
        colors.SetNumberOfTuples(vn)
        for i in range(vn):
            colors.SetTuple3(i, int(255*vertexColor[0]), int(255*vertexColor[1]), int(255*vertexColor[2]))  # 기본색
        poly.GetPointData().SetScalars(colors)
                

        # 3) 저해상도 구체 소스(삼각형 개수 ↓)
        sphere = vtk.vtkSphereSource()
        sphere.SetRadius(max(1e-6, float(vertexSize)))
        sphere.SetThetaResolution(8)
        sphere.SetPhiResolution(8)

        # 4) GPU 인스턴싱 Mapper
        glyphMapper = vtk.vtkGlyph3DMapper()
        glyphMapper.SetInputData(poly)
        glyphMapper.SetSourceConnection(sphere.GetOutputPort())
        glyphMapper.SetSelectionIdArray("VertexID")         # 하드웨어 셀렉션용
        glyphMapper.ScalingOff()      
        
        glyphMapper.SetScalarVisibility(True)
        glyphMapper.SetScalarModeToUsePointFieldData()
        glyphMapper.SelectColorArray("RGB")
        glyphMapper.SetColorModeToDirectScalars() 

        self.m_polyData   = poly
        self.m_mapper     = glyphMapper
        
        self.m_actor.SetMapper(self.m_mapper)
        self.Ready        = True
    def clear(self) :
        # input your code
        self.m_leafCL = None
        super().clear()
    

    @property
    def LeafCL(self) -> algSkeletonGraph.CSkeletonCenterline :
        return self.m_leafCL
    @LeafCL.setter
    def LeafCL(self, leafCL : algSkeletonGraph.CSkeletonCenterline) :
        self.m_leafCL

    




if __name__ == '__main__' :
    pass


# print ("ok ..")

