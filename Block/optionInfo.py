import sys
import os
import numpy as np
import pickle 
import copy

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algLinearMath as algLinearMath
# import example_vtk.frameworkVTK as frameworkVTK


import json


class COptionInfo() :
    s_version = "Common Pipeline v2.1"


    def __init__(self, jsonPath : str) -> None :
        self.m_bReady = False
        self.m_jsonPath = jsonPath
        self.m_jsonData = None

        self.m_version = None
        self.m_dataRootPath = ""
        self.m_cl = ""

        self.m_regInfo = None

        self.m_resamplingToMinSpacing = None
        self.m_resamplingToPhase = None

        self.m_stricture = None

        self.m_recon = None

        self.m_meshBoolean = None
        self.m_meshDecimation = None
        self.m_meshHealing = None

        self.m_blender = None

        self.m_centerline = None
        self.m_targetTerritoryList = None

        self.m_dicPhaseInfo = {}

        self.reload()

    def clear(self) :
        self.m_bReady = False

        self.m_version = None
        self.m_dataRootPath = ""
        self.m_cl = ""

        self.m_regInfo = None

        self.m_resamplingToMinSpacing = None
        self.m_resamplingToPhase = None

        self.m_stricture = None

        self.m_recon = None

        self.m_meshBoolean = None
        self.m_meshDecimation = None
        self.m_meshHealing = None

        self.m_blender = None

        self.m_centerline = None
        self.m_targetTerritoryList = None

        self.m_dicPhaseInfo.clear()

        self.m_jsonPath = ""
        self.m_jsonData = None

    def reload(self) :
        jsonPath = self.m_jsonPath
        self.clear()
        self.m_jsonPath = jsonPath
        
        with open(self.m_jsonPath, 'r', encoding="utf-8") as fp :
            self.m_jsonData = json.load(fp)
        if self.m_jsonData is None or len(self.m_jsonData) == 0 :
            print(f"not found {self.m_jsonPath}")
            return
        
        if "Version" in self.m_jsonData :
            self.m_version = self.m_jsonData["Version"]
        else :
            print("optionInfo warning : not found Version")
        
        if self.m_version["Release"] != COptionInfo.s_version :
            print(f"invalid version : must be {COptionInfo.s_version}")
            return

        if "DataRootPath" in self.m_jsonData :
            self.m_dataRootPath = self.m_jsonData["DataRootPath"]
        else :
            print("optionInfo warning : not found DataRootPath")
        if "CL" in self.m_jsonData :
            self.m_cl = self.m_jsonData["CL"]
        else :
            print("optionInfo warning : not found CL")
        
        if "RegistrationInfo" in self.m_jsonData :
            self.m_regInfo = self.m_jsonData["RegistrationInfo"]
        else :
            print("optionInfo warning : not found RegistrationInfo")
        
        if "ResamplingToMinSpacing" in self.m_jsonData :
            self.m_resamplingToMinSpacing = self.m_jsonData["ResamplingToMinSpacing"]
        else :
            print("optionInfo warning : not found ResamplingToMinSpacing")
        if "ResamplingToPhase" in self.m_jsonData :
            self.m_resamplingToPhase = self.m_jsonData["ResamplingToPhase"]
        else :
            print("optionInfo warning : not found ResamplingToPhase")

        if "Stricture" in self.m_jsonData :
            self.m_stricture = self.m_jsonData["Stricture"]
        else :
            print("optionInfo warning : not found Stricture")
        
        if "Recon" in self.m_jsonData :
            self.m_recon = self.m_jsonData["Recon"]
        else :
            print("optionInfo warning : not found Recon")
        
        if "MeshBoolean" in self.m_jsonData :
            self.m_meshBoolean = self.m_jsonData["MeshBoolean"]
        else :
            print("optionInfo warning : not found MeshBoolean")
        if "MeshDecimation" in self.m_jsonData :
            self.m_meshDecimation = self.m_jsonData["MeshDecimation"]
        else :
            print("optionInfo warning : not found MeshDecimation")
        if "MeshHealing" in self.m_jsonData :
            self.m_meshHealing = self.m_jsonData["MeshHealing"]
        else :
            print("optionInfo warning : not found MeshHealing")
        
        if "Blender" in self.m_jsonData :
            self.m_blender = self.m_jsonData["Blender"]
        else :
            print("optionInfo warning : not found Blender")
        
        if "Centerline" in self.m_jsonData :
            self.m_centerline = self.m_jsonData["Centerline"]
        else :
            print("optionInfo warning : not found Centerline")
        if "TargetTerritoryList" in self.m_jsonData :
            self.m_targetTerritoryList = self.m_jsonData["TargetTerritoryList"]
        else :
            print("optionInfo warning : not found TargetTerritoryList")
        
        self.process_phase_alignment()

        self.m_bReady = True

    def save(self, fullPath : str) :
        os.makedirs(os.path.dirname(fullPath), exist_ok=True)
        with open(fullPath, "w", encoding="utf-8") as f :
            json.dump(self.m_jsonData, f, indent=4, ensure_ascii=False)

    def get_version_release(self) -> str :
        if self.m_version is None :
            return ""
        if "Release" not in self.m_version["Release"] :
            return ""
        return self.m_version["Release"]
    def get_version_desc(self) -> str :
        if self.m_version is None :
            return ""
        if "DESC" not in self.m_version["DESC"] :
            return ""
        return self.m_version["DESC"]
    
    def get_registrationinfo_count(self) -> int :
        if self.m_regInfo is None :
            return 0
        return len(self.m_regInfo)
    def get_registrationinfo(self, inx : int) -> tuple :
        '''
        ret : (TargetMaskName, SrcMaskName, RigidAABB)
               default : None
        '''
        if inx >= self.get_registrationinfo_count() :
            return None
        
        targetMaskName = self.m_regInfo[inx]["Target"]
        srcMaskName = self.m_regInfo[inx]["Src"]
        rigidAABB = self.m_regInfo[inx]["RigidAABB"]
        return (targetMaskName, srcMaskName, rigidAABB)
    def add_registrationinfo(self, target : str, src : str, rigidAABB : int) :
        if self.m_regInfo is None :
            self.m_jsonData["RegistrationInfo"] = []
            
        self.m_regInfo = self.m_jsonData["RegistrationInfo"]
        tmp = {}
        tmp["Target"] = target
        tmp["Src"] = src
        tmp["RigidAABB"] = rigidAABB
        self.m_regInfo.append(tmp)
    def clear_registrationinfo(self) :
        if self.m_regInfo is None :
            self.m_jsonData["RegistrationInfo"] = []
            self.m_regInfo = self.m_jsonData["RegistrationInfo"]
        self.m_regInfo.clear()
    
    def get_resampling_minspacing_count(self) -> int :
        if self.m_resamplingToMinSpacing is None : 
            return 0
        return len(self.m_resamplingToMinSpacing)
    def get_resampling_minspacing(self, inx : int) -> tuple :
        '''
        ret : (inMaskName, outMaskName)
               default : None
        '''
        if inx >= self.get_resampling_minspacing_count() :
            return None
        
        inMaskName = self.m_resamplingToMinSpacing[inx][0]
        outMaskName = self.m_resamplingToMinSpacing[inx][1]
        return (inMaskName, outMaskName)
    def get_resampling_phase_count(self) -> int :
        if self.m_resamplingToPhase is None : 
            return 0
        return len(self.m_resamplingToPhase)
    def get_resampling_phase(self, inx : int) -> tuple :
        '''
        ret : (inMaskName, outMaskName, phase)
               default : None
        '''
        if inx >= self.get_resampling_phase_count() :
            return None
        
        inMaskName = self.m_resamplingToPhase[inx][0]
        outMaskName = self.m_resamplingToPhase[inx][1]
        phase = self.m_resamplingToPhase[inx][2]
        return (inMaskName, outMaskName, phase)
    def add_resampling_phase(self, inMaskName : str, outMaskName : str, phase : str) :
        if self.m_resamplingToPhase is None :
            self.m_jsonData["ResamplingToPhase"] = []
            self.m_resamplingToPhase = self.m_jsonData["ResamplingToPhase"]
        self.m_resamplingToPhase.append([inMaskName, outMaskName, phase])
    def clear_resampling_phase(self) :
        if self.m_resamplingToPhase is None :
            self.m_jsonData["ResamplingToPhase"] = []
            self.m_resamplingToPhase = self.m_jsonData["ResamplingToPhase"]
        self.m_resamplingToPhase.clear()

    
    def get_stricture_count(self) -> int :
        if self.m_stricture is None :
            return 0
        return len(self.m_stricture)
    def get_stricture(self, inx : int) -> tuple :
        '''
        ret : (inMaskName, outMaskName)
               default : None
        '''
        if inx >= self.get_stricture_count() :
            return None 
        
        inMaskName = self.m_stricture[inx][0]
        outMaskName = self.m_stricture[inx][1]
        return (inMaskName, outMaskName)
    
    def get_recon_count(self) -> int :
        if self.m_recon is None :
            return 0
        return len(self.m_recon)
    def get_recon_info(self, inx : int) -> tuple :
        '''
        ret : (contour, gaussian, algorithm, resamplingFactor)
               default : None
        '''
        if inx >= self.get_recon_count() :
            return None
        
        contour = self.m_recon[inx]["contour"]
        gaussian = self.m_recon[inx]["gaussian"]
        algorithm = self.m_recon[inx]["algorithm"]
        resamplingFactor = self.m_recon[inx]["resampling factor"]
        return (contour, gaussian, algorithm, resamplingFactor)
    def get_recon_param_count(self, inx : int) -> int :
        if inx >= self.get_recon_count() :
            return 0
        return len(self.m_recon[inx]["param"])
    def get_recon_param(self, reconInx : int, paramInx : int) -> tuple :
        '''
        ret : (iter, relax, deci)
               default : None
        '''
        if reconInx >= self.get_recon_count() :
            return None 
        if paramInx >= self.get_recon_param_count(reconInx) :
            return None
        
        iter = self.m_recon[reconInx]["param"][paramInx][0]
        relax = self.m_recon[reconInx]["param"][paramInx][1]
        deci = self.m_recon[reconInx]["param"][paramInx][2]
        return (iter, relax, deci)
    def get_recon_list_count(self, inx : int) -> int :
        if inx >= self.get_recon_count() :
            return 0
        return len(self.m_recon[inx]["List"])
    def get_recon_list(self, reconInx : int, listInx : int) -> tuple :
        '''
        ret : (maskName, blenderName, phase, triCnt)
               default : None
        '''
        if reconInx >= self.get_recon_count() :
            return None 
        if listInx >= self.get_recon_list_count(reconInx) :
            return None
        
        maskName = self.m_recon[reconInx]["List"][listInx][0]
        blenderName = self.m_recon[reconInx]["List"][listInx][1]
        phase = self.m_recon[reconInx]["List"][listInx][2]
        triCnt = self.m_recon[reconInx]["List"][listInx][3]
        return (maskName, blenderName, phase, triCnt)
    def set_recon_phase(self, maskName : str, phase : str) :
        retInx = self.find_recon_index_of_maskname(maskName)
        if retInx is None :
            return

        reconInx = retInx[0]
        listInx = retInx[1]
        self.m_recon[reconInx]["List"][listInx][2] = phase
    def set_recon_blendername(self, maskName : str, blendername : str) :
        retInx = self.find_recon_index_of_maskname(maskName)
        if retInx is None :
            return

        reconInx = retInx[0]
        listInx = retInx[1]
        self.m_recon[reconInx]["List"][listInx][1] = blendername
    
    def get_mesh_boolean_count(self) -> int :
        if self.m_meshBoolean is None :
            return 0
        return len(self.m_meshBoolean)
    def get_mesh_boolean(self, inx : int) -> tuple :
        '''
        ret : (oper, blenderName0, blenderName1, outBlenderName2)
               default : None
        '''
        if inx >= self.get_mesh_boolean_count() :
            return None
        
        oper = self.m_meshBoolean[inx][0]
        blenderName0 = self.m_meshBoolean[inx][1]
        blenderName1 = self.m_meshBoolean[inx][2]
        outBlenderName2 = self.m_meshBoolean[inx][3]
        return (oper, blenderName0, blenderName1, outBlenderName2)
    def get_mesh_decimation_count(self) -> int :
        if self.m_meshDecimation is None :
            return 0
        return len(self.m_meshDecimation)
    def get_mesh_decimation(self, inx : int) -> tuple :
        '''
        ret : (blenderName, triCnt)
               default : None
        '''
        if inx >= self.get_mesh_decimation_count() :
            return None
        
        blenderName = self.m_meshDecimation[inx][0]
        triCnt = self.m_meshDecimation[inx][1]
        return (blenderName, triCnt)
    def get_mesh_healing_count(self) -> int :
        if self.m_meshHealing is None :
            return 0
        return len(self.m_meshHealing)
    def get_mesh_healing(self, inx : int) -> tuple :
        '''
        ret : (blenderName, fillHole : int (0 or 1))
               default : None
        '''
        if inx >= self.get_mesh_healing_count() :
            return None
        
        blenderName = self.m_meshHealing[inx][0]
        fillHole = self.m_meshHealing[inx][1]
        return (blenderName, fillHole)
    
    def get_centerline_count(self) -> int :
        if self.m_centerline is None :
            return 0
        return len(self.m_centerline)
    def get_centerline_info(self, inx :int) -> tuple :
        '''
        ret : (advancementRatio, resamplingLength, smoothingIter, smoothingFactor)
               default : None
        '''
        if inx >= self.get_centerline_count() :
            return None
        
        advancementRatio = self.m_centerline[inx]["advancementRatio"]
        resamplingLength = self.m_centerline[inx]["resamplingLength"]
        smoothingIter = self.m_centerline[inx]["smoothingIter"]
        smoothingFactor = self.m_centerline[inx]["smoothingFactor"]
        return (advancementRatio, resamplingLength, smoothingIter, smoothingFactor)
    def get_centerline_list_count(self, inx : int) -> int :
        if inx >= self.get_centerline_count() :
            return 0
        return len(self.m_centerline[inx]["List"])
    def get_centerline_list(self, clInx : int, listInx : int) -> tuple :
        '''
        ret : (blenderName, jsonName)
               default : None
        '''
        if clInx >= self.get_centerline_count() :
            return None
        if listInx >= self.get_centerline_list_count(clInx) :
            return None
        
        blenderName = self.m_centerline[clInx]["List"][listInx][0]
        jsonName = self.m_centerline[clInx]["List"][listInx][1]
        return (blenderName, jsonName)
    
    def get_target_territory_list_count(self) -> int :
        if self.m_targetTerritoryList is None :
            return 0
        return len(self.m_targetTerritoryList)
    def get_target_territory_list(self, inx : int) -> str :
        if inx >= self.get_target_territory_list_count() : 
            return None
        return self.m_targetTerritoryList[inx]


    def find_phase_of_mask(self, maskName : str) -> str :
        iReconCnt = self.get_recon_count()
        for reconInx in range(0, iReconCnt) :
            iListCnt = self.get_recon_list_count(reconInx) 
            for listInx in range(0, iListCnt) :
                _maskName, _blenderName, _phase, _triCnt = self.get_recon_list(reconInx, listInx)
                if _maskName == maskName :
                    return _phase
        return ""
    def find_rigid_aabb_of_mask(self, maskName : str) -> int :
        maskPhase = self.find_phase_of_mask(maskName)

        iRegCnt = self.get_registrationinfo_count() 
        for regInx in range(0, iRegCnt) :
            targetMask, srcMask, rigidAABB = self.get_registrationinfo(regInx)
            regPhase = self.find_phase_of_mask(srcMask)

            if regPhase == maskPhase :
                return rigidAABB
        return 0
    def find_rigid_aabb_of_phase(self, phase : str) -> int :
        iRegCnt = self.get_registrationinfo_count() 
        for regInx in range(0, iRegCnt) :
            targetMask, srcMask, rigidAABB = self.get_registrationinfo(regInx)
            regPhase = self.find_phase_of_mask(srcMask)

            if regPhase == phase :
                return rigidAABB
        return 0
    def find_centerline_index_of_blendername(self, blenderName : str) -> int :
        if self.m_centerline is None :
            return -1
        
        iCLCnt = self.get_centerline_count()
        for clInx in range(0, iCLCnt) :
            iListCnt = self.get_centerline_list_count(clInx)
            for listInx in range(0, iListCnt) :
                _blenderName, _jsonName = self.get_centerline_list(clInx, listInx)
                if _blenderName == blenderName :
                    return clInx
        
        return -1
    def find_tricnt_of_blendername(self, blenderName : str) -> int :
        if self.m_recon is None :
            return -1
        iReconCnt = self.get_recon_count()
        for reconInx in range(0, iReconCnt) :
            iListCnt = self.get_recon_list_count(reconInx)
            for listInx in range(0, iListCnt) :
                _, _blenderName, _, triCnt = self.get_recon_list(reconInx, listInx)
                if blenderName == _blenderName :
                    return triCnt
        return -1
    def add_centerline_list_name(self, clInx : int, blenderName : str, jsonName : str) :
        if self.m_centerline is None :
            return 
        
        dic = self.m_centerline[clInx]
        listName = dic["List"]
        listName.append([blenderName, jsonName])
    def find_recon_index_of_maskname(self, maskName : str) -> tuple :
        '''
        ret : (reconInx, listInx)
              None : 해당 maskName이 존재하지 않음 
        '''
        if self.m_recon is None :
            return None
        iReconCnt = self.get_recon_count()
        for reconInx in range(0, iReconCnt) :
            iListCnt = self.get_recon_list_count(reconInx)
            for listInx in range(0, iListCnt) :
                _maskName, _, _, _ = self.get_recon_list(reconInx, listInx)
                if _maskName == maskName :
                    return (reconInx, listInx)
        return None
    def find_recon_parameter_of_blendername(self, blenderName : str) -> tuple : 
        '''
        ret : (contour, gaussian, algorithm, resampling, listReconParam, triCnt)
        '''
        if self.m_recon is None :
            return None
        iReconCnt = self.get_recon_count()
        for reconInx in range(0, iReconCnt) :
            iListCnt = self.get_recon_list_count(reconInx)
            for listInx in range(0, iListCnt) :
                _, _blenderName, _, triCnt = self.get_recon_list(reconInx, listInx)
                if blenderName == _blenderName :
                    contour, gaussian, algorithm, resampling = self.get_recon_info(reconInx)
                    listReconParam = self.m_recon[reconInx]["param"]
                    return (contour, gaussian, algorithm, resampling, listReconParam, triCnt)
        return None
    
    def get_phase_mask_list(self, phase : str) -> list :
        if phase in self.m_dicPhaseInfo :
            return self.m_dicPhaseInfo[phase]
        return None
    def get_phase_list(self) -> list :
        listPhase = list(self.m_dicPhaseInfo.keys())
        listPhase = [phase for phase in listPhase if phase != ""]
        return listPhase

    # user key-value 
    def set_user_value(self, key : str, value) :
        self.m_jsonData[key] = value
    def get_user_value(self, key : str) :
        if key in self.m_jsonData :
            return self.m_jsonData[key]
        else :
            return None


    # protected 
    def process_phase_alignment(self) :
        self.m_dicPhaseInfo.clear()

        iReconCnt = self.get_recon_count()
        for reconInx in range(0, iReconCnt) :
            iListCnt = self.get_recon_list_count(reconInx)
            for listInx in range(0, iListCnt) :
                maskName, blenderName, phase, triCnt = self.get_recon_list(reconInx, listInx)

                if phase not in self.m_dicPhaseInfo :
                    self.m_dicPhaseInfo[phase] = []
                self.m_dicPhaseInfo[phase].append(maskName)


    @property
    def Ready(self) -> bool :
        return self.m_bReady
    @property
    def JsonData(self) -> dict :
        return self.m_jsonData
    @property
    def DataRootPath(self) -> str :
        return self.m_dataRootPath
    @DataRootPath.setter
    def DataRootPath(self, dataRootPath : str) :
        self.m_dataRootPath = dataRootPath
    @property
    def CL(self) -> str :
        return self.m_cl
    @property
    def BlenderExe(self) -> str :
        if self.m_blender is None :
            return ""
        return self.m_blender["BlenderExe"]



if __name__ == '__main__' :
    pass


# print ("ok ..")

