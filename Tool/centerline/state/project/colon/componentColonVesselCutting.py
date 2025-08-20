import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import copy
import SimpleITK as sitk
import math
from collections import Counter

from PySide6.QtCore import Qt, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTreeView, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QListWidgetItem, QMessageBox, QAbstractItemView
from PySide6.QtGui import QStandardItemModel, QStandardItem
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


import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer

import VtkObj.vtkObjLine as vtkObjLine
import vtkObjInterface as vtkObjInterface

import data as data

import userData as userData

import com.componentSelectionCL as componentSelectionCL

import command.commandKnife as commandKnife
import command.commandVesselKnife as commandVesselKnife


class CColonVesselNode :
    def __init__(self) :
        self.m_name = "Root"
        self.m_subVesselKey = ""
        self.m_listCLID = []
    def clear(self) :
        self.m_name = "Root"
        self.m_subVesselKey = ""
        self.m_listCLID.clear()



class CComColonVesselCutting(componentSelectionCL.CComDrag) :
    s_knifeKeyType = "knife"
    s_tpType = "tp"
    s_subVesselType = "SubVessel"

    s_pickingDepth = 1000.0
    s_minDragDist = 10
    s_tpRadius = 2.0


    def __init__(self, mediator) :
        super().__init__(mediator)
        self.signal_finished_knife = None   # (self, node : treeVessel.CNodeVesselHier)

        self.m_knifeKey = ""
        self.m_listTPKey = []
        self.m_inputUILVVessel = None
    def clear(self) :
        self.signal_finished_knife = None

        self.m_inputUILVVessel = None
        self.m_knifeKey = ""
        self.m_listTPKey.clear()
        super().clear()

    
    # override 
    def ready(self) -> bool :
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

        dataInst = self._get_data()
        clinfoInx = self._get_clinfoinx()
        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey)

        vesselPolydata = vesselObj.PolyData
        vertex = algVTK.CVTK.poly_data_get_vertex(vesselPolydata)
        index = algVTK.CVTK.poly_data_get_triangle_index(vesselPolydata)
        vesselPolydata = algVTK.CVTK.create_poly_data_triangle(vertex, index)

        subVesselKey = data.CData.make_key(CComColonVesselCutting.s_subVesselType, 0, 0)
        subVesselObj = vtkObjInterface.CVTKObjInterface()
        subVesselObj.KeyType = CComColonVesselCutting.s_subVesselType
        subVesselObj.Key = subVesselKey
        subVesselObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        subVesselObj.Opacity = 0.5
        subVesselObj.PolyData = vesselPolydata
        dataInst.add_vtk_obj(subVesselObj)

        node = CColonVesselNode()
        node.m_subVesselKey = subVesselKey
        self._setui_lv_vessel_add_node(node)
    def process_end(self) :
        # input your code
        if self.ready() == False :
            return
        
        self.InputUILVVessel.clear()
        self.m_knifeKey = ""
        self.App.remove_key_type(CComColonVesselCutting.s_knifeKeyType)
        self.App.remove_key_type(CComColonVesselCutting.s_tpType)
        self.App.remove_key_type(CComColonVesselCutting.s_subVesselType)
        self.m_listTPKey.clear()

        self.signal_finished_knife = None
        
        super().process_end()
    
    def click(self, clickX : int, clickY : int, listExceptKeyType=None) -> bool :
        if self.ready() == False :
            return False
        
        super().click(clickX, clickY)
        
        dataInst = self._get_data()
        worldStart, pNearStart, pFarStart= self.App.get_world_from_mouse(self.m_startX, self.m_startY, CComColonVesselCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CComColonVesselCutting.s_pickingDepth)

        self.m_knifeKey = data.CData.make_key(CComColonVesselCutting.s_knifeKeyType, 0, 0)
        inst = vtkObjLine.CVTKObjLine()
        inst.KeyType = CComColonVesselCutting.s_knifeKeyType
        inst.Key = self.m_knifeKey
        inst.set_line_width(2.0)
        inst.set_pos(pFarStart, pFarEnd)
        inst.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.add_vtk_obj(inst)

        self.App.ref_key_type(CComColonVesselCutting.s_knifeKeyType)

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
        
        self.App.remove_key_type(CComColonVesselCutting.s_knifeKeyType)

        # drag 영역이 너무 작을 경우 무시
        dx = self.m_endX - self.m_startX
        dy = self.m_endY - self.m_startY
        dist = math.hypot(dx, dy)
        if dist < CComColonVesselCutting.s_minDragDist :
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
        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(self.m_startX, self.m_startY, CComColonVesselCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(self.m_endX, self.m_endY, CComColonVesselCutting.s_pickingDepth)
        inst = dataInst.find_obj_by_key(self.m_knifeKey)
        inst.set_pos(pFarStart, pFarEnd)
 
        return True

    def get_vessel_node_count(self) -> int :
        return self._getui_lv_vessel_node_count()
    def get_vessel_node(self, inx : int) -> CColonVesselNode :
        return self._getui_lv_vessel_node(inx)


    # command
    def command_knife_vessel(self, startMx, startMy, endMx, endMy) :
        dataInst = self._get_data()
        clinfoInx = self._get_clinfoinx()
        skeleton = self._get_skeleton()


        worldStart, pNearStart, pFarStart = self.App.get_world_from_mouse(startMx, startMy, CComColonVesselCutting.s_pickingDepth)
        worldEnd, pNearEnd, pFarEnd = self.App.get_world_from_mouse(endMx, endMy, CComColonVesselCutting.s_pickingDepth)
        cameraInfo = self.App.get_active_camerainfo()
        cameraPos = cameraInfo[3]

        rootNode = self._getui_lv_vessel_selection()
        if rootNode is None :
            QMessageBox.information(self.App, "Alarm", "리스트 박스에서 혈관을 선택하세요")
            return

        # rootNode = self._getui_lv_vessel_node(0)
        wholeVesselKey = rootNode.m_subVesselKey
        wholeVesselObj = dataInst.find_obj_by_key(wholeVesselKey)
        
        cmd = commandVesselKnife.CCommandSepVesselKMGraphVesselKnife(self.App)
        cmd.InputData = dataInst
        cmd.InputSkeleton = skeleton
        cmd.InputWorldA = worldStart
        cmd.InputWorldB = worldEnd
        cmd.InputWorldC = cameraPos
        cmd.InputWholeVessel = wholeVesselObj.PolyData
        cmd.process()

        print(f"command_knife_vessel : output polydata count {cmd.get_output_polydata_count()}")

        if cmd.get_output_polydata_count() == 0 :
            print("not intersected knife")
            return
        if cmd.get_output_polydata_count() == 1 :
            tpPolyData = algVTK.CVTK.create_poly_data_sphere(
                algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0]), 
                CComColonVesselCutting.s_tpRadius
            )
            cl = skeleton.get_centerline(cmd.OutputCLID)
            pos = cl.get_vertex(cmd.OutputVertexInx)
            color = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])
            id = len(self.m_listTPKey)

            # tpObj
            keyType = CComColonVesselCutting.s_tpType
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

            # whole vessel update
            vesselMesh = cmd.get_output_polydata(0)
            wholeVesselObj.PolyData = vesselMesh
        if cmd.get_output_polydata_count() > 1 :
            self.App.remove_key_type(CComColonVesselCutting.s_tpType)
            self.m_listTPKey.clear()

            if cmd.OutputWhole is None and cmd.OutputSub is None :
                wholePolydata = cmd.get_output_polydata(0)
                subPolydata = cmd.get_output_polydata(1)
            else :
                wholePolydata = cmd.OutputWhole
                subPolydata = cmd.OutputSub

            wholeVesselObj.PolyData = wholePolydata
            nowSubVesselID = self._getui_lv_vessel_node_count()
            key = data.CData.make_key(CComColonVesselCutting.s_subVesselType, 0, nowSubVesselID)
            subVesselObj = vtkObjInterface.CVTKObjInterface()
            subVesselObj.KeyType = CComColonVesselCutting.s_subVesselType
            subVesselObj.Key = key
            subVesselObj.Color = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 1.0])
            subVesselObj.Opacity = 0.5
            subVesselObj.PolyData = subPolydata
            dataInst.add_vtk_obj(subVesselObj)

            ret = self.__find_list_clID(subVesselObj.PolyData)
            if ret is None :
                print("not found sub vessel clID")
                return
            
            name = ret[0]
            if name == "" :
                name = "sub"
            listCLID = ret[1]

            node = CColonVesselNode()
            node.m_name = name
            node.m_subVesselKey = key
            node.m_listCLID = listCLID
            self._setui_lv_vessel_add_node(node)
            self._setui_lv_vessel_selection(node)
            self._command_selection_vessel(node)

        if self.signal_finished_knife is not None :
            self.signal_finished_knife()
    def command_label_name(self, labelName) :
        self._setui_lv_vessel_selection_name(labelName)

    def _command_selection_vessel(self, node : CColonVesselNode) :
        self.App.unref_key_type(CComColonVesselCutting.s_subVesselType)
        key = node.m_subVesselKey
        self.App.ref_key(key)
        self.App.update_viewer()




    
    # ui setting
    def _setui_lv_vessel_add_node(self, node : CColonVesselNode) :
        self.InputUILVVessel.blockSignals(True)

        item = QListWidgetItem(f"{node.m_name}")
        item.setData(Qt.UserRole, node)
        self.InputUILVVessel.addItem(item)

        self.InputUILVVessel.blockSignals(False)
    def _setui_lv_vessel_remove_node(self, node : CColonVesselNode) :
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
    def _setui_lv_vessel_selection(self, targetNode : CColonVesselNode) :
        count = self.InputUILVVessel.count()
        for i in range(count):
            item = self.InputUILVVessel.item(i)
            node = item.data(Qt.UserRole)
            if node == targetNode : 
                self.InputUILVVessel.setCurrentItem(item)
                item.setSelected(True)
                break
    def _setui_lv_vessel_selection_name(self, label : str) :
        item = self.InputUILVVessel.currentItem()
        if item is not None:
            item.setText(label)
            node = item.data(Qt.UserRole)
            if node is not None:
                node.m_name = label
    
    def _getui_lv_vessel_node_count(self) -> int :
        return self.InputUILVVessel.count()
    def _getui_lv_vessel_node(self, inx : int) -> CColonVesselNode :
        item = self.InputUILVVessel.item(inx)
        if item is not None :
            return item.data(Qt.UserRole)
        return None
    def _getui_lv_vessel_selection(self) -> CColonVesselNode :
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
        self._command_selection_vessel(node)


    # private
    def __find_list_clID(self, polydata : vtk.vtkPolyData) -> tuple :
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
            inCnt = commandVesselKnife.CCommandSepVessel.check_in_polydata(polydata, cl.Vertex)
            if inCnt > 1 :
                retList.append(cl.ID)
                retListName.append(cl.Name)
        
        if len(retList) == 0 :
            return None
        
        counter = Counter(retListName)
        mostCommon = counter.most_common(1)
        name = mostCommon[0][0]

        return (name, retList)
        


    @property
    def InputUILVVessel(self) -> QListWidget : 
        return self.m_inputUILVVessel
    @InputUILVVessel.setter
    def InputUILVVessel(self, inputUILVVessel : QListWidget) :
        self.m_inputUILVVessel = inputUILVVessel
    

if __name__ == '__main__' :
    pass


# print ("ok ..")

