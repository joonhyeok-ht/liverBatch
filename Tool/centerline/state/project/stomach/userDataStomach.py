import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import SimpleITK as sitk
from matplotlib import cm

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
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algMeshLib as algMeshLib

import Block.optionInfo as optionInfo

import command.curveInfo as curveInfo
import command.commandExport as commandExport
import command.commandVesselKnife as commandVesselKnife

import vtkObjInterface as vtkObjInterface

import data as data

import userData as userData


class CTPVessel :
    s_tpVesselKeyType = "TPVessel"
    s_tpRadius = 2.0


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




class CUserDataStomach(userData.CUserData) :
    s_userDataKey = "Stomach"
    s_tpInfoPath = "TPInfo"
    s_tpColorCnt = 100


    def __init__(self, data : data.CData, mediator) :
        super().__init__(data, CUserDataStomach.s_userDataKey)
        # input your code
        self.m_mediator = mediator

        # self.m_colors = np.array([cm.get_cmap("tab20", CUserDataStomach.s_tpColorCnt)(i)[:3] for i in range(CUserDataStomach.s_tpColorCnt)])
        self.m_colors = np.array([cm.get_cmap("hsv", CUserDataStomach.s_tpColorCnt)(i)[:3] for i in range(CUserDataStomach.s_tpColorCnt)])
        self.m_listTPABlenderName = []
        self.m_listTPVBlenderName = []
        '''
        inx : groupID or clinfoInx
        value : dict 
                    - key : tpObjKey
                    - value : CVesselTP
        '''
        self.m_listTPVesselGroup = []
    def clear(self) :
        # input your code
        self.m_mediator = None
        self.m_listTPABlenderName.clear()
        self.m_listTPVBlenderName.clear()
        for tpVesselGroup in self.m_listTPVesselGroup :
            for key, tpVessel in tpVesselGroup.items() :
                tpVessel.clear()
            tpVesselGroup.clear()
        self.m_listTPVesselGroup.clear()
        super().clear()

    def load_patient(self) -> bool :
        if super().load_patient() == False :
            return False
        
        # input your code
        tpInfoInPath = self.get_tpinfo_in_path()
        tpInfoOutPath = self.get_tpinfo_out_path()
        if os.path.exists(tpInfoInPath) == False :
            os.makedirs(tpInfoInPath)
        if os.path.exists(tpInfoOutPath) == False :
            os.makedirs(tpInfoOutPath)

        self._export_tp_vessel()

        iCnt = self.Data.get_skeleton_count()
        if iCnt == 0 :
            return 
        for inx in range(0, iCnt) :
            self.m_listTPVesselGroup.append({})
        
        self._create_tp_vessel_obj(0, self.m_listTPABlenderName)
        self._create_tp_vessel_obj(1, self.m_listTPVBlenderName)
        
        return True
    

    # tp vessel
    def get_tpinfo_path(self) -> str :
        patientPath = self.Data.DataInfo.PatientPath
        tpInfoPath = os.path.join(patientPath, CUserDataStomach.s_tpInfoPath)
        return tpInfoPath
    def get_tpinfo_in_path(self) -> str :
        tpInfoInPath = os.path.join(self.get_tpinfo_path(), "in")
        return tpInfoInPath
    def get_tpinfo_out_path(self) -> str :
        tpInfoOutPath = os.path.join(self.get_tpinfo_path(), "out")
        return tpInfoOutPath
    
    def get_color(self, index : int) -> np.ndarray :
        mappedIndex = index % CUserDataStomach.s_tpColorCnt
        return self.m_colors[mappedIndex].reshape(-1, 3)
    
    def add_tp_vessel(self, groupID : int, index : int, label : str, pos : np.ndarray, color : np.ndarray) -> CTPVessel : 
        tpVesselGroup = self.m_listTPVesselGroup[groupID]
        tpVessel = CTPVessel(groupID, index, label, pos, color)
        key = tpVessel.TPVesselObj.Key
        tpVesselGroup[key] = tpVessel
        self.Data.add_vtk_obj(tpVessel.TPVesselObj)
        return tpVessel
    def get_tp_vessel_group(self, groupID : int) -> dict :
        '''
        key : tpObjKey
        value : CTPVessel
        '''
        return self.m_listTPVesselGroup[groupID]
    def get_tp_vessel_count(self, groupID : int) -> int :
        tpVesselGroup = self.get_tp_vessel_group(groupID)
        return len(tpVesselGroup)
    def find_tp_vessel_by_key(self, groupID : int, tpVesselObjKey : str) -> CTPVessel :
        tpVesselGroup = self.get_tp_vessel_group(groupID)
        for key, tpVessel in tpVesselGroup.items() :
            if key == tpVesselObjKey :
                return tpVessel
        return None
    

    # protected
    def _export_tp_vessel(self) :
        dataInst = self.Data
        optionInfoInst = self.Data.OptionInfo
        tpInfoInPath = self.get_tpinfo_in_path()

        patientID = dataInst.DataInfo.PatientID
        patientPath = dataInst.DataInfo.PatientPath
        patientBlenderFullPath = os.path.join(patientPath, f"{patientID}_recon.blend")
        
        commandExportInst = commandExport.CCommandExportList(self.m_mediator)
        commandExportInst.InputData = dataInst
        commandExportInst.OutputPath = tpInfoInPath
        commandExportInst.PatientBlenderFullPath = patientBlenderFullPath

        iCnt = optionInfoInst.get_maskinfo_count()
        for inx in range(0, iCnt) :
            maskInfo = optionInfoInst.get_maskinfo(inx)
            blenderName = maskInfo.BlenderName
            tokens = blenderName.split('_')
            if tokens[-1] == "TPa" :
                self.m_listTPABlenderName.append(blenderName)
                commandExportInst.add_blender_name(blenderName)
            elif tokens[-1] == "TPv" :
                self.m_listTPVBlenderName.append(blenderName)
                commandExportInst.add_blender_name(blenderName)
        commandExportInst.process()
        commandExportInst.clear()
    def _get_polydata_center(self, polyData : vtk.vtkPolyData) -> np.ndarray :
        bounds = polyData.GetBounds()

        # 중심 좌표 계산
        center_x = (bounds[0] + bounds[1]) / 2.0
        center_y = (bounds[2] + bounds[3]) / 2.0
        center_z = (bounds[4] + bounds[5]) / 2.0
        center = algLinearMath.CScoMath.to_vec3([center_x, center_y, center_z])
        return center
    def _create_tp_vessel_obj(self, groupID : int, listTPBlenderName : str) :
        tpInfoInPath = self.get_tpinfo_in_path()
        index = 0

        for tpBlenderName in listTPBlenderName :
            tpFullPath = os.path.join(tpInfoInPath, f"{tpBlenderName}.stl")
            if os.path.exists(tpFullPath) == False :
                continue

            polyData = algVTK.CVTK.load_poly_data_stl(tpFullPath)
            listPolyData = commandVesselKnife.CCommandSepVessel.get_sub_polydata(polyData)
            label = "_".join(tpBlenderName.split("_")[:-1])

            for subPolyData in listPolyData :
                pos = self._get_polydata_center(subPolyData)
                color = self.get_color(index)
                self.add_tp_vessel(groupID, index, label, pos, color)
                index += 1
    

    @property
    def Data(self) -> data.CData :
        return self.m_data
    

if __name__ == '__main__' :
    pass


# print ("ok ..")

