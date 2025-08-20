import numpy as np
import matplotlib.pyplot as plt
import os, sys
import matplotlib.patches as patches
import json

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import scoUtil
import scoData
import scoReg
import scoMath
import scoRenderObj
import scoSkeleton
import scoSkeletonVM
import scoBuffer
import scoBufferAlg

import phaseTable as phaseTable


'''
Name
    - PhysicalInfoBlock
Input
Output
    - "OutputJson"          : json file full path
Property
    - "Active"
    - "PhaseTable"
    - "AddNiftiPath"
    - "AddForceNiftiPath"
}
'''
class CNiftiObj :
    def __init__(self) -> None :
        self.m_shape = None
        self.m_origin = None
        self.m_spacing = None
        self.m_direction = None
        self.m_regOffset = [0, 0, 0]
        self.m_volume = 0
        self.m_matPhy = None
        self.m_matVTKPhy = None
        self.m_maskAABB = None
        self.m_niftiFileName = ""
    def clear(self) : 
        self.m_shape = None
        self.m_origin = None
        self.m_spacing = None
        self.m_direction = None
        self.m_regOffset = [0, 0, 0]
        self.m_volume = 0
        self.m_matPhy = None
        self.m_matVTKPhy = None
        self.m_maskAABB = None
        self.m_niftiFileName = ""
    def process(self, niftiFileName : str, shape, origin, spacing, direction, regOffset, volume) :
        self.m_niftiFileName = niftiFileName
        self.m_shape = shape
        self.m_origin = origin
        self.m_spacing = spacing
        self.m_direction = direction
        self.m_regOffset[0] = regOffset[0]
        self.m_regOffset[1] = regOffset[1]
        self.m_regOffset[2] = regOffset[2]
        self.m_volume = volume
        self._make_mat_aabb()
    def process_from_nifti(self, niftiFullPath : str, regOffset = None) -> None :
        self.m_niftiFileName = scoUtil.CScoUtilOS.get_file_name(niftiFullPath)
        mask, self.m_origin, self.m_spacing, self.m_direction = scoBuffer.CScoBuffer3D.create_instance(niftiFullPath, (2, 1, 0), "uint8", "uint8", 1, 0)
        xInx, yInx, zInx = mask.get_voxel_inx_with_greater(0)
        voxelCnt = len(xInx)
        self.m_shape = mask.Shape
        if regOffset is not None :
            self.m_regOffset[0] = regOffset[0]
            self.m_regOffset[1] = regOffset[1]
            self.m_regOffset[2] = regOffset[2]
        self.m_volume = self.m_spacing[0] * self.m_spacing[1] * self.m_spacing[2] * voxelCnt * 0.001
        self._make_mat_aabb()
    

    @property
    def Shape(self) :
        return self.m_shape
    @property
    def Origin(self) :
        return self.m_origin
    @property
    def Spacing(self) :
        return self.m_spacing
    @property
    def Direction(self) :
        return self.m_direction
    @property
    def RegOffset(self) :
        return self.m_regOffset
    @property
    def Volume(self) :
        return self.m_volume
    @property
    def MatPhy(self) -> scoMath.CScoMat4:
        return self.m_matPhy
    @property
    def MatVTKPhy(self) -> scoMath.CScoMat4:
        return self.m_matVTKPhy
    @property
    def NiftiFileName(self) -> str :
        return self.m_niftiFileName
    @property
    def AABB(self) -> scoMath.CScoAABB :
        return self.m_maskAABB
    

    # protected 
    def _make_mat_aabb(self) :
        self.m_matPhy = scoMath.CScoMath.get_mat_with_spacing_direction_origin(self.m_spacing, self.m_direction, self.m_origin)
        self.m_matVTKPhy = scoMath.CScoMath.get_mat_with_direction_origin(self.m_direction, self.m_origin)
        self.m_maskAABB = scoMath.CScoAABB()
        self.m_maskAABB.make_min_max(scoMath.CScoVec3(0, 0, 0), scoMath.CScoVec3(self.Shape[0] - 1, self.Shape[1] - 1, self.Shape[2] - 1))


class CPhysicalInfo() :
    @staticmethod
    def get_min_max(listV : list) :
        """
        ret
            - tuple
                - (minV, maxV)
        """
        minV = scoMath.CScoVec3(100000.0, 100000.0, 100000.0)
        maxV = scoMath.CScoVec3(-100000.0, -100000.0, -100000.0)

        for v in listV :
            if v.X < minV.X :
                minV.X = v.X
            if v.X > maxV.X :
                maxV.X = v.X
            
            if v.Y < minV.Y :
                minV.Y = v.Y
            if v.Y > maxV.Y :
                maxV.Y = v.Y
            
            if v.Z < minV.Z :
                minV.Z = v.Z
            if v.Z > maxV.Z :
                maxV.Z = v.Z
        return (minV, maxV)
    @staticmethod
    def get_center(minV : scoMath.CScoVec3, maxV : scoMath.CScoVec3) :
        center = scoMath.CScoVec3(minV.X + maxV.X, minV.Y + maxV.Y , minV.Z  + maxV.Z)
        center = scoMath.CScoMath.mul_vec3_scalar(center, 0.5)
        return center
    

    def __init__(self) -> None :
        self.m_outputJson = ""
        self.m_listNiftiPath = []
        self.m_listForceNiftiPath = []
        self.m_listNiftiObj = []
        self.m_center = scoMath.CScoVec3()
        self.m_json = None
        self.m_phaseTable = None
    def clear(self) :
        self.m_outputJson = ""
        self.m_listNiftiPath.clear()
        self.m_listForceNiftiPath.clear()
        for niftiObj in self.m_listNiftiObj :
            niftiObj.clear()
        self.m_listNiftiObj.clear()
        self.m_center = scoMath.CScoVec3()
        if self.m_json is not None :
            self.m_json.clear()
            self.m_json = None
        if self.m_phaseTable is not None :
            self.m_phaseTable = None
    def process(self) :
        # json loading
        if os.path.exists(self.OutputJson) == True :
             with open(self.OutputJson, 'r') as fp :
                self.m_json = json.load(fp)
        else :
            self.m_json = {}
            self.m_json["Center"] = [0, 0, 0]
            self.m_json["NiftiList"] = {}

        # load nifti obj
        self._load_nifti_from_json()
        # load nifti obj from nifti file
        for niftiPath in self.m_listNiftiPath :
            if os.path.exists(niftiPath) == False :
                continue
            self._load_nifti(niftiPath)
        for niftiPath in self.m_listForceNiftiPath :
            if os.path.exists(niftiPath) == False :
                continue
            self._force_load_nifti(niftiPath)
        # find center
        self._find_center()
        # save json
        self._save()

    def add_nifti_path(self, niftiPath : str) :
        self.m_listNiftiPath.append(niftiPath)
    def add_force_nifti_path(self, niftiPath : str) :
        self.m_listForceNiftiPath.append(niftiPath)


    # protected
    def _load_nifti_from_json(self) :
        dicNiftiInfo = self.m_json["NiftiList"]
        for niftiFileName, niftiInfo in dicNiftiInfo.items() :
            niftiObj = CNiftiObj()
            niftiObj.process(
                niftiFileName,
                niftiInfo["shape"], 
                niftiInfo["origin"], niftiInfo["spacing"], niftiInfo["direction"], 
                niftiInfo["RegOffset"], niftiInfo["Volume"]
                )
            self.m_listNiftiObj.append(niftiObj)
    def _load_nifti(self, niftiPath : str) :
        dicNiftiList = self.m_json["NiftiList"]
        listFileName = os.listdir(niftiPath)
        for fileName in listFileName :
            fullPath = os.path.join(niftiPath, fileName)
            if os.path.exists(fullPath) == False :
                continue
            ext = scoUtil.CScoUtilOS.get_ext(fullPath)
            if ext != ".gz" :
                continue
            bCheck = fileName in dicNiftiList
            if bCheck == True :
                continue

            regOffset = [0, 0, 0]
            if self.m_phaseTable is not None :
                phase = self.m_phaseTable.get_phase_name_from_nifti_file(fileName)
                if phase != "" :
                    regOffset = self.m_phaseTable.get_reg_offset(phase)

            niftiObj = CNiftiObj()
            niftiObj.process_from_nifti(fullPath, regOffset)
            self.m_listNiftiObj.append(niftiObj)

            print(f"loaded {fileName}")
    def _force_load_nifti(self, niftiPath : str) :
        listFileName = os.listdir(niftiPath)
        for fileName in listFileName :
            fullPath = os.path.join(niftiPath, fileName)
            if os.path.exists(fullPath) == False :
                continue
            ext = scoUtil.CScoUtilOS.get_ext(fullPath)
            if ext != ".gz" :
                continue

            self._remove_nifti_obj(fileName)

            regOffset = [0, 0, 0]
            if self.m_phaseTable is not None :
                phase = self.m_phaseTable.get_phase_name_from_nifti_file(fileName)
                if phase != "" :
                    regOffset = self.m_phaseTable.get_reg_offset(phase)

            niftiObj = CNiftiObj()
            niftiObj.process_from_nifti(fullPath, regOffset)
            self.m_listNiftiObj.append(niftiObj)

            print(f"force loaded {fileName}")
    def _find_center(self) :
        listPhyVertex = []

        for niftiObj in self.m_listNiftiObj :
            regOffset = niftiObj.RegOffset
            matPhyOffset = scoMath.CScoMat4()
            matPhyOffset.set_translate(regOffset[0], regOffset[1], regOffset[2])
            matPhy = scoMath.CScoMath.mul_mat4(matPhyOffset, niftiObj.MatPhy)

            aabb = niftiObj.AABB
            # v = scoMath.CScoMath.mul_mat4_vec3(matPhy, aabb.Min)
            # listPhyVertex.append(scoMath.CScoVec3(v.X, v.Y, v.Z))
            # v = scoMath.CScoMath.mul_mat4_vec3(matPhy, aabb.Max)
            # listPhyVertex.append(scoMath.CScoVec3(v.X, v.Y, v.Z))
            minV, maxV = aabb.get_min_max_with_world_matrix(matPhy)
            listPhyVertex.append(minV)
            listPhyVertex.append(maxV)

            print(f"{niftiObj.NiftiFileName} : phyVertex : {minV.X}, {minV.Y}, {minV.Z}, oriVertex : {aabb.Min.X}, {aabb.Min.Y}, {aabb.Min.Z}")
            print(f"{niftiObj.NiftiFileName} : phyVertex : {maxV.X}, {maxV.Y}, {maxV.Z}, oriVertex : {aabb.Max.X}, {aabb.Max.Y}, {aabb.Max.Z}")

        matPhy.print()
        
        if len(listPhyVertex) > 0 :
            minV, maxV = CPhysicalInfo.get_min_max(listPhyVertex)
            self.m_center = CPhysicalInfo.get_center(minV, maxV)
            # self.m_center = scoMath.CScoVec3(0.0, 0.0, 0.0)
            print("-"*30)
            print(f"min : {minV.X}, {minV.Y}, {minV.Z}")
            print(f"max : {maxV.X}, {maxV.Y}, {maxV.Z}")
            print("-"*30)
        else :
            self.m_center = scoMath.CScoVec3(0.0, 0.0, 0.0)
    def _remove_nifti_obj(self, niftiFileName : str) :
        findNiftiObj = None
        for niftiObj in self.m_listNiftiObj :
            if niftiFileName == niftiObj.NiftiFileName :
                findNiftiObj = niftiObj
                break
        if findNiftiObj is not None :
            self.m_listNiftiObj.remove(findNiftiObj)
    def _save(self) :
        listCenter = self.m_json["Center"]
        listCenter[0] = self.m_center.X
        listCenter[1] = self.m_center.Y
        listCenter[2] = self.m_center.Z

        self.m_json["NiftiList"] = {}
        dicNiftiList = self.m_json["NiftiList"]
        for niftiObj in self.m_listNiftiObj :
            niftiFileName = niftiObj.NiftiFileName
            shape = niftiObj.Shape
            origin = niftiObj.Origin
            spacing = niftiObj.Spacing
            direction = niftiObj.Direction
            regOffset = niftiObj.RegOffset
            volume = niftiObj.Volume

            dicNiftiList[niftiFileName] = {}
            tmpNiftiInfo = dicNiftiList[niftiFileName]
            tmpNiftiInfo["shape"] = [shape[0], shape[1], shape[2]]
            tmpNiftiInfo["origin"] = [origin[0], origin[1], origin[2]]
            tmpNiftiInfo["spacing"] = [spacing[0], spacing[1], spacing[2]]
            tmpNiftiInfo["direction"] = [
                direction[0], direction[1], direction[2],
                direction[3], direction[4], direction[5],
                direction[6], direction[7], direction[8]
            ]
            tmpNiftiInfo["RegOffset"] = [regOffset[0], regOffset[1], regOffset[2]]
            tmpNiftiInfo["Volume"] = volume
        
        with open(self.OutputJson, "w") as fp : 
            json.dump(self.m_json, fp, indent="\t") 


    @property
    def PhaseTable(self) :
        return self.m_phaseTable
    @PhaseTable.setter
    def PhaseTable(self, phaseTable : phaseTable.CPhaseTable) :
        self.m_phaseTable = phaseTable
    @property
    def OutputJson(self) :
        return self.m_outputJson
    @OutputJson.setter
    def OutputJson(self, outputJson : str) :
        self.m_outputJson = outputJson
        dirPath = os.path.dirname(outputJson)
        if not os.path.exists(dirPath) :
            os.makedirs(dirPath)


    

    






