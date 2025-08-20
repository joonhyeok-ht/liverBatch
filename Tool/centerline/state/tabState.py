import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algVTK as algVTK
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algLinearMath as algLinearMath

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer

import data as data
import operation as op

import VtkObj.vtkObjText as vtkObjText

# import territory as territory


class CTabState :
    def __init__(self, mediator = None) :
        self.m_mediator = mediator
        self.m_tab = QWidget()
        self.init_ui()
    def clear(self) :
        self.m_tab = None
    def init_ui(self) :
        pass

    def process_init(self) :
        pass
    def process(self) :
        pass
    def process_end(self) :
        pass


    def get_btn_stylesheet(self) -> str :
        return self.m_mediator.m_styleSheetBtn
    def get_main_widget(self) -> QWidget :
        return self.m_mediator.m_mainWidget
    def get_data(self) -> data.CData :
        return self.m_mediator.Data
    def get_optioninfo(self) -> optionInfo.COptionInfoSingle :
        dataInst = self.get_data()
        return dataInst.OptionInfo
    def get_phaseinfo_container(self) -> niftiContainer.CPhaseInfoContainer :
        dataInst = self.get_data()
        return dataInst.PhaseInfoContainer
    def get_clinfo_index(self) -> int :
        dataInst = self.get_data()
        return dataInst.CLInfoIndex
    def get_seginfo_count(self) -> int :
        optionInfoInst = CTabState.get_optioninfo(self.m_mediator)
        return optionInfoInst.get_segmentinfo_count()
    def get_seginfo_organ_name(self, groupID : int) -> str : 
        optionInfoInst = CTabState.get_optioninfo(self.m_mediator)
        segmentInfoInst = optionInfoInst.get_segmentinfo(groupID)
        return segmentInfoInst.Organ


    # mediator message
    def clicked_mouse_lb(self, clickX, clickY) :
        pass
    def clicked_mouse_lb_shift(self, clickX, clickY) :
        pass
    def release_mouse_lb(self) :
        pass
    def clicked_mouse_rb(self, clickX, clickY) :
        pass
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        pass
    def release_mouse_rb(self) :
        pass
    def mouse_move(self, clickX, clickY) :
        pass
    def mouse_move_lb(self, clickX, clickY) :
        pass
    def mouse_move_rb(self, clickX, clickY) :
        pass
    def key_press(self, keyCode : str) :
        pass
    def key_press_with_ctrl(self, keyCode : str) : 
        pass
    def changed_project_type(self) :
        pass


    def remove_path(self, path : str) :
        if os.path.exists(path) == False :
            return
        try :
            shutil.rmtree(path)
        except OSError as e:
            print(f"Error: {e}")
    def remove_noise_polydata(self, polyData : vtk.vtkPolyData) :
        connectivityFilter = vtk.vtkConnectivityFilter()
        connectivityFilter.SetInputData(polyData)
        connectivityFilter.SetExtractionModeToLargestRegion()
        connectivityFilter.Update()

        # 가장 큰 구성 요소를 추출한 결과를 vtkPolyData로 얻기
        return connectivityFilter.GetOutput()
    def get_meshlib(self, vtkMeshInst : vtk.vtkPolyData) :
        npVertex = algVTK.CVTK.poly_data_get_vertex(vtkMeshInst)
        npIndex = algVTK.CVTK.poly_data_get_triangle_index(vtkMeshInst)
        meshLibInst = algMeshLib.CMeshLib.meshlib_create(npVertex, npIndex)
        return meshLibInst
    def get_vtkmesh(self, meshlibInst) -> vtk.vtkPolyData :
        npVertex = algMeshLib.CMeshLib.meshlib_get_vertex(meshlibInst)
        npIndex = algMeshLib.CMeshLib.meshlib_get_index(meshlibInst)
        vtkMesh = algVTK.CVTK.create_poly_data_triangle(npVertex, npIndex)
        return vtkMesh
    def find_polydata_include_vertex(self, listPolyData : list, vertex : np.ndarray) -> vtk.vtkPolyData :
        '''
        desc : polydata 리스트에서 vertex들을 포함하는 polydata를 반환한다.
               포함되는것이 없다면 None을 반환,
               vertex들이 여러개의 polydata 내부에 걸쳐 있다면 가장 많이 포함되는 polydata 리턴
        '''
        maxInx = -1
        maxCnt = -1
        for inx, subPolyData in enumerate(listPolyData) :
            nowCnt = self.check_in_polydata(subPolyData, vertex)
            if  nowCnt > maxCnt :
                maxInx = inx
                maxCnt = nowCnt
        
        if maxInx == -1 :
            return None
        return listPolyData[maxInx]
    def get_sub_polydata_count(self, polyData : vtk.vtkPolyData) -> int :
        '''
        desc : polydata에서 분리된 영역의 갯수 리턴
        '''
        connectivityFilter = vtk.vtkConnectivityFilter()
        connectivityFilter.SetInputData(polyData)
        connectivityFilter.SetExtractionModeToAllRegions()
        connectivityFilter.ColorRegionsOn()
        connectivityFilter.Update()

        labeledPolyData = connectivityFilter.GetOutput()
        numRegions = connectivityFilter.GetNumberOfExtractedRegions()
        return numRegions
    def get_sub_polydata(self, polyData : vtk.vtkPolyData) -> list :
        '''
        desc : polydata에서 분리된 영역, 각각의 polydata를 리스트 형태로 반환
               만약 없을 경우 None 반환
        '''
        connectivityFilter = vtk.vtkConnectivityFilter()
        connectivityFilter.SetInputData(polyData)
        connectivityFilter.SetExtractionModeToAllRegions()
        connectivityFilter.ColorRegionsOn()
        connectivityFilter.Update()

        labeledPolyData = connectivityFilter.GetOutput()
        numRegions = connectivityFilter.GetNumberOfExtractedRegions()

        listPolyData = []

        for regionId in range(numRegions):
            threshold = vtk.vtkThreshold()
            threshold.SetInputData(labeledPolyData)
            threshold.SetInputArrayToProcess(
                0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, "RegionId")
            
            # regionId만 걸러내기
            threshold.SetLowerThreshold(regionId)
            threshold.SetUpperThreshold(regionId)
            threshold.SetThresholdFunction(vtk.vtkThreshold.THRESHOLD_BETWEEN)
            threshold.Update()

            # PolyData로 변환
            surfaceFilter = vtk.vtkGeometryFilter()
            surfaceFilter.SetInputConnection(threshold.GetOutputPort())
            surfaceFilter.Update()

            region_polydata = surfaceFilter.GetOutput()
            listPolyData.append(region_polydata)
        
        if len(listPolyData) == 0 :
            return None
        return listPolyData
    def check_in_polydata(self, polyData : vtk.vtkPolyData, vertex : np.ndarray) -> int :
        '''
        desc : polygon 내부에 존재하는 vertex들의 갯수 반환
        '''
        iCnt = vertex.shape[0]
        testPt = vtk.vtkPoints()
        for inx in range(0, iCnt) :
            testPt.InsertNextPoint(vertex[inx, 0], vertex[inx, 1], vertex[inx, 2])

        testPolyData = vtk.vtkPolyData()
        testPolyData.SetPoints(testPt)

        selEnPt = vtk.vtkSelectEnclosedPoints()
        selEnPt.SetSurfaceData(polyData)
        selEnPt.SetInputData(testPolyData)
        selEnPt.Update()

        retCnt = 0

        for i in range(testPt.GetNumberOfPoints()) :
            bInside = selEnPt.IsInside(i)
            if bInside == 1 :
                retCnt += 1

        return retCnt
    def dilation_polydata(self, polyData : vtk.vtkPolyData, scale : float = 1.0) -> vtk.vtkPolyData :
        '''
        desc : polyData를 scale 만큼 확장 (normal vector 기준)
        '''
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(polyData)
        normals.ComputePointNormalsOn()
        normals.Update()

        points = normals.GetOutput().GetPoints()
        normalsArray = normals.GetOutput().GetPointData().GetNormals()

        newPoints = vtk.vtkPoints()
        for i in range(points.GetNumberOfPoints()):
            p = points.GetPoint(i)
            n = normalsArray.GetTuple(i)
            moved = [p[j] + scale * n[j] for j in range(3)]
            newPoints.InsertNextPoint(moved)

        dilatedPoly = vtk.vtkPolyData()
        dilatedPoly.DeepCopy(polyData)
        dilatedPoly.SetPoints(newPoints)
        return dilatedPoly

    # protected 
    def _init_cl_label(self) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        labelColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            iCLInx = int(cl.get_vertex_count() / 2)
            pos = cl.get_vertex(iCLInx)
            activeCamera = self.m_mediator.get_active_camera()
            clName = cl.Name

            key = data.CData.make_key(data.CData.s_textType, 0, cl.ID)
            vtkText = vtkObjText.CVTKObjText(activeCamera, pos, clName, 1.0)
            vtkText.KeyType = data.CData.s_textType
            vtkText.Key = key
            vtkText.Color = labelColor
            dataInst.add_vtk_obj(vtkText)
        
        self.m_mediator.ref_key_type(data.CData.s_textType)
    def _clear_cl_label(self) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        self.m_mediator.remove_key_type(data.CData.s_textType)
    def _update_cl_label(self,  clKey : str) :
        dataInst = self.get_data()
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        keyType, groupID, clID = data.CData.get_keyinfo(clKey)
        cl = skeleton.get_centerline(clID)

        textKey = data.CData.make_key(data.CData.s_textType, 0, cl.ID)
        textObj = dataInst.find_obj_by_key(textKey)
        if textObj is not None :
            textObj.Text = cl.Name


    @property
    def Tab(self) -> QWidget :
        return self.m_tab
        
    





if __name__ == '__main__' :
    pass


# print ("ok ..")

