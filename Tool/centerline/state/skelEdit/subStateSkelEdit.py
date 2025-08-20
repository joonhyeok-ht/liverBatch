import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
from scipy.spatial import KDTree

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QMessageBox
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


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjSphere as vtkObjSphere

import vtkObjGuideCL as vtkObjGuideCL

import data as data

import operation as operation


class CSubStateSkelEdit() :
    def __init__(self, mediator):
        # input your code
        self.m_mediator = mediator
    def clear(self) :
        # input your code
        self.m_mediator = None

    def process_init(self) :
        pass
    def process(self) :
        pass
    def process_end(self) :
        pass

    def clicked_mouse_rb(self, clickX, clickY) :
        pass
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        pass
    def release_mouse_rb(self) :
        pass
    def mouse_move(self, clickX, clickY) :
        pass
    def mouse_move_rb(self, clickX, clickY) :
        pass
    def key_press(self, keyCode : str) :
        pass
    def key_press_with_ctrl(self, keyCode : str) :
        pass

    def check_cl_hierarchy(self, bChecked : bool) :
        pass
    def check_cl_ancestor(self, bChecked : bool) :
        pass
    def apply_root_cl(self) :
        pass
    def save_cl(self) :
        dataInst = self._get_data()
        if dataInst.Ready == False : 
            return
        
        clinfoInx = self._get_clinfo_index()
        skeleton = self._get_skeleton()
        if skeleton is None :
            return
        
        self._update_skeleton()

        # clInPath = dataInst.get_cl_in_path()
        clOutPath = dataInst.get_cl_out_path()
        # file = "clDataInfo.pkl"
        # pklFullPath = os.path.join(clInPath, file)
        # data.CData.save_inst(pklFullPath, dataInst.DataInfo)

        clInfo = dataInst.OptionInfo.get_centerlineinfo(clinfoInx)
        blenderName = clInfo.get_input_blender_name()
        outputFileName = clInfo.OutputName
        outputFullPath = os.path.join(clOutPath, f"{outputFileName}.json")
        skeleton.save(outputFullPath, blenderName)

        print(f"completed save skeleton : {outputFileName}")
    def change_range(self, range : int) :
        pass


    # protected
    def _get_data(self) -> data.CData :
        return self.m_mediator.get_data()
    def _get_operator_selection_cl(self) -> operation.COperationSelectionCL :
        return self.m_mediator.m_opSelectionCL
    def _get_operator_selection_br(self) -> operation.COperationSelectionBr :
        return self.m_mediator.m_opSelectionBr
    def _get_operator_selection_ep(self) -> operation.COperationSelectionEP :
        return self.m_mediator.m_opSelectionEP
    def _get_clinfo_index(self) -> int :
        return self.m_mediator.get_clinfo_index()
    def _get_skeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_mediator.Skeleton
    
    def _setui_rootid(self, rootID : int) :
        self.m_mediator.setui_rootid(rootID)
    def _setui_cl_count(self, clCount : int) :
        self.m_mediator.setui_cl_count(clCount)
    def _setui_br_count(self, brCount : int) :
        self.m_mediator.setui_br_count(brCount)
    def _setui_range(self, range : int) :
        self.m_mediator.setui_range(range)

    def _getui_cl_hierarchy(self) -> bool :
        return self.m_mediator.getui_cl_hierarchy()
    def _getui_cl_ancestor(self) -> bool :
        return self.m_mediator.getui_cl_ancestor()
    def _getui_range(self) -> int :
        return self.m_mediator.getui_range()
    

    def _update_skeleton(self) : 
        self.__update_cl_radius()
        skeleton = self._get_skeleton()
        skeleton.rebuild_centerline_related_data()
        QMessageBox.information(self.m_mediator.m_mediator, "Alarm", "complete to save vessel")
    
    
    # private
    # def __update_cl_radius(self) :
    #     dataInst = self._get_data()
    #     skeleton = self._get_skeleton()
    #     clinfoIndex = self._get_clinfo_index()

    #     vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoIndex, 0)
    #     vesselObj = dataInst.find_obj_by_key(vesselKey)
    #     if vesselObj is None :
    #         return
    #     vesselPolyData = vesselObj.PolyData
    #     anchorVertex = algVTK.CVTK.poly_data_get_vertex(vesselPolyData)
    #     tree = KDTree(anchorVertex)

    #     iCnt = skeleton.get_centerline_count()
    #     for inx in range(0, iCnt) :
    #         cl = skeleton.get_centerline(inx)
    #         dist, self.m_npNNIndex = tree.query(cl.Vertex, k=1)
    #         print(f"dist : {dist}")
    #         inx = 0
    def __update_cl_radius(self) :
        dataInst = self._get_data()
        skeleton = self._get_skeleton()
        clinfoIndex = self._get_clinfo_index()

        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoIndex, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey)
        if vesselObj is None :
            return
        vesselPolyData = vesselObj.PolyData
        # anchorVertex = algVTK.CVTK.poly_data_get_vertex(vesselPolyData)
        # tree = KDTree(anchorVertex)

        distCalculator = vtk.vtkImplicitPolyDataDistance()
        distCalculator.SetInput(vesselPolyData)

        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            dist = np.zeros(len(cl.Vertex))
            for ptInx, point in enumerate(cl.Vertex) :
                radius = abs(distCalculator.EvaluateFunction(point))
                # radius = distCalculator.EvaluateFunction(point)
                dist[ptInx] = radius
            # dist, self.m_npNNIndex = tree.query(cl.Vertex, k=1)
            # print(f"dist : {dist}")
            cl.Radius = dist
            inx = 0


    @property
    def App(self) : 
        return self.m_mediator.m_mediator

if __name__ == '__main__' :
    pass


# print ("ok ..")

