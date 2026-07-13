import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import copy
import SimpleITK as sitk
from pathlib import Path
import subRecon.subReconLiver as reconLiver
import progressWindow as PW
from PySide6.QtWidgets import QDialog, QMessageBox

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
import Block.makeInputFolder as makeInputFolder

import data as data

import userData as userData

import command.commandRecon as commandRecon
import commandReconCommon as commandReconCommon
import command.commandVesselKnife as commandVesselKnife
from collections import deque
from collections import defaultdict

import liver.subDetectOverlap.subDetectOverlapLiver as detectOverlap

import vtkObjInterface as vtkObjInterface

import graphVessel

class CTPVessel :
    s_tpVesselKeyType = "TPVessel"
    s_tpRadius = 1.6


    def __init__(self, groupID : int, id : int, label : str, pos : np.ndarray, color : np.ndarray) :
        tpPolyData = algVTK.CVTK.create_poly_data_sphere(
        algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0]), 
        CTPVessel.s_tpRadius
                )
        
        keyType = CTPVessel.s_tpVesselKeyType
        key = data.CData.make_key(keyType, groupID, id)

        self.m_tpVesselObj = vtkObjInterface.CVTKObjInterface()
        self.m_tpVesselObj.KeyType = keyType
        self.m_tpVesselObj.Key = key
        self.m_tpVesselObj.Color = color
        self.m_tpVesselObj.Opacity = 0.5
        self.m_tpVesselObj.PolyData = tpPolyData
        self.m_tpVesselObj.Pos = pos

        self.m_label = label
        self.m_id = id
    def clear(self) :
        self.m_label = ""
        self.m_tpVesselObj.clear()
        self.m_tpVesselObj = None
        self.m_id = -1

    @property
    def TPVesselObj(self) -> vtkObjInterface.CVTKObjInterface :
        return self.m_tpVesselObj
    @property
    def Label(self) -> str :
        return self.m_label
    @property
    def ID(self) -> int :
        return self.m_id


class CUserDataLiver(userData.CUserData) :
    s_userDataKey = "Liver"
    s_intermediatePathAlias = "OutTemp"
    
    s_tpClinfoIdxMapper = {
        "TP_S1":0,
        "TP_S2":0,
        "TP_S3":0,
        "TP_S4":0,
        "TP_S23":0,
        "TP_S34":0,
        "TP_S24":0,
        "TP_S234":0,
        "TP_S5":0,
        "TP_S6":0,
        "TP_S7":0,
        "TP_S8":0,
        "TP_S56":0,
        "TP_S57":0,
        "TP_S58":0,
        "TP_S67":0,
        "TP_S68":0,
        "TP_S78":0,
        "TP_S567":0,
        "TP_S568":0,
        "TP_S578":0,
        "TP_S678":0,
        "TP_S5678":0,
        "TP_LPV":0,
        "TP_RPV":0,
        "TP_RHV":1,
        "TP_LHV":1,
        "TP_MHV":1,
        "TP_IHV":1,
        "TP_CA":2,
        "TP_CD":3
    }

    def __init__(self, data : data.CData, mediator):
        super().__init__(data, CUserDataLiver.s_userDataKey)
        # input your code
        self.m_mediator = mediator
        
        self.m_resPath = ""
        self.m_scriptPath = ""
        self.m_reconScriptFullPath = ""
        self.m_cleanScriptFullPath = ""
        self.m_remodelingSaveScriptFullPath = ""

        self.m_movingBlenderPath = ""
        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""
        self.m_localReconBlenderFullPath = ""
        self.m_localCleanBlenderFullPath = ""
        self.m_outputOverlapBlenderFullPath = ""
        self.m_outputReconBlenderFullPath = ""
        self.m_outputCleanBlenderFullPath = ""
        self.m_registrationMethod = ""
        self.m_tumorSegSet = set()
        self.m_listTPBlenderName = defaultdict(list)
        self.m_listTPVesselGroup = []
        
        try:
            # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = "."
        except AttributeError:
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))

        self.m_makeInputFolder = makeInputFolder.CMakeInputFolder()

        self.MovingBlenderPath = ""
    def clear(self) :
        # input your code
        self.m_mediator = None
        # input your code
        self.m_resPath = ""
        self.m_scriptPath = ""
        self.m_reconScriptFullPath = ""
        self.m_cleanScriptFullPath = ""
        self.m_remodelingSaveScriptFullPath = ""

        self.m_movingBlenderPath = ""
        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""
        self.m_localReconBlenderFullPath = ""
        self.m_localCleanBlenderFullPath = ""
        self.m_outputOverlapBlenderFullPath = ""
        self.m_outputReconBlenderFullPath = ""
        self.m_outputCleanBlenderFullPath = ""
        self.m_registrationMethod = ""
        self.m_tumorSegSet = set()

        self.m_makeInputFolder.clear()
        self.m_listTPBlenderName.clear()
        self.m_listTPVesselGroup = []

        super().clear()
        
        
    def _generate_progress_window(self, instance):
        dialog = PW.ProgressWindow(self.m_mediator, instance)
        result = dialog.exec()

        if result == QDialog.Accepted:
            QMessageBox.information(self.m_mediator, "Done", "작업이 완료되었습니다!")
            return True
        elif result == QDialog.Rejected:
            QMessageBox.warning(self.m_mediator, "Canceled", "작업이 취소되었습니다.")
            return False
        

    def set_patient_zippath(self, zipPath : str) :
        dataInst = self.Data
        self.MakeInputFolder.clear()
        self.MakeInputFolder.ZipPath = zipPath
        self.MakeInputFolder.OptionInfo = dataInst.OptionInfo
        self.MakeInputFolder.process()

        dataRootPath = self.MakeInputFolder.DataRootPath
        patientID = self.MakeInputFolder.PatientID

        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""

        if self.MakeInputFolder.Ready == True :
            # dataInst refresh 
            self.m_outputTempPath = os.path.join(os.path.dirname(dataRootPath), CUserDataLiver.s_intermediatePathAlias)
            self.m_outputTempPatientPath = os.path.join(self.m_outputTempPath, patientID)
            if os.path.exists(self.m_outputTempPath) == False :
                os.makedirs(self.m_outputTempPath, exist_ok=True)

            dataInst.PatientID = patientID
            dataInst.OutputPath = self.m_outputTempPath
            self.MovingBlenderPath = self.MakeInputFolder.BlenderSavePath
            
        else :
            dataInst.PatientID = ""
            dataInst.OutputPath = ""
            self.MovingBlenderPath = ""
            return
        
        self._refresh_optioninfo()

    def load_patient(self) -> bool :
        if super().load_patient() == False :
            return False
        # input your code
        
        return True
    

    # override
    def override_changed_optioninfo(self) :
        super().override_changed_optioninfo()

        # input your code
        if self.Data.OptionInfo is None :
            optioninfoPath = ""
        else :
            optioninfoPath = self.Data.OptionInfoPath

        self.m_resPath = os.path.join(optioninfoPath, "Res")
        self.m_commonPath = os.path.join(self.m_resPath, "common")
        self.m_scriptPath = os.path.join(self.m_resPath, "liver_batch")
        self.m_reconScriptFullPath = os.path.join(self.m_scriptPath, "bspRecon.py")
        self.m_individualReconScriptFullPath = os.path.join(self.m_scriptPath, "bspIndRecon.py")
        self.m_cleanScriptFullPath = os.path.join(self.m_scriptPath, "bspClean.py")
        self.m_remodelingSaveScriptFullPath = os.path.join(self.m_scriptPath, "bspRemodelingSave.py")
        #self.m_cleanScriptFullPath = os.path.join(self.m_commonPath, "bsmClean.py")

        self.MakeInputFolder.clear()

        self.m_movingBlenderPath = ""
        self.m_outputTempPath = ""
        self.m_outputTempPatientPath = ""
        self.m_localReconBlenderFullPath = ""
        self.m_localCleanBlenderFullPath = ""
        self.m_outputReconBlenderFullPath = ""
        self.m_outputOverlapBlenderFullPath = ""
        self.m_outputCleanBlenderFullPath = ""
    def override_recon(self, inputSliceID) :
        dataInst = self.Data
        optioninfo = dataInst.OptionInfo
        
        # print("get_phase_list()!", file=sys.__stdout__, flush=True)
        # print(optioninfo.get_phase_list(), file=sys.__stdout__, flush=True)
        folderInfo = self.MakeInputFolder

        # dataRoot의 Mask를 OutTemp로 복사
        copiedMaskPath = os.path.join(dataInst.OutputPatientPath, "Mask")
        if os.path.exists(self.OutputReconBlenderFullPath) == False :
            folderInfo.copy_mask(copiedMaskPath)
        reconStlPath = os.path.join(dataInst.OutputPatientPath, "Result")
        blendSavePath = dataInst.OutputPatientPath

        if self.m_registrationMethod == "rigid":
            self.reset_warped_mask_name()
            self._refresh_optioninfo()
        else:
            dicom_zip_path = os.path.join(self.MakeInputFolder.m_zipPath, self.MakeInputFolder.sZip_Dicom)
            if not os.path.exists(dicom_zip_path):
                QMessageBox.information(self.m_mediator, "Alarm", "Need Diccom to non-rigid registration")
                return
            

        # recon 수행 
        reconInst = reconLiver.CSubReconLiver()
        reconInst.m_registrationMethod = self.m_registrationMethod
        reconInst.InputSliceID = inputSliceID
        reconInst.m_folderInfo = folderInfo
        reconInst.IntermediateDataPath = dataInst.OutputPatientPath
        reconInst.InputData = self.Data
        success = self._generate_progress_window(reconInst)
        reconInst.clear()
        if not success:
            return

        # blender 수행 
        '''
        param
            - "InputPath"       : import 할 mesh file들이 있는 folder  
            - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로
        '''
        dicParam = {
            "InputPath" : reconStlPath,
            "SaveFullPath" : self.m_localReconBlenderFullPath
        }
        optionFullPath = self._blender_script_param(dicParam)
        scriptFullPath = self.m_reconScriptFullPath

        # blenderExe = optioninfo.BlenderExe
        
        #self.m_reconScriptFullPath = os.path.join(self.fileAbsPath, 'blenderScriptLiver.py')
        # saveName = os.path.basename(self.m_localReconBlenderFullPath)
        # saveName = saveName.split('.')[0]
        #userData.CUserData.blender_process(blenderExe, scriptFullPath, dataInst.PatientID, "Basic", optioninfo.m_jsonPath, reconStlPath, blendSavePath, saveName, False)
        #userData.CUserData.blender_process(blenderExe, scriptFullPath, dataInst.PatientID, "Basic", optioninfo.m_jsonPath, reconStlPath, blendSavePath, saveName, False)
        self.blender_process(None, scriptFullPath, optionFullPath, False)

        # save blender folder로 move 
        if self.m_movingBlenderPath:
            src = self.m_localReconBlenderFullPath
            dst_dir = self.m_movingBlenderPath
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, os.path.basename(src))
            try:
                os.replace(src, dst)
            except OSError:
                shutil.move(src, dst)
    def override_overlap(self):
        reconBlenderFullPath = self.m_outputReconBlenderFullPath
        if os.path.exists(reconBlenderFullPath) == False :
            print("not found blender file")
            return
        
        datainst = self.Data
        
        # 원본 blender는 복사 후 rename 
        shutil.copy2(reconBlenderFullPath, self.OutputOverlapBlenderFullPath)
        overlapBlenderFullPath = self.OutputOverlapBlenderFullPath

        listBlenderName = ["Artery", "Vein", "Portal", "Duct"]

        # blender 파일에서 listBlenderName 목록에 대해서만 clean 수행 
        # param 설정 
        '''
        param
            - "ListMeshName"    : clean-up 할 mesh name, None or 원소가 없다면 전체를 clean-up 한다.
            - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로, None or "" 라면 덮어쓴다. 
        '''
        dicParam = {
            "ListMeshName" : listBlenderName,
            "SaveFullPath" : None
        }
        scriptFullPath = self.m_cleanScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(overlapBlenderFullPath, scriptFullPath, optionFullPath, True)

        # export 
        exportPath = os.path.join(datainst.OutputPatientPath, "Overlap")
        self.blender_exporter(overlapBlenderFullPath, listBlenderName, exportPath)

        # overlap
        overlapinst = detectOverlap.CSubDetectOverlap()
        overlapinst.StlPath = exportPath
        overlapinst.LogPath = datainst.OutputPatientPath
        overlapinst.process()

        # import
        '''
        param
            - "StlPath"         : stl 파일들이 저장되어 있는 folder path, 없다면 "" 또는 None을 입력 
            - "ListStlFullPath  : stl파일들의 전체 경로를 저장한 list, 없다면 None을 입력 
        
        desc 
            - 기존 내용에 추가적으로 stl 파일들을 import 한다. 
        '''
        dicParam = {
            "StlPath" : exportPath,
            "ListStlFullPath" : None
        }
        scriptPath = os.path.join(self.ResPath, "common")
        scriptFullPath = os.path.join(scriptPath, "bsmImportStl.py")
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(overlapBlenderFullPath, scriptFullPath, optionFullPath, False)

        # clear 
        if os.path.exists(exportPath) == True :
            shutil.rmtree(exportPath)
            
            
        
    def override_clean(self) :
        overlapBlenderFullPath = self.OutputOverlapBlenderFullPath
        if os.path.exists(overlapBlenderFullPath) == False :
            return
        
        datainst = self.Data

        # 원본 blender는 복사 후 rename 
        shutil.copy2(overlapBlenderFullPath, self.OutputCleanBlenderFullPath)
        cleanBlenderFullPath = self.OutputCleanBlenderFullPath

        # # blender 파일에 대해 import 수행 
        # listStlPath = self._find_stl_path_from_out(datainst.OutputPatientPath)
        # if len(listStlPath) > 0 :
        #     '''
        #     param
        #         - "StlPath"         : stl 파일들이 저장되어 있는 folder path, 없다면 "" 또는 None을 입력 
        #         - "ListStlFullPath  : stl파일들의 전체 경로를 저장한 list, 없다면 None을 입력 
            
        #     desc 
        #         - 기존 내용에 추가적으로 stl 파일들을 import 한다. 
        #     '''
        #     dicParam = {
        #         "StlPath" : None,
        #         "ListStlFullPath" : listStlPath
        #     }
        #     scriptPath = os.path.join(self.ResPath, "common")
        #     scriptFullPath = os.path.join(scriptPath, "bsmImportStl.py")
        #     optionFullPath = self._blender_script_param(dicParam)
        #     self.blender_process(cleanBlenderFullPath, scriptFullPath, optionFullPath, True)

        # blender 파일에 대해 clean 수행  
        # param 설정 
        '''
        param
            - "ListMeshName"    : clean-up 할 mesh name, None or 원소가 없다면 전체를 clean-up 한다.
            - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로, None or "" 라면 덮어쓴다. 
        '''
        dicParam = {
            "ListMeshName" : None,
            "SaveFullPath" : None
        }
        scriptFullPath = self.m_cleanScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(cleanBlenderFullPath, scriptFullPath, optionFullPath, False)
    
    def remodeling_blender_save(self):
        dataInst = self.Data
        folderInfo = self.MakeInputFolder
        patientID = folderInfo.PatientID
        saveName = f"{patientID}_remodel"
        dirPath = os.path.dirname(self.m_outputReconBlenderFullPath)
        
        remodelBlenderPath = os.path.join(dirPath, f"{saveName}.blend")
        reconStlPath = dataInst.get_terri_out_path()
        
        '''
        param
            - "StlPath"    : remodeling된 stl 파일들이 저장되어 있는 folder path
            - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로
            - "OverWriteFlag" : 동일 이름 mesh가 있을 때 덮어 쓸지
        '''
        
        if os.path.exists(remodelBlenderPath) == False :
            if os.path.exists(self.OutputCleanBlenderFullPath) == False :
                return

            # 원본 blender는 복사 후 rename 
            shutil.copy2(self.OutputCleanBlenderFullPath, remodelBlenderPath)
            dicParam = {
                "StlPath" : reconStlPath,
                "SaveFullPath" : remodelBlenderPath,
                "OverWriteFlag" : str(1)
            }
            
        else:
            msg = QMessageBox()
            msg.setWindowTitle("Save Remodel Blender")
            msg.setText(f"이미 {saveName}.blend 가 존재합니다. 새로 remodeling된 혈관으로 덮어씌우겠습니까?")
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.Ok)

            result = msg.exec()

            if result == QMessageBox.Ok:
                dicParam = {
                    "StlPath" : reconStlPath,
                    "SaveFullPath" : remodelBlenderPath,
                    "OverWriteFlag" : str(1)
                }
            elif result == QMessageBox.No:
                dicParam = {
                    "StlPath" : reconStlPath,
                    "SaveFullPath" : remodelBlenderPath,
                    "OverWriteFlag" : str(0)
                }

        scriptFullPath = self.m_remodelingSaveScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(remodelBlenderPath, scriptFullPath, optionFullPath, False)
        
    def clean_remodel_blender(self):
        folderInfo = self.MakeInputFolder
        patientID = folderInfo.PatientID
        saveName = f"{patientID}_remodel"
        dirPath = os.path.dirname(self.m_outputReconBlenderFullPath)
        
        remodelBlenderPath = os.path.join(dirPath, f"{saveName}.blend")
        cleanBlenderFullPath = remodelBlenderPath

        '''
        param
            - "ListMeshName"    : clean-up 할 mesh name, None or 원소가 없다면 전체를 clean-up 한다.
            - "SaveFullPath"    : 저장 할 blend 파일명의 전체 경로, None or "" 라면 덮어쓴다. 
        '''
        dicParam = {
            "ListMeshName" : None,
            "SaveFullPath" : None
        }
        scriptFullPath = self.m_cleanScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(cleanBlenderFullPath, scriptFullPath, optionFullPath, True)
    
    

    # protected
    def _refresh_optioninfo(self) :
        if self.MakeInputFolder.Ready == False :
            return
        optioninfo = self.Data.OptionInfo
        if optioninfo is None :
            return
        folderInfo = self.MakeInputFolder

        dataRootPath = self.MakeInputFolder.DataRootPath
        optioninfo.DataRootPath = dataRootPath
        
        
        maskPath = folderInfo.MaskPath
        p = Path(maskPath)
        phaseList = [f.name for f in p.iterdir() if f.is_dir()]

        phaseMaskList = []
        for phase in phaseList :
            phaseFullPath = Path(maskPath) / phase
            if not phaseFullPath.is_dir() :
                continue

            maskList = [
                f.name[:-7]
                for f in phaseFullPath.iterdir()
                if f.is_file() and f.name.endswith(".nii.gz")
            ]

            if not maskList :
                continue

            phaseMaskList.append({'phase': phase, 'files': maskList})

        '''
        key : maskName
        value : phase
        '''
        dicMaskPhase = {}
        for maskinfo in phaseMaskList :
            phase = maskinfo['phase']
            listMask = maskinfo['files']
            for maskName in listMask :
                dicMaskPhase[maskName] = phase

        # optioninfo mask의 phase refresh
        iCnt = optioninfo.get_recon_count()
        for reconInx in range(0, iCnt) :
            listCnt = optioninfo.get_recon_list_count(reconInx)
            for listInx in range(0, listCnt) :
                maskName, _, _, _ = optioninfo.get_recon_list(reconInx, listInx)
                phase = ""
                if maskName in dicMaskPhase :
                    phase = dicMaskPhase[maskName]
                optioninfo.set_recon_phase(maskName, phase)

        self._post_refresh_optioninfo()
    def _post_refresh_optioninfo(self) :
        dataInst = self.Data
        optioninfo = dataInst.OptionInfo
        
        # ResamplingToPhase 
        iCnt = optioninfo.get_resampling_phase_count()
        for inx in range(0, iCnt) :
            _, outMaskName, phase = optioninfo.get_resampling_phase(inx)
            optioninfo.set_recon_phase(outMaskName, phase)
        # ResamplingToMinSpacing 
        iCnt = optioninfo.get_resampling_minspacing_count()
        for inx in range(0, iCnt) :
            inMaskName, outMaskName = optioninfo.get_resampling_minspacing(inx)
            inPhase = optioninfo.find_phase_of_mask(inMaskName)
            optioninfo.set_recon_phase(outMaskName, inPhase)
        # Stricture 
        iCnt = optioninfo.get_stricture_count()
        for inx in range(0, iCnt) :
            inMaskName, outMaskName = optioninfo.get_stricture(inx)
            inPhase = optioninfo.find_phase_of_mask(inMaskName)
            optioninfo.set_recon_phase(outMaskName, inPhase)

        optioninfo.process_phase_alignment()
        
    def get_tp_vessel_count(self, groupID : int) -> int :
        tpVesselGroup = self.get_tp_vessel_group(groupID)
        return len(tpVesselGroup)
    def find_tp_vessel_by_key(self, groupID : int, tpVesselObjKey : str) -> CTPVessel :
        tpVesselGroup = self.get_tp_vessel_group(groupID)
        for key, tpVessel in tpVesselGroup.items() :
            if key == tpVesselObjKey :
                return tpVessel
        return None

    def get_tp_vessel_group(self, groupID : int) -> dict :
        '''
        key : tpObjKey
        value : CTPVessel
        '''
        if len(self.m_listTPVesselGroup) > groupID:
            return self.m_listTPVesselGroup[groupID]
        else:
            for inx in range(0, groupID+1) :
                self.m_listTPVesselGroup.append({})
            return

    def _find_TP_blender_name(self) :
        dataInst = self.Data
        stlPath = os.path.join(dataInst.OutputPatientPath, "Result")
        
        for fileName in os.listdir(stlPath):
            blenderName = os.path.splitext(fileName)[0]
            #if tokens[-1] == "TPa" :
            if blenderName in self.s_tpClinfoIdxMapper.keys():
                self.m_listTPBlenderName[self.s_tpClinfoIdxMapper[blenderName]].append(blenderName)
        
    def override_load_centerline(self) :
        self._find_TP_blender_name()

        iCnt = self.Data.get_skelinfo_count()
        if iCnt == 0 :
            return 
        for inx in range(0, iCnt) :
            self.m_listTPVesselGroup.append({})
            self._create_tp_vessel_obj(inx, self.m_listTPBlenderName[inx])
            
        return True
    
    def add_tp_vessel(self, groupID : int, index : int, label : str, pos : np.ndarray, color : np.ndarray) -> CTPVessel : 
        tpVesselGroup = self.m_listTPVesselGroup[groupID]
        tpVessel = CTPVessel(groupID, index, label, pos, color)
        key = tpVessel.TPVesselObj.Key
        tpVesselGroup[key] = tpVessel
        
        self.Data.add_vtk_obj(tpVessel.TPVesselObj)
        return tpVessel
    
    def _create_tp_vessel_obj(self, groupID : int, listTPBlenderName : str) :
        self.m_listTPVesselGroup[groupID].clear()
        dataInst = self.Data
        stlPath = os.path.join(dataInst.OutputPatientPath, "Result")
        index = 0
        
        skeleton = self.Data.get_skeleton(groupID)
        graphvessel = graphVessel.CNodeGraph(skeleton)
        if skeleton:
            graphvessel.build_graph()
        
        if len(graphvessel.m_IDtoNode.keys()) > 1 and skeleton != None:
            visitedNodeID = set()
            visitedNodeID.add(graphvessel.m_startNode.ID)
            nodeQueue = deque([graphvessel.m_startNode])
            
            while nodeQueue:
                node = nodeQueue.popleft()
                
                for clID in node.m_seedCLID:
                #clID = node.m_listCLID[0]
                    cl = skeleton.get_centerline(clID)
                    vertexInx = int(cl.get_vertex_count() / 2)
                    pos = cl.get_vertex(vertexInx)
                    color = self.m_mediator.get_cl_color(node.Name)
                    label = node.Name
                    self.add_tp_vessel(groupID, index, label, pos, color)
                    index += 1
                
                for adjNodeID in graphvessel.m_graph[node.ID]:
                    if adjNodeID in visitedNodeID:
                        continue
                    adjNode = graphvessel.m_IDtoNode[adjNodeID]
                    nodeQueue.append(adjNode)
                    visitedNodeID.add(adjNodeID)
            
        else:
            label_to_color = {}
            for tpBlenderName in listTPBlenderName :
                tpFullPath = os.path.join(stlPath, f"{tpBlenderName}.stl")
                if os.path.exists(tpFullPath) == False :
                    continue
                

                polyData = algVTK.CVTK.load_poly_data_stl(tpFullPath)
                listPolyData = algVTK.CVTK.get_sub_polydata(polyData)
                
                if "START" in tpBlenderName:
                    tpBlenderName = "_".join(tpBlenderName.split("_")[-2:])
                else:
                    tpBlenderName = tpBlenderName.split("_")[-1]
                    
                label = tpBlenderName
                for subPolyData in listPolyData :
                    pos = algVTK.CVTK.get_polydata_center(subPolyData)
                    if label not in label_to_color.keys():
                        color = np.array(self.m_mediator.m_colorList[index]).reshape(-1, 3)
                        label_to_color[label] = color
                    else:
                        color = label_to_color[label]
                    #color = self.get_color(index)
                    self.add_tp_vessel(groupID, index, label, pos, color)
                    index += 1
    
    
    def override_individual_recon(self, phaseinfo : dict) :
        dataInst = self.Data
        optioninfo = dataInst.OptionInfo
        folderinfo = self.MakeInputFolder

        tmpMaskPath = os.path.join(dataInst.OutputPatientPath, "tmpMask")
        self._copy_phaseinfo(tmpMaskPath, phaseinfo)

        # targetMaskPath -> dataRoot Mask로 복사
        # dataRoot Mask -> OutTemp로 복사
        # optioninfo refresh
        copiedMaskPath = os.path.join(dataInst.OutputPatientPath, "IndividualMask")
        for phase, _ in phaseinfo.items() :
            targetMaskPath = os.path.join(tmpMaskPath, phase)
            folderinfo.copy_target_mask(targetMaskPath, phase, copiedMaskPath)
            

        if os.path.exists(tmpMaskPath) == True :
            shutil.rmtree(tmpMaskPath)

        self._refresh_optioninfo()
        reconStlPath = os.path.join(dataInst.OutputPatientPath, "IndividualResult")

        if self.m_registrationMethod == "rigid":
            self.reset_warped_mask_name()
            self._refresh_optioninfo()
        else:
            dicom_zip_path = os.path.join(self.MakeInputFolder.m_zipPath, self.MakeInputFolder.sZip_Dicom)
            if not os.path.exists(dicom_zip_path):
                QMessageBox.information(self.m_mediator, "Alarm", "Need Diccom to non-rigid registration")
                return

        # recon 수행 
        reconInst = reconLiver.CSubReconLiver()
        reconInst.m_registrationMethod = self.m_registrationMethod
        reconInst.m_folderInfo = self.MakeInputFolder
        reconInst.IntermediateDataPath = dataInst.OutputPatientPath
        reconInst.InputData = self.Data
        reconInst.m_resultPath = reconStlPath
        reconInst.m_maskCpyPath = copiedMaskPath
        success = self._generate_progress_window(reconInst)
        reconInst.clear()
        if not success:
            return

        '''
        param
            - "InputPath"       : import 할 mesh file들이 있는 folder  
        '''
        dicParam = {
            "InputPath" : reconStlPath
        }
        scriptFullPath = self.m_individualReconScriptFullPath
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(self.OutputReconBlenderFullPath, scriptFullPath, optionFullPath, False)
 
        # remove input, output folders
        if os.path.exists(copiedMaskPath) == True :
            shutil.rmtree(copiedMaskPath)
        if os.path.exists(reconStlPath) == True :
            shutil.rmtree(reconStlPath)

    @property
    def Data(self) -> data.CData :
        return self.m_data
    @property
    def MovingBlenderPath(self) -> str :
        return self.m_movingBlenderPath
    @MovingBlenderPath.setter
    def MovingBlenderPath(self, movingBlenderPath : str) :
        folderInfo = self.MakeInputFolder
        patientID = folderInfo.PatientID

        self.m_movingBlenderPath = movingBlenderPath

        # saveName = f"{patientID}_recon_{timestr}"
        saveName = f"{patientID}_recon"
        self.m_localReconBlenderFullPath = os.path.join(self.OutputTempPatientPath, f"{saveName}.blend")
        if self.m_movingBlenderPath == "" :
            self.m_outputReconBlenderFullPath = self.m_localReconBlenderFullPath
        else :
            self.m_outputReconBlenderFullPath = os.path.join(self.m_movingBlenderPath, f"{saveName}.blend")
        
        saveName = f"{patientID}_overlap"
        dirPath = os.path.dirname(self.m_outputReconBlenderFullPath)
        self.m_outputOverlapBlenderFullPath = os.path.join(dirPath, f"{saveName}.blend")

        saveName = f"{patientID}_clean"
        dirPath = os.path.dirname(self.m_outputReconBlenderFullPath)
        self.m_outputCleanBlenderFullPath = os.path.join(dirPath, f"{saveName}.blend")
    
    def reset_warped_mask_name(self):
        dataInst = self.Data
        iReconCnt = dataInst.OptionInfo.get_recon_count()
        for ri in range(iReconCnt):
            iReconListCnt = dataInst.OptionInfo.get_recon_list_count(ri)
            for rli in range(iReconListCnt):
                maskName, blenderName, phase, triCnt = dataInst.OptionInfo.get_recon_list(ri, rli)
                if "warped_resampled_" in maskName:
                    dataInst.OptionInfo.set_recon_maskname(maskName, maskName.split("warped_resampled_")[1])
        
    @property
    def OutputTempPath(self) -> str :
        return self.m_outputTempPath
    @property
    def OutputTempPatientPath(self) -> str :
        return self.m_outputTempPatientPath
    @property
    def OutputReconBlenderFullPath(self) -> str :
        return self.m_outputReconBlenderFullPath
    @property
    def OutputCleanBlenderFullPath(self) -> str :
        return self.m_outputCleanBlenderFullPath
    @property
    def OutputOverlapBlenderFullPath(self) -> str :
        return self.m_outputOverlapBlenderFullPath
    @property
    def MakeInputFolder(self) -> makeInputFolder.CMakeInputFolder :
        return self.m_makeInputFolder
    @property
    def Data(self) -> data.CData :
        return self.m_data

    

if __name__ == '__main__' :
    pass


# print ("ok ..")

