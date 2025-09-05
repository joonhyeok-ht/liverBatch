import sys
import os
import numpy as np

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK
import AlgUtil.algGeometry as algGeometry

from Algorithm import scoReg

import multiProcessTask as multiProcessTask
import niftiContainer as niftiContainer
import optionInfo as optionInfo

class CRegistration(multiProcessTask.CMultiProcessTask) :
    def __init__(self) -> None:
        super().__init__()
        # input your code 
        self.m_inputOptionInfo = None
        self.m_inputNiftiContainer = None
        self.m_outputListOffset = None
    def clear(self) :
        # input your code
        self.m_inputOptionInfo = None
        self.m_inputNiftiContainer = None
        if self.m_outputListOffset is not None :
            self.m_outputListOffset.clear()
            self.m_outputListOffset = None
        super().clear()
    def process(self) :
        if self.InputOptionInfo is None :
            print("reg : not found optionInfo")
            return
        if self.InputNiftiContainer is None :
            print("reg : not found nifti container")
            return
        
        listParam = []
        paramCnt = 0
        iRegInfoCnt = self.InputOptionInfo.get_reginfo_count()
        for inx in range(0, iRegInfoCnt) :
            regInfo = self.InputOptionInfo.get_reginfo(inx)
            target = regInfo.Target
            src = regInfo.Src

            targetNiftiInfoList = self.InputNiftiContainer.find_nifti_info_list_by_name(target)
            srcNiftiInfoList = self.InputNiftiContainer.find_nifti_info_list_by_name(src)

            if targetNiftiInfoList is None or srcNiftiInfoList is None :
                print("reg : not found target and src nifti info")
                continue

            targetFullPath = targetNiftiInfoList[0].FullPath
            srcFullPath = srcNiftiInfoList[0].FullPath
            rigidAABB = regInfo.RigidAABB
            # print(f"RegInfo[{inx}] targetFullPath : {targetFullPath}")
            # print(f"               srcFullPath : {srcFullPath}")

            listParam.append((paramCnt, targetFullPath, srcFullPath, rigidAABB))
            paramCnt += 1
        
        if paramCnt == 0 or len(listParam) == 0:
            print("passed registration")
            return
        
        self._alloc_shared_list(paramCnt)
        super().process(self._task, listParam)
        self.m_outputListOffset = self.get_shared_list()

    
    def _task(self, param : tuple) :
        inx = param[0]
        targetFullPath = param[1]
        srcFullPath = param[2]
        rigidAABB = param[3]
        
        if os.path.exists(targetFullPath) == False or os.path.exists(srcFullPath) == False :
            print("-" * 30)
            print(f"not found registration files")
            print(f"target path : {targetFullPath}")
            print(f"src path : {srcFullPath}")
            print("-" * 30)
            self.m_sharedList[inx] = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
        else :
            if rigidAABB == 1 :
                ctVertex, ctOrigin, ctSpacing, ctDirection, ctSize = algImage.CAlgImage.get_vertex_from_nifti(targetFullPath)
                mrVertex, mrOrigin, mrSpacing, mrDirection, mrSize = algImage.CAlgImage.get_vertex_from_nifti(srcFullPath)
                rigidPhysicalOffset = self.__get_rigid_physical_offset(
                    (ctVertex, ctOrigin, ctSpacing, ctDirection),
                    (mrVertex, mrOrigin, mrSpacing, mrDirection)
                )

                offsetX = float(rigidPhysicalOffset[0, 0])
                offsetY = float(rigidPhysicalOffset[0, 1])
                offsetZ = float(rigidPhysicalOffset[0, 2])
            else :
                offsetX = 0.0
                offsetY = 0.0
                offsetZ = 0.0
                rigidPhysicalOffset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
            reg = scoReg.CRegRigidRefinedTransform()
            reg.process(srcFullPath, targetFullPath, [offsetX, offsetY, offsetZ])
            diceScore = reg.DiceScore
            offsetX = reg.OffsetX
            offsetY = reg.OffsetY
            offsetZ = reg.OffsetZ

            matTargetPhy = reg.MatTargetPhy.m_npMat.copy()
            matTargetPhy = algLinearMath.CScoMath.from_mat3_to_mat4(matTargetPhy[0 : 3, 0 : 3])
            offsetV = algLinearMath.CScoMath.to_vec4([offsetX, offsetY, offsetZ, 1.0])
            phyOffsetV = algLinearMath.CScoMath.from_vec4_to_vec3(algLinearMath.CScoMath.mul_mat4_vec4(matTargetPhy, offsetV))
            phyOffsetV = phyOffsetV + rigidPhysicalOffset

            self.m_sharedList[inx] = phyOffsetV
            print(f"completed registration {srcFullPath}", file=sys.__stdout__, flush= True)

    def __get_rigid_physical_offset(self, targetInfo : tuple, srcInfo : tuple) -> np.ndarray :
        targetVertex = targetInfo[0]
        targetOrigin = targetInfo[1]
        targetSpacing = targetInfo[2]
        targetDirection = targetInfo[3]

        srcVertex = srcInfo[0]
        srcOrigin = srcInfo[1]
        srcSpacing = srcInfo[2]
        srcDirection = srcInfo[3]

        targetMatPhysical = algVTK.CVTK.get_phy_matrix(targetOrigin, targetSpacing, targetDirection)
        srcMatPhysical = algVTK.CVTK.get_phy_matrix(srcOrigin, srcSpacing, srcDirection)

        targetAABB = algGeometry.CScoAABB()
        targetAABB.init_with_vertex(targetVertex)
        srcAABB = algGeometry.CScoAABB()
        srcAABB.init_with_vertex(srcVertex)

        targetMin = algLinearMath.CScoMath.mul_mat4_vec3(targetMatPhysical, targetAABB.Min)
        targetMax = algLinearMath.CScoMath.mul_mat4_vec3(targetMatPhysical, targetAABB.Max)
        targetAABB.init_with_min_max(targetMin, targetMax)

        srcMin = algLinearMath.CScoMath.mul_mat4_vec3(srcMatPhysical, srcAABB.Min)
        srcMax = algLinearMath.CScoMath.mul_mat4_vec3(srcMatPhysical, srcAABB.Max)
        srcAABB.init_with_min_max(srcMin, srcMax)

        targetCenter = targetAABB.Center
        srcCenter = srcAABB.Center
        retOffset = targetCenter - srcCenter

        return retOffset
    

    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, inputOptionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = inputOptionInfo
    @property
    def InputNiftiContainer(self) -> niftiContainer.CNiftiContainer :
        return self.m_inputNiftiContainer
    @InputNiftiContainer.setter
    def InputNiftiContainer(self, inputNiftiContainer : niftiContainer.CNiftiContainer) :
        self.m_inputNiftiContainer = inputNiftiContainer
    @property
    def OutputListOffset(self) -> list :
        return self.m_outputListOffset







if __name__ == '__main__' :
    pass


# print ("ok ..")

