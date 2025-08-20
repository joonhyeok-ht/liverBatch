import sys
import os
import numpy as np
import scipy.ndimage as ndimage
import vtk

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import multiProcessTask as multiProcessTask
import niftiContainer as niftiContainer
import optionInfo as optionInfo
import reconstruction as reconstruction


import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath



class CIntersect() :
    def __init__(self):
        self.m_listRayInfo = []
        self.m_listResult = []
    def clear(self) :
        self.m_listRayInfo.clear()
        self.m_listResult.clear()


    def add_ray_info(self, rayStart : np.ndarray, rayEnd : np.ndarray) :
        self.m_listRayInfo.append((rayStart, rayEnd))
        self.m_listResult.append(None)
    def get_ray_info(self, inx : int) -> tuple :
        '''
        ret : (rayStart, rayEnd)
        '''
        return self.m_listRayInfo[inx]
    def get_result(self, inx : int) -> np.ndarray :
        return self.m_listResult[inx]
    def get_ray_info_count(self) -> int :
        return len(self.m_listRayInfo)
    def clear_ray_info(self) :
        self.m_listRayInfo.clear()
        self.m_listResult.clear()


class CIntersectNifti(CIntersect) :
    def __init__(self, npImg : np.ndarray) -> None:
        super().__init__()
        # input your code
        self.m_npImg = npImg
        self.m_bInside = False
    def clear(self) :
        # input your code
        self.m_npImg = None
        self.m_bInside = False
        super().clear()
    def process(self) :
        for inx in range(0, self.get_ray_info_count()) :
            rayStart, rayEnd = self.get_ray_info(inx)
            vertex = algImage.CAlgImage.get_vertex_by_line(self.m_npImg, rayStart, rayEnd, 255, dtype=np.int32)
            if vertex is None :
                self.m_listResult[inx] = None
                continue

            if self.Inside == True :
                pt = vertex[-1].reshape(-1, 3)
            else : 
                pt = vertex[0].reshape(-1, 3)
            self.m_listResult[inx] = pt
    

    @property
    def Inside(self) -> bool :
        return self.m_bInside
    @Inside.setter
    def Inside(self, bInside : bool) :
        self.m_bInside = bInside


class CIntersectStl(CIntersect) :
    def __init__(self, polyData : vtk.vtkPolyData) -> None:
        super().__init__()
        # input your code
        self.m_polyData = polyData
        self.m_obbTree = vtk.vtkOBBTree()
        self.m_obbTree.SetDataSet(polyData)
        self.m_obbTree.BuildLocator()
    def clear(self) :
        self.m_polyData = None
        self.m_obbTree = None
        # input your code
        super().clear()
    def process(self) :
        for inx in range(0, self.get_ray_info_count()) :
            rayStart, rayEnd = self.get_ray_info(inx)
            rayStart = [rayStart[0, 0], rayStart[0, 1], rayStart[0, 2]]
            rayEnd = [rayEnd[0, 0], rayEnd[0, 1], rayEnd[0, 2]]

            intersectionPoints = vtk.vtkPoints()
            intersected = self.m_obbTree.IntersectWithLine(rayStart, rayEnd, intersectionPoints, None)
            if intersected:
                pt = np.array(intersectionPoints.GetPoint(0)).reshape(-1, 3)
                intersectedCnt = intersectionPoints.GetNumberOfPoints()
                self.m_listResult[inx] = pt
            else:
                self.m_listResult[inx] = None


    @property
    def OBBTree(self) :
        return self.m_obbTree






class CMetricCrossCheck() :
    '''
    반드시 같은 phase에서 수행
    '''
    @staticmethod
    def get_z_slice(npImg : np.ndarray, zInx : int) -> np.ndarray :
        zSize = npImg.shape[2]
        if zInx >= zSize :
            print(f"범위 벗어남")
            return None
        return npImg[:, :, zInx]
    

    def __init__(self):
        self.m_inputNiftiContainer = None
        self.m_inputPatientPath = ""
        self.m_inputAnchorName = ""
        self.m_inputTargetName = ""
        self.m_inputAnchorStlName = ""
        self.m_inputTargetStlName = ""

    def clear(self) :
        self.m_inputNiftiContainer = None
        self.m_inputPatientPath = ""
        self.m_inputAnchorName = ""
        self.m_inputTargetName = ""
        self.m_inputAnchorStlName = ""
        self.m_inputTargetStlName = ""

        self.m_niftiFullPath1 = ""
        self.m_niftiFullPath2 = ""
        self.m_polyData1 = None
        self.m_polyData2 = None
        self.m_listZInx.clear()
        self.m_listNiftiMetricInfo.clear()
        self.m_listStlMetricInfo.clear()
    def pre_process_load_mask(self) :
        if self.InputNiftiContainer is None :
            return
        if self.InputAnchorName == "" :
            return
        if self.InputTargetName == "" :
            return
        
        retList = self.InputNiftiContainer.find_nifti_info_list_by_name(self.InputAnchorName)
        if retList is None :
            self.m_npImg1 = None
            return
        niftiInfo = retList[0]
        niftiFullPath = niftiInfo.FullPath
        self.m_npImg1, self.m_origin, self.m_spacing, self.m_direction, self.m_size = algImage.CAlgImage.get_np_from_nifti(niftiFullPath)
        print(f"origin : {self.m_origin}")
        print(f"spacing : {self.m_spacing}")
        print(f"direction : {self.m_direction}")
        print(f"size : {self.m_size}")

        retList = self.InputNiftiContainer.find_nifti_info_list_by_name(self.InputTargetName)
        if retList is None :
            self.m_npImg2 = None
            return
        niftiInfo = retList[0]
        niftiFullPath = niftiInfo.FullPath
        self.m_npImg2, self.m_origin, self.m_spacing, self.m_direction, self.m_size = algImage.CAlgImage.get_np_from_nifti(niftiFullPath)
        print(f"origin : {self.m_origin}")
        print(f"spacing : {self.m_spacing}")
        print(f"direction : {self.m_direction}")
        print(f"size : {self.m_size}")
    def process(self) :
        if self.InputNiftiContainer is None :
            print("Metric Cross Check : not setting nifti container")
            return
        if self.InputPatientPath == "" :
            print("Metric Cross Check : not found patient path")
            return
        if self.InputAnchorName == "" :
            print("Metric Cross Check : not setting anchor name")
            return
        if self.InputTargetName == "" :
            print("Metric Cross Check : not setting target name")
            return
        if self.InputAnchorStlName == "" :
            print("Metric Cross Check : not setting anchor stl name")
            return
        if self.InputTargetStlName == "" :
            print("Metric Cross Check : not setting target stl name")
            return
        if self.m_npImg1 is None :
            print("Metric Cross Check : failed loading npImg1")
            return
        if self.m_npImg2 is None :
            print("Metric Cross Check : failed loading npImg2")
            return
        
        niftiInfo = self.get_nifti_info(self.InputAnchorName)
        anchorStlFullPath = os.path.join(self.InputPatientPath, niftiInfo.MaskInfo.BlenderName)
        anchorStlFullPath = os.path.join(anchorStlFullPath, f"{self.InputAnchorStlName}.stl")

        niftiInfo = self.get_nifti_info(self.InputTargetName)
        targetStlFullPath = os.path.join(self.InputPatientPath, niftiInfo.MaskInfo.BlenderName)
        targetStlFullPath = os.path.join(targetStlFullPath, f"{self.InputTargetStlName}.stl")

        if os.path.exists(anchorStlFullPath) == False :
            print(f"Metric Cross Check : failed loading {self.InputAnchorStlName}")
            return
        if os.path.exists(targetStlFullPath) == False :
            print(f"Metric Cross Check : failed loading {self.InputTargetStlName}")
            return
        
        phase = niftiInfo.MaskInfo.Phase
        phaseInfo = self.InputNiftiContainer.find_phase_info(phase)
        phaseOffset = phaseInfo.Offset
        
        self.m_polyData1 = algVTK.CVTK.load_poly_data_stl(anchorStlFullPath)
        self.m_polyData2 = algVTK.CVTK.load_poly_data_stl(targetStlFullPath)

        self.m_intersectNifti1 = CIntersectNifti(self.m_npImg1)
        self.m_intersectNifti1.Inside = True
        self.m_intersectNifti2 = CIntersectNifti(self.m_npImg2)
        self.m_intersectNifti2.Inside = False
        self.m_intersectStl1 = CIntersectStl(self.m_polyData1)
        self.m_intersectStl2 = CIntersectStl(self.m_polyData2)

        self.m_matPhy = algVTK.CVTK.get_vtk_phy_matrix_with_spacing(self.m_origin, self.m_spacing, self.m_direction, phaseOffset)
        npVertex = algImage.CAlgImage.get_vertex_from_np(self.m_npImg2, dtype=np.int32)
        minV = algLinearMath.CScoMath.get_min_vec3(npVertex).astype(np.int32)
        maxV = algLinearMath.CScoMath.get_max_vec3(npVertex).astype(np.int32)

        self.m_listZInx = []
        self.m_listNiftiMetricInfo = []
        self.m_listStlMetricInfo = []

        # print("-- Metric Start --")
        for zInx in range(minV[0, 2], maxV[0, 2] + 1) :
            niftiMetricInfo, stlMetricInfo = self._get_info(zInx)
            self.m_listZInx.append(zInx)
            self.m_listNiftiMetricInfo.append(niftiMetricInfo)
            self.m_listStlMetricInfo.append(stlMetricInfo)
        # print("-- Metric End --")


    def get_nifti_info(self, maskName : str) -> niftiContainer.CNiftiInfo :
        retList = self.InputNiftiContainer.find_nifti_info_list_by_name(maskName)
        if retList is None :
            return None
        niftiInfo = retList[0]
        return niftiInfo
    
    def get_info_count(self) -> int :
        return len(self.m_listZInx)
    def get_z_inx(self, inx : int) -> int :
        return self.m_listZInx[inx]
    def get_nifti_info_center(self, inx : int) -> np.ndarray :
        if self.m_listNiftiMetricInfo[inx][0] is None :
            return None
        return self.m_listNiftiMetricInfo[inx][0]
    def get_nifti_info_ray(self, inx : int, rayInx : int) -> tuple :
        '''
        ret : (rayStart, rayEnd)
        '''
        if self.m_listNiftiMetricInfo[inx][1 + rayInx] is None :
            return (None, None)
        return self.m_listNiftiMetricInfo[inx][1 + rayInx]
    def get_nifti_info_pt(self, inx : int, ptInx : int) -> tuple :
        '''
        ret : (pt_N, pt_N, dist)
        '''
        if self.m_listNiftiMetricInfo[inx][5 + ptInx] is None :
            return (None, None, None)
        return self.m_listNiftiMetricInfo[inx][5 + ptInx]
    def get_stl_info_center(self, inx : int) -> np.ndarray :
        if self.m_listStlMetricInfo[inx][0] is None :
            return None
        return self.m_listStlMetricInfo[inx][0]
    def get_stl_info_ray(self, inx : int, rayInx : int) -> tuple :
        '''
        ret : (rayStart, rayEnd)
        '''
        if self.m_listStlMetricInfo[inx][1 + rayInx] is None :
            return (None, None)
        return self.m_listStlMetricInfo[inx][1 + rayInx]
    def get_stl_info_pt(self, inx : int, ptInx : int) -> tuple :
        '''
        ret : (pt_N, pt_N, dist)
        '''
        if self.m_listStlMetricInfo[inx][5 + ptInx] is None :
            return (None, None, None)
        return self.m_listStlMetricInfo[inx][5 + ptInx]


    def _get_info(self, zInx : int) :
        '''
        ret : (retNiftiMetricInfo, retStlMetricInfo)
        retNiftiMetricInfo = [npCenterPoint, rayInfo0, rayInfo1, rayInfo2, rayInfo3, (pt0 - pt0), (pt1 - pt1), (pt2 - pt2), (pt3 - pt3)]
        retStlMetricInfo = [npCenterPoint, rayInfo0, rayInfo1, rayInfo2, rayInfo3,  (pt0 - pt0), (pt1 - pt1), (pt2 - pt2), (pt3 - pt3)]
        '''
        retNiftiMetricInfo = []
        retStlMetricInfo = []

        npImgZSlice1 = CMetricCrossCheck.get_z_slice(self.m_npImg1, zInx)
        npImgZSlice2 = CMetricCrossCheck.get_z_slice(self.m_npImg2, zInx)

        npVertex = np.array(np.where(npImgZSlice1 > 0), dtype=np.int32).transpose()
        if npVertex.size == 0 :
            retNiftiMetricInfo = [None for _ in range(0, 9)]
            retStlMetricInfo = [None for _ in range(0, 9)]
            return (retNiftiMetricInfo, retStlMetricInfo)
        npCenterPoint = np.mean(npVertex, axis=0).reshape(-1, 2)
        z_values = np.zeros((npCenterPoint.shape[0], 1))
        npCenterPoint = np.hstack((npCenterPoint, z_values))

        w = self.m_npImg1.shape[0]
        h = self.m_npImg1.shape[1]
        cx = int(npCenterPoint[0, 0] + 0.5)
        cy = int(npCenterPoint[0, 1] + 0.5)
        cz = zInx

        retNiftiMetricInfo.append(npCenterPoint)
        npCenterPoint = algLinearMath.CScoMath.mul_mat4_vec3(self.m_matPhy, npCenterPoint)
        retStlMetricInfo.append(npCenterPoint)

        listRayInfo = []
        zOffset = 0.5
        s = algLinearMath.CScoMath.to_vec3([cx, cy, cz + zOffset]).astype(np.int32)
        e = algLinearMath.CScoMath.to_vec3([cx, h, cz + zOffset]).astype(np.int32)
        listRayInfo.append((s, e))
        s = algLinearMath.CScoMath.to_vec3([cx, cy, cz + zOffset]).astype(np.int32)
        e = algLinearMath.CScoMath.to_vec3([cx, 0, cz + zOffset]).astype(np.int32)
        listRayInfo.append((s, e))
        s = algLinearMath.CScoMath.to_vec3([cx, cy, cz + zOffset]).astype(np.int32)
        e = algLinearMath.CScoMath.to_vec3([w, cy, cz + zOffset]).astype(np.int32)
        listRayInfo.append((s, e))
        s = algLinearMath.CScoMath.to_vec3([cx, cy, cz + zOffset]).astype(np.int32)
        e = algLinearMath.CScoMath.to_vec3([0, cy, cz + zOffset]).astype(np.int32)
        listRayInfo.append((s, e))

        self.m_intersectNifti1.clear_ray_info()
        self.m_intersectNifti2.clear_ray_info()
        self.m_intersectStl1.clear_ray_info()
        self.m_intersectStl2.clear_ray_info()
        for rayInfo in listRayInfo :
            rayStart = rayInfo[0]
            rayEnd = rayInfo[1]
            retNiftiMetricInfo.append((rayStart, rayEnd))
            self.m_intersectNifti1.add_ray_info(rayStart, rayEnd)
            self.m_intersectNifti2.add_ray_info(rayStart, rayEnd)

            rayStart = algLinearMath.CScoMath.mul_mat4_vec3(self.m_matPhy, rayStart)
            rayEnd = algLinearMath.CScoMath.mul_mat4_vec3(self.m_matPhy, rayEnd)
            retStlMetricInfo.append((rayStart, rayEnd))
            self.m_intersectStl1.add_ray_info(rayStart, rayEnd)
            self.m_intersectStl2.add_ray_info(rayStart, rayEnd)
        self.m_intersectNifti1.process()
        self.m_intersectNifti2.process()
        self.m_intersectStl1.process()
        self.m_intersectStl2.process()

        niftiSpacing = np.array(self.m_spacing).reshape(3,)

        for inx in range(0, 4) :
            pt1 = self.m_intersectNifti1.get_result(inx)
            pt2 = self.m_intersectNifti2.get_result(inx)
            dist = None
            if pt1 is not None and pt2 is not None :
                scaledDiff = (pt1.reshape(3,) - pt2.reshape(3,)) * niftiSpacing
                dist = np.sqrt(np.sum(scaledDiff**2))
            retNiftiMetricInfo.append((pt1, pt2, dist))

            pt1 = self.m_intersectStl1.get_result(inx)
            pt2 = self.m_intersectStl2.get_result(inx)
            dist = None
            if pt1 is not None and pt2 is not None :
                scaledDiff = (pt1.reshape(3,) - pt2.reshape(3,))
                dist = np.sqrt(np.sum(scaledDiff**2))
            retStlMetricInfo.append((pt1, pt2, dist))
        
        return (retNiftiMetricInfo, retStlMetricInfo)
    

    @property
    def InputNiftiContainer(self) -> niftiContainer.CNiftiContainer :
        return self.m_inputNiftiContainer
    @InputNiftiContainer.setter
    def InputNiftiContainer(self, inputNiftiContainer : niftiContainer.CNiftiContainer) :
        self.m_inputNiftiContainer = inputNiftiContainer
    @property
    def InputPatientPath(self) -> str :
        return self.m_inputPatientPath
    @InputPatientPath.setter
    def InputPatientPath(self, inputPatientPath : str) :
        self.m_inputPatientPath = inputPatientPath
    @property
    def InputAnchorName(self) -> str :
        return self.m_inputAnchorName
    @InputAnchorName.setter
    def InputAnchorName(self, inputAnchorName : str) :
        self.m_inputAnchorName = inputAnchorName
    @property
    def InputTargetName(self) -> str :
        return self.m_inputTargetName
    @InputTargetName.setter
    def InputTargetName(self, inputTargetName : str) :
        self.m_inputTargetName = inputTargetName
    @property
    def InputAnchorStlName(self) -> str :
        return self.m_inputAnchorStlName
    @InputAnchorStlName.setter
    def InputAnchorStlName(self, inputAnchorStlName : str) :
        self.m_inputAnchorStlName = inputAnchorStlName
    @property
    def InputTargetStlName(self) -> str :
        return self.m_inputTargetStlName
    @InputTargetStlName.setter
    def InputTargetStlName(self, inputTargetStlName : str) :
        self.m_inputTargetStlName = inputTargetStlName
    


    @property
    def NpImg1(self) -> np.ndarray :
        return self.m_npImg1
    @property
    def NpImg2(self) -> np.ndarray :
        return self.m_npImg2
    @property
    def MatPhy(self) -> np.ndarray :
        return self.m_matPhy






if __name__ == '__main__' :
    pass


# print ("ok ..")

