import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
from matplotlib import cm

from scipy.spatial import KDTree

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QListWidgetItem, QMessageBox, QAbstractItemView, QTableWidget, QTableWidgetItem, QHeaderView
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


import data as data

import operation as operation

import tabState as tabState

import state.project.liver.userDataLiver as userDataLiver

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideMeshBound as vtkObjGuideMeshBound

import command.commandTerritory as commandTerritory

import componentLiverVesselCutting as componentLiverVesselCutting


class CListVessel :
    def __init__(self) :
        '''
        value = [(blenderName : str, vesselKey : str, clKey : str), .. ]
        '''
        self.m_listInfo = []
    def clear(self) :
        self.m_listInfo.clear()

    def add_info(self, blenderName, key : str = "", clKey : str = "") :
        self.m_listInfo.append((blenderName, key, clKey))
    def get_info_count(self) -> int :
        return len(self.m_listInfo)
    def get_blender_name(self, inx : int) -> str :
        return self.m_listInfo[inx][0]
    def get_vessel_key(self, inx : int) -> str :
        return self.m_listInfo[inx][1]
    def get_cl_key(self, inx : int) -> str :
        return self.m_listInfo[inx][2]
class CCmdData :
    def __init__(self) :
        self.m_selectionInx = -1
        self.m_polydata = None
    def clear(self) :
        self.m_selectionInx = -1
        self.m_polydata = None



class CTabStateReg(tabState.CTabState) :
    s_editVesselType = "editVessel"
    s_editCLType = "editCL"
    s_colors = np.array(
            [
                [1.0, 0.0, 0.0],
                # [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],

                [1.0, 1.0, 0.0],
                [0.0, 1.0, 1.0],
                [1.0, 0.0, 1.0],

                [1.0, 1.0, 1.0],
                [0.0, 0.0, 0.0],
            ]
        )


    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_opSelectionCL = operation.COperationDragSelectionCL(mediator)
        self.m_vesselInfo = CListVessel()
        self.m_comVesselCutting = None
        self.m_listVesselRes = []   # [(vertex : np.ndarray, [spherePolyData0, .. ])]
        self.m_listCmd = []
    def clear(self) :
        # input your code
        self.m_comVesselCutting = None
        self.m_vesselInfo.clear()
        self.m_listVesselRes.clear()
        self.m_listCmd.clear()
        super().clear()

    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        if userData is None :
            return
        
        self.m_opSelectionCL.Skeleton = None
        self.m_comVesselCutting = componentLiverVesselCutting.CComLiverVesselCutting(self)
        self.m_comVesselCutting.signal_finished_knife = self.slot_finished_knife
        
        self.m_mediator.unref_key_type(dataInst.s_vesselType)
        self.m_mediator.unref_key_type(dataInst.s_skelTypeCenterline)
        
        self.setui_vessel_list_init()
        self.m_mediator.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        userData = self._get_userdata()
        if userData is None :
            return
        
        if self.m_opSelectionCL.Skeleton is not None :
            self.m_opSelectionCL.process_reset()
        if self.m_comVesselCutting is not None :
            self.m_comVesselCutting.clear()
            self.m_comVesselCutting = None
        
        for cmdData in self.m_listCmd :
            cmdData.clear()
        self.m_listCmd.clear()

        self.m_vesselInfo.clear()
        self.m_listVesselRes.clear()
        self.m_tableVessel.setRowCount(0)

        dataInst = self.get_data()
        self.m_mediator.remove_key_type(CTabStateReg.s_editVesselType)
        self.m_mediator.remove_key_type(CTabStateReg.s_editCLType)

        clinfoInx = dataInst.CLInfoIndex
        self.m_mediator.ref_key_type_groupID(dataInst.s_vesselType, clinfoInx)
        self.m_mediator.ref_key_type_groupID(dataInst.s_skelTypeCenterline, clinfoInx)

        self.m_mediator.update_viewer()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Vessel List --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        self.m_tableVessel = QTableWidget()
        self.m_tableVessel.setColumnCount(4)
        self.m_tableVessel.setHorizontalHeaderLabels(["BlenderName", "Visible", "Save", "Load"])
        self.m_tableVessel.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.m_tableVessel.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.m_tableVessel.setSelectionMode(QAbstractItemView.SingleSelection)
        tabLayout.addWidget(self.m_tableVessel)
        self.m_tableVessel.cellClicked.connect(self._on_clicked_vessel)


        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)


    def clicked_mouse_rb(self, clickX, clickY) :
        dataInst = self.get_data()
        if self.m_comVesselCutting is not None :
            selectionInx = self.getui_vessel_list_selection_index()
            vesselKey = self.m_vesselInfo.get_vessel_key(selectionInx)
            self.m_comVesselCutting.InputCLInfoInx = selectionInx
            self.m_comVesselCutting.InputEditVesselKey = vesselKey
            self.m_comVesselCutting.click(clickX, clickY)
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        self.m_mediator.update_viewer()
    def release_mouse_rb(self) :
        if self.m_comVesselCutting is not None :
            self.m_comVesselCutting.release(0, 0)
        self.m_mediator.update_viewer()
    def mouse_move_rb(self, clickX, clickY) :
        if self.m_comVesselCutting is not None :
            self.m_comVesselCutting.move(clickX, clickY)
        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        if keyCode == "Escape" :
            self.m_opSelectionCL.process_reset()
            self.m_mediator.update_viewer()
    def key_press_with_ctrl(self, keyCode : str) : 
        if keyCode == "z" :
            self._undo()

        
    # ui get/set
    def setui_vessel_list_init(self) :
        dataInst = self.get_data()
        self.m_tableVessel.setRowCount(0)

        clinfoCnt = dataInst.DataInfo.get_info_count()
        for clinfoInx in range(0, clinfoCnt) :
            clInfo = dataInst.DataInfo.get_clinfo(clinfoInx)
            skeleton = dataInst.get_skeleton(clinfoInx)

            # init vessel res
            self._add_vessel_res(skeleton)

            vesselKey = data.CData.make_key(dataInst.s_vesselType, clinfoInx, 0)
            vesselObj = dataInst.find_obj_by_key(vesselKey)

            blenderName = clInfo.get_input_blender_name()
            editVesselKey = self._create_edit_vessel_obj(clinfoInx, vesselObj.PolyData)
            editCLKey = self._create_edit_cl_obj(clinfoInx)

            self.m_vesselInfo.add_info(blenderName, editVesselKey, editCLKey)
            self._ref_edit_vessel(clinfoInx)
            self._ref_edit_vessel_cl(clinfoInx)

        self.m_tableVessel.setRowCount(self.m_vesselInfo.get_info_count())
        for row in range(0, self.m_vesselInfo.get_info_count()) :
            flag = Qt.ItemIsSelectable | Qt.ItemIsEnabled
            blenderName = self.m_vesselInfo.get_blender_name(row)
            vesselVisible = True

            # blenderName
            item = QTableWidgetItem(blenderName)
            item.setFlags(flag)
            self.m_tableVessel.setItem(row, 0, item)

            # vessel visible checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(vesselVisible)
            checkbox.stateChanged.connect(lambda state, row=row: self._on_clicked_vessel_visible(row, state))
            wrapper = QFrame()
            layout = QHBoxLayout(wrapper)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(checkbox)
            self.m_tableVessel.setCellWidget(row, 1, wrapper)

            button = QPushButton("save")
            button.clicked.connect(lambda checked=False, row=row: self._on_clicked_save(row))
            self.m_tableVessel.setCellWidget(row, 2, button)

            button = QPushButton("load")
            button.clicked.connect(lambda checked=False, row=row: self._on_clicked_load(row))
            self.m_tableVessel.setCellWidget(row, 3, button)

        if clinfoCnt > 0 :
            self.setui_vessel_list_selection(0)
    def setui_vessel_list_selection(self, inx : int) :
        self.m_tableVessel.selectRow(inx)
        self._on_clicked_vessel(0, 0)
    
    def getui_vessel_list_selection_index(self) -> int : 
        '''
        ret : -1 (non-selection)
        '''
        return self.m_tableVessel.currentRow()
        

    # protected
    def _get_userdata(self) -> userDataLiver.CUserDataLiver :
        return self.get_data().find_userdata(userDataLiver.CUserDataLiver.s_userDataKey)
    def _get_color(self, inx : int) -> np.ndarray :
        iCnt = CTabStateReg.s_colors.shape[0]
        return CTabStateReg.s_colors[inx % iCnt].reshape(-1, 3)
    
    def _add_vessel_res(self, skeleton : algSkeletonGraph.CSkeleton) :
        dataInst = self.get_data()
        vertex = None
        listPolyData = []

        if skeleton is None :
            self.m_listVesselRes.append((None, None))
            return

        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            if vertex is None :
                vertex = cl.Vertex.copy()
            else :
                vertex = np.vstack((vertex, cl.Vertex))
        
        clPtCnt = vertex.shape[0]
        for clPtInx in range(0, clPtCnt) :
            pos = vertex[clPtInx].reshape(-1, 3)
            polyData = algVTK.CVTK.create_poly_data_sphere(pos, dataInst.CLSize)
            listPolyData.append(polyData)
        
        self.m_listVesselRes.append((vertex, listPolyData))
    def _get_vessel_res_vertex_count(self, inx : int) -> int :
        vertex = self._get_vessel_res_vertex(inx)
        if vertex is None :
            return 0
        return vertex.shape[0]
    def _get_vessel_res_vertex(self, inx : int) -> np.ndarray :
        return self.m_listVesselRes[inx][0]
    def _get_vessel_res_polydata(self, inx : int, vertexInx : int) -> vtk.vtkPolyData :
        tupleData = self.m_listVesselRes[inx]
        listPolyData = tupleData[1]
        if listPolyData is None :
            return None
        return listPolyData[vertexInx]
    
    def _create_edit_vessel_obj(self, clinfoInx : int, polydata : vtk.vtkPolyData) -> str :
        '''
        ret : key
        '''
        dataInst = self.get_data()
        vertex = algVTK.CVTK.poly_data_get_vertex(polydata)
        index = algVTK.CVTK.poly_data_get_triangle_index(polydata)
        editVesselPolydata = algVTK.CVTK.create_poly_data_triangle(vertex.copy(), index.copy())

        key = data.CData.make_key(CTabStateReg.s_editVesselType, clinfoInx, 0)
        editVesselObj = vtkObjInterface.CVTKObjInterface()
        editVesselObj.KeyType = CTabStateReg.s_editVesselType
        editVesselObj.Key = key
        editVesselObj.Color = self._get_color(clinfoInx)
        editVesselObj.Opacity = 0.1
        editVesselObj.PolyData = editVesselPolydata
        dataInst.add_vtk_obj(editVesselObj)
        return key
    def _create_edit_cl_obj(self, clinfoInx : int) -> str :
        vertexCnt = self._get_vessel_res_vertex_count(clinfoInx)
        if vertexCnt == 0 :
            return ""
        
        appendFilter = vtk.vtkAppendPolyData()
        for inx in range(0, vertexCnt) :
            sphere = self._get_vessel_res_polydata(clinfoInx, inx)
            appendFilter.AddInputData(sphere)
        appendFilter.Update()
        polydata = appendFilter.GetOutput()

        dataInst = self.get_data()
        vertex = algVTK.CVTK.poly_data_get_vertex(polydata)
        index = algVTK.CVTK.poly_data_get_triangle_index(polydata)
        editCLPolydata = algVTK.CVTK.create_poly_data_triangle(vertex, index)

        key = data.CData.make_key(CTabStateReg.s_editCLType, clinfoInx, 0)
        editCLObj = vtkObjInterface.CVTKObjInterface()
        editCLObj.KeyType = CTabStateReg.s_editCLType
        editCLObj.Key = key
        editCLObj.Color = dataInst.CLColor
        editCLObj.Opacity = 1.0
        editCLObj.PolyData = editCLPolydata
        dataInst.add_vtk_obj(editCLObj)

        return key

    def _ref_edit_vessel(self, inx : int) :
        self.m_mediator.ref_key_type_groupID(CTabStateReg.s_editVesselType, inx)
    def _unref_edit_vessel(self, inx : int) :
        self.m_mediator.unref_key_type_groupID(CTabStateReg.s_editVesselType, inx)
    def _ref_edit_vessel_cl(self, inx : int) :
        self.m_mediator.ref_key_type_groupID(CTabStateReg.s_editCLType, inx)
    def _unref_edit_vessel_cl(self, inx : int) :
        self.m_mediator.unref_key_type_groupID(CTabStateReg.s_editCLType, inx)
    def _undo(self) :
        if len(self.m_listCmd) == 0 :
            return
        
        dataInst = self.get_data()
        cmdData = self.m_listCmd.pop()

        vesselKey = self.m_vesselInfo.get_vessel_key(cmdData.m_selectionInx)
        vesselObj = dataInst.find_obj_by_key(vesselKey)
        vesselObj.PolyData = cmdData.m_polydata
        vesselObj.Color = self._get_color(cmdData.m_selectionInx)

        self._command_refresh_cl(cmdData.m_selectionInx)
        self.m_mediator.update_viewer()

    # protected
    def _command_selection_vessel(self, clinfoInx : int) :
        dataInst = self.get_data()
        iCnt = self.m_vesselInfo.get_info_count()
        for inx in range(0, iCnt) :
            clKey = self.m_vesselInfo.get_cl_key(inx)
            if clKey == "" :
                return
            color = None
            if inx == clinfoInx :
                color = dataInst.SelectionCLColor
            else :
                color = dataInst.CLColor
            clObj = dataInst.find_obj_by_key(clKey)
            clObj.Color = color
    def _command_refresh_cl(self, clinfoInx : int) :
        clKey = self.m_vesselInfo.get_cl_key(clinfoInx)
        if clKey == "" :
            return
        
        dataInst = self.get_data()
        vesselKey = self.m_vesselInfo.get_vessel_key(clinfoInx)
        vesselObj = dataInst.find_obj_by_key(vesselKey)
        vesselPolyData = vesselObj.PolyData

        vertex = self._get_vessel_res_vertex(clinfoInx)
        listFlag = self.__check_inside(vesselPolyData, vertex)

        appendFilter = vtk.vtkAppendPolyData()
        for inx in range(0, vertex.shape[0]) :
            if listFlag[inx] == False :
                continue
            sphere = self._get_vessel_res_polydata(clinfoInx, inx)
            appendFilter.AddInputData(sphere)
        appendFilter.Update()
        polydata = appendFilter.GetOutput()
        # 일단 예외처리는 하지 말자.

        color = None 
        selectionInx = self.getui_vessel_list_selection_index()
        if clinfoInx == selectionInx :
            color = dataInst.SelectionCLColor
        else :
            color = dataInst.CLColor

        editCLObj = dataInst.find_obj_by_key(clKey)
        editCLObj.Color = color
        editCLObj.Opacity = 1.0
        editCLObj.PolyData = polydata

        
        


    # ui event 
    def _on_clicked_vessel(self, row, column) :
        blenderName = self.m_tableVessel.item(row, 0).text()
        self._command_selection_vessel(row)
        self.m_mediator.update_viewer()
    def _on_clicked_vessel_visible(self, row, state) :
        blenderName = self.m_tableVessel.item(row, 0).text()
        visible = (state == 2)
        if visible == True :
            self._ref_edit_vessel(row)
            self._ref_edit_vessel_cl(row)
        else :
            self._unref_edit_vessel(row)
            self._unref_edit_vessel_cl(row)
        self.m_mediator.update_viewer()
    def _on_clicked_save(self, row) :
        dataInst = self.get_data()
        terriOutPath = dataInst.get_terri_out_path()
        if os.path.exists(terriOutPath) == False :
            print(f"not found path : {terriOutPath}")
            return
        
        filePath, _ = QFileDialog.getSaveFileName(
            self.m_mediator,
            "Save STL File",
            os.path.join(terriOutPath, "vessel.stl"),  # 기본 폴더 + 기본 파일명
            "STL Files (*.stl)"
        )

        if filePath : 
            vesselKey = self.m_vesselInfo.get_vessel_key(row)
            vesselObj = dataInst.find_obj_by_key(vesselKey)
            algVTK.CVTK.save_poly_data_stl(filePath, vesselObj.PolyData)

            msg = QMessageBox(self.m_mediator)
            msg.setWindowTitle("알림")
            msg.setText("성공적으로 저장 되었습니다")
            msg.setIcon(QMessageBox.Information)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
    def _on_clicked_load(self, row) :
        dataInst = self.get_data()
        terriOutPath = dataInst.get_terri_out_path()
        if os.path.exists(terriOutPath) == False :
            print(f"not found path : {terriOutPath}")
            return
        
        filePath, _ = QFileDialog.getOpenFileName(
            self.m_mediator,
            "Load STL File",
            terriOutPath, 
            "STL Files (*.stl)"
        )

        if filePath : 
            polydata = algVTK.CVTK.load_poly_data_stl(filePath)
            vertex = algVTK.CVTK.poly_data_get_vertex(polydata)
            index = algVTK.CVTK.poly_data_get_triangle_index(polydata)
            polydata = algVTK.CVTK.create_poly_data_triangle(vertex, index)

            vesselKey = self.m_vesselInfo.get_vessel_key(row)
            vesselObj = dataInst.find_obj_by_key(vesselKey)
            vesselObj.PolyData = polydata
            self._command_refresh_cl(row)
            


    # private 
    def __check_inside(self, polydata : vtk.vtkPolyData, vertex : np.ndarray) -> list :
        '''
        ret : [True, False, ..] total : vertex.shape[0]
        '''
        retList = []
        testPt = vtk.vtkPoints()

        for inx in range(0, vertex.shape[0]) :
            testPt.InsertNextPoint(vertex[inx, 0], vertex[inx, 1], vertex[inx, 2])
        testPolyData = vtk.vtkPolyData()
        testPolyData.SetPoints(testPt)

        selEnPt = vtk.vtkSelectEnclosedPoints()
        selEnPt.SetSurfaceData(polydata)
        selEnPt.SetInputData(testPolyData)
        selEnPt.Update()

        for i in range(testPt.GetNumberOfPoints()) :
            bInside = selEnPt.IsInside(i)
            retList.append(bInside == 1)
        return retList


    # slot
    def slot_finished_knife(self, polydata : vtk.vtkPolyData) :
        vertex = algVTK.CVTK.poly_data_get_vertex(polydata)
        index = algVTK.CVTK.poly_data_get_triangle_index(polydata)
        polydata = algVTK.CVTK.create_poly_data_triangle(vertex, index)

        dataInst = self.get_data()
        selectionInx = self.getui_vessel_list_selection_index()

        vesselKey = self.m_vesselInfo.get_vessel_key(selectionInx)
        vesselObj = dataInst.find_obj_by_key(vesselKey)

        cmdData = CCmdData()
        cmdData.m_selectionInx = selectionInx
        cmdData.m_polydata = vesselObj.PolyData
        self.m_listCmd.append(cmdData)

        vesselObj.PolyData = polydata
        vesselObj.Color = self._get_color(selectionInx)

        self._command_refresh_cl(selectionInx)

        self.m_mediator.update_viewer()


if __name__ == '__main__' :
    pass


# print ("ok ..")

