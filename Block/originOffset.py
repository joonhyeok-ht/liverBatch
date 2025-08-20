import sys
import os
import numpy as np

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algGeometry as algGeometry
import AlgUtil.algVTK as algVTK

import niftiContainer as niftiContainer
import optionInfo as optionInfo


class COriginOffset() :
    def __init__(self) -> None:
        # input your code 
        self.m_inputOptionInfo = None
        self.m_inputNiftiContainer = None
        self.m_outputOriginOffset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
    def clear(self) :
        # input your code
        self.m_inputOptionInfo = None
        self.m_inputNiftiContainer = None
        self.m_outputOriginOffset = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
    def process(self) :
        if self.InputOptionInfo is None :
            print("originOffset : not found optionInfo")
            return
        if self.InputNiftiContainer is None :
            print("originOffset : not found nifti container")
            return
        
        iPhaseCnt = self.InputNiftiContainer.get_phase_info_count()
        listPhaseInfo = []
        for inx in range(0, iPhaseCnt) :
            phaseInfo = self.InputNiftiContainer.get_phase_info(inx)
            phase = phaseInfo.Phase
            if phaseInfo.is_valid() == False or self.InputOptionInfo.is_rigid_reg_by_phase(phase) == True :
                continue
            else :
                listPhaseInfo.append(phaseInfo)
        self.m_outputOriginOffset = self._calc_center_offset(listPhaseInfo)

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
    def OutputOriginOffset(self) -> np.ndarray :
        return self.m_outputOriginOffset
    

    # protected
    def _calc_center_offset(self, listPhaseInfo : list) -> np.ndarray :
        if len(listPhaseInfo) == 0 :
            return algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
        
        totalV = None
        
        for phaseInfo in listPhaseInfo :
            origin = phaseInfo.Origin
            spacing = phaseInfo.Spacing
            direction = phaseInfo.Direction
            size = phaseInfo.Size

            phyMat = algVTK.CVTK.get_phy_matrix(origin, spacing, direction)

            aabb = algGeometry.CScoAABB()
            vMin = algLinearMath.CScoMath.to_vec3([0.0, 0.0, 0.0])
            vMax = algLinearMath.CScoMath.to_vec3([size[0], size[1], size[2]])
            aabb.init_with_min_max(vMin, vMax)
            v = aabb.transform(phyMat)

            if totalV is None :
                totalV = v
            else :
                totalV = np.concatenate((totalV, v), axis=0, dtype=np.float32)

        vMin = algLinearMath.CScoMath.get_min_vec3(totalV)
        vMax = algLinearMath.CScoMath.get_max_vec3(totalV)
        vOffset = (vMin + vMax) / 2.0
        return vOffset







if __name__ == '__main__' :
    pass


# print ("ok ..")

