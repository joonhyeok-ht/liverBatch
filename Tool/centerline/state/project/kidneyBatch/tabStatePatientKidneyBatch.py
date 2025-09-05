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

import state.project.kidneyBatch.userDataKidneyBatch as userDataKidney

# import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
# import AlgUtil.algImage as algImage

# import Block.optionInfo as optionInfo
# import Block.niftiContainer as niftiContainer
# import Block.reconstruction as reconstruction

# import VtkObj.vtkObj as vtkObj

# import command.commandInterface as commandInterface
import command.commandLoadingPatient as commandLoadingPatient
# import command.commandExtractionCL as commandExtractionCL
# import command.commandRecon as commandRecon

import data as data
# import operation as op

import tabState as tabState

#sally
import makeInputFolderKidneyBatch as makeInputFolder
import checkIntegrity as checkIntegrity
import subRecon.subReconKidney as reconKidney
import subDetectOverlap.subDetectOverlap as detectOverlap

class CTabStatePatient(tabState.CTabState) :
    '''
    state
        - optionInfo, patientPath가 준비되지 않은 상태
        - optionInfo, patientPath가 준비된 상태
            - clInfo change 상태 
    '''
    s_listStepName = [
        # "CheckMask",
        "Recon",
        "Overlap",
        "Separate+MeshClean"

    ]
    s_intermediatePathAlias = "OutTemp"
    def __init__(self, mediator):
        self.m_bReady = False
        self.m_listStepBtnEvent = [
            # self._on_btn_check_mask,
            self._on_btn_recon,
            self._on_btn_overlap,
            self._on_btn_separate_and_clean
        ]

        super().__init__(mediator)
        # input your code
        self.m_bReady = True
        self.m_reconKidney = None #sally
        self.m_reconReady = False #sally
        
        
        #sally
        try :
        # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = "."
        except AttributeError :
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))
        
        self.m_outputPath = ""
        self.m_zipPathPatientID = ""
        self.m_bReady = False
        self.m_reconKidney = None #sally
        self.m_reconReady = False #sally

        self.m_dataRootPath = ""
        self.m_patientID = ""
        self.m_tumorPhase = ""
        self.m_targetKidney = ""
        self.m_srcKidney = None


    def clear(self) :
        # input your code
        self.m_outputPath = ""
        self.m_zipPathPatientID = ""
        self.m_bReady = False
        self.m_reconKidney = None #sally
        self.m_reconReady = False #sally

        self.m_dataRootPath = ""
        self.m_patientID = ""
        self.m_tumorPhase = ""
        self.m_targetKidney = ""
        self.m_srcKidney = None

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
        btn.clicked.connect(self._on_btn_output_temp_path) # rename output -> media (sally)
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
        # label = QLabel("-- Centerline --")
        # label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        # label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        # tabLayout.addWidget(label)

        # layout, self.m_cbSkelIndex = self.m_mediator.create_layout_label_combobox("Centerline Index")
        # self.m_cbSkelIndex.currentIndexChanged.connect(self._on_cb_skel_index_changed)
        # tabLayout.addLayout(layout)

        #sally
        btn = QPushButton("Do Blender")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_do_blender)
        tabLayout.addWidget(btn)
        
        # btn = QPushButton("Extract Centerline")
        # btn.setStyleSheet(self.get_btn_stylesheet())
        # btn.clicked.connect(self._on_btn_extraction_centerline)
        # tabLayout.addWidget(btn)


        # line = QFrame()
        # line.setFrameShape(QFrame.Shape.HLine)
        # line.setFrameShadow(QFrame.Shadow.Sunken)
        # tabLayout.addWidget(line)

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
    def setui_output_path(self, outputPath : str) :
        self.m_editOutputPath.setText(outputPath)
    def getui_patientID(self) -> str :
        return self.m_cbPatientID.currentText()
    def getui_output_path(self) -> str :
        return self.m_editOutputPath.text()

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

        self.setui_output_path("")
        self.m_mediator.update_viewer()
        
        # 여기서 Tumor_exo, Tumor_endo, Kidney 의 phase를 찾아낸 후 실제에 맞게 변경해줘야함. option.json에는 디폴트로 DP로 설정되어 있음.
        if self.m_dataRootPath != "" and self.m_patientID != "" :
            self.m_tumorPhase, self.m_targetKidney, self.m_srcKidney, realPhaseMaskList = self._get_tumor_phase_with_kidney_name(self.m_dataRootPath, self.m_patientID)
            # 마스크들의 실제 Phase 폴더에 맞춰 maskInfo를 갱신함.
            for phaseMask in realPhaseMaskList :
                for maskfile in phaseMask['files'] :
                    maskname = maskfile.split('.')[0]
                    maskInfo = dataInst.m_optionInfo.find_maskinfo_by_blender_name(maskname)
                    if maskInfo != None :
                        maskInfo.Phase = phaseMask['phase']
            if self.m_tumorPhase != "" and self.m_targetKidney != "" :
                organlist = ["Kidney", "Tumor_exo", "Tumor_endo"]
                for organ in organlist :
                    maskInfo = dataInst.m_optionInfo.find_maskinfo_by_blender_name(organ)
                    if maskInfo != None :
                        maskInfo.Phase = self.m_tumorPhase
            
        else : 
            return False
        return True
    def _command_patientID(self) :
        dataInst = self.get_data()
        self.m_mediator.remove_all_key()
        dataInst.clear_patient()
        self.m_outputPath = self.getui_output_path()
        self.m_mediator.update_viewer()
    

    # protected
    def _get_userdata(self) -> userDataKidney.CUserDataKidney :
        return self.get_data().find_userdata(userDataKidney.CUserDataKidney.s_userDataKey)
    
    def _changed_input_path(self, inputPath) -> str:
        rootpath = ''
        huid = ''
        mkInputFold = makeInputFolder.CMakeInputFolder()
        mkInputFold.ZipPath = inputPath  #"D:\\jys\\StomachKidney_newfolder\\zippath" 
        mkInputFold.FolderMode = mkInputFold.eMode_Kidney 
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
        
        # get patientID
        patientID = '--'
        for dirfile in os.listdir(new_data_root_path) :
            if os.path.isdir(os.path.join(new_data_root_path,dirfile)) :
                patientID = dirfile

        self.m_dataRootPath = new_data_root_path
        self.m_patientID = patientID
        self._command_option_path() #sally 0526
        self._command_patientID()    #sally 0526

        return patientID 
     
    def _out_temp_auto_setting(self, new_data_root_path) :
        # OutTemp auto setting   
        outputTempPath = os.path.join(os.path.dirname(new_data_root_path), "OutTemp")
        if os.path.exists(outputTempPath) == False :
            os.makedirs(outputTempPath, exist_ok=True)
        self._changed_output_temp_path(outputTempPath)

    def do_blender(self) :
        dataInst = self.get_data()

        currPatientID = self.getui_patientID()
        if currPatientID == '' :
            print(f"ERROR : CurrPatientID is empty.")
            return
        stlPath = os.path.join(self.m_outputPath, currPatientID, "Result")
        savePath = os.path.join(self.m_dataRootPath, currPatientID, "02_SAVE", "02_BLENDER_SAVE")
        cmd = f"{dataInst.OptionInfo.BlenderExe} --python {os.path.join(self.fileAbsPath, 'blenderScriptKidney.py')} -- --patientID {currPatientID} --path {stlPath} --saveAs {savePath} --funcMode Basic"
        os.system(cmd)
         
    def _clicked_do_blender(self) :
        if self.m_reconKidney != None and self.m_reconReady == True:    
                self.do_blender()
                self.m_mediator.show_dialog("Do Blender Done!" )  
        else :
            print(f"tabStatereconKidney - Error : m_reconKidney None or m_reconReady False!")
            self.m_mediator.show_dialog(f"Do Blender FAIL! \nOption 또는 {CTabStatePatient.s_intermediatePathAlias} 경로를 확인해주세요.")
            
    def _clicked_recon_mask(self) :
        dataInst = self.get_data()
        if dataInst.OptionInfo.m_registrationInfo == None :
            self.m_mediator.show_dialog("ERROR !!!! : m_registrationInfo is None .")
            return
        if self.m_reconKidney != None and self.m_reconReady == True: 
            self.m_reconKidney.process()
            self.m_reconKidney.clear()
            self.do_blender()
            self.m_mediator.show_dialog("Reconstruction(.blend) Done.")
        else :
            self.m_mediator.show_dialog(f"Reconstruction FAIL! \nOption 또는 {CTabStatePatient.s_intermediatePathAlias} 경로를 확인해주세요.")
        
        # self._clicked_do_blender()

    def _clicked_overlap(self) :
        #Step1 : Auto01_Recon의 .blend의 obj들을 export.
        dataInst = self.get_data()
        currPatientID = self.getui_patientID()
        if currPatientID == '' :
            print(f"ERROR : CurrPatientID is empty.")
            return
        stlPath = os.path.join(self.m_outputPath, currPatientID, "Result")
        savePath = os.path.join(self.m_dataRootPath, currPatientID, "02_SAVE", "02_BLENDER_SAVE")
        cmd = f"{dataInst.OptionInfo.BlenderExe} -b --python {os.path.join(self.fileAbsPath, 'blenderScriptKidney.py')} -- --patientID {currPatientID} --path {stlPath} --saveAs {savePath} --funcMode Export"
        os.system(cmd)
        
        #Step2 : Overlap Detect 수행
        #Step3 : Detecting결과를 다시 .blend 에 import
        overlap = detectOverlap.CSubDetectOverlap()
        outputPatientFullPath = os.path.join(self.m_outputPath, currPatientID)
        overlap.StlPath = os.path.join(outputPatientFullPath, "ExportStl")
        overlap.LogPath = outputPatientFullPath
        overlap.process()
        # self.m_mediator.show_dialog(f"Detect Overlap Done")

        stlPath = os.path.join(outputPatientFullPath, "ExportStl")
        savePath = os.path.join(self.m_dataRootPath, currPatientID, "02_SAVE", "02_BLENDER_SAVE")
        cmd = f"{dataInst.OptionInfo.BlenderExe} --python {os.path.join(self.fileAbsPath, 'blenderScriptKidney.py')} -- --patientID {currPatientID} --path {stlPath} --saveAs {savePath} --funcMode ImportSave"
        os.system(cmd)
        
        self.m_mediator.show_dialog(f"OverlapDetection(.blend) Done.")

    def _clicked_separate_and_clean(self) :
        dataInst = self.get_data()
        currPatientID = self.getui_patientID()
        
        if currPatientID == '' :
            print(f"ERROR : CurrPatientID is empty.")
            return
        stlPath = os.path.join(self.m_outputPath, currPatientID, "Result")
        savePath = os.path.join(self.m_dataRootPath, currPatientID, "02_SAVE", "02_BLENDER_SAVE")
        cmd = f"{dataInst.OptionInfo.BlenderExe} -b --python {os.path.join(self.fileAbsPath, 'blenderScriptKidney.py')} -- --patientID {currPatientID} --path {stlPath} --saveAs {savePath} --funcMode SeparateClean"
        os.system(cmd)

        cmd = f"{dataInst.OptionInfo.BlenderExe} --python {os.path.join(self.fileAbsPath, 'blenderScriptKidney.py')} -- --patientID {currPatientID} --path {stlPath} --saveAs {savePath} --funcMode OpenBlend"
        os.system(cmd)
        
        self.m_mediator.show_dialog(f"Separate & Mesh-Clean Done")

    def _init_recon_kidney(self, tumorPhase) -> bool:
        if self.m_reconKidney == None :
            self.m_reconKidney = reconKidney.CSubReconKidney()
        self.m_reconKidney.OptionPath = self.m_optionFullPath
        self.m_reconKidney.PatientID = self.getui_patientID()
        unzipPath = self.m_editUnzipPath.text()
        maskRoot = os.path.join(unzipPath, self.getui_patientID(), "02_SAVE", "01_MASK")
        self.m_reconKidney.APPath = os.path.join(maskRoot, "Mask_AP")
        self.m_reconKidney.PPPath = os.path.join(maskRoot, "Mask_PP")
        self.m_reconKidney.DPPath = os.path.join(maskRoot, "Mask_DP")
        self.m_reconKidney.IntermediateDataPath = self.m_outputPath
        self.m_reconKidney.TumorPhase = tumorPhase
        #----------------------------------------------------------------------
        ### TODO Registration Info 셋팅 :sally 0602
        ## option과 mask data 경로까지 모두 정해진 이 시점에서 Registration 관련 셋팅이 이뤄져야함.
        ## option의 data.m_optionInfo.m_registrationInfo 가 None 상태일 것이므로, 
        ## Tumor의 phase를 찾아서 정합의 기준이 될 Kidney를 정하고, cyst의 phase도 알아놓고, registration info를 셋팅한다.
        # self.m_mediator.load_userdata()
        #registration info 셋팅은 recon init 직후에 하도록 함.
        # userData = self._get_userdata()        
        # self.m_reconKidney.TumorPhase = userData.TumorPhase #sally
        ##---------------------------------------------------------------------
        self.m_mediator.load_userdata()
        userData = self._get_userdata()
        dataInst = self.get_data()
        result = self.m_reconKidney.init(dataInst.OptionInfo, userData)
        return result
    # def _decim_clean_mesh_for_centerline_extraction(self) :        
    #     dataInst = self.get_data()
    #     if dataInst.Ready == False : 
    #         return 
    #     currPatientID = self.getui_patientID()
    #     if currPatientID == '' :
    #         print(f"Decimate&Mesh-Clean - ERROR : CurrPatientID is empty.")
    #         return
    #     terriStlPath = dataInst.get_terri_out_path()
    #     # blender background 실행
    #     saveAs = f"{currPatientID}.blend"
    #     cmd = f"{dataInst.OptionInfo.BlenderExe} -b --python {os.path.join(self.fileAbsPath, 'blenderScriptLung.py')} -- --patientID {currPatientID} --path {terriStlPath} --saveAs {saveAs} --funcMode CleanForCenterline"
    #     os.system(cmd)
    def _get_tumor_phase_with_kidney_name(self, dataRootPath, patientID) :
        tumor_phase = ""
        target_kidney = "" # 정합의 기준이 되는 Kidney name
        tumor = "Tumor_" # Tumor_* 가 있는 phase 기준으로 정합 수행(exo, endo 상관없이)
        phaseMaskList = []

        unzipPath = dataRootPath
        maskRoot = os.path.join(unzipPath, patientID, "02_SAVE", "01_MASK")
        apPath = os.path.join(maskRoot, "Mask_AP")
        ppPath = os.path.join(maskRoot, "Mask_PP")
        dpPath = os.path.join(maskRoot, "Mask_DP")        
        list_ap = os.listdir(apPath)
        list_pp = os.listdir(ppPath)
        list_dp = os.listdir(dpPath)
        phaseMaskList.append({'phase':'AP', 'files': list_ap})
        phaseMaskList.append({'phase':'PP', 'files': list_pp})
        phaseMaskList.append({'phase':'DP', 'files': list_dp})
        print(f"PhaseMaskList : {phaseMaskList}")
        tumorfindFlag = False
        targetfindFlag = False
        for phaseMask in phaseMaskList :
            for mask in phaseMask['files'] :
                if tumor in mask :
                    tumor_phase = phaseMask['phase']
                    tumorfindFlag = True
                    break
            if tumorfindFlag :
                for mask in phaseMask['files'] :
                    if 'Kidney' in mask :
                        target_kidney = mask
                        targetfindFlag = True
                        break
            if targetfindFlag :
                break
        if not tumorfindFlag :
            return "", "", None, phaseMaskList
        
        directionAndExtention = target_kidney.split(f"_{tumor_phase[0]}")[1]  # "Kidney_AL.nii.gz" -> "L.nii.gz"
        phases = ['AP','PP','DP']
        phases.remove(tumor_phase)
        srcs = []  # registration시 src가 되는 kidney 
        srcs.append(f"Kidney_{phases[0][0]}{directionAndExtention}")
        srcs.append(f"Kidney_{phases[1][0]}{directionAndExtention}")
        print(f"Tumor Phase : {tumor_phase}, Target Kidney : {target_kidney}, Src Kidney : {srcs}")   

        return tumor_phase, target_kidney, srcs, phaseMaskList
        
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

        self._out_temp_auto_setting(root_path)
        
    def _on_btn_unzip_path(self) : #sally
        unzipPath = QFileDialog.getExistingDirectory(self.get_main_widget(), "Select Output Path")
        self.m_editUnzipPath.setText(unzipPath) # Output 폴더구조 path
        if unzipPath != "" :
            option_path = self.m_editOptionPath.text()
            huid = self._changed_unzip_path(option_path, unzipPath)
            self.setui_reset_patientID([huid])

            ## _on_btn_input_zip_path() 수행시 감지된 huid와 현재 huid가 서로 다르면 다른 환자의 데이터를 가져오는 것이므로 input path 칸은 혼통 방지를 위해 클리어한다.
            if huid != self.m_zipPathPatientID : 
                self.m_editInputPath.setText("")
            
            self._out_temp_auto_setting(unzipPath)

    def _changed_output_temp_path(self, outputPath) :
        self.setui_output_path(outputPath)
        self.m_outputPath = outputPath

        tumorPhase = self.m_tumorPhase
        targetKidney = self.m_targetKidney
        srcKidney = self.m_srcKidney
        # tumorPhase, targetKidney, srcKidney = self._get_tumor_phase_with_kidney_name() => command_option_path() 로 옮김
        #----------------------------------------------------------------------
        # optionInfoInst = self.get_optioninfo()
        # listTmp = os.listdir(optionInfoInst.DataRootPath)
        # for patientID in listTmp :
        #     patientFullPath = os.path.join(optionInfoInst.DataRootPath, patientID)
        #     patientMaskFullPath = os.path.join(patientFullPath, "02_SAVE", "01_MASK", "AP")
        # dataInst = self.get_data()
        # dataInst.DataInfo.PatientPath = os.path.join(self.m_editUnzipPath.text(), self.m_zipPathPatientID)
        # dataInst.DataInfo.PatientID = self.m_zipPathPatientID
        #----------------------------------------------------------------------

        self.m_reconReady = self._init_recon_kidney(tumorPhase)

        
        # sally 0604
        # Tumor의 Phase를 기준으로 Registration Info 셋팅
        dataInst = self.get_data()
        if dataInst.OptionInfo.m_registrationInfo == None :
            print(f"Info : Registration info is None - Reset the registration information based on the tumor phase.")
            # userData = self._get_userdata()
            # if userData is None :
            #     return
            
            targetKidney = targetKidney.split('.')[0]
            srcKidney[0] = srcKidney[0].split('.')[0]
            srcKidney[1] = srcKidney[1].split('.')[0]
            infoList = []
            dic1 = {"Target" : f"{targetKidney}", "Src" : f"{srcKidney[0]}", "RigidAABB" : 0}
            dic2 = {"Target" : f"{targetKidney}", "Src" : f"{srcKidney[1]}", "RigidAABB" : 0}
            infoList.append(dic1)
            infoList.append(dic2)
            regInfo = {}
            regInfo["RegistrationInfo"] = infoList
            # "RegistrationInfo" : [
            #     {"Target" : "Kidney_DR", "Src" : "Kidney_AR", "RigidAABB" : 0},        
            #     {"Target" : "Kidney_DR", "Src" : "Kidney_PR", "RigidAABB" : 0}
            # ],
            dataInst.OptionInfo.m_registrationInfo = infoList #regInfo
            dataInst.OptionInfo._init_registration_info()
            print(f"New Reg Info : {regInfo}")
            self.m_mediator.show_dialog("입력데이터 로딩 완료. Recon 버튼을 클릭하세요!" ) 

    def _on_btn_output_temp_path(self) :
        outputPath = QFileDialog.getExistingDirectory(self.get_main_widget(), f"Select {CTabStatePatient.s_intermediatePathAlias} Path") 
        self._changed_output_temp_path(outputPath)

    # def _on_btn_recon_all(self) :
    #     pass
    # def _on_btn_check_mask(self) :
    #     self._check_mask()
    def _on_btn_recon(self) :
        self._clicked_recon_mask() #sally
    def _on_btn_overlap(self) :
        self._clicked_overlap()
    def _on_btn_separate_and_clean(self) :
        self._clicked_separate_and_clean()  #sally
        pass  #TODO
    def _on_btn_do_blender(self) :
        self._clicked_do_blender()
        
    def _on_cb_patientID_changed(self, index) :
        patientID = self.getui_patientID()
        if patientID == "" :
            print("not select patientID")
            return
        self._command_patientID()
    
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

