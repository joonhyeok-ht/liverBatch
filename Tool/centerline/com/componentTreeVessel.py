import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

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

import data as data
import operation as operation
import component as component
import treeVessel as treeVessel


class CComTreeVessel(component.CCom) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        self.m_inputUITVVessel = None
        self.m_treeVessel = None

        self.signal_vessel_hierarchy = None # (self, listCLID : list)
        self.signal_vessel_hierarchy_node = None # (self, listCLID : list, listNode : list)
    def clear(self) :
        self.signal_vessel_hierarchy = None
        self.signal_vessel_hierarchy_node = None # (self, listCLID : list, listNode : list)

        self.m_inputUITVVessel = None
        if self.m_treeVessel is not None :
            self.m_treeVessel.clear()
            self.m_treeVessel = None
        super().clear()

    
    # override 
    def ready(self) -> bool :
        if self.InputUITVVessel is None :
            return False
        return True
    def process_init(self) :
        super().process_init()
        # input your code
        skeleton = self._get_skeleton()
        self.m_treeVessel = treeVessel.CTreeVessel(skeleton)
        self.command_init_tree_vessel()
    def process_end(self) :
        # input your code
        if self.m_treeVessel is not None :
            self.m_treeVessel.clear()
        self.m_treeVessel = None
        
        if self.InputUITVVessel.model() is not None :
            self.InputUITVVessel.model().clear()

        self.signal_vessel_hierarchy = None
        self.signal_vessel_hierarchy_node = None

        super().process_end()


    def command_init_tree_vessel(self) -> bool :
        if self.ready() == False :
            return False
        
        skeleton = self._get_skeleton()
        rootID = skeleton.RootCenterline.ID
        self.m_treeVessel.clear_node()
        self.m_treeVessel.build_tree_with_label(rootID)

        firstRootNode = self.m_treeVessel.get_first_root_node()
        if firstRootNode is None :
            return False
        
        clLabel = self.m_treeVessel.get_cl_label(firstRootNode)
        
        # 빈 모델 생성
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(['Vessel Hierarchy'])

        # 항목 추가
        parentItem = QStandardItem(clLabel)
        parentItem.setData(firstRootNode, Qt.UserRole)
        self._setui_tree_vessel(firstRootNode, parentItem)

        # 모델에 루트 아이템 추가
        model.appendRow(parentItem)
        self.InputUITVVessel.setModel(model)
        self.InputUITVVessel.selectionModel().selectionChanged.connect(self._on_tv_vessel_selection_changed)
        self.InputUITVVessel.expandAll()

        return True
    def command_clear_selection(self) -> bool :
        if self.ready() == False :
            return False
        self.InputUITVVessel.clearSelection()
        return True
    

    # protected
    def _setui_tree_vessel(self, node : treeVessel.CNodeVesselHier, item : QStandardItem) :
        iCnt = node.get_child_node_count()
        for inx in range(0, iCnt) :
            childNode = node.get_child_node(inx)
            clLabel = self.m_treeVessel.get_cl_label(childNode)

            childItem = QStandardItem(clLabel)
            childItem.setData(childNode, Qt.UserRole)
            item.appendRow(childItem)
            self._setui_tree_vessel(childNode, childItem)

    
    # event
    def _on_tv_vessel_selection_changed(self, selected: QItemSelection, deselected: QItemSelection) :
        model = self.InputUITVVessel.model()
        modifiers = QApplication.keyboardModifiers()
        if not modifiers & Qt.ShiftModifier :
            indexes = selected.indexes()
            if indexes :
                self.InputUITVVessel.selectionModel().blockSignals(True)
                last_index = indexes[-1]
                self.InputUITVVessel.selectionModel().clearSelection()
                self.InputUITVVessel.selectionModel().select(
                    last_index,
                    QItemSelectionModel.Select | QItemSelectionModel.Current
                )
                self.InputUITVVessel.selectionModel().blockSignals(False)
        # 선택된 항목 출력 예시
        selected_indexes = self.InputUITVVessel.selectedIndexes()
        selectedItems = [model.itemFromIndex(idx) for idx in selected_indexes if idx.column() == 0]

        listRet = []
        listRetNode = []

        for item in selectedItems :
            node = item.data(Qt.UserRole)
            listRetNode.append(node)

            iCnt = node.get_clID_count()
            for inx in range(0, iCnt) :
                clID = node.get_clID(inx)
                listRet.append(clID)
        
        if self.signal_vessel_hierarchy is not None :
            self.signal_vessel_hierarchy(listRet)
        if self.signal_vessel_hierarchy_node is not None :
            self.signal_vessel_hierarchy_node(listRet, listRetNode)



    @property
    def InputUITVVessel(self) :
        return self.m_inputUITVVessel
    @InputUITVVessel.setter
    def InputUITVVessel(self, inputUITVVessel) :
        self.m_inputUITVVessel = inputUITVVessel
    @property
    def TreeVessel(self) -> treeVessel.CTreeVessel :
        return self.m_treeVessel




if __name__ == '__main__' :
    pass


# print ("ok ..")

