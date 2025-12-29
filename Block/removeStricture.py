import sys
import os
import numpy as np

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algImage as algImage

import multiProcessTask as multiProcessTask
import optionInfo as optionInfo



class CRemoveStricture(multiProcessTask.CMultiProcessTask) :
    def __init__(self) -> None:
        super().__init__()
        # input your code
        self.m_inputOptionInfo = None 
        self.m_inputMaskPath = ""
        self.m_outputMaskPath = ""
    def clear(self) :
        # input your code
        self.m_inputMaskPath = ""
        self.m_outputMaskPath = ""
        self.m_inputOptionInfo = None 
        super().clear()
    def process(self) :
        if self.InputOptionInfo is None :
            print("stricture : not setting input option info")
            return 
        if self.InputMaskPath == "" :
            print("stricture : not setting input mask path")
            return 
        if self.OutputMaskPath == "" :
            print("stricture : not setting output mask path")
            return 
        
        listParam = []
        paramCnt = 0
        iStrictureCnt = self.InputOptionInfo.get_stricture_count()
        for iInx in range(0, iStrictureCnt) :
            inMask, outMask = self.InputOptionInfo.get_stricture(iInx)
            inputMaskFullPath = os.path.join(self.InputMaskPath, f"{inMask}.nii.gz")
            outputMaskFullPath = os.path.join(self.OutputMaskPath, f"{outMask}.nii.gz")

            if os.path.exists(inputMaskFullPath) == False :
                continue

            listParam.append((paramCnt, inputMaskFullPath, outputMaskFullPath))
            paramCnt += 1
        
        if paramCnt == 0 :
            print("passed removed vessel stricture")
            return
        
        super().process(self._task, listParam)

    
    # param (inx, inputMaskFullPath, outputMaskFullPath)
    def _task(self, param : tuple) :
        inx = param[0]
        inputMaskFullPath = param[1]
        outputMaskFullPath = param[2]

        npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(inputMaskFullPath)
        vertex = algImage.CAlgImage.get_vertex_from_np(npImg, np.int32)

        vesselVertex = algImage.CAlgImage.get_removed_stricture_voxel_index_from_vertex(vertex, size)
        algImage.CAlgImage.set_clear(npImg, 0)
        algImage.CAlgImage.set_value(npImg, vesselVertex, 255)
        algImage.CAlgImage.save_nifti_from_np(outputMaskFullPath, npImg, origin, spacing, direction, (2, 1, 0))

        print(f"completed removed stricture vessel {outputMaskFullPath}")
    

    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputNiftiContainer
    @InputOptionInfo.setter
    def InputOptionInfo(self, inputNiftiContainer : optionInfo.COptionInfo) :
        self.m_inputNiftiContainer = inputNiftiContainer
    @property
    def InputMaskPath(self) -> str :
        return self.m_inputMaskPath
    @InputMaskPath.setter
    def InputMaskPath(self, inputMaskPath : str) :
        self.m_inputMaskPath = inputMaskPath
    @property
    def OutputMaskPath(self) -> str :
        return self.m_outputMaskPath
    @OutputMaskPath.setter
    def OutputMaskPath(self, outputMaskPath : str) :
        self.m_outputMaskPath = outputMaskPath




if __name__ == '__main__' :
    pass


# print ("ok ..")

