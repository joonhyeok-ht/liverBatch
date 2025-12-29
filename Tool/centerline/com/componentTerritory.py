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
import dataGroup as dataGroup
import operation as operation
import component as component
import treeVessel as treeVessel
import clMask as clMask

import command.commandTerritory as commandTerritory

import vtkObjInterface as vtkObjInterface


class CComTerritory(component.CCom) :
    s_terriColor = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.6])


    def __init__(self, mediator) :
        super().__init__(mediator)

        self.m_organKey = ""
        self.m_clMask = None
        self.m_terriInfo = None
        self.m_terriGroup = None
    def clear(self) :
        self.m_organKey = ""
        if self.m_clMask is not None :
            self.m_clMask.clear()
            self.m_clMask = None
        self.m_terriInfo = None
        self.m_terriGroup = None
        super().clear()

    
    # override 
    def ready(self) -> bool :
        dataInst = self._get_data()
        if dataInst.Ready == False :
            return False 
        return True
    def process_init(self) :
        super().process_init()
        # input your code
    def process_end(self) :
        # input your code
        self.m_organKey = ""
        if self.m_clMask is not None :
            self.m_clMask.clear()
            self.m_clMask = None
        self.m_terriInfo = None
        if self.m_terriGroup is not None :
            self.m_terriGroup.clear()
        self.m_terriGroup = None

        self.App.remove_key_type(data.CData.s_territoryType)
        self.App.remove_key_type(data.CData.s_outsideKeyType)
        super().process_end()

    
    # command
    def command_changed_organ_name(self, organName : str, bShow : bool) -> bool :
        # opSelectionCL = self.m_opSelectionCL
        # opSelectionCL.process_reset()

        if self.ready() == False :
            return False
        
        dataInst = self._get_data()
        skeleton = self._get_skeleton()
        
        if self.m_organKey != "" :
            self.App.unref_key(self.m_organKey)
        self.App.remove_key_type(data.CData.s_outsideKeyType)
        self.App.remove_key_type(data.CData.s_territoryType)
        if self.m_clMask is not None :
            self.m_clMask.clear()
            self.m_clMask = None

        selectionOrganName = organName
        findTerriInx = dataInst.find_terriinfo_index_by_blender_name(selectionOrganName)
        self.m_terriInfo = dataInst.find_terriinfo_by_blender_name(selectionOrganName)
        self.m_organKey = data.CData.make_key(data.CData.s_organType, 0, findTerriInx)
        organObj = dataInst.find_obj_by_key(self.m_organKey)
        if organObj is None :
            print(f"not found organObj : {self.m_organKey}")
            return False

        # clMask setting
        self.m_clMask = clMask.CCLMask(organObj.PolyData)
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            self.m_clMask.attach_cl(cl)
        self.App.load_outside_key(self.m_clMask)
        self.command_show_organ(bShow)
        return True
    def command_show_organ(self, bShow : bool) -> bool :
        if self.ready() == False :
            return False
        
        if bShow == True :
            self.App.ref_key(self.m_organKey)
            self.App.ref_key_type(data.CData.s_outsideKeyType)
        else :
            self.App.unref_key(self.m_organKey)
            self.App.unref_key_type(data.CData.s_outsideKeyType)
        return True
    def command_do_territory(self) -> bool :
        if self.ready() == False :
            return False
        
        dataInst = self._get_data()
        clinfoInx = self._get_clinfoinx()
        skeleton = dataInst.get_skeleton(clinfoInx)

        self.App.remove_key_type(data.CData.s_territoryType)

        cmdTerritory = commandTerritory.CCommandMultiTerritoryLabel(self.App)
        cmdTerritory.InputData = dataInst
        cmdTerritory.InputSkeleton = skeleton
        cmdTerritory.InputTerriInfo = self.m_terriInfo
        cmdTerritory.InputCLMask = self.m_clMask
        cmdTerritory.process()

        if self.m_terriGroup is not None :
            self.m_terriGroup.clear()
            self.m_terriGroup = None
        self.m_terriGroup = cmdTerritory.OutputDataGroupPolyData

        listLabel = self.m_terriGroup.get_all_polydata_label()
        if listLabel is None :
            print("not found territory group label list")
            return False
        
        iCnt = self.m_terriGroup.get_polydata_label_count()
        for id in range(0, iCnt) :
            label = self.m_terriGroup.get_polydata_label(id)
            polyData = self.m_terriGroup.get_polydata(label)
            if polyData is None :
                continue
        
            key = data.CData.make_key(data.CData.s_territoryType, 0, id)
            terriObj = vtkObjInterface.CVTKObjInterface()
            terriObj.KeyType = data.CData.s_territoryType
            terriObj.Key = key
            terriObj.Color = CComTerritory.s_terriColor
            terriObj.Opacity = 0.5
            terriObj.PolyData = polyData
            dataInst.add_vtk_obj(terriObj)
        
        return True
    def command_show_territory(self, listCLID : list) :
        self.App.unref_key_type(data.CData.s_territoryType)
        if self.m_terriGroup is None :
            return
        
        skeleton = self._get_skeleton()
        for clID in listCLID :
            cl = skeleton.get_centerline(clID)
            label = cl.Name
            terriID = self.m_terriGroup.find_polydata_label_index(label)
            key = data.CData.make_key(data.CData.s_territoryType, 0, terriID)
            self.App.ref_key(key)
    

    # protected

    
    # event


    # property
    @property
    def OutputDataGroupPolyData(self) -> dataGroup.CDataGroupLabelingPolyData :
        return self.m_terriGroup





if __name__ == '__main__' :
    pass


# print ("ok ..")

