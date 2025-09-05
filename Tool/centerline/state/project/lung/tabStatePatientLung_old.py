import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
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
import AlgUtil.algImage as algImage

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.reconstruction as reconstruction

import VtkObj.vtkObj as vtkObj

import command.commandInterface as commandInterface
import command.commandLoadingPatient as commandLoadingPatient
import command.commandExtractionCL as commandExtractionCL

import data as data
import operationLung as operation

import tabState as tabState


class CTabStatePatient(tabState.CTabState) :
    '''
    state
        - optionInfo, patientPath가 준비되지 않은 상태
        - optionInfo, patientPath가 준비된 상태
            - clInfo change 상태 
    '''
    
    def __init__(self, mediator):
        self.m_bReady = False
        super().__init__(mediator)

        try:
        # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = os.getcwd() #"."
        except AttributeError:
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))
        
        # input your code
        self.m_state = 0
        self.m_bReady = True
    def clear(self) :
        # input your code
        self.m_state = 0
        super().clear()


    def process_init(self) :        
        pass
    def process(self) :
        pass
    def process_end(self) :
        pass


    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        # path ui
        label = QLabel("-- Path Info --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        btn = QPushButton("Load Existing Option and Patient Setting")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_load_existing_option_patient)
        tabLayout.addWidget(btn)

        layout, self.m_editOptionPath, btn = self.m_mediator.create_layout_label_editbox_btn("Option", False, "..")
        btn.clicked.connect(self._on_btn_option_path)
        tabLayout.addLayout(layout)

        layout, self.m_editPatientPath, btn = self.m_mediator.create_layout_label_editbox_btn("Patient", False, "..")
        btn.clicked.connect(self._on_btn_patient_path)
        tabLayout.addLayout(layout)
               
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        # centerline ui
        label = QLabel("-- Centerline Info --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, self.m_cbSkelIndex = self.m_mediator.create_layout_label_combobox("Centerline Index")
        self.m_cbSkelIndex.currentIndexChanged.connect(self._on_cb_skel_index_changed)
        tabLayout.addLayout(layout)

        layout, self.m_editCLType = self.m_mediator.create_layout_label_editbox("CenterlineType", True)
        tabLayout.addLayout(layout)
        layout, self.m_editCLTypeAdvancementRatio = self.m_mediator.create_layout_label_editbox("AdvancementRatio", False)
        tabLayout.addLayout(layout)
        layout, self.m_editCLTypeResamplingLength = self.m_mediator.create_layout_label_editbox("ResamplingLength", False)
        tabLayout.addLayout(layout)
        layout, self.m_editCLTypeSmoothingIter = self.m_mediator.create_layout_label_editbox("SmoothingIter", False)
        tabLayout.addLayout(layout)
        layout, self.m_editCLTypeSmoothingFactor = self.m_mediator.create_layout_label_editbox("SmoothingFactor", False)
        tabLayout.addLayout(layout)

        layout, self.m_cbCLInputKey = self.m_mediator.create_layout_label_combobox("Centerline Input Key")
        for inputKey in data.CData.s_clInputKey :
            self.m_cbCLInputKey.addItem(inputKey)
        tabLayout.addLayout(layout)

        layout, self.m_editCLInputBlenderName = self.m_mediator.create_layout_label_editbox("Input BlenderName", True)
        tabLayout.addLayout(layout)
        layout, self.m_editCLInputReconType = self.m_mediator.create_layout_label_editbox("Input ReconType", True)
        tabLayout.addLayout(layout)

        layout, self.m_cbCLFindCell = self.m_mediator.create_layout_label_combobox("FindCell")
        for findCell in data.CData.s_clFindCell :
            self.m_cbCLFindCell.addItem(findCell)
        tabLayout.addLayout(layout)

        layout, self.m_editCLOutputName = self.m_mediator.create_layout_label_editbox("OutputName", True)
        tabLayout.addLayout(layout)

        # skel recon
        label = QLabel("-- Recon Info --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, self.m_editCLReconType = self.m_mediator.create_layout_label_editbox("Recon Type", True)
        tabLayout.addLayout(layout)
        layout, self.m_editCLReconContour = self.m_mediator.create_layout_label_editbox("Recon Contour", False)
        tabLayout.addLayout(layout)
        layout, self.m_editCLReconIter, self.m_editCLReconRelax, self.m_editCLReconDeci = self.m_mediator.create_layout_label_editbox3("Recon Param")
        tabLayout.addLayout(layout)

        layout, self.m_cbCLReconGaussian = self.m_mediator.create_layout_label_combobox("Gaussian")
        for gaussian in data.CData.s_reconGaussian :
            self.m_cbCLReconGaussian.addItem(gaussian)
        tabLayout.addLayout(layout)

        layout, self.m_cbCLReconAlgorithm = self.m_mediator.create_layout_label_combobox("Algorithm")
        for algorithm in data.CData.s_reconAlgorithm :
            self.m_cbCLReconAlgorithm.addItem(algorithm)
        tabLayout.addLayout(layout)

        layout, self.m_cbCLReconResampling = self.m_mediator.create_layout_label_combobox("Resampling Factor")
        for resampling in data.CData.s_reconResampling :
            self.m_cbCLReconResampling.addItem(resampling)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        btn = QPushButton("Decimate + Mesh-Clean")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_decimate_and_mesh_clean)
        tabLayout.addWidget(btn)

        btn = QPushButton("Extract Centerline")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_extraction_centerline)
        tabLayout.addWidget(btn)


        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)


    def get_clinfo_index(self) -> int :
        return self.m_cbSkelIndex.currentIndex()
    
    # protected 
    def _changed_option_path(self, optionFullPath : str, patientClear=True) :
        dataInst = self.get_data()
        if dataInst == None :
            print("ERROR : dataInst is None. ")
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

        self.m_cbSkelIndex.clear()
        for clInx in range(0, dataInst.DataInfo.get_info_count()) :
            self.m_cbSkelIndex.addItem(f"{clInx}")
        self.m_cbSkelIndex.setCurrentIndex(0)
        if patientClear :
            self.m_editPatientPath.setText("")
    def _changed_patient_path(self, patientFullPath : str) :
        dataInst = self.get_data()
        dataInst.load_patient(patientFullPath)
        self.m_mediator.remove_all_key()

        cmd = commandLoadingPatient.CCommandLoadingPatient(self.m_mediator)
        cmd.InputData = dataInst
        cmd.process()

        clInfoInx = 0
        self.m_mediator.ref_key_type_groupID(dataInst.s_vesselType, clInfoInx)
        skeleton = dataInst.get_skeleton(clInfoInx)
        if skeleton is not None :
            self.m_mediator.ref_key_type_groupID(dataInst.s_skelTypeCenterline, clInfoInx)

        self.m_mediator.update_viewer()
        self._update_ui_clinfo_inx(0)
    def _changed_clinfo_inx(self, inx : int) :
        self.m_mediator.unref_all_key()
        
        dataInst = self.get_data()

        clInfoInx = inx
        self.m_mediator.ref_key_type_groupID(dataInst.s_vesselType, clInfoInx)
        skeleton = dataInst.get_skeleton(clInfoInx)
        if skeleton is not None :
            self.m_mediator.ref_key_type_groupID(dataInst.s_skelTypeCenterline, clInfoInx)
        self.m_mediator.update_viewer()
        self._update_ui_clinfo_inx(inx)

    def _decim_clean_mesh_for_centerline_extraction(self) :        
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return 
        currPatientID = self.m_mediator.CurrPatientID
        if currPatientID == '' :
            print(f"_import_territory()-ERROR : CurrPatientID is empty.")
            return
        terriStlPath = dataInst.get_terri_out_path()
        # blender background 실행
        saveAs = dataInst.OptionInfo.get_blender_name(dataInst.OptionInfo.s_processName, currPatientID)
        #TODO : 아래 코드 동작확인하기
        cmd = f"{dataInst.OptionInfo.BlenderExe} -b --python {os.path.join(self.fileAbsPath, 'blenderScriptLung.py')} -- --patientID {currPatientID} --path {terriStlPath} --saveAs {saveAs} --funcMode CleanForCenterline"
        os.system(cmd)

    def _clicked_extraction_cl(self) :
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


    # ui update
    def _update_ui_clinfo_inx(self, inx : int) :
        dataInst = self.get_data()
        clInfo = dataInst.DataInfo.get_clinfo(inx)
        clParam = dataInst.DataInfo.get_clparam(inx)
        reconParam = dataInst.DataInfo.get_reconparam(inx)
        if clInfo is None :
            print("invalid clInfo, clParam, reconParam")
            return
        
        self.m_editCLType.setText(clInfo.CenterlineType)
        self.m_editCLTypeAdvancementRatio.setText(f"{clParam.AdvancementRatio}")
        self.m_editCLTypeResamplingLength.setText(f"{clParam.ResamplingLength}")
        self.m_editCLTypeSmoothingIter.setText(f"{clParam.SmoothingIter}")
        self.m_editCLTypeSmoothingFactor.setText(f"{clParam.SmoothingFactor}")

        inputKeyIndex = data.CData.get_list_index(data.CData.s_clInputKey, clInfo.InputKey)
        if inputKeyIndex == -1 :
            print("invalid inputKey")
        else :
            self.m_cbCLInputKey.setCurrentIndex(inputKeyIndex)

        self.m_editCLInputBlenderName.setText(f"{clInfo.get_input_blender_name()}")
        self.m_editCLInputReconType.setText(f"{clInfo.get_input_recon_type()}")

        findCellIndex = data.CData.get_list_index(data.CData.s_clFindCell, clInfo.FindCell)
        if findCellIndex == -1 :
            print("invalid findCell")
        else :
            self.m_cbCLFindCell.setCurrentIndex(findCellIndex)

        self.m_editCLOutputName.setText(f"{clInfo.OutputName}")

        reconType = clInfo.get_input_recon_type()
    
        self.m_editCLReconType.setText(reconType)
        self.m_editCLReconContour.setText(f"{reconParam.Contour}")
        self.m_editCLReconIter.setText(f"{reconParam.Param[0]}")
        self.m_editCLReconRelax.setText(f"{reconParam.Param[1]}")
        self.m_editCLReconDeci.setText(f"{reconParam.Param[2]}")

        findGaussianIndex = data.CData.get_list_index(data.CData.s_reconGaussian, f"{reconParam.Gaussian}")
        self.m_cbCLReconGaussian.setCurrentIndex(findGaussianIndex)
        findAlgorithmIndex = data.CData.get_list_index(data.CData.s_reconAlgorithm, f"{reconParam.Algorithm}")
        self.m_cbCLReconAlgorithm.setCurrentIndex(findAlgorithmIndex)
        findResamplingIndex = data.CData.get_list_index(data.CData.s_reconResampling, f"{reconParam.ResamplingFactor}")
        self.m_cbCLReconResampling.setCurrentIndex(findResamplingIndex)

    
    # ui event 
    def _on_btn_load_existing_option_patient(self) :
        # Recon Tab에서 셋팅한 option path로 초기화함.sally
        if self.m_mediator.CurrOptionPath != '' :
            print(f"_on_btn_load_existing_option_patient() CurrOptionPath : {self.m_mediator.CurrOptionPath}")
            self.m_editOptionPath.setText(self.m_mediator.CurrOptionPath)
            self._changed_option_path(self.m_mediator.CurrOptionPath, patientClear=True)  
        # Recon Tab에서 셋팅한 output폴더구조를 따라 patient path를 설정함. sally
        print(f"_on_btn_load_existing_option_patient() IntermediateDataPath : {self.m_mediator.IntermediateDataPath}")
        if self.m_mediator.IntermediateDataPath != '' and self.m_mediator.CurrPatientID != '' :
            outputPatientFullPath = os.path.join(self.m_mediator.IntermediateDataPath, self.m_mediator.CurrPatientID)
            self.m_editPatientPath.setText(outputPatientFullPath)  
            if outputPatientFullPath != "" :
                print(f"---tabStatePatientLung: init_ui() : Do _changed_patient_path()")
                self._changed_patient_path(outputPatientFullPath) 
                # self._decim_clean_mesh_for_centerline_extraction()  #ReconTab에서 recon한 메쉬들이 수정되었을 경우를 대비해서 Decimation&Mesh-Clean수행. #TODO : 여기서 수행해도 되는건가???

    def _on_btn_option_path(self) :
        optionPath, _ = QFileDialog.getOpenFileName(self.get_main_widget(), "Select Option File", "", "JSON Files (*.json)")
        self.m_editOptionPath.setText(optionPath)
        self.m_editPatientPath.setText("")

        if optionPath == "" :
            return
        self.m_mediator.CurrOptionPath = optionPath
        self._changed_option_path(optionPath, patientClear=True)
    def _on_btn_patient_path(self) :
        patientPath = QFileDialog.getExistingDirectory(self.get_main_widget(), "Selection Patient Path")
        self.m_editPatientPath.setText(patientPath)
        if patientPath != "" :
            if self.m_mediator.CurrOptionPath != "" :
                self._changed_option_path(self.m_mediator.CurrOptionPath, patientClear=False)
                self._changed_patient_path(patientPath)
                self.m_mediator.show_dialog("Patient Loading Done.")
    def _on_cb_skel_index_changed(self, index) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        self._changed_clinfo_inx(index)
    def _on_btn_extraction_centerline(self) :
        self._clicked_extraction_cl()
        self.m_mediator.show_dialog("Centerline Extraction Done.")
    def _on_btn_decimate_and_mesh_clean(self) :
        patientPath = self.m_editPatientPath.text()
        if patientPath != "" :
            self._decim_clean_mesh_for_centerline_extraction()
            self.m_mediator.show_dialog("Decimation and Mesh-Clean Done.")
        else : 
            self.m_mediator.show_dialog("Option과 Patient설정을 확인해주세요.")
    # private


if __name__ == '__main__' :
    pass


# print ("ok ..")

