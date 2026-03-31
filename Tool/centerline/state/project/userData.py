import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
from pathlib import Path

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStatePath = os.path.dirname(fileAbsPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import data as data
import Block.makeInputFolder as makeInputFolder


class CUserData :
    s_phaseInfoFileName = "phaseInfo"


    def __init__(self, datainst : data.CData, mediator) :
        # input your code
        self.m_data = datainst
        self.m_mediator = mediator

        '''
        [
            {
                'phase' : phase, 
                'files' : [maskName0, maskName1, .. ]
            },
            ..
        ]
        '''
        self.m_phaseMaskList = None
        '''
        key : maskName
        value : phase
        '''
        self.m_dicMaskPhase = None
    def clear(self) :
        self.m_data = None
        self.m_mediator = None
        self._collecting_clear_mask_phase()
        # input your code

    def blender_process(self, blenderFullPath : str, scriptFullPath : str, optionFullPath : str, bBackground : bool = False) :
        '''
        Desc
            - blender script를 통해 blender를 실행한다.
        Input 
            - blenderFullPath : 로딩 할 blend 파일의 fullpath, None or ""인 경우 New로 blender를 실행한다.
            - scriptFullPath : blender가 실행해야 할 scirpt fullpath, None or ""인 경우 script 없이 실행한다.
            - optionFullPath : option.json의 fullpath, None or ""인 경우 option file의 경로를 지정하지 않는다. 
                                optionFullPath가 지정된 경우, 함수 내부에서 모든 처리 후 자동 삭제 된다. 
            - bBackground : blender를 background로 실행 시킬 여부 지정 
        '''
        optioninfo = self.Data.OptionInfo
        if optioninfo is None :
            return

        parts = []
        parts.append(f"{optioninfo.BlenderExe} ")

        if bBackground == True :
            parts.append("-b ")

        if blenderFullPath is not None and blenderFullPath != "" :
            if os.path.exists(blenderFullPath) == False :
                print("not found blender file")
                return
            parts.append(f"{blenderFullPath} ")
        
        if scriptFullPath is not None and scriptFullPath != "" :
            if os.path.exists(scriptFullPath) == False :
                print(f"not found script file : {os.path.basename(scriptFullPath)}")
                return
            parts.append(f"--python {scriptFullPath} ")
        
        if optionFullPath is not None and optionFullPath != "" :
            if os.path.exists(optionFullPath) == False :
                print(f"not found option file : {os.path.basename(optionFullPath)}")
                return
            parts.append(f"-- --optionFullPath {optionFullPath}")
        
        cmd = "".join(parts)
        os.system(cmd)

        # clear
        if optionFullPath and os.path.exists(optionFullPath) :
            os.remove(optionFullPath)
    def blender_exporter(self, blenderFullPath : str, listObjName : list, exportPath : str) :
        '''
        Desc
            - Res/common/bsmExport.py script를 통해 export를 수행 
        '''
        optioninfo = self.Data.OptionInfo
        if optioninfo is None :
            return

        scriptPath = os.path.join(self.ResPath, "common")
        scriptFullPath = os.path.join(scriptPath, "bsmExport.py")

        # blender 수행 
        # param 설정 
        '''
        param
            - "ListObjName"     : stl 파일들이 저장되어 있는 folder path, 없다면 "" 또는 None을 입력 
            - "ExportPath"      : export 할 folder path를 지정
        '''
        dicParam = {
            "ListObjName" : listObjName,
            "ExportPath" : exportPath
        }
        optionFullPath = self._blender_script_param(dicParam)
        self.blender_process(blenderFullPath, scriptFullPath, optionFullPath, True)
    
    
    # override
    def override_changed_optioninfo(self) :
        '''
        data에서 optioninfo가 바뀌었을 때 code 작성 
        '''
        self._collecting_clear_mask_phase()
    def override_recon(self) :
        '''
        reconstruction code 작성
        '''
        pass
    def override_individual_recon(self, phaseinfo : dict) :
        '''
        개별 reconstruction code 작성
        
        ret
            - phaseinfo : dict
                - key -> phase : str
                - value -> listFullPath : list (nii.gz or zip)
                       
        '''
        pass
    def override_clean(self, blenderFullPath : str) :
        '''
        해당 blenderFullPath의 mesh들을 clean 한다.  
        이 때, option 파일을 참고한다. 
        '''
        pass
    def override_load_centerline(self) :
        '''
        Main Tab에서 centerline button click시 작성 
        '''
        pass


    # protected
    def _blender_script_param(self, dicParam : dict) -> str :
        datainst = self.Data
        optioninfo = self.Data.OptionInfo

        os.makedirs(datainst.OutputPatientPath, exist_ok=True)
        optionFullPath = os.path.join(datainst.OutputPatientPath, "option.json")

        for key, param in dicParam.items() :
            optioninfo.set_user_value(key, param)
        optioninfo.save(optionFullPath)

        return optionFullPath

    def _copy_phaseinfo(self, targetPath : str, phaseinfo : dict) :
        for phase, listFullPath in phaseinfo.items() :
            folderPath = os.path.join(targetPath, phase)
            if not os.path.exists(folderPath) :
                os.makedirs(folderPath)

            tmpPath = os.path.join(targetPath, "tmp")
            if not os.path.exists(tmpPath) :
                os.makedirs(tmpPath)

            for fullPath in listFullPath :
                shutil.copy(fullPath, tmpPath)
            
            makeInputFolder.CFileOper.unzip_in_folder(tmpPath)
            makeInputFolder.CFileOper.copy_folder_ext(folderPath, tmpPath, ("nii.gz"))
            makeInputFolder.CFileOper.remove_folder(tmpPath)
            
            self.__copy_child_folder_nifti(folderPath)
    def _find_stl_path_from_out(self, targetPath : str) -> list :
        root = Path(targetPath)
        result = []

        for out_dir in root.rglob("out"):
            if out_dir.is_dir():
                for stl_file in out_dir.glob("*.stl"):
                    result.append(str(stl_file.resolve()))

        return result
    
    # collecting mask phase
    def _collecting_collect_mask_phase(self, targetPath) :
        self._collecting_clear_mask_phase()

        p = Path(targetPath)
        phaseList = [f.name for f in p.iterdir() if f.is_dir()]
        
        self.m_phaseMaskList = []
        for phase in phaseList :
            phaseFullPath = Path(targetPath) / phase
            if not phaseFullPath.is_dir() :
                continue

            maskList = [
                f.name[:-7]
                for f in phaseFullPath.iterdir()
                if f.is_file() and f.name.endswith(".nii.gz")
            ]

            if not maskList :
                continue

            self.m_phaseMaskList.append({'phase': phase, 'files': maskList})
        
        self.m_dicMaskPhase = {}
        for maskinfo in self.m_phaseMaskList :
            phase = maskinfo['phase']
            listMask = maskinfo['files']
            for maskName in listMask :
                self.m_dicMaskPhase[maskName] = phase
                # # tumor phase 감지
                # if tumorToken in maskName :
                #     tumorPhase = phase
                # # kidney phase 감지 
                # if kidneyToken in maskName :
                #     dicKidneyPhase[phase] = maskName
    def _collecting_clear_mask_phase(self) :
        if self.m_phaseMaskList is not None :
            self.m_phaseMaskList.clear()
        if self.m_dicMaskPhase is not None :
            self.m_dicMaskPhase.clear()
        self.m_phaseMaskList = None
        self.m_dicMaskPhase = None
    def _collecting_phase_count(self) -> int :
        return len(self.m_phaseMaskList)
    def _collecting_phase(self, inx : int) -> str :
        return self.m_phaseMaskList[inx]['phase']
    def _collecting_exist_phase(self, phase : str) -> bool :
        iCnt = self._collecting_phase_count()
        for inx in range(0, iCnt) :
            targetPhase = self._collecting_phase(inx)
            if targetPhase == phase :
                return True 
        return False 
    def _collecting_masknamelist_of_index(self, inx : int) -> list :
        return self.m_phaseMaskList[inx]['files']
    def _collecting_masknamelist_of_phase(self, phase : str) -> list :
        iCnt = self._collecting_phase_count()
        for inx in range(0, iCnt) :
            if phase == self.m_phaseMaskList[inx]['phase'] : 
                return self.m_phaseMaskList[inx]['files']
        return None
    def _collecting_masknamelist_of_keyword(self, keyword : str) -> list :
        retList = []

        for maskname, phase in self.m_dicMaskPhase.items() :
            if keyword in maskname :
                retList.append(maskname)
        
        if len(retList) == 0 :
            return None
        return retList
    def _collecting_search_maskname_in_phase(self, phase : str, keyword : str) -> list :
        retList = []

        iCnt = self._collecting_phase_count()
        for inx in range(0, iCnt) :
            targetPhase = self._collecting_phase(inx)
            if targetPhase != phase :
                continue

            listMask = self._collecting_masknamelist_of_index(inx)
            for maskName in listMask :
                if keyword in maskName :
                    retList.append(maskName)
            break
        
        if len(retList) == 0 :
            return None
        return retList
    def _collecting_search_phase_of_maskname(self, maskname : str) -> str :
        if maskname in self.m_dicMaskPhase :
            return self.m_dicMaskPhase[maskname]
        return ""
    def _collecting_search_phase_of_maskname_keyword(self, keyword : str) -> str :
        for maskname, phase in self.m_dicMaskPhase.items() :
            if keyword in maskname :
                return phase
        return ""


    # private 
    def __copy_child_folder_nifti(self, targetPath : str) :
        target = Path(targetPath)
        for item in target.iterdir() :
            if item.is_dir() :
                folderPath = str(item)
                self.__copy_nifti(targetPath, folderPath)
                shutil.rmtree(folderPath)
    def __copy_nifti(self, targetPath : str, folderPath : str) :
        target = Path(targetPath)
        target.mkdir(parents=True, exist_ok=True)
        
        for file in Path(folderPath).rglob("*.nii.gz"):
            shutil.copy2(file, target / file.name)


    @property
    def Data(self) -> data.CData :
        return self.m_data
    @property
    def Mediator(self) :
        return self.m_mediator
    @property
    def ResPath(self) :
        optioninfoPath = ""
        if self.Data.OptionInfo is None :
            return ""
        else :
            optioninfoPath = self.Data.OptionInfoPath
        return os.path.join(optioninfoPath, "Res")

    

if __name__ == '__main__' :
    pass


# print ("ok ..")

