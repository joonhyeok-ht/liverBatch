import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileCommonPath = os.path.dirname(fileAbsPath)
fileStateProjectPath = os.path.dirname(fileCommonPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileCommonPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algMeshLib as algMeshLib


import data as data

import operation as operation

import tabState as tabState

import VtkObj.vtkObjLine as vtkObjLine
import vtkObjInterface as vtkObjInterface

import command.commandVesselKnife as commandVesselKnife

import remodelingNode as remodelingNode
import remodelingVessel as remodelingVessel



class CCommandRemodeling :
    s_pickingDepth = 1000.0
    s_minDragDist = 10


    def __init__(self, mediator) :
        '''
        mediator : CTabState
        '''
        self.m_mediator = mediator
        self.m_undoListRemodelingNode = []
        self.m_undoSelectedIndex = -1
    def clear(self) :
        self.m_mediator = None
        self.m_undoListRemodelingNode.clear()
        self.m_undoSelectedIndex = -1
    def undo(self) :
        pass

    # protected 
    def _copy_remodeling_node(self, listNode : list) :
        listCopiedNode = []
        for node in listNode :
            if node == self.m_mediator.MainNode :
                listCopiedNode.append(node)
            else :
                copiedNode = remodelingNode.CRemodelingNode()
                copiedNode.Name = node.Name
                copiedNode.Key = node.Key
                copiedNode.SkelKey = node.SkelKey
                copiedNode.Skeleton = node.Skeleton
                copiedNode.SkeletonEn = node.SkeletonEn
                copiedNode.RootEntity = node.RootEntity
                listCopiedNode.append(copiedNode)
        return listCopiedNode


    @property
    def App(self) :
        return self.m_mediator.m_mediator

class CCommandRemodelingCutting(CCommandRemodeling) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self, startX : int, startY : int, endX : int, endY : int) -> bool :
        dataInst = self.m_mediator.get_data()
        clinfoInx = self.m_mediator.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)

        self.m_undoListRemodelingNode = self._copy_remodeling_node(self.m_mediator.m_listRemodelingNode)
        self.m_undoSelectedIndex = self.m_mediator.getui_lv_cuttednode_selected_index()
        if self.m_undoSelectedIndex == -1 :
            return False
        selectedNode = self.m_mediator.m_listRemodelingNode[self.m_undoSelectedIndex]
        vesselPolydata = self.m_mediator.get_cuttedmesh_polydata(selectedNode.Key)

        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(startX, startY, CCommandRemodeling.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(endX, endY, CCommandRemodeling.s_pickingDepth)
        cameraInfo = self.App.get_active_camerainfo()
        cameraPos = cameraInfo[3]

        cmd = commandVesselKnife.CCommandMeshCutting(self.App)
        cmd.InputData = dataInst
        cmd.InputSkeleton = skeleton
        cmd.InputWorldA = worldStart
        cmd.InputWorldB = worldEnd
        cmd.InputWorldC = cameraPos
        cmd.InputWholeVessel = vesselPolydata
        cmd.process()

        listCuttingKey = []
        if cmd.OutputListPolydata is None :
            return False
        if len(cmd.OutputListPolydata) == 0 :
            return False
    
        iCnt = len(cmd.OutputListPolydata)
        for inx in range(0, iCnt) :
            polydata = cmd.OutputListPolydata[inx]
            cuttingKey = self.m_mediator.create_cuttedmesh_key(polydata)
            listCuttingKey.append(cuttingKey)
        
        self._refresh_cutting_key(listCuttingKey)

        return True
    def undo(self) :
        self.m_mediator.refresh_remodeling_node_list(self.m_undoListRemodelingNode)
        self.m_mediator.select_index_cuttedmesh(self.m_undoSelectedIndex)
    
    # protected
    def _refresh_cutting_key(self, listCuttingKey : list) :
        nowSelectedIndex = self.m_undoSelectedIndex
        selectedNode = self.m_mediator.getui_lv_cuttednode_selected_node()
        listNode = self._copy_remodeling_node(self.m_mediator.m_listRemodelingNode)

        if selectedNode == self.m_mediator.MainNode :
            for inx, cuttingKey in enumerate(listCuttingKey) :
                node = remodelingNode.CRemodelingNode()
                node.Key = cuttingKey
                node.Name = self.m_mediator.get_node_name()
                listNode.insert(nowSelectedIndex + inx, node)
        else :
            for inx, cuttingKey in enumerate(listCuttingKey) :
                node = remodelingNode.CRemodelingNode()
                node.Key = cuttingKey

                if inx == 0 :
                    node.Name = listNode[nowSelectedIndex].Name
                    listNode[nowSelectedIndex] = node
                else :
                    node.Name = self.m_mediator.get_node_name()
                    listNode.insert(nowSelectedIndex + inx, node)
        
        self.m_mediator.refresh_remodeling_node_list(listNode)
        self.m_mediator.select_index_cuttedmesh(nowSelectedIndex)
class CCommandRemodelingRemove(CCommandRemodeling) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) -> bool :
        if len(self.m_mediator.m_listRemodelingNode) <= 1 :
            return False

        self.m_undoListRemodelingNode = self._copy_remodeling_node(self.m_mediator.m_listRemodelingNode)
        self.m_undoSelectedIndex = self.m_mediator.getui_lv_cuttednode_selected_index()
        if self.m_undoSelectedIndex == -1 :
            return False
        selectedNode = self.m_mediator.m_listRemodelingNode[self.m_undoSelectedIndex]

        self.App.unref_key(selectedNode.Key)
        self.m_mediator.m_listRemodelingNode.remove(selectedNode)
        self.m_mediator.setui_lv_cuttednode_remove_node(selectedNode)

        self.m_mediator.refresh_remodeling_node_list(self.m_mediator.m_listRemodelingNode)
        self.m_mediator.select_index_cuttedmesh(0)

        return True
    def undo(self) :
        self.m_mediator.refresh_remodeling_node_list(self.m_undoListRemodelingNode)
        self.m_mediator.select_index_cuttedmesh(self.m_undoSelectedIndex)
class CCommandRemodelingAdd(CCommandRemodeling) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_inputAnchorNode = None
        self.m_inputRemodelingMesh = None
    def clear(self) :
        # input your code
        self.m_inputAnchorNode = None
        self.m_inputRemodelingMesh = None
        super().clear()
    def process(self) -> bool :
        if self.InputAnchorNode is None :
            return False
        if self.InputRemodelingMesh is None :
            return False 

        self.m_undoListRemodelingNode = self._copy_remodeling_node(self.m_mediator.m_listRemodelingNode)
        self.m_undoSelectedIndex = self.m_mediator.getui_lv_cuttednode_selected_index()
        if self.m_undoSelectedIndex == -1 :
            return False
        
        index = self.m_mediator.getui_lv_cuttednode_find_index_by_name(self.InputAnchorNode.Name)
        cuttingKey = self.m_mediator.create_cuttedmesh_key(self.InputRemodelingMesh)
        node = remodelingNode.CRemodelingNode()
        node.Key = cuttingKey
        node.Name = f"{self.InputAnchorNode.Name}_Re"
        self.m_mediator.m_listRemodelingNode.insert(index, node)

        self.m_mediator.refresh_remodeling_node_list(self.m_mediator.m_listRemodelingNode)
        self.m_mediator.select_index_cuttedmesh(index)

        return True
    def undo(self) :
        self.m_mediator.refresh_remodeling_node_list(self.m_undoListRemodelingNode)
        self.m_mediator.select_index_cuttedmesh(self.m_undoSelectedIndex)
    

    @property
    def InputAnchorNode(self) -> remodelingNode.CRemodelingNode :
        return self.m_inputAnchorNode
    @InputAnchorNode.setter
    def InputAnchorNode(self, anchorNode : remodelingNode.CRemodelingNode) :
        self.m_inputAnchorNode = anchorNode
    @property
    def InputRemodelingMesh(self) -> vtk.vtkPolyData :
        return self.m_inputRemodelingMesh
    @InputRemodelingMesh.setter
    def InputRemodelingMesh(self, inputRemodelingMesh : vtk.vtkPolyData) :
        self.m_inputRemodelingMesh = inputRemodelingMesh
    




# vessel remodeling command
class CCommandRemodelingTreeVessel :
    '''
    input
        InputNode : remodeling 할 node,  CRemodelingNode
    '''
    def __init__(self) :
        self.m_treeVesselRemodeling = remodelingVessel.CTreeVesselRemodeling()
        self.m_inputNode = None
        self.m_inputRadiusMargin = 0.0
    def clear(self) :
        self.m_inputNode = None
        self.m_inputRadiusMargin = 0.0
        self.m_outputRemodelingMesh = None
    def process(self) :
        if self.InputNode is None :
            return
        
        skeleton = self.InputNode.SkeletonEn
        if skeleton is None :
            return

        # root radius refinement 
        rootCL = skeleton.RootCenterline
        maxRadius = np.max(rootCL.Radius)
        rootCL.Radius[0] = maxRadius

        self.m_treeVesselRemodeling = remodelingVessel.CTreeVesselRemodeling()
        self.m_treeVesselRemodeling.InputSkeleton = skeleton
        self.m_treeVesselRemodeling.InputRadiusMargin = self.InputRadiusMargin
        self.m_treeVesselRemodeling.process()
        print("-- completed remodeling mesh --")


    @property
    def InputNode(self) -> remodelingNode.CRemodelingNode :
        return self.m_inputNode
    @InputNode.setter
    def InputNode(self, inputNode : remodelingNode.CRemodelingNode) :
        self.m_inputNode = inputNode
    @property
    def InputRadiusMargin(self) -> float :
        return self.m_inputRadiusMargin
    @InputRadiusMargin.setter
    def InputRadiusMargin(self, inputRadiusMargin : float) :
        self.m_inputRadiusMargin = inputRadiusMargin
    
    
    @property
    def OutputRemodelingMesh(self) -> vtk.vtkPolyData :
        return self.m_treeVesselRemodeling.MergedMesh
    
    @property
    def TreeVesselRemodeling(self) -> remodelingVessel.CTreeVesselRemodeling :
        return self.m_treeVesselRemodeling


if __name__ == '__main__' :
    pass


# print ("ok ..")

