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

import VtkUI.vtkUI as vtkUI
import VtkObj.vtkObj as vtkObj
import VtkObj.vtkObjPolyData as vtkObjPolyData


class CTerritoryInfo :
    def __init__(self) :
        self.m_blenderName = ""
        self.m_reconType = ""
        self.m_spacing = None
        self.m_mat = None
        self.m_invMat = None
        self.m_queryVertex = None
        self.m_organInfo = None
    def clear(self) :
        self.m_blenderName = ""
        self.m_reconType = ""
        self.m_spacing = None
        self.m_mat = None
        self.m_invMat = None
        self.m_queryVertex = None
        self.m_organInfo = None

    def voxelize(self, polyData : vtk.vtkPolyData) :
        self.m_organInfo = algVTK.CVTK.poly_data_voxelize(polyData, self.Spacing, 255.0)
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
    def ReconType(self) -> str :
        return self.m_reconType
    @ReconType.setter
    def ReconType(self, reconType : str) :
        self.m_reconType = reconType
    @property
    def Spacing(self) :
        return self.m_spacing
    @Spacing.setter
    def Spacing(self, spacing) :
        self.m_spacing = spacing
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

    s_vesselType = "vessel"
    s_organType = "organ"
    s_territoryType = "territory"
    s_skelTypeCenterline = "centerline"
    s_skelTypeBranch = "branch"
    s_skelTypeEndPoint = "endPoint"
    s_outsideKeyType = "outsideCLType"
    s_textType = "text"

    s_clInputKey = ["nifti", "blenderName", "voxelize"]
    s_clFindCell = ["minX", "maxX", "minY", "maxY", "minZ", "maxZ"]

    s_reconGaussian = ["0", "1"]
    s_reconAlgorithm = ["Marching", "MarchingPro", "Flying", "FlyingPro"]
    s_reconResampling = ["1", "2", "3"]


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
    
    @staticmethod
    def save_inst(fullPath, inst) :
        '''
        fullPath : *.pkl
        '''
        with open(fullPath, "wb") as fp:
            pickle.dump(inst, fp)
    @staticmethod
    def load_inst(fullPath) :
        if os.path.exists(fullPath) == False :
            return None
        
        with open(fullPath, "rb") as fp:
            inst = pickle.load(fp)
        return inst
    

    def __init__(self) :
        '''
        key : string id
        value : (polyData, color, opacity)
        '''
        self.m_dataInfo = optionInfo.CCLDataInfo()
        self.m_optionInfo = None
        self.m_phaseInfoContainer = niftiContainer.CPhaseInfoContainer()
        self.m_dicUserData = {}

        self.m_clinfoIndex = -1

        self.m_dicObj = {}
        self.m_listSkel = []
        self.m_listTerriInfo = []

        self.m_clSize = 1.0
        self.m_clColor = algLinearMath.CScoMath.to_vec3([0.3, 0.3, 0.0])
        self.m_rootCLColor = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])
        self.m_selectionCLColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])

        self.m_brSize = 1.0
        self.m_brColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 1.0])
        self.m_selectionBrColor = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])

        self.m_epSize = 1.0
        self.m_epColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])
        self.m_selectionEPColor = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
    def clear(self) : 
        self.clear_patient()

        self.m_dataInfo.clear()

        if self.m_optionInfo is not None :
            self.OptionInfo.clear()
        self.m_optionInfo = None

        self.m_clinfoIndex = -1

        self.m_clSize = 1.0
        self.m_clColor = algLinearMath.CScoMath.to_vec3([0.3, 0.3, 0.0])
        self.m_rootCLColor = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])
        self.m_selectionCLColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])

        self.m_brSize = 1.0
        self.m_brColor = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 1.0])
        self.m_selectionBrColor = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])

        self.m_epSize = 1.0
        self.m_epColor = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])
        self.m_selectionEPColor = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
    def clear_patient(self) :
        for skel in self.m_listSkel :
            if skel is not None :
                skel.clear()
        self.m_listSkel.clear()
        for key, obj in self.m_dicObj.items() :
            obj.clear()
        self.m_dicObj.clear()

        for terriInfo in self.m_listTerriInfo :
            terriInfo.clear()
        self.m_listTerriInfo.clear()

        self.PhaseInfoContainer.clear()

        for key, userData in self.m_dicUserData.items() :
            userData.clear()
        self.m_dicUserData.clear()
        self.DataInfo.PatientPath = ""
        self.m_clinfoIndex = -1

    def load_optioninfo(self, fullPath) :
        self.clear()
        self.m_optionInfo = optionInfo.COptionInfoSingle(fullPath)

        self.DataInfo.OptionFullPath = fullPath
        self.DataInfo.PatientPath = ""

        clCnt = self.OptionInfo.get_centerlineinfo_count()
        if clCnt == 0 :
            print("not found centerline info")
            return
        for clInx in range(0, clCnt) :
            clInfo = self.OptionInfo.get_centerlineinfo(clInx)
            clParam = self.OptionInfo.find_centerline_param(clInfo.CenterlineType)
            reconType = clInfo.get_input_recon_type()
            reconParam = self.OptionInfo.find_recon_param(reconType)
            if reconParam is None :
                print(f"not found recon type : {reconType}")
                self.DataInfo.add_info(None, None, None)
            else :
                self.DataInfo.add_info(clInfo, clParam, reconParam)
    def load_patient(self, fullPath) :
        if self.OptionInfo is None or self.DataInfo.OptionFullPath == "" :
            print(f"not loaded optionInfo")
            return
        self.DataInfo.PatientPath = fullPath

        self.PhaseInfoContainer.clear()
        phaseInfoFullPath = os.path.join(self.DataInfo.PatientPath, "phaseInfo.json")
        if os.path.exists(phaseInfoFullPath) == False :
            print(f"not found phaseInfo.jon")
            return 
        self.PhaseInfoContainer.InputFullPath = phaseInfoFullPath
        self.PhaseInfoContainer.process()

        self._load_terriinfo()

    def get_cl_path(self) -> str :
        patientPath = self.DataInfo.PatientPath
        clPath = os.path.join(patientPath, "SkelInfo")
        return clPath
    def get_cl_in_path(self) -> str :
        clInPath = os.path.join(self.get_cl_path(), "in")
        return clInPath
    def get_cl_out_path(self) -> str :
        clOutPath = os.path.join(self.get_cl_path(), "out")
        return clOutPath
    def get_terri_path(self) -> str :
        patientPath = self.DataInfo.PatientPath
        terriPath = os.path.join(patientPath, "TerriInfo")
        return terriPath
    def get_terri_in_path(self) -> str :
        terriInPath = os.path.join(self.get_terri_path(), "in")
        return terriInPath
    def get_terri_out_path(self) -> str :
        terriOutPath = os.path.join(self.get_terri_path(), "out")
        return terriOutPath

    def add_userdata(self, key : str, userData) :
        self.m_dicUserData[key] = userData
    def get_userdata_count(self) -> int :
        return len(self.m_dicUserData)
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

        
    def create_skeleton(self, skelCnt : int) :
        for skel in self.m_listSkel :
            if skel is not None :
                skel.clear()
        self.m_listSkel.clear()
        self.m_listSkel = [None for i in range(0, skelCnt)]
    def attach_skeleton(self) :
        self.m_listSkel.append(None)
    def set_skeleton(self, inx : int, fullPath : str) :
        skeleton = self.m_listSkel[inx]
        if skeleton is not None :
            skeleton.clear()
            skeleton = None
        if os.path.exists(fullPath) == False :
            print(f"not found skeleton : {fullPath}")
        else :
            skeleton = algSkeletonGraph.CSkeleton()
            skeleton.load(fullPath)
        self.m_listSkel[inx] = skeleton
    def get_skeleton_count(self) -> int :
        return len(self.m_listSkel)
    def get_skeleton(self, inx : int) -> algSkeletonGraph.CSkeleton :
        return self.m_listSkel[inx]
    

    def get_terriinfo_count(self) -> int :
        return len(self.m_listTerriInfo)
    def get_terriinfo(self, inx : int) -> CTerritoryInfo :
        return self.m_listTerriInfo[inx]
    def find_terriinfo_by_blender_name(self, blenderName : str) -> CTerritoryInfo :
        iCnt = self.get_terriinfo_count()
        for inx in range(0, iCnt) :
            terriInfo = self.get_terriinfo(inx)
            if terriInfo.BlenderName == blenderName :
                return terriInfo
        return None
    def find_terriinfo_index_by_blender_name(self, blenderName : str) -> int :
        iCnt = self.get_terriinfo_count()
        for inx in range(0, iCnt) :
            terriInfo = self.get_terriinfo(inx)
            if terriInfo.BlenderName == blenderName :
                return inx
        return -1
    

    # protected
    def _load_terriinfo(self) :
        if self.Ready == False :
            return
        iCnt = self.OptionInfo.get_segmentinfo_count()
        for inx in range(0, iCnt) :
            segInfo = self.OptionInfo.get_segmentinfo(inx)
            blenderName = segInfo.Organ

            terriInfo = self.find_terriinfo_by_blender_name(blenderName)
            if terriInfo is not None :
                continue

            organMaskInfo = self.OptionInfo.find_maskinfo_by_blender_name(blenderName)
            if organMaskInfo is None :
                print(f"territory pre : not found territory organ {blenderName}")
                continue

            organMaskPhase = organMaskInfo.Phase
            phaseInfo = self.PhaseInfoContainer.find_phaseinfo(organMaskPhase)
            if phaseInfo is None :
                print("territory pre : not found phase")
                continue

            spacing = phaseInfo.Spacing

            terriInfo = CTerritoryInfo()
            terriInfo.BlenderName = blenderName
            terriInfo.ReconType = organMaskInfo.ReconType
            terriInfo.Spacing = spacing
            self.m_listTerriInfo.append(terriInfo)


    @property
    def Ready(self) -> bool :
        optionInfoInst = self.OptionInfo
        if optionInfoInst is None :
            return False
        if self.DataInfo.OptionFullPath == "" :
            return False
        if self.DataInfo.PatientPath == "" :
            return False
        return True
    @property
    def DataInfo(self) -> optionInfo.CCLDataInfo :
        return self.m_dataInfo
    @DataInfo.setter
    def DataInfo(self, dataInfo : optionInfo.CCLDataInfo) :
        self.m_dataInfo = dataInfo
    @property
    def OptionInfo(self) -> optionInfo.COptionInfoSingle :
        return self.m_optionInfo
    @property
    def PhaseInfoContainer(self) -> niftiContainer.CPhaseInfoContainer :
        return self.m_phaseInfoContainer
    @property
    def CLInfoIndex(self) -> int :
        return self.m_clinfoIndex
    @CLInfoIndex.setter
    def CLInfoIndex(self, clinfoIndex : int) :
        self.m_clinfoIndex = clinfoIndex
        
    @property
    def CLSize(self) -> float :
        return self.m_clSize
    @CLSize.setter
    def CLSize(self, clSize : float) :
        self.m_clSize = clSize
    @property
    def CLColor(self) -> np.ndarray :
        return self.m_clColor
    @CLColor.setter
    def CLColor(self, clColor : np.ndarray) :
        self.m_clColor = clColor
    @property
    def RootCLColor(self) -> np.ndarray :
        return self.m_rootCLColor
    @RootCLColor.setter
    def RootCLColor(self, rootCLColor : np.ndarray) :
        self.m_rootCLColor = rootCLColor
    @property
    def SelectionCLColor(self) -> np.ndarray :
        return self.m_selectionCLColor
    @SelectionCLColor.setter
    def SelectionCLColor(self, selectionCLColor : np.ndarray) :
        self.m_selectionCLColor = selectionCLColor

    @property
    def BrSize(self) -> float :
        return self.m_brSize
    @BrSize.setter
    def BrSize(self, brSize : float) :
        self.m_brSize = brSize
    @property
    def BrColor(self) -> np.ndarray :
        return self.m_brColor
    @BrColor.setter
    def BrColor(self, brColor : np.ndarray) :
        self.m_brColor = brColor
    @property
    def SelectionBrColor(self) -> np.ndarray :
        return self.m_selectionBrColor
    @SelectionBrColor.setter
    def SelectionBrColor(self, selectionBrColor : np.ndarray) :
        self.m_selectionBrColor = selectionBrColor


    @property
    def EPSize(self) -> float :
        return self.m_epSize
    @BrSize.setter
    def EPSize(self, epSize : float) :
        self.m_epSize = epSize
    @property
    def EPColor(self) -> np.ndarray :
        return self.m_epColor
    @EPColor.setter
    def EPColor(self, epColor : np.ndarray) :
        self.m_epColor = epColor
    @property
    def SelectionEPColor(self) -> np.ndarray :
        return self.m_selectionEPColor
    @SelectionEPColor.setter
    def SelectionEPColor(self, selectionEPColor : np.ndarray) :
        self.m_selectionEPColor = selectionEPColor
    


if __name__ == '__main__' :
    pass


# print ("ok ..")

