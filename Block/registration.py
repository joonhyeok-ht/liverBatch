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
import AlgUtil.algImage as algImage
import AlgUtil.algGeometry as algGeometry

from Algorithm import scoReg

import multiProcessTask as multiProcessTask
import optionInfo as optionInfo

from collections import deque
import multiprocessing as mp


def _registration_task_worker(param: tuple):
    """
    param = (sharedListProxy, inx, targetFullPath, srcFullPath, rigidAABB)
    """
    sharedList, inx, targetFullPath, srcFullPath, rigidAABB = param

    if os.path.exists(targetFullPath) == False or os.path.exists(srcFullPath) == False:
        print("-" * 30)
        print("not found registration files")
        print(f"target path : {targetFullPath}")
        print(f"src path : {srcFullPath}")
        print("-" * 30)
        sharedList[inx] = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
        return True

    # ---- 여기부터는 기존 _task 내용을 최대한 그대로 ----
    if rigidAABB == 1:
        ctVertex, ctOrigin, ctSpacing, ctDirection, ctSize = algImage.CAlgImage.get_vertex_from_nifti(targetFullPath)
        mrVertex, mrOrigin, mrSpacing, mrDirection, mrSize = algImage.CAlgImage.get_vertex_from_nifti(srcFullPath)

        # ✅ 기존 self.__get_rigid_physical_offset 의존이 문제라서
        #    아래 3)에서 "정적 함수"로 빼서 호출하도록 함
        rigidPhysicalOffset = CRegistration.get_rigid_physical_offset(
            (ctVertex, ctOrigin, ctSpacing, ctDirection),
            (mrVertex, mrOrigin, mrSpacing, mrDirection)
        )

        offsetX = float(rigidPhysicalOffset[0, 0])
        offsetY = float(rigidPhysicalOffset[0, 1])
        offsetZ = float(rigidPhysicalOffset[0, 2])
    else:
        offsetX = offsetY = offsetZ = 0.0
        rigidPhysicalOffset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])

    reg = scoReg.CRegRigidRefinedTransform()
    reg.process(srcFullPath, targetFullPath, [offsetX, offsetY, offsetZ])

    offsetX = reg.OffsetX
    offsetY = reg.OffsetY
    offsetZ = reg.OffsetZ

    matTargetPhy = reg.MatTargetPhy.m_npMat.copy()
    matTargetPhy = algLinearMath.CScoMath.from_mat3_to_mat4(matTargetPhy[0:3, 0:3])
    offsetV = algLinearMath.CScoMath.to_vec4([offsetX, offsetY, offsetZ, 1.0])
    phyOffsetV = algLinearMath.CScoMath.from_vec4_to_vec3(
        algLinearMath.CScoMath.mul_mat4_vec4(matTargetPhy, offsetV)
    )
    phyOffsetV = phyOffsetV + rigidPhysicalOffset

    sharedList[inx] = phyOffsetV
    print(f"completed registration {srcFullPath}")
    return True


class CRegistration(multiProcessTask.CMultiProcessTaskProgress) :
    @staticmethod
    def get_rigid_physical_offset(targetInfo, srcInfo):
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
    
    
    
    def __init__(self) -> None :
        super().__init__()
        # input your code 
        self.m_inputOptionInfo = None
        self.m_inputMaskPath = ""
        self.m_outputListOffset = None
    def clear(self) :
        # input your code
        self.m_inputOptionInfo = None
        self.m_inputMaskPath = ""
        if self.m_outputListOffset is not None :
            self.m_outputListOffset.clear()
            self.m_outputListOffset = None
        super().clear()
    # def process(self) :
    #     if self.InputOptionInfo is None :
    #         print("reg : not found optionInfo")
    #         return
    #     if self.InputMaskPath == "" :
    #         print("reg : not setting input mask path")
    #         return
        
    #     listParam = []
    #     paramCnt = 0

    #     iRegInfoCnt = self.InputOptionInfo.get_registrationinfo_count()
    #     for inx in range(0, iRegInfoCnt) :
    #         targetMaskName, srcMaskName, rigidAABB = self.InputOptionInfo.get_registrationinfo(inx)

    #         targetFullPath = os.path.join(self.InputMaskPath, f"{targetMaskName}.nii.gz")
    #         srcFullPath = os.path.join(self.InputMaskPath, f"{srcMaskName}.nii.gz")

    #         listParam.append((paramCnt, targetFullPath, srcFullPath, rigidAABB))
    #         paramCnt += 1
        
    #     if paramCnt == 0 :
    #         print("passed registration")
    #         return
        
    #     self._alloc_shared_list(paramCnt)
    #     super().process(self._task, listParam)
    #     self.m_outputListOffset = self.get_shared_list()
    
    def process(self):
        if self.InputOptionInfo is None:
            print("reg : not found optionInfo")
            return False
        if self.InputMaskPath == "":
            print("reg : not setting input mask path")
            return False

        listParam = []
        paramCnt = 0

        iRegInfoCnt = self.InputOptionInfo.get_registrationinfo_count()
        for inx in range(0, iRegInfoCnt):
            targetMaskName, srcMaskName, rigidAABB = self.InputOptionInfo.get_registrationinfo(inx)

            targetFullPath = os.path.join(self.InputMaskPath, f"{targetMaskName}.nii.gz")
            srcFullPath = os.path.join(self.InputMaskPath, f"{srcMaskName}.nii.gz")

            # ✅ sharedList를 파라미터에 포함 (전역 worker가 사용)
            listParam.append((paramCnt, targetFullPath, srcFullPath, rigidAABB))
            paramCnt += 1

        if paramCnt == 0:
            print("passed registration")
            return True

        self._alloc_shared_list(paramCnt)

        # ✅ 전역 worker에 sharedList를 넣어서 전달
        listParam2 = [(self.m_sharedList, p[0], p[1], p[2], p[3]) for p in listParam]

        ok = super().process(
            _registration_task_worker,  # ✅ 전역 함수
            listParam2,
            progress_callback=getattr(self, "progress_callback", None),
            is_interrupted=getattr(self, "is_interrupted", None),
            status_prefix="Registration...",
            chunksize=1
        )
        if not ok:
            return False

        self.m_outputListOffset = self.get_shared_list()
        return True

    
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
            print(f"completed registration {srcFullPath}")

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
    def InputMaskPath(self) -> str :
        return self.m_inputMaskPath
    @InputMaskPath.setter
    def InputMaskPath(self, inputMaskPath : str) :
        self.m_inputMaskPath = inputMaskPath
    @property
    def OutputListOffset(self) -> list :
        return self.m_outputListOffset


if __name__ == '__main__' :
    pass


# print ("ok ..")

