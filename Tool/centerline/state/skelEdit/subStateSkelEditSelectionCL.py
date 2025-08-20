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
import vtkObjRadius as vtkObjRadius

import data as data

import operation as operation

import command.commandSkelEdit as commandSkelEdit

import subStateSkelEdit as subStateSkelEdit


class CSubStateSkelEditSelectionCL(subStateSkelEdit.CSubStateSkelEdit) :
    s_radiusKeyType = "radius"


    def __init__(self, mediator):
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()

    def process_init(self) :
        self._get_operator_selection_cl().ChildSelectionMode = self._getui_cl_hierarchy()
        self._get_operator_selection_cl().ParentSelectionMode = self._getui_cl_ancestor()
        self.App.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        opSelectionCL = self._get_operator_selection_cl()
        opSelectionCL.process_reset()
        self.App.remove_key_type(CSubStateSkelEditSelectionCL.s_radiusKeyType)

    def clicked_mouse_rb(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
            CSubStateSkelEditSelectionCL.s_radiusKeyType,
        ]

        key = self.App.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""
            return

        intersectedPt = self.App.picking_intersected_point(clickX, clickY, listExceptKeyType)
        dataInst = self._get_data()
        skeleton = self._get_skeleton()
        clInx = data.CData.get_id_from_key(key)
        cl = skeleton.get_centerline(clInx)
        vertexIndex = self.__find_closest_vertex_index(skeleton.get_centerline(clInx), intersectedPt)

        # radius obj
        self.App.remove_key_type(CSubStateSkelEditSelectionCL.s_radiusKeyType)
        radiusKey = data.CData.make_key(CSubStateSkelEditSelectionCL.s_radiusKeyType, 0, 0)
        radiusObj = vtkObjRadius.CVTKObjRadius()
        radiusObj.KeyType = CSubStateSkelEditSelectionCL.s_radiusKeyType
        radiusObj.Key = radiusKey
        radiusObj.set_cl(cl, vertexIndex, algLinearMath.CScoMath.to_vec3([1.0, 0.0, 1.0]))
        radiusObj.Opacity = 0.3
        dataInst.add_vtk_obj(radiusObj)
        self.App.ref_key_type(CSubStateSkelEditSelectionCL.s_radiusKeyType)
        
        operation.COperationSelectionCL.clicked(self._get_operator_selection_cl(), key)
        self.App.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_vesselType,
        ]

        key = self.App.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""

        operation.COperationSelectionCL.multi_clicked(self._get_operator_selection_cl(), key)
        self.App.update_viewer()
    def release_mouse_rb(self) :
        pass
    def mouse_move_rb(self, clickX, clickY) :
        pass
    def key_press(self, keyCode : str) :
        if keyCode == "Delete" :
            self._remove_cl()

    def check_cl_hierarchy(self, bChecked : bool) :
        operation.COperationSelectionCL.checked_hierarchy(self._get_operator_selection_cl(), bChecked)
        self.App.update_viewer()
    def check_cl_ancestor(self, bChecked : bool) :
        operation.COperationSelectionCL.checked_ancestor(self._get_operator_selection_cl(), bChecked)
        self.App.update_viewer()
    def apply_root_cl(self) :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        
        clinfoInx = self._get_clinfo_index()
        skeleton = self._get_skeleton()
        if skeleton is None :
            return
        
        opSelectionCL = self._get_operator_selection_cl()
        retList = opSelectionCL.get_selection_cl_list()
        if retList is None :
            print("not selecting centerline")
            return
        
        clID = retList[0]
        skeleton.build_tree(clID)

        self.App.refresh_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx, dataInst.CLColor)
        rootKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
        self.App.refresh_key(rootKey, dataInst.RootCLColor)

        rootID = skeleton.RootCenterline.ID
        clCount = skeleton.get_centerline_count()
        brCount = skeleton.get_branch_count()
        self._setui_rootid(rootID)
        self._setui_cl_count(clCount)
        self._setui_br_count(brCount)
        self.App.update_viewer()
    

    # protected
    def _remove_cl(self) :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return
        
        opSelectionCL = self._get_operator_selection_cl()
        retList = opSelectionCL.get_all_selection_cl()
        if retList is None :
            return

        cmd = commandSkelEdit.CCommandAutoRemoveCL(self.App)
        cmd.InputData = dataInst
        cmd.InputSkeleton = self._get_skeleton()
        for clID in retList :
            cmd.add_clID(clID)
        cmd.process()

        opSelectionCL.process_reset()

        self.App.update_viewer()

    
    # private
    def __find_closest_vertex_index(self, cl : algSkeletonGraph.CSkeletonCenterline, pos : np.ndarray) -> int :
        '''
        desc : cl point들 중에 pos와 가장 가까운 cl point의 index를 리턴 
        '''
        pos = pos.reshape(-1)
        dist = np.linalg.norm(cl.Vertex - pos, axis=1)
        return np.argmin(dist)

if __name__ == '__main__' :
    pass


# print ("ok ..")

