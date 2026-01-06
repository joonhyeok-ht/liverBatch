import sys
import os
import numpy as np
import vtk
import json
import re
import pickle 
import copy

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileToolPath = os.path.dirname(fileAbsPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algVTK as algVTK
import AlgUtil.algImage as algImage

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer

import VtkObj.vtkObj as vtkObj


class CSkelInfo :
    def __init__(self) :
        self.m_advancementRatio = 1.001
        self.m_resamplingLength = 1.0
        self.m_smoothingIter = 10
        self.m_smoothingFactor = 0.1

        self.m_blenderName = ""
        self.m_jsonName = ""
        self.m_skeleton = None
    def clear(self) :
        self.m_advancementRation = 1.001
        self.m_resamplingLength = 1.0
        self.m_smoothingIter = 10
        self.m_smoothingFactor = 0.1

        self.m_blenderName = ""
        self.m_jsonName = ""
        if self.m_skeleton is not None :
            self.m_skeleton.clear()
    

    @property
    def AdvancementRatio(self) -> float :
        return self.m_advancementRatio
    @AdvancementRatio.setter
    def AdvancementRatio(self, advancementRatio : float) :
        self.m_advancementRatio = advancementRatio
    @property
    def ResamplingLength(self) -> float :
        return self.m_resamplingLength
    @ResamplingLength.setter
    def ResamplingLength(self, resamplingLength : float) :
        self.m_resamplingLength = resamplingLength
    @property
    def SmoothingIter(self) -> int :
        return self.m_smoothingIter
    @SmoothingIter.setter
    def SmoothingIter(self, smoothingIter : int) :
        self.m_smoothingIter = smoothingIter
    @property
    def SmoothingFactor(self) -> float :
        return self.m_smoothingFactor
    @SmoothingFactor.setter
    def SmoothingFactor(self, smoothingFactor : float) :
        self.m_smoothingFactor = smoothingFactor
    
    @property
    def BlenderName(self) -> str :
        return self.m_blenderName
    @BlenderName.setter
    def BlenderName(self, blenderName : str) :
        self.m_blenderName = blenderName
    @property
    def JsonName(self) -> str :
        return self.m_jsonName
    @JsonName.setter
    def JsonName(self, jsonName : str) :
        self.m_jsonName = jsonName
    
    @property
    def Skeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_skeleton
    @Skeleton.setter
    def Skeleton(self, skeleton : algSkeletonGraph.CSkeleton) :
        self.m_skeleton = skeleton
    


class CTerritoryInfo :
    def __init__(self) :
        self.m_blenderName = ""
        self.m_mat = None
        self.m_invMat = None
        self.m_queryVertex = None
        self.m_organInfo = None
    def clear(self) :
        self.m_blenderName = ""
        self.m_mat = None
        self.m_invMat = None
        self.m_queryVertex = None
        self.m_organInfo = None

    def voxelize(self, polyData : vtk.vtkPolyData, spacing) :
        self.m_organInfo = algVTK.CVTK.poly_data_voxelize(polyData, spacing, 255.0)
        self.m_mat = algVTK.CVTK.get_phy_matrix(self.m_organInfo[1], self.m_organInfo[2], self.m_organInfo[3])
        self.m_invMat = algLinearMath.CScoMath.inv_mat4(self.m_mat)
        self.m_queryVertex = algImage.CAlgImage.get_vertex_from_np(self.m_organInfo[0], np.int32)

    
    @property
    def BlenderName(self) -> str :
        return self.m_blenderName
    @BlenderName.setter
    def BlenderName(self, blenderName : str) :
        self.m_blenderName = blenderName
    @property
    def Mat(self) -> np.ndarray :
        return self.m_mat
    @property
    def InvMat(self) -> np.ndarray :
        return self.m_invMat
    @property
    def QueryVertex(self) -> np.ndarray :
        return self.m_queryVertex
    @property
    def OrganInfo(self) :
        return self.m_organInfo


class CData :
    s_anaconda_env = "hutom-solution-common"
    s_anaconda_env_cl = "hutom-solution"
    s_version = "1.0"
    s_fileName = "dataInfo"     # json 파일명 

    s_vesselType = "vessel"
    s_organType = "organ"
    s_territoryType = "territory"
    s_skelTypeCenterline = "centerline"
    s_skelTypeBranch = "branch"
    s_skelTypeEndPoint = "endPoint"
    s_skelTypeVertex = "vertex"
    s_outsideKeyType = "outsideCLType"
    s_textType = "text"

    s_clSize = 0.4
    s_clColor = algLinearMath.CScoMath.to_vec3([0.3, 0.3, 0.0])
    s_rootCLColor = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])
    s_selectionCLColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])

    s_brSize = 0.5
    s_brColor = algLinearMath.CScoMath.to_vec3([1.0, 0.647, 0.0])
    s_selectionBrColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])

    s_epSize = 0.5
    s_epColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])
    s_selectionEPColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
    
    s_vertexSize = 0.4
    s_vertexColor = algLinearMath.CScoMath.to_vec3([0.0, 0.3, 0.3])
    s_selectionVertexColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])

    @staticmethod
    def make_key(type : str, groupID : int, id : int) -> str :
        key = f"{type}_{groupID}_{id}"
        return key
    @staticmethod
    def get_type_from_key(key : str) -> str :
        type, groupID, id = key.split("_")
        return type
    @staticmethod
    def get_groupID_from_key(key : str) -> int :
        type, groupID, id = key.split("_")
        return int(groupID)
    @staticmethod
    def get_id_from_key(key : str) -> int :
        type, groupID, id = key.split("_")
        return int(id)
    @staticmethod
    def get_keyinfo(key : str) -> tuple :
        type, groupID, id = key.split("_")
        return type, int(groupID), int(id)
    @staticmethod
    def get_list_index(targetList : list, value : str) -> int :
        try:
            index = targetList.index(value)
            return index
        except ValueError:
            return -1
    

    def __init__(self) :
        '''
        key : string id
        value : (polyData, color, opacity)
        '''
        self.m_optionInfo = None
        self.m_outputPath = ""
        self.m_patientID = ""

        self.m_phase = None

        self.m_dicUserData = {}

        self.m_clinfoIndex = -1

        self.m_dicObj = {}
        self.m_listSkelInfo = []
        self.m_listTerriInfo = []
        self.m_clinfoIndexList = []
    def clear(self) : 
        self.clear_patient()

        self.m_outputPath = ""
        self.m_patientID = ""
        if self.m_optionInfo is not None :
            self.OptionInfo.clear()
        self.m_optionInfo = None

        self.m_clinfoIndex = -1
    def clear_patient(self) :
        for key, obj in self.m_dicObj.items() :
            obj.clear()
        self.m_dicObj.clear()

        for skelinfo in self.m_listSkelInfo :
            skelinfo.clear()
        self.m_listSkelInfo.clear()

        for terriInfo in self.m_listTerriInfo :
            terriInfo.clear()
        self.m_listTerriInfo.clear()
        
        # for clIndexInfo in self.m_clinfoIndexList :
        #     clIndexInfo.clear()
        self.m_clinfoIndexList.clear()

        if self.Phase is not None :
            self.Phase.clear()
        self.Phase = None

        for key, userData in self.m_dicUserData.items() :
            userData.clear()
        self.m_dicUserData.clear()

        self.m_clinfoIndex = -1
    
    def save(self, fullPath : str) -> bool :
        '''
        fullPath : dataInfo.json의 full 경로 
        '''
        if self.Ready == False :
            print("failed save data")
            return False
        dicData = {}
        
        iSkelInfoCnt = self.get_skelinfo_count()
        listSkelInfo = []
        for inx in range(0, iSkelInfoCnt) :
            skelinfo = self.get_skelinfo(inx)
            tmp = [skelinfo.AdvancementRatio, skelinfo.ResamplingLength, skelinfo.SmoothingIter, skelinfo.SmoothingFactor, skelinfo.BlenderName, skelinfo.JsonName]
            listSkelInfo.append(tmp)
        
        iTerriInfoCnt = self.get_terriinfo_count()
        listTerriInfo = []
        for inx in range(0, iTerriInfoCnt) :
            terriinfo = self.get_terriinfo(inx)
            listTerriInfo.append(terriinfo.BlenderName)

        dicData["skelInfo"] = listSkelInfo
        dicData["terriInfo"] = listTerriInfo

        with open(fullPath, "w", encoding="utf-8") as f :
            json.dump(dicData, f, ensure_ascii=False, indent=4)

        return True
    def load(self, fullPath : str) -> bool :
        '''
        fullPath : dataInfo.json의 full 경로 
        '''
        if self.Ready == False :
            print("failed load : not ready")
            return False
        
        patientID = self.PatientID
        self.clear_patient()
        self.PatientID = patientID

        if os.path.exists(fullPath) == False :
            return False 
        with open(fullPath, 'r', encoding="utf-8") as fp :
            dicData = json.load(fp)
        
        iSkelInfoCnt = len(dicData["skelInfo"])
        for inx in range(0, iSkelInfoCnt) :
            listTmp = dicData["skelInfo"][inx]

            skelinfo = CSkelInfo()
            skelinfo.AdvancementRatio = listTmp[0]
            skelinfo.ResamplingLength = listTmp[1]
            skelinfo.SmoothingIter = listTmp[2]
            skelinfo.SmoothingFactor = listTmp[3]
            skelinfo.BlenderName = listTmp[4]
            skelinfo.JsonName = listTmp[5]
            self.add_skelinfo(skelinfo)
        
        iTerriInfoCnt = len(dicData["terriInfo"])
        for inx in range(0, iTerriInfoCnt) :
            tmp = dicData["terriInfo"][inx]

            terriinfo = CTerritoryInfo()
            terriinfo.BlenderName = tmp
            self.add_terriinfo(terriinfo)
        
        return True


    def get_cl_path(self) -> str :
        patientPath = self.OutputPatientPath
        clPath = os.path.join(patientPath, "SkelInfo")
        return clPath
    def get_cl_in_path(self) -> str :
        clInPath = os.path.join(self.get_cl_path(), "in")
        return clInPath
    def get_cl_out_path(self) -> str :
        clOutPath = os.path.join(self.get_cl_path(), "out")
        return clOutPath
    def get_terri_path(self) -> str :
        patientPath = self.OutputPatientPath
        terriPath = os.path.join(patientPath, "TerriInfo")
        return terriPath
    def get_terri_in_path(self) -> str :
        terriInPath = os.path.join(self.get_terri_path(), "in")
        return terriInPath
    def get_terri_out_path(self) -> str :
        terriOutPath = os.path.join(self.get_terri_path(), "out")
        return terriOutPath
    def add_clinfoIndex(self, inx : int):
        self.m_clinfoIndexList.append(inx)
    def add_userdata(self, key : str, userData) :
        self.m_dicUserData[key] = userData
    def get_userdata_count(self) -> int :
        return len(self.m_dicUserData)
    def get_clinfoIndex_count(self) -> int :
        return len(self.m_clinfoIndexList)
    def find_userdata(self, key : str) :
        if key in self.m_dicUserData : 
            return self.m_dicUserData[key]
        return None
    def get_userdata(self) :
        for key, userData in self.m_dicUserData.items() :
            return userData
        return None
    def remove_userdata(self, key : str) :
        userData = self.m_dicUserData.pop(key, None)
        if userData is not None :
            userData.clear()
    def remove_all_userdata(self) :
        for key, userData in self.m_dicUserData.items() :
            userData.clear()
        self.m_dicUserData.clear()
    
    def add_vtk_obj(self, vtkObj : vtkObj.CVTKObj) :
        # vtkObj.Key = key
        key = vtkObj.Key
        self.m_dicObj[key] = vtkObj
    def get_obj_count(self) -> int :
        return len(self.m_dicObj)
    def find_obj_by_key(self, key : str) -> vtkObj.CVTKObj :
        if key in self.m_dicObj :
            return self.m_dicObj[key]
        return None
    def find_obj_list_by_type(self, type : str) -> list :
        retList = []
        for key, obj in self.m_dicObj.items() :
            _type = CData.get_type_from_key(key)
            if _type == type :
                retList.append(obj)
        
        if len(retList) == 0 : 
            return None
        return retList
    def find_obj_list_by_type_groupID(self, type : str, groupID : int) -> list :
        retList = []
        for key, obj in self.m_dicObj.items() :
            _type, _groupID, _id = CData.get_keyinfo(key)
            if _type == type and _groupID == groupID :
                retList.append(obj)
        
        if len(retList) == 0 : 
            return None
        return retList
    def find_key_by_obj(self, obj : vtkObj.CVTKObj) -> str :
        key = next((k for k, v in self.m_dicObj.items() if v == obj), None)
        return key
    def find_key_list_by_type(self, type : str) -> list :
        retList = []
        for key, obj in self.m_dicObj.items() :
            _type = CData.get_type_from_key(key)
            if _type == type :
                retList.append(key)
        
        if len(retList) == 0 : 
            return None
        return retList
    def find_key_list_by_type_groupID(self, type : str, groupID : int) -> list :
        retList = []
        for key, obj in self.m_dicObj.items() :
            _type, _groupID, _id = CData.get_keyinfo(key)
            if _type == type and _groupID == groupID :
                retList.append(key)
        
        if len(retList) == 0 : 
            return None
        return retList

    def detach_key(self, key : str) -> vtkObj.CVTKObj :
        detachedObj = self.m_dicObj.pop(key, None)
        if detachedObj is not None :
            return detachedObj
        return None
    def remove_key(self, key : str) :
        removedObj = self.m_dicObj.pop(key, None)
        if removedObj is not None :
            removedObj.clear()
            removedObj = None
    def remove_all_key(self) : 
        for key, obj in self.m_dicObj.items() :
            obj.clear()
        self.m_dicObj.clear()
        
    def get_clinfoIndex(self, inx : int) -> CTerritoryInfo :
        return self.m_clinfoIndexList[inx]
    def clear_clinfoIndex(self) :
        self.m_clinfoIndexList = []
        
    def add_skelinfo(self, skelinfo : CSkelInfo) :
        self.m_listSkelInfo.append(skelinfo)
    def get_skelinfo_count(self) -> int :
        return len(self.m_listSkelInfo)
    def get_skelinfo(self, inx : int) -> CSkelInfo :
        return self.m_listSkelInfo[inx]
    def remove_skelinfo(self, inx : int):
        self.m_listSkelInfo.pop(inx)
    def get_skeleton(self, inx : int) -> algSkeletonGraph.CSkeleton :
        skelinfo = self.get_skelinfo(inx)
        if skelinfo is None :
            return None
        return skelinfo.Skeleton

    def add_terriinfo(self, terriinfo : CTerritoryInfo) :
        self.m_listTerriInfo.append(terriinfo)
    def get_terriinfo_count(self) -> int :
        return len(self.m_listTerriInfo)
    def get_terriinfo(self, inx : int) -> CTerritoryInfo :
        return self.m_listTerriInfo[inx]
    

    # protected

    @property
    def Ready(self) -> bool :
        optionInfoInst = self.OptionInfo
        if optionInfoInst is None :
            return False
        if self.OutputPath == "" :
            return False
        if self.PatientID == "" :
            return False
        return True
    @property
    def OptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_optionInfo
    @OptionInfo.setter
    def OptionInfo(self, optionInfo : optionInfo.COptionInfo) :
        self.m_optionInfo = optionInfo
    @property
    def OptionInfoPath(self) -> str :
        if self.OptionInfo is None :
            return ""
        return os.path.dirname(self.OptionInfo.m_jsonPath)
    @property
    def OutputPath(self) -> str :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath
    @property
    def PatientID(self) -> str :
        return self.m_patientID
    @PatientID.setter
    def PatientID(self, patientID : str) :
        self.m_patientID = patientID
    @property
    def OutputPatientPath(self) -> str :
        return os.path.join(self.OutputPath, self.PatientID)

    @property
    def Phase(self) -> niftiContainer.CPhase :
        return self.m_phase
    @Phase.setter
    def Phase(self, phase : niftiContainer.CPhase) :
        self.m_phase = phase
    
    @property
    def CLInfoIndex(self) -> int :
        return self.m_clinfoIndex
    @CLInfoIndex.setter
    def CLInfoIndex(self, clinfoIndex : int) :
        self.m_clinfoIndex = clinfoIndex
    

if __name__ == '__main__' :
    pass


# print ("ok ..")

