import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import state.project.lung.userDataLung as userDataLung

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

import data as data
import operation as op

import tabState as tabState

import makeInputFolder as makeInputFolder
import checkIntegrity as checkIntegrity
import subRecon.subReconLung as reconLung

class CTabStatePatient(tabState.CTabState) :
    '''
    state
        - optionInfo, patientPath가 준비되지 않은 상태
        - optionInfo, patientPath가 준비된 상태
            - clInfo change 상태 
    '''
    s_listStepName = [
        "CheckMask",
        "Recon",
        "DoBlender",
        "Centerline",

    ]
    s_intermediatePathAlias = "OutTemp"
    def __init__(self, mediator):
        self.m_bReady = False
        self.m_listStepBtnEvent = [
            self._on_btn_check_mask,
            self._on_btn_recon,
            self._on_btn_clean,
            self._on_btn_centerline
        ]

        super().__init__(mediator)
        # input your code
        self.m_bReady = True
        self.m_reconLung = None #sally
        self.m_reconReady = False #sally
        self.m_zipPathPatientID = ""
        
        #sally
        try :
        # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = "."
        except AttributeError :
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))

    def clear(self) :
        # input your code
        self.m_outputPath = ""
        self.m_bReady = False
        self.m_reconLung = None #sally
        self.m_reconReady = False #sally
        super().clear()

    def process_init(self) :
        pass
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

        # sally : 아래 두 루틴은 _chaged_unzip_path() 안으로 옮김. 0526
        # self._command_option_path()
        # self._command_patientID()


    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        # path ui
        label = QLabel("-- Path Info --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)


        #sally
        layout, self.m_editInputPath, btn = self.m_mediator.create_layout_label_editbox_btn("Input", False, "..")
        btn.clicked.connect(self._on_btn_input_zip_path)
        tabLayout.addLayout(layout)
        #sally
        layout, self.m_editUnzipPath, btn = self.m_mediator.create_layout_label_editbox_btn("Output", False, "..")
        btn.clicked.connect(self._on_btn_unzip_path)
        tabLayout.addLayout(layout) 
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        layout, self.m_editOptionPath, btn = self.m_mediator.create_layout_label_editbox_btn("Option", False, "..")
        btn.clicked.connect(self._on_btn_option_path)
        tabLayout.addLayout(layout)

        layout, self.m_editOutputPath, btn = self.m_mediator.create_layout_label_editbox_btn(f"{CTabStatePatient.s_intermediatePathAlias}", False, "..")
        btn.clicked.connect(self._on_btn_output_path) # rename output -> media (sally)
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


        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        # centerline ui
        label = QLabel("-- Centerline --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, self.m_cbSkelIndex = self.m_mediator.create_layout_label_combobox("Centerline Index")
        self.m_cbSkelIndex.currentIndexChanged.connect(self._on_cb_skel_index_changed)
        tabLayout.addLayout(layout)

        #sally
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


    def setui_patientID(self, inx : int) :
        self.m_cbPatientID.blockSignals(True)
        self.m_cbPatientID.setCurrentIndex(inx)
        self.m_cbPatientID.blockSignals(False)
    def setui_reset_patientID(self, listPatientID : str) :
        self.m_cbPatientID.blockSignals(True)
        self.m_cbPatientID.clear()
        for patientID in listPatientID :
            self.m_cbPatientID.addItem(f"{patientID}")
        self.m_cbPatientID.blockSignals(False)
        self.setui_patientID(0)
    def setui_skelinfo_inx(self, inx : int) :
        self.m_cbSkelIndex.blockSignals(True)
        self.m_cbSkelIndex.setCurrentIndex(inx)
        self.m_cbSkelIndex.blockSignals(False)
        self.m_mediator.CLInfoIndex = inx
    def setui_reset_skelinfo_inx(self) :
        dataInst = self.get_data()
        self.m_cbSkelIndex.blockSignals(True)
        self.m_cbSkelIndex.clear()
        for clInx in range(0, dataInst.DataInfo.get_info_count()) :
            self.m_cbSkelIndex.addItem(f"{clInx}")
        self.m_cbSkelIndex.blockSignals(False)
        self.setui_skelinfo_inx(0)
    def setui_output_path(self, outputPath : str) :
        self.m_editOutputPath.setText(outputPath)

    def getui_patientID(self) -> str :
        return self.m_cbPatientID.currentText()
    def getui_output_path(self) -> str :
        return self.m_editOutputPath.text()
    def getui_skelinfo_inx(self) -> int :
        return self.m_cbSkelIndex.currentIndex()
    

    # command
    def _command_option_path(self) -> bool:
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_patient()

        self.m_editOptionPath.setText(self.m_optionFullPath)
        if self.m_optionFullPath == "" :
            return False
        # unzipPath = self.m_editUnzipPath.text() #sally
        
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

        ## 아래 주석 부분은  input, output 버튼 클릭시 _changed_unzip_path()에서 patientID를 받아서 셋팅함. sally 0526
        # retList = []
        # optionInfoInst = self.get_optioninfo()
        # listTmp = os.listdir(optionInfoInst.DataRootPath)
        # for patientID in listTmp :
        #     patientFullPath = os.path.join(optionInfoInst.DataRootPath, patientID)
        #     patientMaskFullPath = os.path.join(patientFullPath, "02_SAVE", "01_MASK", "AP")
        #     if os.path.exists(patientMaskFullPath) == True :
        #         retList.append(patientID)
        # self.setui_reset_patientID(retList)
        self.setui_reset_skelinfo_inx()
        self.setui_output_path("")
        self.m_mediator.update_viewer()
        return True
    def _command_patientID(self) :
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_patient()
        self.m_outputPath = self.getui_output_path()
        self.m_mediator.update_viewer()
    def _command_centerline(self) :
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()

        patientID = self.getui_patientID()
        outputPatientPath = os.path.join(self.OutputPath, patientID)

        cmd = commandLoadingPatient.CCommandLoadingPatient(self.m_mediator)
        cmd.InputData = dataInst
        # cmd.PatientBlenderFullPath = os.path.join(outputPatientPath, f"{self.getui_patientID()}_recon.blend") #commented by sally
        cmd.PatientBlenderFullPath = os.path.join(outputPatientPath, f"{self.getui_patientID()}.blend") #sally

        cmd.process()
        self.m_mediator.load_userdata()
        
        self._command_skelinfo_inx()
    def _command_skelinfo_inx(self) :
        dataInst = self.get_data()
        self.m_mediator.unref_all_key()

        skelinfoInx = self.getui_skelinfo_inx()
        dataInst.CLInfoIndex = skelinfoInx
        self.m_mediator.ref_key_type_groupID(dataInst.s_vesselType, skelinfoInx)
        skeleton = dataInst.get_skeleton(skelinfoInx)
        if skeleton is not None :
            self.m_mediator.ref_key_type_groupID(dataInst.s_skelTypeCenterline, skelinfoInx)
        
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
    def _get_userdata(self) -> userDataLung.CUserDataLung :
        return self.get_data().find_userdata(userDataLung.CUserDataLung.s_userDataKey)
    
    def _changed_input_path(self, inputPath) -> str:
        rootpath = ''
        huid = ''
        mkInputFold = makeInputFolder.CMakeInputFolder()
        mkInputFold.ZipPath = inputPath  #"D:\\jys\\StomachKidney_newfolder\\zippath" 
        mkInputFold.FolderMode = mkInputFold.eMode_Lung 
        result = mkInputFold.process()
        if result == True:
            rootpath = mkInputFold.get_data_root_path()
            huid = mkInputFold.PatientID
            print(f"Making Input Folder Done. RootPath={rootpath}")
            
        return rootpath, huid
    def _changed_unzip_path(self, option_path, data_root_path) -> str:
        #현재 option 파일의 dataRootPath를 변경해줘야 함.
        new_data_root_path = data_root_path.replace("\\", "\\\\").replace("/", "\\\\")
        jsonpath = option_path
        if os.path.exists(jsonpath) :
            #임시 파일에 업데이트된 DataRootPath 포함해서 json내용 복사
            temp_path = os.path.join(os.path.dirname(jsonpath), "tmp.json")
            target_str = '"DataRootPath"'
            
            with open(jsonpath, 'r', encoding='utf-8') as org_file, open(temp_path, 'w', encoding='utf-8') as temp_file:
                for line in org_file:
                    # DataRootPath 부분 찾아서 새로운 패스로 바꿈
                    if target_str in line:
                        # line = line.replace(target_str, replacement_string)
                        line = f'\t"DataRootPath" : "{new_data_root_path}",\n'
                    temp_file.write(line)

            os.replace(temp_path, jsonpath)
        

        self._command_option_path() #sally 0526
        self._command_patientID()    #sally 0526
        
        # get patientID
        patientID = '--'
        for dirfile in os.listdir(new_data_root_path) :
            if os.path.isdir(os.path.join(new_data_root_path,dirfile)) :
                patientID = dirfile
        return patientID  
    def _clicked_do_blender(self) :
        if self.m_reconLung != None and self.m_reconReady == True:    
                self.m_reconLung.do_blender(self.getui_patientID())
                self.m_mediator.show_dialog("Do Blender Done!" )  
        else :
            print(f"tabStateReconLung - Error : m_reconLung None or m_reconReady False!")
            self.m_mediator.show_dialog(f"Do Blender FAIL! \nOption 또는 {CTabStatePatient.s_intermediatePathAlias} 경로를 확인해주세요.")
            
    def _clicked_recon_mask(self) :
        if self.m_reconLung != None and self.m_reconReady == True: 
            self.m_reconLung.process()
            self.m_reconLung.clear()
            self.m_mediator.show_dialog("Reconstruction Done.")
        else :
            self.m_mediator.show_dialog(f"Reconstruction FAIL! \nOption 또는 {CTabStatePatient.s_intermediatePathAlias} 경로를 확인해주세요.")

    def _check_mask(self) :
        optionPath = self.m_editOptionPath.text()
        unzipPath = self.m_editUnzipPath.text()
        if optionPath != '' and unzipPath != '':
            checkMask = checkIntegrity.CCheckIntegrity()
            checkMask.OptionPath = optionPath
            checkMask.PatientID = self.getui_patientID()
            result = checkMask.process()
            if result :
                print("CheckIntegrity -> PASS")
                self.m_mediator.show_dialog("CheckIntegrity PASS")
            else : 
                print("CheckIntegrity -> FAIL")
                self.m_mediator.show_dialog("CheckIntegrity FAIL!\ncheck.csv파일 내용을 확인해주세요.")
        else : 
            self.m_mediator.show_dialog(f"Check Mask FAIL!\nOption 또는 Output 경로를 확인해주세요.")    
    def _init_recon_lung(self, mediator) -> bool:
        if self.m_reconLung == None :
            self.m_reconLung = reconLung.CSubReconLung(mediator)
        self.m_reconLung.OptionPath = self.m_optionFullPath
        self.m_reconLung.IntermediateDataPath = self.m_outputPath
        result = self.m_reconLung.init()
        return result
    def _decim_clean_mesh_for_centerline_extraction(self) :        
        dataInst = self.get_data()
        if dataInst.Ready == False : 
            return 
        currPatientID = self.getui_patientID()
        if currPatientID == '' :
            print(f"Decimate&Mesh-Clean - ERROR : CurrPatientID is empty.")
            return
        terriStlPath = dataInst.get_terri_out_path()
        # blender background 실행
        saveAs = f"{currPatientID}.blend"
        cmd = f"{dataInst.OptionInfo.BlenderExe} -b --python {os.path.join(self.fileAbsPath, 'blenderScriptLung.py')} -- --patientID {currPatientID} --path {terriStlPath} --saveAs {saveAs} --funcMode CleanForCenterline"
        os.system(cmd)

    # ui event 
    def _on_btn_option_path(self) :
        optionPath, _ = QFileDialog.getOpenFileName(self.get_main_widget(), "Select Option File", "", "JSON Files (*.json)")
        if optionPath == "" :
            return        
        self.m_optionFullPath = optionPath
        self._command_option_path()
    
    def _on_btn_input_zip_path(self) : #sally
        inputPath = QFileDialog.getExistingDirectory(self.get_main_widget(), "Select Zip Folder")
        self.m_editInputPath.setText(inputPath)
        self.m_editUnzipPath.setText("")
        if inputPath == "" :
            return
        root_path, huid = self._changed_input_path(inputPath)
        self.m_editUnzipPath.setText(root_path)
        option_path = self.m_optionFullPath
        self._changed_unzip_path(option_path, root_path)
        self.setui_reset_patientID([huid])
        self.m_zipPathPatientID = huid #sally: 이값을 저장해 놓았다가 _on_btn_unzip_path() 수행시 감지한 huid 와 이 값이 다르면 self.m_editInputPath 칸을 클리어한다.
        
    def _on_btn_unzip_path(self) : #sally
        unzipPath = QFileDialog.getExistingDirectory(self.get_main_widget(), "Select Output Path")
        self.m_editUnzipPath.setText(unzipPath) # Output 폴더구조 path
        if unzipPath != "" :
            option_path = self.m_editOptionPath.text()
            huid = self._changed_unzip_path(option_path, unzipPath)
            self.setui_reset_patientID([huid])

            ## _on_btn_input_zip_path() 수행시 감지된 huid와 현재 huid가 서로 다르면 다른 환자의 데이터를 가져오는 것이므로 input path 칸은 혼동 방지를 위해 클리어한다.
            if huid != self.m_zipPathPatientID : 
                self.m_editInputPath.setText("")
            
    def _on_btn_output_path(self) :
        outputPath = QFileDialog.getExistingDirectory(self.get_main_widget(), f"Select {CTabStatePatient.s_intermediatePathAlias} Path") 
        self.setui_output_path(outputPath)
        self.m_outputPath = outputPath
        self.m_reconReady = self._init_recon_lung(self.m_mediator)

    def _on_btn_recon_all(self) :
        pass
    def _on_btn_check_mask(self) :
        self._check_mask()
    def _on_btn_recon(self) :
        self._clicked_recon_mask() #sally
        # if self.getui_patientID() == "" :
        #     print("not selection patientID")
        #     return
        # if self.getui_output_path() == "" :
        #     print("not setting output path")
        #     return 
        
        # cmd = commandRecon.CCommandReconDevelopCommon(self.m_mediator)
        # cmd.InputData = self.get_data()
        # cmd.InputPatientID = self.getui_patientID()
        # cmd.InputBlenderScritpFileName = "blenderScriptRecon"
        # cmd.InputSaveBlenderName = f"{self.getui_patientID()}_recon"
        # cmd.OutputPath = self.getui_output_path()
        # cmd.process()
    def _on_btn_centerline(self) :
        patientID = self.getui_patientID()
        if self.OutputPath == '' :
            self.m_mediator.show_dialog(f"Loading FAIL!\nOption과 {CTabStatePatient.s_intermediatePathAlias} 경로를 확인해주세요.")
            return
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
        self._clicked_do_blender()  #sally
        # if self.getui_patientID() == "" :
        #     print("not selection patientID")
        #     return
        # if self.getui_output_path() == "" :
        #     print("not setting output path")
        #     return 
        
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
        patientID = self.getui_patientID()
        if patientID == "" :
            print("not select patientID")
            return
        self._command_patientID()
    def _on_cb_skel_index_changed(self, index) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        self._command_skelinfo_inx()
    def _on_btn_extraction_centerline(self) :
        self._command_extraction_cl()        
    def _on_btn_decimate_and_mesh_clean(self) :
        patientPath = os.path.join(self.m_outputPath, self.getui_patientID())
        if patientPath != "" :
            self._decim_clean_mesh_for_centerline_extraction()
            self.m_mediator.show_dialog("Decimation and Mesh-Clean Done.")
        else : 
            self.m_mediator.show_dialog(f"Blender FAIL!\nOption과 {CTabStatePatient.s_intermediatePathAlias} 경로를 확인해주세요.")

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

