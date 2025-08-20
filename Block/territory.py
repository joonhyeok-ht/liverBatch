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
import AlgUtil.algSegment as algSegment
import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath


class CTerritory(multiProcessTask.CMultiProcessTask) :
    def __init__(self) -> None:
        super().__init__()
        self.m_inputPath = ""
        self.m_inputNiftiContainer = None
        self.m_inputOptionInfo = None
        self.m_inputSegInx = -1
        self.m_outputPath = ""

        self.m_organInfo = None
        self.m_matOrgan = None
        self.m_matInvOrgan = None
        self.m_queryVertex = None
    def clear(self) :
        # input your code
        self.m_inputPath = ""
        self.m_inputNiftiContainer = None
        self.m_inputOptionInfo = None
        self.m_inputSegInx = -1
        self.m_outputPath = ""

        self.m_organInfo = None
        self.m_matOrgan = None
        self.m_matInvOrgan = None
        self.m_queryVertex = None
        self.m_wholeVesselInfo = None
        super().clear()
    def process(self) :
        if self.InputPath == "" :
            print("not setting input path")
            return
        if self.InputNiftiContainer is None :
            print("not setting input nifti container")
            return 
        if self.InputOptionInfo is None :
            print("not setting input option info")
            return
        if self.InputSegInx == -1 :
            print("not setting input seg inx")
            return
        
        segInfo = self.InputOptionInfo.get_segmentinfo(self.InputSegInx)
        organName = segInfo.Organ
        organMaskInfo = self.InputNiftiContainer.find_nifti_info_by_blender_name(organName)
        if organMaskInfo is None or organMaskInfo.Valid == False :
            print(f"not found organ maskInfo : {organName}")
            return
        organMaskPhase = organMaskInfo.MaskInfo.Phase
        phaseInfo = self.InputNiftiContainer.find_phase_info(organMaskPhase)
        if phaseInfo is None :
            print(f"not found organ phaseInfo : {organName}")
            return

        spacing = phaseInfo.Spacing
        reconType = organMaskInfo.MaskInfo.ReconType
        organStlFullPath = os.path.join(self.InputPath, f"{organName}.stl")
        if os.path.exists(organStlFullPath) == False : 
            print(f"not found organ stl : {organName}")
            return
        organPolyData = algVTK.CVTK.load_poly_data_stl(organStlFullPath)
        self.m_organInfo = algVTK.CVTK.poly_data_voxelize(organPolyData, spacing, 255.0)
        self.m_matOrgan = algVTK.CVTK.get_phy_matrix(self.m_organInfo[1], self.m_organInfo[2], self.m_organInfo[3])
        self.m_matInvOrgan = algLinearMath.CScoMath.inv_mat4(self.m_matOrgan)
        self.m_queryVertex = algImage.CAlgImage.get_vertex_from_np(self.m_organInfo[0], np.int32)

        listParam = []
        paramCnt = 0

        vesselInfoCnt = segInfo.get_vesselinfo_count()
        for inx in range(0, vesselInfoCnt) :
            wholeVesselName = segInfo.get_vesselinfo_whole_vessel(inx)
            wholeVesselFullPath = os.path.join(self.InputPath, f"{wholeVesselName}.stl")
            if os.path.exists(wholeVesselFullPath) == False :
                print(f"territory : not found whole vessel : {wholeVesselName}")
                continue

            wholeVesselMaskInfo = self.InputNiftiContainer.find_nifti_info_by_blender_name(wholeVesselName)
            if wholeVesselMaskInfo is None or wholeVesselMaskInfo.Valid == False :
                print(f"not found whole vessel maskInfo : {wholeVesselName}")
                continue
            
            wholeVesselMaskPhase = wholeVesselMaskInfo.MaskInfo.Phase
            phaseInfo = self.InputNiftiContainer.find_phase_info(wholeVesselMaskPhase)
            if phaseInfo is None :
                print(f"not found whole vessel phaseInfo : {wholeVesselName}")
                continue
            spacing = phaseInfo.Spacing

            wholeVesselPolyData = algVTK.CVTK.load_poly_data_stl(wholeVesselFullPath)
            self.m_wholeVesselInfo = algVTK.CVTK.poly_data_voxelize(wholeVesselPolyData, spacing, 255.0)
            self.m_matWholeVessel = algVTK.CVTK.get_phy_matrix(self.m_wholeVesselInfo[1], self.m_wholeVesselInfo[2], self.m_wholeVesselInfo[3])

            self.m_dilationIter = segInfo.get_vesselinfo_dilation_iter(inx)
            self.m_noiseSegCnt = segInfo.get_vesselinfo_noise_seg_count(inx)
            childVesselStartInx = segInfo.get_vesselinfo_child_start(inx)
            childVesselEndInx = segInfo.get_vesselinfo_child_end(inx)

            for childInx in range(childVesselStartInx, childVesselEndInx + 1) :
                # vessel segment 
                vesselName = f"{wholeVesselName}{childInx}"
                vesselFullPath = os.path.join(self.InputPath, f"{vesselName}.stl")
                if os.path.exists(vesselFullPath) == False :
                    print(f"territory : not found vessel : {vesselName}")
                    continue

                # organ segment 
                territoryName = f"{organName}_{vesselName}"
                '''
                (paramInx, vesselFullPath, reconType, territoryName)
                '''
                listParam.append((paramCnt, vesselFullPath, reconType, territoryName))
                paramCnt += 1

        if paramCnt == 0 :
            print("passed removed vessel stricture")
            return
        
        self._alloc_shared_list(paramCnt)
        super().process(self._task, listParam)


    def _task(self, param : tuple) :
        inx = param[0]
        vesselFullPath = param[1]
        reconType = param[2]
        territoryName = param[3]

        wholeInfo = self.m_wholeVesselInfo
        spacing = wholeInfo[2]

        subVessel = algVTK.CVTK.load_poly_data_stl(vesselFullPath)
        subInfo = algVTK.CVTK.poly_data_voxelize(subVessel, spacing, 255.0)

        # wholeVertex = algImage.CAlgImage.get_vertex_from_np(wholeInfo[0], np.int32)
        subVertex = algImage.CAlgImage.get_vertex_from_np(subInfo[0], np.int32)

        matWhole = self.m_matWholeVessel
        invMatWhole = algLinearMath.CScoMath.inv_mat4(matWhole)
        matSub = algVTK.CVTK.get_phy_matrix(subInfo[1], subInfo[2], subInfo[3])
        toMatWhole = algLinearMath.CScoMath.mul_mat4_mat4(invMatWhole, matSub)
        matToOrgan = algLinearMath.CScoMath.mul_mat4_mat4(self.m_matInvOrgan, matWhole)

        subVertex = algLinearMath.CScoMath.mul_mat4_vec3(toMatWhole, subVertex)
        subVertex = np.round(subVertex).astype(np.int32)

        subMask = algImage.CAlgImage.create_np(wholeInfo[4], np.uint8)
        algImage.CAlgImage.set_clear(subMask, 0)
        algImage.CAlgImage.set_value(subMask, subVertex, 1)

        extractedWholeMask = wholeInfo[0].copy() 
        extractedWholeMask[extractedWholeMask > 0] = 1


        # process
        structure = np.ones((3, 3, 3), dtype=np.uint8)
        binaryMask = subMask > 0
        subMask = ndimage.binary_dilation(binaryMask, structure=structure, iterations=self.m_dilationIter).astype(np.uint8)
        extractedWholeMask[subMask == 1] = 0
        # removing noise
        self.__remove_noise(extractedWholeMask, self.m_noiseSegCnt)


        # territory
        extractedWholeVertex = algImage.CAlgImage.get_vertex_from_np(extractedWholeMask, np.int32)
        extractedWholeVertex = algLinearMath.CScoMath.mul_mat4_vec3(matToOrgan, extractedWholeVertex)
        subVertex = algLinearMath.CScoMath.mul_mat4_vec3(matToOrgan, subVertex)

        segmentProcess = algSegment.CSegmentBasedVoxelProcess()
        segmentProcess.add_anchor(extractedWholeVertex, 1)
        segmentProcess.add_anchor(subVertex, 2)
        segmentProcess.process(self.m_queryVertex)
        territoryVertex = segmentProcess.get_query_vertex_with_seg_index(2)

        territoryFullPath = os.path.join(self.OutputPath, f"{territoryName}.stl")

        reconParam = self.InputOptionInfo.find_recon_param(reconType)
        contour = reconParam.Contour
        algorithm = reconParam.Algorithm
        param = reconParam.Param
        gaussian = reconParam.Gaussian
        resampling = reconParam.ResamplingFactor
  
        inputNiftiFullPath = os.path.join(self.OutputPath, f"{territoryName}.nii.gz")
        npImg = algImage.CAlgImage.create_np(self.m_organInfo[4], np.uint8)
        algImage.CAlgImage.set_clear(npImg, 0)
        algImage.CAlgImage.set_value(npImg, territoryVertex, 255)
        algImage.CAlgImage.save_nifti_from_np(inputNiftiFullPath, npImg, self.m_organInfo[1], self.m_organInfo[2], self.m_organInfo[3], (2, 1, 0))
        print(f"saved territory nifti : {inputNiftiFullPath}")
        npImg = None

        territoryPolyData = reconstruction.CReconstruction.reconstruction_territory(inputNiftiFullPath, self.m_organInfo[1], self.m_organInfo[3], contour, param, algorithm, gaussian, resampling)
        algVTK.CVTK.save_poly_data_stl(territoryFullPath, territoryPolyData)

        print(f"completed territory : {territoryFullPath}")


    def __remove_noise(self, npImg : np.ndarray, minCnt : int = 5) :
        structure = np.ones((3, 3, 3), dtype=np.uint8)
        labeledMask, num_features = ndimage.label(npImg, structure=structure)
        componentSizes = np.bincount(labeledMask.ravel())
        removeMask = componentSizes < minCnt
        removeMask[0] = 0 # 배경 제외
        cleanedMask = removeMask[labeledMask]
        npImg[cleanedMask > 0] = 0
    def __subtract_voxel_regions2(
        self, 
        mesh1_voxel: tuple, 
        mesh2_voxel: tuple,
        dilationIter: int = 1
    ) -> np.ndarray:
        """
        mesh1의 voxel 영역에서 mesh2의 voxel 영역을 0으로 만듭니다.

        Parameters:
        - mesh1_voxel : (npImg, origin, spacing, direction, size)
        - mesh2_voxel : (npImg, origin, spacing, direction, size)

        Returns:
        - mesh1의 voxel 데이터에서 mesh2와 겹치는 부분을 0으로 설정한 npImg 배열
        """
        # mesh1과 mesh2의 정보 추출
        mesh1_img, mesh1_origin, mesh1_spacing, _, mesh1_size = mesh1_voxel
        mesh2_img, mesh2_origin, mesh2_spacing, _, mesh2_size = mesh2_voxel

        structure = np.ones((3, 3, 3), dtype=np.uint8)
        mesh2_img = ndimage.binary_dilation(mesh2_img, structure=structure, iterations=dilationIter).astype(mesh2_img.dtype)

        # 원점과 크기를 기준으로 겹치는 영역을 계산
        mesh1_min_bound = np.array(mesh1_origin)
        mesh1_max_bound = mesh1_min_bound + np.array(mesh1_size) * np.array(mesh1_spacing)
        
        mesh2_min_bound = np.array(mesh2_origin)
        mesh2_max_bound = mesh2_min_bound + np.array(mesh2_size) * np.array(mesh2_spacing)

        # 겹치는 영역의 최소, 최대 좌표 계산
        overlap_min_bound = np.maximum(mesh1_min_bound, mesh2_min_bound)
        overlap_max_bound = np.minimum(mesh1_max_bound, mesh2_max_bound)

        # 겹치는 영역이 있는지 확인
        if np.any(overlap_min_bound >= overlap_max_bound):
            print("겹치는 영역이 없습니다.")
            return mesh1_img  # 겹치는 영역이 없으면 원본을 반환

        # 겹치는 영역의 인덱스를 계산 (최대 겹치는 크기를 고려하여 크기 맞춤)
        overlap_min_idx_mesh1 = np.round((overlap_min_bound - mesh1_min_bound) / np.array(mesh1_spacing)).astype(int)
        overlap_max_idx_mesh1 = np.round((overlap_max_bound - mesh1_min_bound) / np.array(mesh1_spacing)).astype(int)

        overlap_min_idx_mesh2 = np.round((overlap_min_bound - mesh2_min_bound) / np.array(mesh2_spacing)).astype(int)
        overlap_max_idx_mesh2 = np.round((overlap_max_bound - mesh2_min_bound) / np.array(mesh2_spacing)).astype(int)

        # 겹치는 영역에서 mesh1과 mesh2의 크기를 동일하게 맞춤
        overlap_shape_mesh1 = [overlap_max_idx_mesh1[i] - overlap_min_idx_mesh1[i] for i in range(3)]
        overlap_shape_mesh2 = [overlap_max_idx_mesh2[i] - overlap_min_idx_mesh2[i] for i in range(3)]

        # 겹치는 영역의 최소 크기로 조정하여 두 배열의 크기를 맞춤
        min_overlap_shape = np.minimum(overlap_shape_mesh1, overlap_shape_mesh2)

        overlap_max_idx_mesh1 = overlap_min_idx_mesh1 + min_overlap_shape
        overlap_max_idx_mesh2 = overlap_min_idx_mesh2 + min_overlap_shape

        # 겹치는 영역 추출
        mesh1_overlap_region = mesh1_img[overlap_min_idx_mesh1[0]:overlap_max_idx_mesh1[0],
                                        overlap_min_idx_mesh1[1]:overlap_max_idx_mesh1[1],
                                        overlap_min_idx_mesh1[2]:overlap_max_idx_mesh1[2]]

        mesh2_overlap_region = mesh2_img[overlap_min_idx_mesh2[0]:overlap_max_idx_mesh2[0],
                                        overlap_min_idx_mesh2[1]:overlap_max_idx_mesh2[1],
                                        overlap_min_idx_mesh2[2]:overlap_max_idx_mesh2[2]]

        # mesh2의 영역에서 값이 1인 곳에 대해 mesh1의 값을 0으로 설정
        mesh1_overlap_region[mesh2_overlap_region > 0] = 0

        return mesh1_img
    def __subtract_voxel_regions(
            self, 
            mesh1_voxel: tuple, 
            mesh2_voxel: tuple,
            dilatiionIter : int = 1
            ) -> np.ndarray:
        """
        mesh1의 voxel 영역에서 mesh2의 voxel 영역을 0으로 만듭니다.

        Parameters:
        - mesh1_voxel : (npImg, origin, spacing, direction, size)
        - mesh2_voxel : (npImg, origin, spacing, direction, size)

        Returns:
        - mesh1의 voxel 데이터에서 mesh2와 겹치는 부분을 0으로 설정한 npImg 배열
        """
        # mesh1과 mesh2의 정보 추출
        mesh1_img, mesh1_origin, mesh1_spacing, _, mesh1_size = mesh1_voxel
        mesh2_img, mesh2_origin, mesh2_spacing, _, mesh2_size = mesh2_voxel

        mesh2_img = ndimage.binary_dilation(mesh2_img, structure=None, iterations=dilatiionIter).astype(mesh2_img.dtype)

        # 원점과 크기를 기준으로 겹치는 영역을 계산
        mesh1_min_bound = np.array(mesh1_origin)
        mesh1_max_bound = mesh1_min_bound + np.array(mesh1_size) * np.array(mesh1_spacing)
        
        mesh2_min_bound = np.array(mesh2_origin)
        mesh2_max_bound = mesh2_min_bound + np.array(mesh2_size) * np.array(mesh2_spacing)

        # 겹치는 영역의 최소, 최대 좌표 계산
        overlap_min_bound = np.maximum(mesh1_min_bound, mesh2_min_bound)
        overlap_max_bound = np.minimum(mesh1_max_bound, mesh2_max_bound)

        # 겹치는 영역이 있는지 확인
        if np.any(overlap_min_bound >= overlap_max_bound):
            print("겹치는 영역이 없습니다.")
            return mesh1_img  # 겹치는 영역이 없으면 원본을 반환

        # 겹치는 영역의 인덱스를 계산 (최대 겹치는 크기를 고려하여 크기 맞춤)
        overlap_min_idx_mesh1 = np.floor((overlap_min_bound - mesh1_min_bound) / np.array(mesh1_spacing)).astype(int)
        overlap_max_idx_mesh1 = np.ceil((overlap_max_bound - mesh1_min_bound) / np.array(mesh1_spacing)).astype(int)

        overlap_min_idx_mesh2 = np.floor((overlap_min_bound - mesh2_min_bound) / np.array(mesh2_spacing)).astype(int)
        overlap_max_idx_mesh2 = np.ceil((overlap_max_bound - mesh2_min_bound) / np.array(mesh2_spacing)).astype(int)

        # 겹치는 영역에서 mesh1과 mesh2의 크기를 동일하게 맞춤
        overlap_shape_mesh1 = [overlap_max_idx_mesh1[i] - overlap_min_idx_mesh1[i] for i in range(3)]
        overlap_shape_mesh2 = [overlap_max_idx_mesh2[i] - overlap_min_idx_mesh2[i] for i in range(3)]

        # 겹치는 영역의 최소 크기로 조정하여 두 배열의 크기를 맞춤
        min_overlap_shape = np.minimum(overlap_shape_mesh1, overlap_shape_mesh2)

        overlap_max_idx_mesh1 = overlap_min_idx_mesh1 + min_overlap_shape
        overlap_max_idx_mesh2 = overlap_min_idx_mesh2 + min_overlap_shape

        # 겹치는 영역 추출
        mesh1_overlap_region = mesh1_img[overlap_min_idx_mesh1[0]:overlap_max_idx_mesh1[0],
                                        overlap_min_idx_mesh1[1]:overlap_max_idx_mesh1[1],
                                        overlap_min_idx_mesh1[2]:overlap_max_idx_mesh1[2]]

        mesh2_overlap_region = mesh2_img[overlap_min_idx_mesh2[0]:overlap_max_idx_mesh2[0],
                                        overlap_min_idx_mesh2[1]:overlap_max_idx_mesh2[1],
                                        overlap_min_idx_mesh2[2]:overlap_max_idx_mesh2[2]]

        # mesh2의 영역에서 값이 1인 곳에 대해 mesh1의 값을 0으로 설정
        mesh1_overlap_region[mesh2_overlap_region > 0] = 0

        return mesh1_img


    @property
    def InputPath(self) -> str :
        return self.m_inputPath
    @InputPath.setter
    def InputPath(self, inputPath : str) :
        self.m_inputPath = inputPath
    @property
    def InputNiftiContainer(self) -> niftiContainer.CNiftiContainer :
        return self.m_inputNiftiContainer
    @InputNiftiContainer.setter
    def InputNiftiContainer(self, inputNiftiContainer : niftiContainer.CNiftiContainer) :
        self.m_inputNiftiContainer = inputNiftiContainer
    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, optionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = optionInfo
    @property
    def InputSegInx(self) -> int :
        return self.m_inputSegInx
    @InputSegInx.setter
    def InputSegInx(self, inputSegInx : int) :
        self.m_inputSegInx = inputSegInx
    
    @property
    def OutputPath(self) -> str :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath



class CTerritoryMask(multiProcessTask.CMultiProcessTask) :
    def __init__(self) -> None:
        super().__init__()
        self.m_inputPath = ""
        self.m_inputNiftiContainer = None
        self.m_inputOptionInfo = None
        self.m_inputSegInx = -1
        self.m_outputPath = ""
        self.m_queryVertex = None
    def clear(self) :
        # input your code
        self.m_inputPath = ""
        self.m_inputNiftiContainer = None
        self.m_inputOptionInfo = None
        self.m_inputSegInx = -1
        self.m_outputPath = ""
        self.m_queryVertex = None
        super().clear()
        

    def process(self) :
        if self.InputPath == "" :
            print("not setting input path")
            return
        if self.InputNiftiContainer is None :
            print("not setting input nifti container")
            return 
        if self.InputOptionInfo is None :
            print("not setting input option info")
            return
        if self.InputSegInx == -1 :
            print("not setting input seg inx")
            return
        
        segInfo = self.InputOptionInfo.get_segmentinfo(self.InputSegInx)
        organName = segInfo.Organ
        organMaskName = self._find_mask_name(organName)
        if organMaskName == "" :
            print(f"not found organMaskName : {organMaskName}")
            return
        organMaskPath = f"{organMaskName}.nii.gz"
        organMaskFullPath = os.path.join(self.InputPath, organMaskPath)
        if os.path.exists(organMaskFullPath) == False :
            print(f"not found organMaskPath : {organMaskPath}")
            return
        
        self.m_organMaskInfo = self._find_mask_info(organName)
        organMaskPhase = self.m_organMaskInfo.Phase
        self.m_organPhaseInfo = self.InputNiftiContainer.find_phase_info(organMaskPhase)
        queryVertex, origin, spacing, direction, size = algImage.CAlgImage.get_vertex_from_nifti(organMaskFullPath)

        invOrganMat = algVTK.CVTK.get_phy_matrix(origin, spacing, direction)
        offsetMat = algLinearMath.CScoMath.translation_mat4(self.m_organPhaseInfo.Offset)
        invOrganMat = algLinearMath.CScoMath.mul_mat4_mat4(offsetMat, invOrganMat)
        invOrganMat = algLinearMath.CScoMath.inv_mat4(invOrganMat)

        listParam = []
        paramCnt = 0

        vesselInfoCnt = segInfo.get_vesselinfo_count()
        for inx in range(0, vesselInfoCnt) :
            wholeVesselName = segInfo.get_vesselinfo_whole_vessel(inx)
            wholeVesselMaskName = self._find_mask_name(wholeVesselName)
            if wholeVesselMaskName == "" :
                print(f"not found wholeVesselMaskName : {wholeVesselMaskName}")
                continue
            wholeVesselMaskPath = f"{wholeVesselMaskName}.nii.gz"
            wholeVesselMaskFullPath = os.path.join(self.InputPath, wholeVesselMaskPath)
            if os.path.exists(wholeVesselMaskFullPath) == False :
                print(f"not found wholeVesselMaskPath : {wholeVesselMaskPath}")
                continue

            wholeVesselMaskInfo = self._find_mask_info(wholeVesselName)
            wholeVesselMaskPhase = wholeVesselMaskInfo.Phase
            wholeVesselPhaseInfo = self.InputNiftiContainer.find_phase_info(wholeVesselMaskPhase)

            transFlag = False
            transMat = None
            if organMaskPhase != wholeVesselMaskPhase :
                transFlag = True
                offset = wholeVesselPhaseInfo.Offset
                offsetMat = algLinearMath.CScoMath.translation_mat4(offset)
                vesselMat = algVTK.CVTK.get_phy_matrix(wholeVesselPhaseInfo.Origin, wholeVesselPhaseInfo.Spacing, wholeVesselPhaseInfo.Direction)
                transMat = algLinearMath.CScoMath.mul_mat4_mat4(offsetMat, vesselMat)
                transMat = algLinearMath.CScoMath.mul_mat4_mat4(invOrganMat, transMat)
            
            npImgWholeVessel, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(wholeVesselMaskFullPath)
            childVesselStartInx = segInfo.get_vesselinfo_child_start(inx)
            childVesselEndInx = segInfo.get_vesselinfo_child_end(inx)

            for childInx in range(childVesselStartInx, childVesselEndInx + 1) :
                vesselMaskName = f"{wholeVesselMaskName}{childInx}"
                vesselMaskPath = f"{vesselMaskName}.nii.gz"
                vesselMaskFullPath = os.path.join(self.InputPath, vesselMaskPath)
                vesselBlenderName = f"{wholeVesselName}{childInx}"
                territoryName = f"{organName}_{vesselBlenderName}"

                if os.path.exists(vesselMaskFullPath) == False :
                    continue

                '''
                (paramInx, queryVertex, npImgWholeVessel, vesselMaskFullPath, territoryName, transFlag : bool, transMat)
                '''
                listParam.append((paramCnt, queryVertex, npImgWholeVessel, vesselMaskFullPath, territoryName, transFlag, transMat))
                paramCnt += 1

        if paramCnt == 0 :
            print("passed removed vessel stricture")
            return
        
        super().process(self._task, listParam)


    '''
    (paramInx, queryVertex, npImgWholeVessel, vesselMaskFullPath, territoryName, transFlag : bool, transMat)
    '''
    def _task(self, param : tuple) :
        inx = param[0]
        queryVertex = param[1]
        npImgWholeVessel = param[2]
        vesselMaskFullPath = param[3]
        territoryName = param[4]
        transFlag = param[4]
        transMat = param[5]

        npImg, origin, spacing, direction, size = algImage.CAlgImage.get_np_from_nifti(vesselMaskFullPath)
        retNpImg = np.where(npImg > 0, 0, npImgWholeVessel)
        wholeVesselVertex = algImage.CAlgImage.get_vertex_from_np(retNpImg, np.int32)
        vesselVertex = algImage.CAlgImage.get_vertex_from_np(npImg, np.int32)
        if transFlag == True :
            wholeVesselVertex = algLinearMath.CScoMath.mul_mat4_vec3(transMat, wholeVesselVertex)
            vesselVertex = algLinearMath.CScoMath.mul_mat4_vec3(transMat, vesselVertex)

        segmentProcess = algSegment.CSegmentBasedVoxelProcess()
        segmentProcess.add_anchor(wholeVesselVertex, 1)
        segmentProcess.add_anchor(vesselVertex, 2)
        segmentProcess.process(queryVertex)

        territoryVertex = segmentProcess.get_query_vertex_with_seg_index(2)
        territoryFullPath = os.path.join(self.OutputPath, f"{territoryName}.stl")

        reconType = self.m_organMaskInfo.ReconType
        reconParam = self.InputOptionInfo.find_recon_param(reconType)
        contour = reconParam.Contour
        algorithm = reconParam.Algorithm
        param = reconParam.Param
        gaussian = reconParam.Gaussian
        resampling = reconParam.ResamplingFactor
  
        inputNiftiFullPath = os.path.join(self.OutputPath, f"{territoryName}.nii.gz")
        npImg = algImage.CAlgImage.create_np(self.m_organPhaseInfo.Size, np.uint8)
        algImage.CAlgImage.set_clear(npImg, 0)
        algImage.CAlgImage.set_value(npImg, territoryVertex, 255)
        algImage.CAlgImage.save_nifti_from_np(inputNiftiFullPath, npImg, self.m_organPhaseInfo.Origin, self.m_organPhaseInfo.Spacing, self.m_organPhaseInfo.Direction, (2, 1, 0))
        print(f"saved territory nifti : {inputNiftiFullPath}")
        npImg = None

        territoryPolyData = reconstruction.CReconstruction.reconstruction_nifti(inputNiftiFullPath, self.m_organPhaseInfo.Origin, self.m_organPhaseInfo.Spacing, self.m_organPhaseInfo.Direction, self.m_organPhaseInfo.Offset, contour, param, algorithm, gaussian, resampling, True)
        algVTK.CVTK.save_poly_data_stl(territoryFullPath, territoryPolyData)

        npImg = None
        retNpImg = None
        wholeVesselVertex = None
        vesselVertex = None

        print(f"completed territory : {territoryFullPath}")


    def _find_mask_name(self, blenderName : str) -> str :
        maskInfo = self.InputOptionInfo.find_maskinfo_by_blender_name(blenderName)
        if maskInfo is None :
            return ""
        return maskInfo.Name
    def _find_mask_info(self, blenderName : str) -> optionInfo.CMaskInfo :
        maskInfo = self.InputOptionInfo.find_maskinfo_by_blender_name(blenderName)
        if maskInfo is None :
            return None
        return maskInfo


    @property
    def InputPath(self) -> str :
        return self.m_inputPath
    @InputPath.setter
    def InputPath(self, inputPath : str) :
        self.m_inputPath = inputPath
    @property
    def InputNiftiContainer(self) -> niftiContainer.CNiftiContainer :
        return self.m_inputNiftiContainer
    @InputNiftiContainer.setter
    def InputNiftiContainer(self, inputNiftiContainer : niftiContainer.CNiftiContainer) :
        self.m_inputNiftiContainer = inputNiftiContainer
    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, optionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = optionInfo
    @property
    def InputSegInx(self) -> int :
        return self.m_inputSegInx
    @InputSegInx.setter
    def InputSegInx(self, inputSegInx : int) :
        self.m_inputSegInx = inputSegInx
    @property
    def OutputPath(self) -> str :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath



if __name__ == '__main__' :
    pass


# print ("ok ..")

