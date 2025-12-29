import sys
import os
# import torch
# from torch.autograd import Variable
import numpy as np
# import math
# from scipy.ndimage import binary_erosion
import SimpleITK as sitk
import vtk
# from sklearn.decomposition import PCA


fileAbsPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(fileAbsPath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algVTK as algVTK
import AlgUtil.algImage as algImage
import AlgUtil.algGeometry as algGeometry

import algLinearMath as algLinearMath
import algOpen3D as algOpen3D
from radiomics import featureextractor
from radiomics import shape


class CAlgMetric :
    @staticmethod
    def find_pca_axis(vertex : np.ndarray) -> tuple :
        '''
        ret : (long, middle, short, halfSize, center)
        '''
        o3dOBB = algOpen3D.COpen3DMesh.create_obb(vertex)
        axis = algOpen3D.COpen3DMesh.obb_get_axis(o3dOBB)
        halfSize = algOpen3D.COpen3DMesh.obb_get_half_size(o3dOBB)
        center = algOpen3D.COpen3DMesh.obb_get_center(o3dOBB)

        axis = axis.T
        return (axis[0].reshape(-1, 3), axis[1].reshape(-1, 3), axis[2].reshape(-1, 3), halfSize, center)
    @staticmethod
    def get_centroid(vertex : np.ndarray) -> np.ndarray :
        return np.mean(vertex, axis=0).reshape(-1, 3)
    @staticmethod
    def get_diff_axis(self, targetV : np.ndarray, srcV : np.ndarray) -> float :
        totalV = srcV
        totalV = np.concatenate((totalV, -srcV), axis=0, dtype=np.float32)

        dot0 = algLinearMath.CScoMath.dot_vec3(targetV, totalV[0].reshape(-1, 3))
        dot1 = algLinearMath.CScoMath.dot_vec3(targetV, totalV[1].reshape(-1, 3))

        if dot0 > dot1 :
            return algLinearMath.CScoMath.rad_to_deg(np.arccos(dot0))
        else :
            return algLinearMath.CScoMath.rad_to_deg(np.arccos(dot1))
        

    def __init__(self) -> None:
        pass


class CAlgRadiomics :
    def __init__(self, niftiFullPath : str) -> None:
        # sitkImg = sitk.ReadImage(niftiFullPath)
        sitkMask = self._load_mask(niftiFullPath)

        # featureextractor.

        # self.m_extractor = featureextractor.RadiomicsFeatureExtractor()
        self.m_extractor = shape.RadiomicsShape(sitkMask, sitkMask)
        self.m_extractor.enableAllFeatures()
        result = self.m_extractor.execute()

        # self.m_extractor.disableAllFeatures()
        # self.m_extractor.enableFeaturesByName(shape=['SurfaceArea'])
        # result = self.m_extractor.execute(sitkMask, sitkMask)

        # for feature_name, value in result.items() :
        #     print(f"{feature_name}: {value}")
        # print("-" * 30)
    def clear(self) :
        self.m_extractor = None
    

    # 3d shape
    def get_voxel_volume(self) -> float :
        return self.m_extractor.getVoxelVolumeFeatureValue()
    def get_mesh_volume(self) -> float :
        return self.m_extractor.getMeshVolumeFeatureValue()
    def get_surface_area(self) -> float :
        return self.m_extractor.getSurfaceAreaFeatureValue()
    def get_surface_area_volume_ratio(self) -> float :
        return self.m_extractor.getSurfaceVolumeRatioFeatureValue()
    def get_sphericity(self) -> float :
        return self.m_extractor.getSphericityFeatureValue()
    def get_compactness_1(self) -> float :
        return self.m_extractor.getCompactness1FeatureValue()
    def get_compactness_2(self) -> float :
        return self.m_extractor.getCompactness2FeatureValue()
    def get_spherical_disproportion(self) -> float :
        return self.m_extractor.getSphericalDisproportionFeatureValue()
    def get_feret_diameter(self) -> float :
        return self.m_extractor.getMaximum3DDiameterFeatureValue()
    def get_axial_diameter(self) -> float :
        return self.m_extractor.getMaximum2DDiameterSliceFeatureValue()
    def get_coronal_diameter(self) -> float :
        return self.m_extractor.getMaximum2DDiameterColumnFeatureValue()
    def get_sagittal_diameter(self) -> float :
        return self.m_extractor.getMaximum2DDiameterRowFeatureValue()
    def get_major_axis_length(self) -> float :
        return self.m_extractor.getMajorAxisLengthFeatureValue()
    def get_minor_axis_length(self) -> float :
        return self.m_extractor.getMinorAxisLengthFeatureValue()
    def get_least_axis_length(self) -> float :
        return self.m_extractor.getLeastAxisLengthFeatureValue()
    def get_elongation(self) -> float :
        return self.m_extractor.getElongationFeatureValue()
    def get_flatness(self) -> float :
        return self.m_extractor.getFlatnessFeatureValue()
    

    # protected
    def _load_mask(self, maskFullPath : str) :
        mask = sitk.ReadImage(maskFullPath, sitk.sitkUInt8)
        npMask = sitk.GetArrayFromImage(mask)
        npMask[npMask > 1] = 1

        sitkMask = sitk.GetImageFromArray(npMask)
        sitkMask.CopyInformation(mask)

        return sitkMask
    


"""
ray distance metric
반드시 동일 phase의 nifti를 대상으로 한다.
"""
class CMetricRayDistNifti :
    @staticmethod
    def transform_ray(transMat : np.ndarray, rayOrigin : np.ndarray, rayDir : np.ndarray) :
        transOrigin = algLinearMath.CScoMath.mul_mat4_vec3(transMat, rayOrigin)
        transDir = algLinearMath.CScoMath.from_vec3_to_vec4(rayDir)
        transDir[0, 3] = 0
        transDir = algLinearMath.CScoMath.mul_mat4_vec4(transMat, transDir)
        transDir = algLinearMath.CScoMath.from_vec4_to_vec3(transDir)
        return (transOrigin, transDir)
        

    def __init__(
            self, 
            origin, spacing, direction, 
            reOrigin, reSpacing, reDirection,
            targetReVertex : np.ndarray, srcReVertex : np.ndarray
            ) -> None:
        self.m_origin = origin
        self.m_spacing = spacing
        self.m_direction = direction
        self.m_reOrigin = reOrigin
        self.m_reSpacing = reSpacing
        self.m_reDirection = reDirection
        self.m_targetReVertex = targetReVertex
        self.m_srcReVertex = srcReVertex

        self.m_listRayInfo = []
        self.m_listRayResult = []
    def clear(self) :
        self.m_origin = None
        self.m_spacing = None
        self.m_direction = None
        self.m_reOrigin = None
        self.m_reSpacing = None
        self.m_reDirection = None
        self.m_targetReVertex = None
        self.m_srcReVertex = None

        self.m_listRayInfo.clear()
        self.m_listRayResult.clear()
    def process(self) -> bool :
        self.m_phyReMat = algVTK.CVTK.get_phy_matrix(self.m_reOrigin, self.m_reSpacing, self.m_reDirection)
        self.m_invPhyMat = algVTK.CVTK.get_phy_matrix(self.m_origin, self.m_spacing, self.m_direction)
        self.m_invPhyMat = algLinearMath.CScoMath.inv_mat4(self.m_invPhyMat)

        self.override_make_ray()

        return True
    

    # override
    def override_make_ray(self) :
        pass


    # protected
    def _add_ray_info(
            self, 
            rayReOrigin : np.ndarray, rayReDir : np.ndarray,
            rayPhyOrigin : np.ndarray, rayPhyDir : np.ndarray,
            rayOrigin : np.ndarray, rayDir : np.ndarray
            ) :
        self.m_listRayInfo.append((rayReOrigin, rayReDir, rayPhyOrigin, rayPhyDir, rayOrigin, rayDir))
        self.m_listRayResult.append((None, None, None, None, None, None, None))
    

    @property
    def ListRayInfo(self) :
        return self.m_listRayInfo
    @property
    def ListIntersectedResult(self) :
        return self.m_listRayResult
class CMetricRayDistNiftiYAlign(CMetricRayDistNifti) :
    @staticmethod
    def intersect_align_y_ray_vertex(rayOrigin : np.ndarray, niftiVertex : np.ndarray) :
        x = rayOrigin[0, 0]
        z = rayOrigin[0, 2]
        con = (niftiVertex[:, 0] == x) & (niftiVertex[:, 2] == z)
        detectedVertex = niftiVertex[con]

        y = detectedVertex[:, 1]
        minYInx = np.argmin(y)
        maxYInx = np.argmax(y)

        minV = detectedVertex[minYInx].reshape(-1, 3)
        maxV = detectedVertex[maxYInx].reshape(-1, 3)

        return (minV, maxV)


    def __init__(
            self, 
            origin, spacing, direction, 
            reOrigin, reSpacing, reDirection,
            targetReVertex : np.ndarray, srcReVertex : np.ndarray
            ) -> None:
        super().__init__(origin, spacing, direction, reOrigin, reSpacing, reDirection, targetReVertex, srcReVertex)
    def clear(self) :
        super().clear()
    def process(self) -> bool :
        if super().process() == False :
            return
        # input your code
        for inx, rayInfo in enumerate(self.m_listRayInfo) :
            rayOrigin = rayInfo[0]
            srcMin, srcMax = self.intersect_align_y_ray_vertex(rayOrigin, self.m_srcReVertex)
            targetMin, targetMax = self.intersect_align_y_ray_vertex(rayOrigin, self.m_targetReVertex)
            tmpData = [None, None, None, None, None, None, None]
            tmpData[1] = srcMax
            tmpData[4] = targetMin

            srcMax = algLinearMath.CScoMath.mul_mat4_vec3(self.m_phyReMat, srcMax)
            targetMin = algLinearMath.CScoMath.mul_mat4_vec3(self.m_phyReMat, targetMin)
            dist = np.linalg.norm(srcMax - targetMin)
            tmpData[0] = dist
            tmpData[2] = srcMax
            tmpData[5] = targetMin

            srcMax = algLinearMath.CScoMath.mul_mat4_vec3(self.m_invPhyMat, srcMax)
            targetMin = algLinearMath.CScoMath.mul_mat4_vec3(self.m_invPhyMat, targetMin)
            tmpData[3] = srcMax
            tmpData[6] = targetMin
            self.m_listRayResult[inx] = tmpData
    
    # override
    def override_make_ray(self) :
        super().override_make_ray()
        # input your code
    
class CMetricRayDistNiftiSimple(CMetricRayDistNiftiYAlign) :
    def __init__(
            self, 
            origin, spacing, direction, 
            reOrigin, reSpacing, reDirection,
            targetReVertex : np.ndarray, srcReVertex : np.ndarray
            ) -> None:
        super().__init__(origin, spacing, direction, reOrigin, reSpacing, reDirection, targetReVertex, srcReVertex)
    def clear(self) :
        super().clear()
    def process(self) :
        if super().process() == False :
            return

    # override
    def override_make_ray(self) :
        # create ray
        tmpVertex = self.m_srcReVertex[self.m_srcReVertex[:,0] == 61]
        # tmpVertex = mesoVertex[mesoVertex[:,0] == 198]
        # print(tmpVertex)

        rayReOrigin = tmpVertex[0].reshape(-1, 3)
        rayReOrigin[0, 1] = 0
        rayReDir = algLinearMath.CScoMath.to_vec3([0, 1, 0]).astype(np.int32)

        rayPhyOrigin , rayPhyDir = self.transform_ray(self.m_phyReMat, rayReOrigin, rayReDir)
        rayOrigin, rayDir = self.transform_ray(self.m_invPhyMat, rayPhyOrigin, rayPhyDir)
        self._add_ray_info(rayReOrigin, rayReDir, rayPhyOrigin, rayPhyDir, rayOrigin, rayDir)



class CMetricRayDistStl :
    def __init__(self, targetOBBTree : vtk.vtkOBBTree, srcOBBTree : vtk.vtkOBBTree) -> None:
        self.m_listRayInfo = []
        self.m_listResult = []
        self.m_targetOBBTree = targetOBBTree
        self.m_srcOBBTree = srcOBBTree
    def clear(self) :
        self.m_listRayInfo.clear()
        self.m_listResult.clear()
        self.m_targetOBBTree = None
        self.m_srcOBBTree = None
    def process(self, rayRatio : int) :
        for rayInfo in self.m_listRayInfo :
            rayOrigin = rayInfo[0]
            rayDir = rayInfo[1]

            rayStart = rayOrigin
            rayEnd = rayOrigin + rayDir * rayRatio
            rayStart = [rayStart[0, 0], rayStart[0, 1], rayStart[0, 2]]
            rayEnd = [rayEnd[0, 0], rayEnd[0, 1], rayEnd[0, 2]]

            phyStart = None
            phyEnd = None

            intersectionPoints = vtk.vtkPoints()
            intersected = self.m_srcOBBTree.IntersectWithLine(rayStart, rayEnd, intersectionPoints, None)
            if intersected:
                intersectedCnt = intersectionPoints.GetNumberOfPoints()
                if intersectedCnt == 2 :
                    phyStart = np.array(intersectionPoints.GetPoint(1)).reshape(-1, 3)
                elif intersectedCnt == 1 :
                    phyStart = np.array(intersectionPoints.GetPoint(0)).reshape(-1, 3)
            else:
                print("not intersecting ray and src polyData")
            
            intersectionPoints = vtk.vtkPoints()
            intersected = self.m_targetOBBTree.IntersectWithLine(rayStart, rayEnd, intersectionPoints, None)
            if intersected:
                intersectedCnt = intersectionPoints.GetNumberOfPoints()
                phyEnd = np.array(intersectionPoints.GetPoint(0)).reshape(-1, 3)
            else:
                print("not intersecting ray and target polyData")
            self._add_result(phyStart, phyEnd)


    def add_ray_info(self, rayOrigin : np.ndarray, rayDir : np.ndarray) :
        self.m_listRayInfo.append((rayOrigin, rayDir))


    # protected
    def _add_result(self, startPt : np.ndarray, endPt : np.ndarray) :
        dist = np.linalg.norm(endPt - startPt)
        self.m_listResult.append((startPt, endPt, dist))

    
    @property
    def ListRayInfo(self) :
        return self.m_listRayInfo
    @property
    def ListResult(self) :
        return self.m_listResult