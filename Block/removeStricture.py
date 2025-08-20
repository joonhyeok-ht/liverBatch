import sys
import os
import numpy as np

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algImage as algImage

import multiProcessTask as multiProcessTask
import niftiContainer as niftiContainer



class CRemoveStricture(multiProcessTask.CMultiProcessTask) :
    def __init__(self) -> None:
        super().__init__()
        # input your code 
        self.m_inputNiftiContainer = None
    def clear(self) :
        # input your code
        self.m_inputNiftiContainer = None
        super().clear()
    def process(self) :
        if self.InputNiftiContainer is None :
            print("not setting input nifti container")
            return 
        
        listStrictureNiftiInfo = self.InputNiftiContainer.find_nifti_info_list_by_stricture_mode(1)
        if listStrictureNiftiInfo is None :
            print("not found stricture nifti file")
            return
        
        listParam = []
        listNiftiInfo = []
        paramCnt = 0
        for niftiInfo in listStrictureNiftiInfo :
            phaseInfo = self.InputNiftiContainer.find_phase_info(niftiInfo.MaskInfo.Phase)
            if niftiInfo.Valid == True and phaseInfo is not None :
                listParam.append((paramCnt, niftiInfo, phaseInfo.Size))
                listNiftiInfo.append(niftiInfo)
                paramCnt += 1
        
        if paramCnt == 0 :
            print("passed removed vessel stricture")
            return
        
        self._alloc_shared_list(paramCnt)
        super().process(self._task, listParam)

        listRemoveStricturedVertex = self.get_shared_list()
        for inx, vertex in enumerate(listRemoveStricturedVertex) :
            niftiInfo = listNiftiInfo[inx]
            niftiInfo.Vertex = vertex
        listRemoveStricturedVertex.clear()
        listNiftiInfo.clear()
        listStrictureNiftiInfo.clear()

    
    # param (inx,)
    def _task(self, param : tuple) :
        inx = param[0]
        niftiInfo = param[1]
        shape = param[2]

        npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(niftiInfo.FullPath)
        vertex = algImage.CAlgImage.get_vertex_from_np(npImg, np.int32)

        vesselVertex = algImage.CAlgImage.get_removed_stricture_voxel_index_from_vertex(vertex, shape)
        self.m_sharedList[inx] = vesselVertex
        print(f"completed removed stricture vessel {niftiInfo.MaskInfo.Name}")
    

    @property
    def InputNiftiContainer(self) -> niftiContainer.CNiftiContainer :
        return self.m_inputNiftiContainer
    @InputNiftiContainer.setter
    def InputNiftiContainer(self, inputNiftiContainer : niftiContainer.CNiftiContainer) :
        self.m_inputNiftiContainer = inputNiftiContainer




if __name__ == '__main__' :
    pass


# print ("ok ..")

