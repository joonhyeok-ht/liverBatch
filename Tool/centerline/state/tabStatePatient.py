import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtCore import Qt, QItemSelectionModel, QModelIndex
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QTableView
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


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.reconstruction as reconstruction

import VtkObj.vtkObj as vtkObj

import command.commandInterface as commandInterface
import command.commandLoadingPatient as commandLoadingPatient
import command.commandExtractionCL as commandExtractionCL
import command.commandRecon as commandRecon

import state.project.userData as userData

import data as data
import operation as op

import tabState as tabState


class CTabStatePatient(tabState.CTabState) :
    '''
    state
        - optionInfo, patientPath가 준비되지 않은 상태
        - optionInfo, patientPath가 준비된 상태
            - clInfo change 상태 
    '''
    s_listStepName = [
        "ReconAll",
        "Recon",
        "Centerline",
        "Clean",
    ]
    
    def __init__(self, mediator) :
        self.m_bReady = False
        self.m_listStepBtnEvent = [
            self._on_btn_recon_all,
            self._on_btn_recon,
            self._on_btn_centerline,
            self._on_btn_clean
        ]

        super().__init__(mediator)
        # input your code
        self.m_outputPath = ""
        self.m_bReady = True
    def clear(self) :
        # input your code
        self.m_btnCL = None
        self.m_outputPath = ""
        self.m_bReady = False
        super().clear()


    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            print("not setting patient path")
            return
        self._command_reset_clinfo_inx()
    def process(self) :
        pass
    def process_end(self) :
        pass

    def changed_project_type(self) :
        self.m_optionFullPath = os.path.join(self.m_mediator.FilePath, "option.json")
        if os.path.exists(self.m_optionFullPath) == False :
            self.m_optionFullPath = os.path.join(self.m_mediator.CommonPipelinePath, "option.json")
            if os.path.exists(self.m_optionFullPath) == False :
                self.m_optionFullPath = ""
        self._command_option_path(self.m_optionFullPath)


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

        layout, btnList = self.m_mediator.create_layout_btn_array(CTabStatePatient.s_listStepName)
        for inx, stepName in enumerate(CTabStatePatient.s_listStepName) :
            btnList[inx].clicked.connect(self.m_listStepBtnEvent[inx])
        tabLayout.addLayout(layout)
        self.m_btnCL = btnList[2]


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

    # command
    def _command_option_path(self, optionPath : str) :
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_patient()

        self.m_optionFullPath = optionPath
        self.m_editOptionPath.setText(self.m_optionFullPath)
        if os.path.exists(self.m_optionFullPath) == False :
            print("not existing option file")
            self.setui_reset_patientID([])
            self._command_reset_clinfo_inx()
            self.setui_output_path("")
            self.m_mediator.update_viewer()
            return
        
        optionFullPath = self.m_optionFullPath
        dataInst.load_optioninfo(optionFullPath)
        dataInst.CLColor = algLinearMath.CScoMath.to_vec3([0.3, 0.3, 0.0])
        dataInst.RootCLColor = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])
        dataInst.SelectionCLColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])
        dataInst.CLSize = 0.4
        dataInst.BrColor = algLinearMath.CScoMath.to_vec3([1.0, 0.647, 0.0])
        dataInst.SelectionBrColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.BrSize = 0.5
        dataInst.EPColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])
        dataInst.SelectionEPColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        dataInst.EPSize = 0.5

        self._command_reset_clinfo_inx()
        self.setui_output_path("")
        self.m_mediator.update_viewer()
    def _command_output_path(self, outputPath : str) :
        self.setui_output_path(outputPath)
        self.m_outputPath = outputPath
        self.m_mediator.remove_all_key()

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

        if os.path.exists(self.m_outputPath) == True :
            listTmp = os.listdir(self.m_outputPath)
            for patientID in listTmp :
                patientFullPath = os.path.join(self.m_outputPath, patientID)
                reconBlendFullPath = os.path.join(patientFullPath, f"{patientID}_recon.blend")
                if os.path.exists(reconBlendFullPath) == True :
                    retList.append(patientID)

        # 중복되지 않게 한다.
        retList = list(set(retList))
        self.setui_reset_patientID(retList)

        self.m_mediator.update_viewer()
    def _command_patientID(self) :
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_patient()
        
        self.m_outputPath = self.getui_output_path()

        patientID = self.getui_patientID()
        self.m_mediator.set_title(patientID)
        self.m_mediator.update_viewer()
    def _command_reset_clinfo_inx(self) :
        dataInst = self.get_data()

        self.m_tvCLInfo.blockSignals(True)
        self.m_modelCLInfo.removeRows(0, self.m_modelCLInfo.rowCount())
        for dataInfoInx in range(0, dataInst.DataInfo.get_info_count()) :
            clInfo = dataInst.DataInfo.get_clinfo(dataInfoInx)
            blenderName = clInfo.get_input_blender_name()
            outputName = clInfo.OutputName
            self.m_modelCLInfo.appendRow([QStandardItem(f"{dataInfoInx}"), QStandardItem(blenderName), QStandardItem(outputName)])
        self.m_tvCLInfo.blockSignals(False)

        clinfoInx = dataInst.CLInfoIndex
        if clinfoInx == -1 :
            clinfoInx = 0
        if clinfoInx > dataInst.DataInfo.get_info_count() :
            dataInst.CLInfoIndex = -1
            return

        self.setui_clinfo_inx(clinfoInx)
        self._command_clinfo_inx()
    def _command_centerline(self) :
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()

        patientID = self.getui_patientID()
        outputPatientPath = os.path.join(self.OutputPath, patientID)

        cmd = commandLoadingPatient.CCommandLoadingPatient(self.m_mediator)
        cmd.InputData = dataInst
        cmd.PatientBlenderFullPath = os.path.join(outputPatientPath, f"{self.getui_patientID()}_recon.blend")   
        cmd.process()
        self.m_mediator.load_userdata()

        self._command_reset_clinfo_inx()
        self.m_btnCL.setEnabled(False)
    def _command_clinfo_inx(self) :
        dataInst = self.get_data()
        self.m_mediator.unref_all_key()

        if dataInst.get_skeleton_count() == 0 :
            self.m_mediator.update_viewer()
            return

        clinfoInx = self.getui_clinfo_inx()
        dataInst.CLInfoIndex = clinfoInx
        self.m_mediator.ref_key_type_groupID(dataInst.s_vesselType, clinfoInx)
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is not None :
            self.m_mediator.ref_key_type_groupID(dataInst.s_skelTypeCenterline, clinfoInx)
        
        self.m_mediator.update_viewer()
    def _command_extraction_cl(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            print("not setting patient path")
            return

        clOutPath = dataInst.get_cl_out_path()
        if os.path.exists(clOutPath) == False :
            print("not found clOutPath")
            return False

        clinfoInx = self.get_clinfo_index()
        clinfo = dataInst.DataInfo.get_clinfo(clinfoInx)

        self.m_mediator.remove_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
        self.m_mediator.remove_key_type_groupID(data.CData.s_skelTypeBranch, clinfoInx)
        self.m_mediator.remove_key_type_groupID(data.CData.s_skelTypeEndPoint, clinfoInx)
        
        cmd = commandExtractionCL.CCommandExtractionCL(self.m_mediator)
        cmd.InputData = dataInst
        cmd.InputIndex = clinfoInx
        cmd.process()

        clOutput = clinfo.OutputName
        clOutputFullPath = os.path.join(clOutPath, f"{clOutput}.json")
        if os.path.exists(clOutputFullPath) == False :
            print(f"not found skelinfo : {clOutputFullPath}")
            return False
        
        dataInst.set_skeleton(clinfoInx, clOutputFullPath)
        self.m_mediator.load_cl_key(clinfoInx)
        self.m_mediator.load_br_key(clinfoInx)
        self.m_mediator.load_ep_key(clinfoInx)

        self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
        self.m_mediator.update_viewer()


    # protected 

    
    # ui event 
    def _on_btn_option_path(self) :
        self.m_btnCL.setEnabled(True)

        optionPath, _ = QFileDialog.getOpenFileName(self.get_main_widget(), "Select Option File", "", "JSON Files (*.json)")
        if optionPath == "" :
            return
        
        self.m_optionFullPath = optionPath
        self._command_option_path(optionPath)
    def _on_btn_output_path(self) :
        self.m_btnCL.setEnabled(True)

        outputPath = QFileDialog.getExistingDirectory(self.get_main_widget(), "Selection Output Path")
        self._command_output_path(outputPath)
    def _on_btn_recon_all(self) :
        pass
    def _on_btn_recon(self) :
        if self.getui_patientID() == "" :
            print("not selection patientID")
            return
        if self.getui_output_path() == "" :
            print("not setting output path")
            return 
        
        userData = self.m_mediator.ReconUserData
        if userData is not None :
            userData.override_recon(self.getui_patientID(), self.getui_output_path())
        
        # cmd = commandRecon.CCommandReconDevelopCommon(self.m_mediator)
        # cmd.InputData = self.get_data()
        # cmd.InputPatientID = self.getui_patientID()
        # cmd.InputBlenderScritpFileName = "blenderScriptRecon"
        # cmd.InputSaveBlenderName = f"{self.getui_patientID()}_recon"
        # cmd.OutputPath = self.getui_output_path()
        # cmd.process()
    def _on_btn_centerline(self) :
        patientID = self.getui_patientID()
        outputPatientPath = os.path.join(self.OutputPath, patientID)
        if os.path.exists(outputPatientPath) == False :
            print("not found output recon patient path")
            return 

        dataInst = self.get_data()
        dataInst.load_patient(outputPatientPath)

        if dataInst.Ready == False :
            print("not setting option or patientID")
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
            userData.override_clean(self.getui_patientID(), self.getui_output_path())
        
        # patientID = self.getui_patientID()
        # blenderScritpFileName = "blenderScriptClean"
        # saveBlenderName = f"{self.getui_patientID()}"
        # outputPath = self.getui_output_path()

        # outputPatientPath = os.path.join(outputPath, patientID)
        # saveBlenderFullPath = os.path.join(outputPatientPath, f"{saveBlenderName}.blend")
        # srcBlenderFullPath = os.path.join(outputPatientPath, f"{self.getui_patientID()}_recon.blend")

        # if os.path.exists(srcBlenderFullPath) == False :
        #     print("not found recon blender file")
        #     return

        # # 기존것은 지움
        # if os.path.exists(saveBlenderFullPath) == True :
        #     os.remove(saveBlenderFullPath)
        # # 새롭게 생성 
        # shutil.copy(srcBlenderFullPath, saveBlenderFullPath)

        # cmd = commandRecon.CCommandReconDevelopClean(self.m_mediator)
        # cmd.InputData = self.get_data()
        # cmd.InputPatientID = patientID
        # cmd.InputBlenderScritpFileName = blenderScritpFileName
        # cmd.InputSaveBlenderName = saveBlenderName
        # cmd.OutputPath = self.getui_output_path()
        # cmd.process()
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
        self._command_clinfo_inx()
    def _on_btn_extraction_centerline(self) :
        self._command_extraction_cl()


    @property
    def OutputPath(self) -> str :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath
        


    # private


if __name__ == '__main__' :
    pass


# print ("ok ..")

