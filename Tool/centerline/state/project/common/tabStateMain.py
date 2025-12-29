import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtCore import Qt, QItemSelectionModel, QModelIndex
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QTableView, QMessageBox
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


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.reconstruction as reconstruction

import VtkObj.vtkObj as vtkObj
import vtkObjInterface as vtkObjInterface

import command.commandInterface as commandInterface
import command.commandLoadingPatient as commandLoadingPatient
import command.commandExtractionCL as commandExtractionCL
import command.commandRecon as commandRecon

import state.project.userData as userData

import data as data
import operation as op

import tabState as tabState


class CTabStateMain(tabState.CTabState) :
    s_guideCellType = "guideCell"
    '''
    groupID : 0 고정
    ID : only 0, 1
    '''
    s_listStepName = [
        "Recon",
        "Centerline",
        "Clean",
    ]
    
    def __init__(self, mediator) :
        self.m_bReady = False
        self.m_listStepBtnEvent = [
            self._on_btn_recon,
            self._on_btn_centerline,
            self._on_btn_clean
        ]

        super().__init__(mediator)
        # input your code
        self.m_stateSelCell = 0
        self.m_selCellID = -1
        self.m_bReady = True
    def clear(self) :
        # input your code
        self.m_btnCL = None
        self.m_bReady = False
        self.m_stateSelCell = 0
        self.m_selCellID = -1
        super().clear()


    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            print("not setting patient path")
            return
        
        self.setui_clear_clinfo()
        iCnt = dataInst.get_skelinfo_count()
        for inx in range(0, iCnt) :
            skelinfo = dataInst.get_skelinfo(inx)
            self.setui_add_clinfo(inx, skelinfo)

        self.setui_clinfo_inx(dataInst.CLInfoIndex)
        self._command_clinfo_inx()
        self.setui_check_sel_cell(False)
    def process(self) :
        pass
    def process_end(self) :
        self.setui_check_sel_cell(False)

    def changed_project_type(self) :
        optionFullPath = os.path.join(self.m_mediator.FilePath, "option.json")
        if os.path.exists(optionFullPath) == False :
            optionFullPath = os.path.join(self.m_mediator.CommonPipelinePath, "option.json")
            if os.path.exists(optionFullPath) == False :
                optionFullPath = ""
        self._command_option_path(optionFullPath)


    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        # path ui
        label = QLabel("-- Path Info --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, self.m_editOptionPath, btn = self.m_mediator.create_layout_label_editbox_btn("Option", False, "..")
        btn.clicked.connect(self._on_btn_option_path)
        tabLayout.addLayout(layout)

        layout, self.m_editOutputPath, btn = self.m_mediator.create_layout_label_editbox_btn("Output", False, "..")
        btn.clicked.connect(self._on_btn_output_path)
        tabLayout.addLayout(layout)

        layout, self.m_cbPatientID = self.m_mediator.create_layout_label_combobox("PatientID")
        self.m_cbPatientID.currentIndexChanged.connect(self._on_cb_patientID_changed)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        label = QLabel("-- Reconstruction STEP --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, btnList = self.m_mediator.create_layout_btn_array(CTabStateMain.s_listStepName)
        for inx, stepName in enumerate(CTabStateMain.s_listStepName) :
            btnList[inx].clicked.connect(self.m_listStepBtnEvent[inx])
        tabLayout.addLayout(layout)
        self.m_btnCL = btnList[1]


        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        # centerline ui
        label = QLabel("-- Centerline --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        self.m_modelCLInfo = QStandardItemModel()
        self.m_modelCLInfo.setHorizontalHeaderLabels(["Index", "BlenderName", "Output"])
        self.m_tvCLInfo = QTableView()
        self.m_tvCLInfo.setModel(self.m_modelCLInfo)
        self.m_tvCLInfo.setEditTriggers(QTableView.NoEditTriggers)
        self.m_tvCLInfo.horizontalHeader().setStretchLastSection(True)
        self.m_tvCLInfo.verticalHeader().setVisible(False)
        self.m_tvCLInfo.setSelectionBehavior(QTableView.SelectRows)
        self.m_tvCLInfo.clicked.connect(self._on_tv_clicked_clinfo)
        tabLayout.addWidget(self.m_tvCLInfo)

        self.m_checkSelectionStartCell = QCheckBox("Selection Start Cell ")
        self.m_checkSelectionStartCell.setChecked(False)
        self.m_checkSelectionStartCell.stateChanged.connect(self._on_check_sel_cell)
        tabLayout.addWidget(self.m_checkSelectionStartCell)

        layout = QHBoxLayout()
        label = QLabel("CellID ")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.m_editBoxCellID = QLineEdit()
        layout.addWidget(self.m_checkSelectionStartCell)
        layout.addWidget(label)
        layout.addWidget(self.m_editBoxCellID)
        tabLayout.addLayout(layout)


        btn = QPushButton("Extraction Centerline")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_extraction_centerline)
        tabLayout.addWidget(btn)


        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)

    
    def clicked_mouse_rb(self, clickX, clickY) :
        if self.m_stateSelCell == 0 : 
            return
        
        guideCell = self.__get_guide_cell_obj(0)
        polyData = guideCell.PolyData
        if polyData is None :
            return
        
        guideCell = self.__get_guide_cell_obj(1)
        guideCell.PolyData = polyData
        
        self.setui_cellID(self.m_selCellID)
        self.m_mediator.update_viewer()
    def mouse_move(self, clickX, clickY) :
        # vessel과 마우스와의 picking 수행
        # 가장 가까운 cell을 찾음
        # cell의 중심 vertex를 guideEPKey에 세팅 
        listExceptKeyType = [
            data.CData.s_skelTypeCenterline,
            CTabStateMain.s_guideCellType,
        ]

        if self.m_stateSelCell == 0 : 
            return

        self.m_selCellID = self.m_mediator.picking_cellid(clickX, clickY, listExceptKeyType)
        if self.m_selCellID <= 0 :
            return

        if self.m_selCellID > 0 :
            dataInst = self.get_data()
            clinfoInx = self.getui_clinfo_inx()

            vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
            vesselObj = dataInst.find_obj_by_key(vesselKey)
            if vesselObj is None :
                return
            vesselPolyData = vesselObj.PolyData

            pickedPoly = algVTK.CVTK.get_sub_polydata_by_face_fast(vesselPolyData, [self.m_selCellID])
            retPoly = vtk.vtkPolyData()
            retPoly.DeepCopy(pickedPoly)
            guideCell = self.__get_guide_cell_obj(0)
            guideCell.PolyData = retPoly
        self.m_mediator.update_viewer()


    def setui_patientID(self, inx : int) :
        self.m_cbPatientID.blockSignals(True)
        self.m_cbPatientID.setCurrentIndex(inx)
        self.m_cbPatientID.blockSignals(False)

        patientID = self.getui_patientID()
        self.m_mediator.set_title(patientID)
    def setui_reset_patientID(self, listPatientID : str) :
        self.m_cbPatientID.blockSignals(True)
        self.m_cbPatientID.clear()
        for patientID in listPatientID :
            self.m_cbPatientID.addItem(f"{patientID}")
        self.m_cbPatientID.blockSignals(False)
        self.setui_patientID(0)
    def setui_output_path(self, outputPath : str) :
        self.m_editOutputPath.setText(outputPath)
    def setui_clear_clinfo(self) :
        self.m_tvCLInfo.blockSignals(True)
        self.m_modelCLInfo.removeRows(0, self.m_modelCLInfo.rowCount())
        self.m_tvCLInfo.blockSignals(False)
    def setui_add_clinfo(self, inx : int, skelinfo : data.CSkelInfo) :
        blenderName = skelinfo.BlenderName
        jsonName = skelinfo.JsonName
        self.m_tvCLInfo.blockSignals(True)
        self.m_modelCLInfo.appendRow([QStandardItem(f"{inx}"), QStandardItem(blenderName), QStandardItem(jsonName)])
        self.m_tvCLInfo.blockSignals(False)
    def setui_clinfo_inx(self, inx : int) :
        QIndex = self.m_modelCLInfo.index(inx, 0)
        if not QIndex.isValid() :
            return
        
        self.m_tvCLInfo.blockSignals(True)
        self.m_tvCLInfo.selectionModel().clearSelection()  # 기존 선택 지우기
        self.m_tvCLInfo.selectionModel().select(
            QIndex, 
            QItemSelectionModel.Select | QItemSelectionModel.Rows
        )
        self.m_tvCLInfo.setCurrentIndex(QIndex)
        self.m_tvCLInfo.blockSignals(False)
    def setui_cellID(self, cellID : int) :
        self.m_editBoxCellID.setText(str(cellID))
    def setui_check_sel_cell(self, bCheck : bool) -> bool :
        self.m_checkSelectionStartCell.setChecked(bCheck)

    def getui_patientID(self) -> str :
        return self.m_cbPatientID.currentText()
    def getui_output_path(self) -> str :
        return self.m_editOutputPath.text()
    def getui_clinfo_inx(self) -> int :
        '''
        ret : clinfoInx
                -1 : non-selection
        '''
        selectedIndex = self.m_tvCLInfo.selectionModel().selectedIndexes()
        if selectedIndex :
            row = selectedIndex[0].row()
            index = int(self.m_modelCLInfo.item(row, 0).text())
            return index
        return -1
    def getui_clinfo_blenderName(self) -> str :
        '''
        ret : clinfo blenderName
                "" : non-selection
        '''
        selectedIndex = self.m_tvCLInfo.selectionModel().selectedIndexes()
        if selectedIndex :
            row = selectedIndex[0].row()
            blenderName = self.m_modelCLInfo.item(row, 1).text()
            return blenderName
        return ""
    def getui_clinfo_output(self) -> str :
        '''
        ret : clinfo output
                "" : non-selection
        '''
        selectedIndex = self.m_tvCLInfo.selectionModel().selectedIndexes()
        if selectedIndex :
            row = selectedIndex[0].row()
            output = self.m_modelCLInfo.item(row, 2).text()
            return output
        return ""
    def getui_check_sel_cell(self) -> bool :
        if self.m_checkSelectionStartCell.isChecked() :
            return True
        return False
    def getui_cellID(self) -> int :
        cellID = -1
        try :
            cellID = int(self.m_editBoxCellID.text())
        except ValueError:
            cellID = -1
        return cellID

    # command
    def _command_option_path(self, optionFullPath : str) :
        # 기존 ui reset
        # optionInfo loading 

        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_patient()

        self.m_editOptionPath.setText(optionFullPath)
        self.setui_clear_clinfo()
        self.setui_reset_patientID([])
        self.setui_output_path("")

        if os.path.exists(optionFullPath) == False :
            QMessageBox.information(self.m_mediator, "Alarm", "not found option file")
            self.m_editOptionPath.setText("")
            dataInst.OptionInfo = None
            return
        
        optionInfoInst = optionInfo.COptionInfo(optionFullPath)
        dataInst.OptionInfo = optionInfoInst

        self.m_mediator.update_viewer()
    def _command_output_path(self, outputPath : str) :
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_patient()

        dataInst.PatientID = ""
        dataInst.OutputPath = ""

        self.setui_output_path("")
        self.setui_clear_clinfo()
        self.setui_reset_patientID([])

        optionInfoInst = self.get_optioninfo()
        if optionInfoInst is None :
            QMessageBox.information(self.m_mediator, "Alarm", "not found valid option")
            return

        self.setui_output_path(outputPath)

        # patient info refresh 
        retList = []

        optionInfoInst = self.get_optioninfo()
        if os.path.exists(optionInfoInst.DataRootPath) : 
            listTmp = os.listdir(optionInfoInst.DataRootPath)
            for patientID in listTmp :
                patientFullPath = os.path.join(optionInfoInst.DataRootPath, patientID)
                patientMaskFullPath = os.path.join(patientFullPath, "Mask")
                if os.path.exists(patientMaskFullPath) == True :
                    retList.append(patientID)

        if os.path.exists(outputPath) == True :
            listTmp = os.listdir(outputPath)
            for patientID in listTmp :
                patientFullPath = os.path.join(outputPath, patientID)
                reconBlendFullPath = os.path.join(patientFullPath, f"{patientID}_recon.blend")
                if os.path.exists(reconBlendFullPath) == True :
                    retList.append(patientID)

        # 중복되지 않게 한다.
        retList = list(set(retList))
        self.setui_reset_patientID(retList)

        dataInst.OutputPath = self.getui_output_path()
        dataInst.PatientID = self.getui_patientID()
        self.m_mediator.set_title(dataInst.PatientID)

        self.m_mediator.update_viewer()
    def _command_patientID(self) :
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_patient()

        dataInst.PatientID = self.getui_patientID()
        self.m_mediator.set_title(dataInst.PatientID)
        self.m_mediator.update_viewer()
    def _command_centerline(self) :
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_patient()

        if dataInst.Ready == False :
            QMessageBox.information(self.m_mediator, "Alarm", "please setting option, outputPath, patientID")
            return

        patientID = dataInst.PatientID
        outputPatientPath = dataInst.OutputPatientPath
        blenderFullPath = os.path.join(outputPatientPath, f"{patientID}_recon.blend")

        if os.path.exists(blenderFullPath) == False :
            QMessageBox.information(self.m_mediator, "Alarm", f"not found {os.path.basename(blenderFullPath)}")
            return

        cmd = commandLoadingPatient.CCommandLoadingPatient(self.m_mediator)
        cmd.InputData = dataInst
        cmd.PatientBlenderFullPath = blenderFullPath
        cmd.process()
        self.m_mediator.load_userdata()

        self.setui_clear_clinfo()
        iCnt = dataInst.get_skelinfo_count()
        for inx in range(0, iCnt) :
            skelinfo = dataInst.get_skelinfo(inx)
            self.setui_add_clinfo(inx, skelinfo)

        dataInst.CLInfoIndex = 0
        self.setui_clinfo_inx(dataInst.CLInfoIndex)
        self._command_clinfo_inx()

        fullPath = os.path.join(dataInst.OutputPatientPath, f"{data.CData.s_fileName}.json")
        dataInst.save(fullPath)

        self.m_btnCL.setEnabled(False)
    def _command_clinfo_inx(self) :
        dataInst = self.get_data()
        self.m_mediator.unref_all_key()

        clinfoinx = dataInst.CLInfoIndex
        skelinfo = dataInst.get_skelinfo(clinfoinx)
        skeleton = skelinfo.Skeleton

        self.m_mediator.ref_key_type_groupID(dataInst.s_vesselType, clinfoinx)
        if skeleton is not None :
            self.m_mediator.ref_key_type_groupID(dataInst.s_skelTypeCenterline, clinfoinx)
        
        self.setui_check_sel_cell(False)
        
        self.m_mediator.update_viewer()
    def _command_extraction_cl(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            print("not setting patient path")
            return
        clOutPath = dataInst.get_cl_out_path()
        if os.path.exists(clOutPath) == False :
            print("not found clOutPath")
            return 
        clInPath = dataInst.get_cl_in_path()
        if os.path.exists(clInPath) == False :
            print("not found clInPath")
            return 
        
        clinfoinx = dataInst.CLInfoIndex
        self.m_mediator.remove_skeleton_obj(clinfoinx)

        skelinfo = dataInst.get_skelinfo(clinfoinx)
        vtpName = skelinfo.BlenderName

        # centerline 시작 cell이 있으므로 현재 vessel polydata를 vtp로 저장. 
        startCellID = self.getui_cellID()
        if startCellID < 0 :
            startCellID = 0

        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoinx, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey)
        if vesselObj is None :
            print("not found vessel polydata")
            return

        vesselPolyData = vesselObj.PolyData
        vtpFullPath = os.path.join(clInPath, f"{vtpName}.vtp")
        algVTK.CVTK.save_poly_data_vtp(vtpFullPath, vesselPolyData)

        cmd = commandExtractionCL.CCommandExtractionCL(self.m_mediator)
        cmd.InputData = dataInst
        cmd.InputIndex = clinfoinx
        cmd.InputVTPName = vtpName
        cmd.InputCellID = startCellID
        cmd.InputEn = 0
        cmd.process()

        clOutputFullPath = os.path.join(clOutPath, f"{vtpName}.json")
        if os.path.exists(clOutputFullPath) == False :
            print(f"not found skelinfo : {clOutputFullPath}")
            return 
        
        skeleton = algSkeletonGraph.CSkeleton()
        skeleton.load(clOutputFullPath)
        skelinfo.Skeleton = skeleton
        self.m_mediator.add_skeleton_obj(clinfoinx)

        self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoinx)
        self.m_mediator.update_viewer()

        # QMessageBox.information(self.m_mediator, "Alarm", f"completed extracting centerline")

    # protected 

    
    # ui event 
    def _on_btn_option_path(self) :
        self.m_btnCL.setEnabled(True)

        optionPath, _ = QFileDialog.getOpenFileName(self.get_main_widget(), "Select Option File", "", "JSON Files (*.json)")
        if optionPath == "" :
            return
        
        self._command_option_path(optionPath)
    def _on_btn_output_path(self) :
        self.m_btnCL.setEnabled(True)

        outputPath = QFileDialog.getExistingDirectory(self.get_main_widget(), "Selection Output Path")
        self._command_output_path(outputPath)
    def _on_btn_recon(self) :
        if self.getui_patientID() == "" :
            print("not selection patientID")
            return
        if self.getui_output_path() == "" :
            print("not setting output path")
            return 
        
        userData = self.m_mediator.ReconUserData
        if userData is not None :
            userData.override_recon()
            QMessageBox.information(self.m_mediator, "Alarm", f"completed reconstruction")
        else :
            QMessageBox.information(self.m_mediator, "Alarm", f"failed reconstruction")
    def _on_btn_centerline(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            print("not setting option, outputPath, patientID")
            return
        self._command_centerline()
    def _on_btn_clean(self) :
        if self.getui_patientID() == "" :
            print("not selection patientID")
            return
        if self.getui_output_path() == "" :
            print("not setting output path")
            return 
        
        userData = self.m_mediator.ReconUserData
        if userData is not None :
            userData.override_clean()
        
    def _on_cb_patientID_changed(self, index) :
        self.m_btnCL.setEnabled(True)

        patientID = self.getui_patientID()
        if patientID == "" :
            print("not selection patientID")
            return
        self._command_patientID()
    def _on_tv_clicked_clinfo(self, index) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        clinfoInx = self.getui_clinfo_inx()
        if clinfoInx == -1 :
            return
        dataInst.CLInfoIndex = clinfoInx
        self._command_clinfo_inx()
    def _on_check_sel_cell(self, state) :
        '''
        state
            - 0 : unchecked
            - 1 : partially checked
            - 2 : checked
        '''
        if state == 2 :
            bCheck = True
            self.__set_selcellstate(1)
        else :
            bCheck = False
            self.__set_selcellstate(0)
    def _on_btn_extraction_centerline(self) :
        self._command_extraction_cl()
        

    # private
    def __set_selcellstate(self, state : int) :
        # state exit
        if self.m_stateSelCell >= 0 :
            if self.m_stateSelCell == 0 :
                pass
            else :
                self.m_mediator.remove_key_type(CTabStateMain.s_guideCellType)

        self.m_stateSelCell = state
        self.setui_cellID(-1)
        self.m_selCellID = -1

        # state start
        if self.m_stateSelCell >= 0 :
            if self.m_stateSelCell == 0 :
                pass
            else :
                self.m_picker = vtk.vtkCellPicker()
                self.m_picker.SetTolerance(0.0005)
                self.__create_guide_cell_key(0, algLinearMath.CScoMath.to_vec3([1.0, 0.9, 0.2]))
                self.__create_guide_cell_key(1, algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0]))
                self.m_mediator.ref_key_type(CTabStateMain.s_guideCellType)
        self.m_mediator.update_viewer()
    def __create_guide_cell_key(self, id : int, color : np.ndarray) -> str :
        guideKey = data.CData.make_key(CTabStateMain.s_guideCellType, 0, id)
        guideObj = vtkObjInterface.CVTKObjInterface()
        guideObj.KeyType = CTabStateMain.s_guideCellType
        guideObj.Key = guideKey
        guideObj.Color = color
        guideObj.Opacity = 1.0

        dataInst = self.get_data()
        dataInst.add_vtk_obj(guideObj)
        return guideKey
    def __get_guide_cell_obj(self, id : int) -> vtkObjInterface.CVTKObjInterface :
        guideKey = data.CData.make_key(CTabStateMain.s_guideCellType, 0, id)
        dataInst = self.get_data()
        guideObj = dataInst.find_obj_by_key(guideKey)
        return guideObj


if __name__ == '__main__' :
    pass


# print ("ok ..")

