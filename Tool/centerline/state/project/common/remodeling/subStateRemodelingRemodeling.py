import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math
from scipy.spatial import KDTree

from PySide6.QtCore import Qt, QEvent, QObject, QPoint
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QMessageBox, QMenu
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


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjSphere as vtkObjSphere

import vtkObjGuideCL as vtkObjGuideCL

import data as data

import operation as operation

import subStateRemodeling as subStateRemodeling 

import com.componentSelectionCL as componentSelectionCL
from collections import Counter
import remodelingNode as remodelingNode


class SubNodeKeyFilter(QObject) :
    def __init__(self, cbDelete, cbEsc) :
        super().__init__()
        self.m_cbDelete = cbDelete
        self.m_cbEsc = cbEsc
    def eventFilter(self, obj, event) :
        if event.type() == QEvent.KeyPress :
            key = event.key()
            if key in (Qt.Key_Delete, Qt.Key_Backspace) :
                self.m_cbDelete()
                return True
            if key == Qt.Key_Escape :
                self.m_cbEsc()
                return True
        return super().eventFilter(obj, event)


class CSubStateRemodelingRemodeling(subStateRemodeling.CSubStateRemodeling) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_comDrag = None
        self.m_nameID = -1
    def clear(self) :
        # input your code
        if self.m_comDrag is not None :
            self.m_comDrag.clear()
            self.m_comDrag = None
        self.m_nameID = -1
        super().clear()

    def process_init(self) :
        self.m_mediator.m_lvCuttedNode.customContextMenuRequested.connect(self._on_lb_show_context_menu)
        self.m_mediator.setui_lv_anchor_remove_all()
        self.m_mediator.setui_lv_subnode_remove_all()

        self.m_mediator.m_lvAnchor.currentItemChanged.connect(self._on_lb_clicked_anchor)
        self.m_anchorKeyFilter = SubNodeKeyFilter(self._on_lb_clicked_anchor_delete, self._on_lb_clicked_anchor_esc)
        self.m_mediator.m_lvAnchor.installEventFilter(self.m_anchorKeyFilter)

        self.m_mediator.m_lvSubNode.currentItemChanged.connect(self._on_lb_clicked_subnode)
        self.m_subNodeKeyFilter = SubNodeKeyFilter(self._on_lb_clicked_subnode_delete, self._on_lb_clicked_subnode_esc)
        self.m_mediator.m_lvSubNode.installEventFilter(self.m_subNodeKeyFilter)

        self.m_mediator.setui_cb_missing_vessel(True)
        
        selectedNode = self.m_mediator.getui_lv_cuttednode_selected_node()
        self.__refresh_toggle_component(selectedNode)
        self.m_nameID = 0
    def process(self) :
        pass
    def process_end(self) :
        selectedNode = self.m_mediator.getui_lv_anchor_selected_node()
        if selectedNode is not None :
            self.m_mediator.swap_selected_cutting_node(selectedNode, None)
            self.m_mediator.setui_lv_anchor_clear_selection()

        self.m_nameID = -1
        self.m_mediator.m_lvCuttedNode.customContextMenuRequested.disconnect(self._on_lb_show_context_menu)
        self.m_mediator.setui_lv_anchor_remove_all()
        self.m_mediator.setui_lv_subnode_remove_all()

        self.m_mediator.m_lvAnchor.currentItemChanged.disconnect(self._on_lb_clicked_anchor)
        self.m_mediator.m_lvAnchor.removeEventFilter(self.m_anchorKeyFilter)
        self.m_anchorKeyFilter = None

        self.m_mediator.m_lvSubNode.currentItemChanged.disconnect(self._on_lb_clicked_subnode)
        self.m_mediator.m_lvSubNode.removeEventFilter(self.m_subNodeKeyFilter)
        self.m_subNodeKeyFilter = None

        self.m_mediator.setui_cb_missing_vessel(True)

        if self.m_comDrag is not None :
            self.m_comDrag.process_end()
            self.m_comDrag = None

    def clicked_mouse_rb(self, clickX, clickY) :
        if self.m_comDrag is None :
            return
        self.m_comDrag.click(clickX, clickY)
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        if self.m_comDrag is None :
            return
        self.m_comDrag.click_with_shift(clickX, clickY)
    def release_mouse_rb(self) :
        if self.m_comDrag is None :
            return
        if self.m_mediator.getui_rb_selection_single() == True :
            self.m_comDrag.ChildSelectionMode = False
        if self.m_mediator.getui_rb_selection_descendant() == True :
            self.m_comDrag.ChildSelectionMode = True
        self.m_comDrag.release(0, 0)
    def mouse_move(self, clickX, clickY) :
        pass
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_comDrag is None :
            return
        self.m_comDrag.move(clickX, clickY)
    def key_press(self, keyCode : str) :
        pass
    def key_press_with_ctrl(self, keyCode : str) :
        pass


    def changed_cutting_mesh(self, prevNode : remodelingNode.CRemodelingNode, nowNode : remodelingNode.CRemodelingNode) :
        self.__refresh_toggle_component(nowNode)
    def btn_select_minor(self, depth):
        cuttedNode = self.m_mediator.getui_lv_cuttednode_selected_node()
        
        portalSegmentSet = set()
        for i in range(1, 9):
            portalSegmentSet.add(str("S" + str(i)))
            
        veinSegmentSet = set(["LHV", "MHV", "RHV", "IHV"])
        skeletonEn = cuttedNode.SkeletonEn
        
        dataInst = self.m_mediator.get_data()
        skeleton = dataInst.get_skeleton(self.m_mediator.get_clinfo_index())
        
        self.copy_skeleton_cl_label(skeletonEn, skeleton)
        
        if "Portal" in cuttedNode.Name:
            self.m_comDrag._select_minor_vessel(skeletonEn, depth, portalSegmentSet)
        elif "Vein" in cuttedNode.Name:
            self.m_comDrag._select_minor_vessel(skeletonEn, depth, veinSegmentSet)
        else:
            self.m_comDrag._select_minor_vessel(skeletonEn, depth, [])
            
    def btn_minor_score(self):
        cuttedNode = self.m_mediator.getui_lv_cuttednode_selected_node()
        skeletonEn = cuttedNode.SkeletonEn
        self.m_comDrag._check_minor_score(skeletonEn)
            
    def copy_skeleton_cl_label(self, skeletonEn, skeleton):
        
        clNearestCount = {i:[] for i in range(skeletonEn.get_centerline_count())}
        
        for i, v in enumerate(skeletonEn.m_listKDTreeAnchor):
            mainCL = skeleton.find_nearest_centerline(v.reshape(1, 3))
            clNearestCount[skeletonEn.m_listKDTreeAnchorID[i]].append(mainCL.Name)
        
        for ci in range(skeletonEn.get_centerline_count()):
            enCL = skeletonEn.get_centerline(ci)
            enCL.Name = Counter(clNearestCount[enCL.ID]).most_common(1)[0][0]
        
        
    def btn_attach_centerline(self) :
        if self.m_nameID == -1 :
            return
        if self.m_comDrag is None :
            return
        
        cuttedNode = self.m_mediator.getui_lv_cuttednode_selected_node()
        if cuttedNode is None :
            QMessageBox.information(self.App, "Alarm", f"Please Select Cutted Mesh Item")
            return
        retListCLID = self.m_comDrag.get_selection_clid()
        if retListCLID is None :
            QMessageBox.information(self.App, "Alarm", f"Please Select Centerline")
            return
        if len(retListCLID) == 0 :
            QMessageBox.information(self.App, "Alarm", f"Please Select Centerline")
            return
        retListRootCL = cuttedNode.SkeletonEn.find_root_cl(retListCLID)
        if len(retListRootCL) != 1 :
            QMessageBox.information(self.App, "Alarm", f"Must be 1")
            return
        
        name = f"skel_{self.m_nameID}"
        skelNode = remodelingNode.CSkelNode()
        skelNode.Name = name
        skelNode.RemodelingNode = cuttedNode
        skelNode.add_clid_list(retListCLID)
        self.m_mediator.setui_lv_subnode_add_node(skelNode)
        inx = self.m_mediator.getui_lv_subnode_find_index(skelNode)
        if inx > -1 :
            self.m_mediator.setui_lv_subnode_selection_inx(inx)

        self.m_nameID += 1
    def btn_refresh_centerline(self) :
        if self.m_comDrag is None :
            return
        
        selectedNode = self.m_mediator.getui_lv_subnode_selected_node()
        if selectedNode is None :
            QMessageBox.information(self.App, "Alarm", f"Please Select Skel-Node Item")
            return
        
        retListCLID = self.m_comDrag.get_selection_clid()
        if retListCLID is None :
            QMessageBox.information(self.App, "Alarm", f"Please Select Centerline")
            return
        if len(retListCLID) == 0 :
            QMessageBox.information(self.App, "Alarm", f"Please Select Centerline")
            return
        retListRootCL = selectedNode.RemodelingNode.SkeletonEn.find_root_cl(retListCLID)
        if len(retListRootCL) != 1 :
            QMessageBox.information(self.App, "Alarm", f"Must be 1")
            return
        
        selectedNode.clear_clid()
        selectedNode.add_clid_list(retListCLID)



    # protected
    def _on_lb_show_context_menu(self, pos) :
        item = self.m_mediator.m_lvCuttedNode.itemAt(pos)
        if item is None :
            return

        # 메뉴 생성
        menu = QMenu()
        action_attachAnchor = menu.addAction("Attach Anchor")
        # action_attachSub = menu.addAction("Attach Sub")
        action_addCL = menu.addAction("Add Centerline")
        
        # 액션 선택 처리
        action = menu.exec(self.m_mediator.m_lvCuttedNode.mapToGlobal(pos))
        if action == action_attachAnchor :
            self.m_mediator.command_attach_anchor()
        elif action == action_addCL :
            self.m_mediator.command_add_skelinfo()
    def _on_lb_clicked_anchor(self, item, prevItem) :
        prevNode = self.m_mediator.getui_lv_cuttednode_selected_node()
        if prevNode is None :
            if prevItem is not None :
                prevNode = prevItem.data(Qt.UserRole)
        nowNode = None 
        if item is not None :
            nowNode = item.data(Qt.UserRole)
        self.m_mediator.swap_selected_cutting_node(prevNode, nowNode)
        self.m_mediator.setui_lv_cuttednode_clear_selection()
        self.__refresh_toggle_component(None)
        self.App.update_viewer()
    def _on_lb_clicked_anchor_delete(self) :
        selectedNode = self.m_mediator.getui_lv_anchor_selected_node()
        if selectedNode is None :
            return 
        self.m_mediator.swap_selected_cutting_node(selectedNode, None)
        self.m_mediator.setui_lv_anchor_remove(selectedNode)
        self.App.update_viewer()
    def _on_lb_clicked_anchor_esc(self) :
        selectedNode = self.m_mediator.getui_lv_anchor_selected_node()
        if selectedNode is None :
            return 
        self.m_mediator.swap_selected_cutting_node(selectedNode, None)
        self.m_mediator.setui_lv_anchor_clear_selection()
        self.App.update_viewer()
    def _on_lb_clicked_subnode(self, item, prevItem) :
        nowNode = None
        if item is not None :
            nowNode = item.data(Qt.UserRole)
        
        if nowNode is not None :
            cuttingNode = nowNode.RemodelingNode
            prevCuttingNode = self.m_mediator.getui_lv_anchor_selected_node()

            if prevCuttingNode is not None :
                self.m_mediator.setui_lv_anchor_clear_selection()
            else :
                prevCuttingNode = self.m_mediator.getui_lv_cuttednode_selected_node()

            inx = self.m_mediator.getui_lv_cuttednode_find_index_by_name(cuttingNode.Name)
            if inx >= 0 :
                self.m_mediator.setui_lv_cuttednode_selection_inx(inx)
            self.m_mediator.swap_selected_cutting_node(prevCuttingNode, cuttingNode)
            self.__refresh_toggle_component(cuttingNode)

            iCnt = nowNode.get_clid_count()
            retListCLID = []
            for inx in range(0, iCnt) :
                clid = nowNode.get_clid(inx)
                retListCLID.append(clid)
            
            self.m_comDrag.set_toggle_selection_clid(retListCLID)
        self.App.update_viewer()
    def _on_lb_clicked_subnode_delete(self) :
        selectedNode = self.m_mediator.getui_lv_subnode_selected_node()
        if selectedNode is None :
            return 
        self.m_mediator.setui_lv_subnode_remove_node(selectedNode)
        if self.m_comDrag is not None :
            self.m_comDrag.set_toggle_selection_clid([])
        self.App.update_viewer()
    def _on_lb_clicked_subnode_esc(self) :
        self.m_mediator.setui_lv_subnode_clear_selection()
        if self.m_comDrag is not None :
            self.m_comDrag.set_toggle_selection_clid([])
        self.App.update_viewer()

    
    # private
    def __refresh_toggle_component(self, cuttedNode : remodelingNode.CRemodelingNode) :
        if self.m_comDrag is not None :
            self.m_comDrag.process_end()
            self.m_comDrag = None

        if cuttedNode is None :
            return
        if cuttedNode.SkelGroupID < 0 :
            return
        if cuttedNode is not None and cuttedNode.SkelGroupID >= 0 :
            self.m_comDrag = componentSelectionCL.CComDragSkelCL(self.m_mediator)
            self.m_comDrag.InputSkeleton = cuttedNode.SkeletonEn
            self.m_comDrag.InputSkelGroupID = cuttedNode.SkelGroupID
            self.m_comDrag.process_init()
            self.m_comDrag.m_enSkeleton = True



if __name__ == '__main__' :
    pass


# print ("ok ..")

