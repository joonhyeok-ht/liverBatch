import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math
from collections import Counter

from PySide6.QtCore import Qt, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QListWidgetItem, QMessageBox, QAbstractItemView
from PySide6.QtGui import QStandardItemModel, QStandardItem
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK

import data as data
import operation as operation
import component as component
import componentSelectionCL as componentSelectionCL
import treeVessel as treeVessel

import VtkObj.vtkObjLine as vtkObjLine
import vtkObjInterface as vtkObjInterface

import command.commandKnife as commandKnife
import command.commandVesselKnife as commandVesselKnife



class CComAutoCutting(componentSelectionCL.CComDrag) :
    s_knifeKeyType = "knife"
    s_invalidKeyType = "invalid"
    s_pickingDepth = 1000.0
    s_minDragDist = 10


    def __init__(self, mediator) :
        super().__init__(mediator)
        self.m_inputUILVInvalidVessel = None

        self.signal_invalid_node = None     # (self, node : treeVessel.CNodeVesselHier)
        self.signal_finished_knife = None   # (self, node : treeVessel.CNodeVesselHier)

        self.m_knifeKey = ""
    def clear(self) :
        self.m_inputUILVInvalidVessel = None

        self.signal_invalid_node = None     # selected node in invalid list
        self.signal_finished_knife = None   # finished knife action and return the updated node

        self.m_knifeKey = ""
        super().clear()
    
    def ready(self) -> bool :
        if self.InputUILVInvalidVessel is None :
            return False
        return True
    def process_init(self) :
        super().process_init()
        # input your code
        if self.ready() == False :
            return
        self.InputUILVInvalidVessel.itemClicked.connect(self._on_lb_invalid_node)
        self.m_knifeKey = ""
    def process_end(self) :
        # input your code
        if self.ready() == False :
            return
        
        self.m_knifeKey = ""
        self.App.remove_key_type(CComAutoCutting.s_knifeKeyType)
        vesselKey = self._get_invalid_key()
        self.App.remove_key(vesselKey)

        self.InputUILVInvalidVessel.itemClicked.disconnect(self._on_lb_invalid_node)
        self.InputUILVInvalidVessel.clear()
        self.InputUILVInvalidVessel = None

        self.signal_invalid_node = None
        self.signal_finished_knife = None
        
        super().process_end()
    
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        # invalidate list에서 선택된 node가 없다면 무시한다. 
        selectedNode = self._getui_list_selected_node()
        if selectedNode is None :
            return False
        
        super().click(clickX, clickY)
        
        dataInst = self._get_data()
        worldStart, pNearStart, pFarStart= self.App.get_world_from_mouse(self.m_startX, self.m_startY, CComAutoCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CComAutoCutting.s_pickingDepth)

        self.m_knifeKey = data.CData.make_key(CComAutoCutting.s_knifeKeyType, 0, 0)
        inst = vtkObjLine.CVTKObjLine()
        inst.KeyType = CComAutoCutting.s_knifeKeyType
        inst.Key = self.m_knifeKey
        inst.set_line_width(2.0)
        inst.set_pos(pFarStart, pFarEnd)
        inst.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.add_vtk_obj(inst)

        self.App.ref_key_type(CComAutoCutting.s_knifeKeyType)

        self.m_bDrag = True
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        return True
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False
        
        self.App.remove_key_type(CComAutoCutting.s_knifeKeyType)

        # drag 영역이 너무 작을 경우 무시
        dx = self.m_endX - self.m_startX
        dy = self.m_endY - self.m_startY
        dist = math.hypot(dx, dy)
        if dist < CComAutoCutting.s_minDragDist :
            return False

        self._command_knife_vessel(self.m_startX, self.m_startY, self.m_endX, self.m_endY)

        self.m_bDrag = False
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        if self.ready() == False :
            return
        if self.Drag == False :
            return False
        
        super().move(clickX, clickY, listExceptKeyType)

        dataInst = self._get_data()
        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(self.m_startX, self.m_startY, CComAutoCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CComAutoCutting.s_pickingDepth)
        inst = dataInst.find_obj_by_key(self.m_knifeKey)
        inst.set_pos(pFarStart, pFarEnd)
 
        return True
    
    def get_invalid_node_count(self) -> int :
        return self.InputUILVInvalidVessel.count()
    def get_invalid_selection_node(self) -> treeVessel.CNodeVesselHier :
        return self._getui_list_selected_node()

    # command
    def command_clear_selection(self) -> bool :
        if self.ready() == False :
            return False
        self.App.remove_key(self._get_invalid_key())
        self.InputUILVInvalidVessel.clearSelection()
        self.App.update_viewer()
        return True


    # protected
    def _get_invalid_key(self) -> str :
        return data.CData.make_key(CComAutoCutting.s_invalidKeyType, 0, 0)
    def _visible_node(self, node : treeVessel.CNodeVesselHier) :
        datainst = self._get_data()
        vesselKey = self._get_invalid_key()
        self.App.remove_key(vesselKey)

        if node is None :
            return
        wholeVessel = node.get_whole_vessel()
        if wholeVessel is None :
            print("not found wholeVessel")
            return

        vesselObj = vtkObjInterface.CVTKObjInterface()
        vesselObj.KeyType = CComAutoCutting.s_invalidKeyType
        vesselObj.Key = vesselKey
        vesselObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        vesselObj.Opacity = 0.5
        vesselObj.PolyData = wholeVessel
        datainst.add_vtk_obj(vesselObj)
        self.App.ref_key(vesselKey)
        self.App.update_viewer()

    # ui 
    def _getui_list_selected_node(self) -> treeVessel.CNodeVesselHier :
        selectedItems = self.InputUILVInvalidVessel.selectedItems()
        if not selectedItems :
            return None
        
        item = selectedItems[0]
        text = item.text()
        node = item.data(Qt.UserRole)      
        return node
    
    def _setui_list_add_node(self, name : str, node : treeVessel.CNodeVesselHier) :
        self.InputUILVInvalidVessel.blockSignals(True)

        item = QListWidgetItem(f"{name}")
        item.setData(Qt.UserRole, node)
        self.InputUILVInvalidVessel.addItem(item)

        self.InputUILVInvalidVessel.blockSignals(False)
    def _setui_list_remove_node(self, targetNode : treeVessel.CNodeVesselHier) :
        self.InputUILVInvalidVessel.blockSignals(True)

        self.InputUILVInvalidVessel.setCurrentItem(None)
        self.InputUILVInvalidVessel.clearSelection()

        count = self.InputUILVInvalidVessel.count()
        for i in reversed(range(count)):
            item = self.InputUILVInvalidVessel.item(i)
            node = item.data(Qt.UserRole)
            if node == targetNode :
                self.InputUILVInvalidVessel.takeItem(i)
                del item
                break
        
        self.InputUILVInvalidVessel.blockSignals(False)

    # command
    def _command_knife_vessel(self, startMx, startMy, endMx, endMy) :
        dataInst = self._get_data()
        skeleton = self._get_skeleton()

        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(startMx, startMy, CComAutoCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(endMx, endMy, CComAutoCutting.s_pickingDepth)
        cameraInfo = self.App.get_active_camerainfo()
        cameraPos = cameraInfo[3]
        
        node = self._getui_list_selected_node()
        if node is None :
            print("not selected invalid node")
            return

        wholeVessel = node.get_whole_vessel()
        if wholeVessel is None :
            print("not found whole vessel mesh")
            return

        cmd = commandVesselKnife.CCommandMeshCutting(self.App)
        cmd.InputData = dataInst
        cmd.InputSkeleton = skeleton
        cmd.InputWholeVessel = wholeVessel
        cmd.InputWorldA = worldStart
        cmd.InputWorldB = worldEnd
        cmd.InputWorldC = cameraPos
        cmd.process()
        ret = cmd.get_whole_sub()
        
        if ret is None :
            print("failed to vessel knife")
            return
        else :
            whole = ret[0]
            sub = ret[1]
            node.set_whole_vessel(whole)
            node.Vessel = sub

        self._setui_list_remove_node(node)
        self._visible_node(None)
        if self.signal_finished_knife is not None :
            self.signal_finished_knife(node)


    # event
    def _on_lb_invalid_node(self, item) :
        node = item.data(Qt.UserRole)
        if node is None :
            print("not found node")
            return
        self._visible_node(node)
        if self.signal_invalid_node is not None :
            self.signal_invalid_node(node)
    

    @property
    def InputUILVInvalidVessel(self) :
        return self.m_inputUILVInvalidVessel
    @InputUILVInvalidVessel.setter
    def InputUILVInvalidVessel(self, inputUILVInvalidVessel) :
        self.m_inputUILVInvalidVessel = inputUILVInvalidVessel


class CComAutoCuttingTree(CComAutoCutting) :
    def __init__(self, mediator):
        super().__init__(mediator)
        self.m_treeVessel = None
    def clear(self) :
        self.m_treeVessel = None
        super().clear()
    
    def ready(self) -> bool :
        return super().ready()
    def process_init(self) :
        super().process_init()
        # input your code
        if self.ready() == False :
            return
    def process_end(self) :
        # input your code
        if self.ready() == False :
            return
        super().process_end()
    
    # command
    def command_cutting_vessel(self, treeVessel : treeVessel.CTreeVessel, vesselMesh : vtk.vtkPolyData) :
        self.m_treeVessel = treeVessel
        firstRootNode = self.m_treeVessel.get_first_root_node()
        if firstRootNode is None :
            return
        firstRootNode.clear_vessel()
        firstRootNode.Vessel = vesselMesh

        iCnt = firstRootNode.get_child_node_count()
        for inx in range(0, iCnt) :
            node = firstRootNode.get_child_node(inx)
            self._process_sub(node)


    # protected
    def _process_sub(self, node : treeVessel.CNodeVesselHier) :
        wholeVessel = node.get_whole_vessel()
        if wholeVessel is None :
            print("not found whole vessel mesh")
            return
        
        clID = node.get_clID(0)

        cmd = commandVesselKnife.CCommandSepVesselKMTreeVessel(self.m_mediator)
        cmd.m_inputData = self._get_data()
        cmd.m_inputSkeleton = self.m_treeVessel.Skeleton
        cmd.m_inputWholeVessel = wholeVessel
        cmd.m_inputCLID = clID
        cmd.process()

        if cmd.OutputWhole is None or cmd.OutputSub is None :
            clLabel = self.m_treeVessel.get_cl_label(node)
            self._setui_list_add_node(clLabel, node)
        else :
            node.set_whole_vessel(cmd.OutputWhole)
            node.Vessel = cmd.OutputSub

        iCnt = node.get_child_node_count()
        for inx in range(0, iCnt) :
            childNode = node.get_child_node(inx)
            self._process_sub(childNode)

    



'''
knife cutting
'''
class CCuttingNode :
    def __init__(self) :
        self.m_name = ""
        self.m_mesh = None
    def clear(self) :
        self.m_name = ""
        self.m_mesh = None
    

    @property
    def Name(self) -> str :
        return self.m_name
    @Name.setter
    def Name(self, name : str) :
        self.m_name = name
    @property
    def Mesh(self) -> vtk.vtkPolyData :
        return self.m_mesh
    @Mesh.setter
    def Mesh(self, mesh : vtk.vtkPolyData) :
        self.m_mesh = mesh

class CCommandKnifeCutting :
    def __init__(self, mediator : componentSelectionCL.CComDrag, dataInst : data.CData) :
        '''
        mediator : 
        '''
        self.m_mediator = mediator
        self.m_data = dataInst
        self.m_inputCuttingNode = None
    def clear(self) :
        self.m_mediator = None
        self.m_data = None
        self.m_inputCuttingNode = None

    def process(self) -> bool :
        return True
    def process_undo(self) :
        pass


    @property
    def App(self) :
        return self.m_mediator.App
    @property
    def Data(self)  -> data.CData :
        return self.m_data
    @property
    def InputCuttingNode(self) -> CCuttingNode :
        return self.m_inputCuttingNode
    @InputCuttingNode.setter
    def InputCuttingNode(self, inputCuttingNode : CCuttingNode) :
        self.m_inputCuttingNode = inputCuttingNode
class CCommandKnifeCuttingTP(CCommandKnifeCutting) :
    def __init__(self, mediator : componentSelectionCL.CComDrag, dataInst : data.CData) :
        super().__init__(mediator, dataInst)
        self.m_inputVessel = None
        self.m_inputTPPos = None
        self.m_undoVessel = None
    def clear(self) :
        self.m_inputVessel = None
        self.m_inputTPPos = None
        self.m_undoVessel = None
        super().clear()

    def process(self) -> bool :
        if self.InputCuttingNode is None :
            return False
        if self.InputVessel is None :
            return False
        if self.InputTPPos is None :
            return False
        
        self.m_undoVessel = self.InputCuttingNode.Mesh
        self.m_mediator.pushback_tp(self.InputTPPos)
        self.InputCuttingNode.Mesh = self.InputVessel
        return True
    def process_undo(self) :
        self.InputCuttingNode.Mesh = self.m_undoVessel
        self.m_mediator.popback_tp()
        self.m_mediator.command_selection_vessel(self.InputCuttingNode)

    
    @property
    def InputVessel(self) -> vtk.vtkPolyData :
        return self.m_inputVessel
    @InputVessel.setter
    def InputVessel(self, inputVessel : vtk.vtkPolyData) :
        self.m_inputVessel = inputVessel
    @property
    def InputTPPos(self) -> np.ndarray :
        return self.m_inputTPPos
    @InputTPPos.setter
    def InputTPPos(self, inputTPPos : np.ndarray) :
        self.m_inputTPPos = inputTPPos
class CCommandKnifeCuttingCut(CCommandKnifeCutting) :
    def __init__(self, mediator : componentSelectionCL.CComDrag, dataInst : data.CData) :
        super().__init__(mediator, dataInst)
        self.m_inputWholeVessel = None
        self.m_inputSubVessel = None
        self.m_undoVessel = None
        self.m_undoListTPPos = []
        self.m_undoNode = None
    def clear(self) :
        self.m_inputWholeVessel = None
        self.m_inputSubVessel = None
        self.m_undoVessel = None
        self.m_undoListTPPos.clear()
        self.m_undoNode = None
        super().clear()

    def process(self) -> bool :
        if self.InputCuttingNode is None :
            return False
        if self.InputWholeVessel is None :
            return False
        if self.InputSubVessel is None :
            return False
        
        # tp 제거 
        iCnt = self.m_mediator.get_tp_key_count()
        for inx in range(0, iCnt) :
            tpKey = self.m_mediator.get_tp_key(inx)
            tpObj = self.Data.find_obj_by_key(tpKey)
            pos = tpObj.Pos
            self.m_undoListTPPos.append(pos)
        self.m_mediator.clear_tp()

        self.m_undoVessel =self.InputCuttingNode.Mesh
        self.InputCuttingNode.Mesh = self.InputWholeVessel

        ret = self.m_mediator.find_list_clID(self.InputSubVessel)
        if ret is None :
            print("not found sub vessel clID")
            return False
        
        name = ret[0]
        if name == "" :
            name = "sub"
        listCLID = ret[1]

        node = CCuttingNode()
        node.Name = name
        node.Mesh = self.InputSubVessel
        self.m_mediator.setui_lv_vessel_add_node(node)
        self.m_mediator.command_selection_vessel(node)
        self.m_undoNode = node

        return True
    def process_undo(self) :
        self.InputCuttingNode.Mesh = self.m_undoVessel

        for tpPos in self.m_undoListTPPos :
            self.m_mediator.pushback_tp(tpPos)
        
        node = self.m_undoNode
        self.m_mediator.setui_lv_vessel_remove_node(node)
        self.m_mediator.command_selection_vessel(self.InputCuttingNode)


    @property
    def InputWholeVessel(self) -> vtk.vtkPolyData :
        return self.m_inputWholeVessel
    @InputWholeVessel.setter
    def InputWholeVessel(self, inputWholeVessel : vtk.vtkPolyData) :
        self.m_inputWholeVessel = inputWholeVessel
    @property
    def InputSubVessel(self) -> vtk.vtkPolyData :
        return self.m_inputSubVessel
    @InputSubVessel.setter
    def InputSubVessel(self, inputSubVessel : vtk.vtkPolyData) :
        self.m_inputSubVessel = inputSubVessel


class CComKnifeCutting(componentSelectionCL.CComDrag) :
    s_knifeKeyType = "knife"
    s_nodeKeyType = "node"
    s_tpType = "tp"

    s_pickingDepth = 1000.0
    s_minDragDist = 10

    s_tpRadius = 2.0
    s_tpColor = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])


    def __init__(self, mediator) :
        super().__init__(mediator)

        self.m_inputUILVVessel = None
        self.signal_finished_knife = None   # (self, node : treeVessel.CNodeVesselHier)

        self.m_knifeKey = ""
        self.m_listTPKey = []
        self.m_listCmd = []
    def clear(self) :
        self.m_inputUILVVessel = None
        self.signal_finished_knife = None

        self.m_knifeKey = ""
        self.m_listCmd.clear()
        self.m_listTPKey.clear()
        super().clear()

    
    # override 
    def ready(self) -> bool :
        if self.InputUILVVessel is None :
            return
        return True
    def process_init(self) :
        super().process_init()
        # input your code
        if self.ready() == False :
            return
        if self.InputUILVVessel is None :
            return
        self.InputUILVVessel.itemClicked.connect(self._on_lv_vessel)

        self.m_knifeKey = ""
        self.m_listTPKey.clear()
    def process_end(self) :
        # input your code
        if self.ready() == False :
            return
        
        self.InputUILVVessel.itemClicked.disconnect(self._on_lv_vessel)
        self.InputUILVVessel.clear()
        self.InputUILVVessel = None

        self.m_knifeKey = ""
        self.App.remove_key_type(CComKnifeCutting.s_knifeKeyType)

        self.clear_tp()
        self.m_listCmd.clear()
        
        self.App.remove_key(self._get_node_key())
        super().process_end()
    

    def get_vessel_node_count(self) -> int :
        return self._getui_lv_vessel_node_count()
    def get_vessel_node(self, inx : int) -> CCuttingNode :
        return self._getui_lv_vessel_node(inx)
    def pushback_tp(self, pos : np.ndarray) -> str :
        dataInst = self._get_data()
        tpPolyData = algVTK.CVTK.create_poly_data_sphere(
            algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0]), 
            CComKnifeCutting.s_tpRadius
        )

        id = len(self.m_listTPKey)
        color = CComKnifeCutting.s_tpColor

        # tpObj
        keyType = CComKnifeCutting.s_tpType
        key = data.CData.make_key(keyType, 0, id)
        tpVesselObj = vtkObjInterface.CVTKObjInterface()
        tpVesselObj.KeyType = keyType
        tpVesselObj.Key = key
        tpVesselObj.Color = color
        tpVesselObj.Opacity = 1.0
        tpVesselObj.PolyData = tpPolyData
        tpVesselObj.Pos = pos
        dataInst.add_vtk_obj(tpVesselObj)
        self.App.ref_key(key)
        self.m_listTPKey.append(key)
        return key
    def popback_tp(self) -> str :
        tpKey = self.m_listTPKey.pop()
        self.App.remove_key(tpKey)
        return tpKey
    def clear_tp(self) :
        self.App.remove_key_type(CComKnifeCutting.s_tpType)
        self.m_listTPKey.clear()
    def get_tp_key_count(self) -> int :
        return len(self.m_listTPKey)
    def get_tp_key(self, inx : int) -> str :
        return self.m_listTPKey[inx]
    def find_list_clID(self, polydata : vtk.vtkPolyData) -> tuple :
        '''
        ret : (name : str, [clID0, clID1, .. ])
            name : clID list에서 가장 많이 등장하는 name 
        '''
        retList = []
        retListName = []
        skeleton = self._get_skeleton()
        iCnt = skeleton.get_centerline_count()

        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            inCnt = algVTK.CVTK.check_in_polydata(polydata, cl.Vertex)
            if inCnt > 1 :
                retList.append(cl.ID)
                retListName.append(cl.Name)
        
        if len(retList) == 0 :
            return None
        
        counter = Counter(retListName)
        mostCommon = counter.most_common(1)
        name = mostCommon[0][0]

        return (name, retList)
    def get_all_polydata(self) -> dict :
        '''
        desc
            - cutting name별로 polydata를 반환 
        ret 
            - key : cutting name
            - value : vtkPolyData
        '''
        retDic = {}
        iCnt = self.get_vessel_node_count()
        for inx in range(0, iCnt) :
            cuttingNode = self.get_vessel_node(inx)
            cuttingName = cuttingNode.Name
            cuttingMesh = cuttingNode.Mesh
            if cuttingName in retDic.keys() :
                subMesh = retDic[cuttingName]
                append_filter = vtk.vtkAppendPolyData()
                append_filter.AddInputData(cuttingMesh)
                append_filter.AddInputData(subMesh)
                append_filter.Update()
                combinedPolydata = append_filter.GetOutput()

                if combinedPolydata is not None and combinedPolydata.GetNumberOfPoints() != 0 :
                    retDic[cuttingName] = combinedPolydata
            else :
                retDic[cuttingName] = cuttingMesh

        return retDic

    
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        selectionNode = self._getui_lv_vessel_selection()
        if selectionNode is None :
            return False

        super().click(clickX, clickY)
        
        dataInst = self._get_data()
        worldStart, pNearStart, pFarStart= self.App.get_world_from_mouse(self.m_startX, self.m_startY, CComKnifeCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CComKnifeCutting.s_pickingDepth)

        self.m_knifeKey = data.CData.make_key(CComKnifeCutting.s_knifeKeyType, 0, 0)
        inst = vtkObjLine.CVTKObjLine()
        inst.KeyType = CComKnifeCutting.s_knifeKeyType
        inst.Key = self.m_knifeKey
        inst.set_line_width(2.0)
        inst.set_pos(pFarStart, pFarEnd)
        inst.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.add_vtk_obj(inst)

        self.App.ref_key_type(CComKnifeCutting.s_knifeKeyType)

        self.m_bDrag = True
        return True
    def click_with_shift(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        return True
    def release(self, clickX : int, clickY : int) :
        if self.ready() == False :
            return False
        if self.Drag == False :
            return False
        
        self.App.remove_key_type(CComKnifeCutting.s_knifeKeyType)

        # drag 영역이 너무 작을 경우 무시
        dx = self.m_endX - self.m_startX
        dy = self.m_endY - self.m_startY
        dist = math.hypot(dx, dy)
        if dist < CComKnifeCutting.s_minDragDist :
            self.m_bDrag = False
            return False

        self.command_knife_vessel(self.m_startX, self.m_startY, self.m_endX, self.m_endY)

        self.m_bDrag = False
        return True
    def move(self, clickX : int, clickY : int, listExceptKeyType=None) :
        if self.ready() == False :
            return
        if self.Drag == False :
            return False
        
        super().move(clickX, clickY, listExceptKeyType)

        dataInst = self._get_data()
        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(self.m_startX, self.m_startY, CComKnifeCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CComKnifeCutting.s_pickingDepth)
        inst = dataInst.find_obj_by_key(self.m_knifeKey)
        inst.set_pos(pFarStart, pFarEnd)
 
        return True
    
    # command
    def command_init_with_mesh(self, label : str, mesh : vtk.vtkPolyData) :
        if self.ready() == False :
            return
        
        self.InputUILVVessel.clear()
        self.clear_tp()
        self.m_listCmd.clear()
        self.App.remove_key(self._get_node_key())

        node = CCuttingNode()
        node.Name = label
        node.Mesh = mesh
        self.setui_lv_vessel_add_node(node)
        self.command_selection_vessel(node)
    def command_init_with_tree_vessel(self, treevessel : treeVessel.CTreeVessel) :
        if self.ready() == False :
            return
        
        self.InputUILVVessel.clear()
        self.clear_tp()
        self.m_listCmd.clear()
        self.App.remove_key(self._get_node_key())

        skeleton = treevessel.Skeleton

        firstNode = treevessel.get_first_root_node()
        listNode = [firstNode]
        while len(listNode) > 0 :
            node = listNode.pop()
            if node.Vessel is not None :
                clid = node.get_clID(0)
                label = skeleton.get_centerline(clid).Name
                cuttingNode = CCuttingNode()
                cuttingNode.Name = label
                cuttingNode.Mesh = node.Vessel
                self.setui_lv_vessel_add_node(cuttingNode)
            iCnt = node.get_child_node_count()
            for inx in range(0, iCnt) :
                childNode = node.get_child_node(inx)
                listNode.append(childNode)
        
        cuttingNode = self._getui_lv_vessel_node(0)
        self.command_selection_vessel(cuttingNode)
    def command_knife_vessel(self, startMx, startMy, endMx, endMy) :
        dataInst = self._get_data()
        skeleton = self._get_skeleton()


        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(startMx, startMy, CComKnifeCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(endMx, endMy, CComKnifeCutting.s_pickingDepth)
        cameraInfo = self.App.get_active_camerainfo()
        cameraPos = cameraInfo[3]

        rootNode = self._getui_lv_vessel_selection()
        if rootNode is None :
            QMessageBox.information(self.App, "Alarm", "리스트 박스에서 혈관을 선택하세요")
            return

        wholeVessel = rootNode.Mesh

        cmd = commandVesselKnife.CCommandMeshCutting(self.App)
        cmd.InputData = dataInst
        cmd.InputSkeleton = skeleton
        cmd.InputWholeVessel = wholeVessel
        cmd.InputWorldA = worldStart
        cmd.InputWorldB = worldEnd
        cmd.InputWorldC = cameraPos
        cmd.process()

        if cmd.get_output_polydata_count() == 0 :
            print("not intersected knife")
            return
        if cmd.get_output_polydata_count() == 1 :
            cl = skeleton.get_centerline(cmd.OutputCLID)
            pos = cl.get_vertex(cmd.OutputVertexInx)

            undoCmd = CCommandKnifeCuttingTP(self, dataInst)
            undoCmd.InputCuttingNode = rootNode
            undoCmd.InputVessel = cmd.get_output_polydata(0)
            undoCmd.InputTPPos = pos
            undoCmd.process()
            self.m_listCmd.append(undoCmd)
            self.App.update_viewer()
        if cmd.get_output_polydata_count() > 1 :
            wholePolydata, subPolydata = cmd.get_whole_sub()
            
            undoCmd = CCommandKnifeCuttingCut(self, dataInst)
            undoCmd.InputCuttingNode = rootNode
            undoCmd.InputWholeVessel = wholePolydata
            undoCmd.InputSubVessel = subPolydata
            undoCmd.process()
            self.m_listCmd.append(undoCmd)
            self.App.update_viewer()

        if self.signal_finished_knife is not None :
            self.signal_finished_knife()
    def command_label_name(self, labelName) :
        self._setui_lv_vessel_selection_name(labelName)
    def command_selection_vessel(self, node : CCuttingNode) :
        self._setui_lv_vessel_selection(node)
        self._visible_node(node)
    def command_undo(self) :
        if len(self.m_listCmd) == 0 :
            return
        undoCmd = self.m_listCmd.pop()
        undoCmd.process_undo()
        self.App.update_viewer()
    

    # protected
    def _get_node_key(self) -> str :
        return data.CData.make_key(CComKnifeCutting.s_nodeKeyType, 0, 0)
    def _visible_node(self, node : CCuttingNode) :
        datainst = self._get_data()
        nodeKey = self._get_node_key()
        self.App.remove_key(nodeKey)

        mesh = node.Mesh
        if mesh is None :
            print("not found mesh")
            return

        vesselObj = vtkObjInterface.CVTKObjInterface()
        vesselObj.KeyType = CComKnifeCutting.s_nodeKeyType
        vesselObj.Key = nodeKey
        vesselObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        vesselObj.Opacity = 0.5
        vesselObj.PolyData = mesh
        datainst.add_vtk_obj(vesselObj)
        self.App.ref_key(nodeKey)
        self.App.update_viewer()

    # ui setting
    def setui_lv_vessel_add_node(self, node : CCuttingNode) :
        self.InputUILVVessel.blockSignals(True)

        item = QListWidgetItem(f"{node.Name}")
        item.setData(Qt.UserRole, node)
        self.InputUILVVessel.addItem(item)

        self.InputUILVVessel.blockSignals(False)
    def setui_lv_vessel_remove_node(self, node : CCuttingNode) :
        self.InputUILVVessel.blockSignals(True)

        self.InputUILVVessel.setCurrentItem(None)
        self.InputUILVVessel.clearSelection()

        count = self.InputUILVVessel.count()
        for i in reversed(range(count)):
            item = self.InputUILVVessel.item(i)
            node = item.data(Qt.UserRole)
            if node == node :
                self.InputUILVVessel.takeItem(i)
                del item
                break
        
        self.InputUILVVessel.blockSignals(False)
    def _setui_lv_vessel_selection(self, targetNode : CCuttingNode) :
        self.InputUILVVessel.blockSignals(True)

        count = self.InputUILVVessel.count()
        for i in range(count):
            item = self.InputUILVVessel.item(i)
            node = item.data(Qt.UserRole)
            if node == targetNode : 
                self.InputUILVVessel.setCurrentItem(item)
                item.setSelected(True)
                break

        self.InputUILVVessel.blockSignals(False)
    def _setui_lv_vessel_selection_name(self, label : str) :
        item = self.InputUILVVessel.currentItem()
        if item is not None:
            item.setText(label)
            node = item.data(Qt.UserRole)
            if node is not None:
                node.Name = label
    def _setui_lv_vessel_clear_selection(self) :
        self.InputUILVVessel.blockSignals(True)
        self.InputUILVVessel.clearSelection()
        self.InputUILVVessel.blockSignals(False)
    
    def _getui_lv_vessel_node_count(self) -> int :
        return self.InputUILVVessel.count()
    def _getui_lv_vessel_node(self, inx : int) -> CCuttingNode :
        item = self.InputUILVVessel.item(inx)
        if item is not None :
            return item.data(Qt.UserRole)
        return None
    def _getui_lv_vessel_selection(self) -> CCuttingNode :
        item = self.InputUILVVessel.currentItem()
        if item is not None:
            return item.data(Qt.UserRole)
        return None
    

    # event
    def _on_lv_vessel(self, item) :
        node = item.data(Qt.UserRole)
        if node is None :
            print("not found node")
            return
        self._visible_node(node)
        


    @property
    def InputUILVVessel(self) -> QListWidget : 
        return self.m_inputUILVVessel
    @InputUILVVessel.setter
    def InputUILVVessel(self, inputUILVVessel : QListWidget) :
        self.m_inputUILVVessel = inputUILVVessel





if __name__ == '__main__' :
    pass


# print ("ok ..")

