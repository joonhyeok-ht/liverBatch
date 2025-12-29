import matplotlib.pyplot as plt
import SimpleITK as sitk
import cv2
import numpy as np
import os
import open3d as o3d
import open3d.core
import open3d.visualization

import vtk
import struct


class CScoUtilSimpleITK :
    def __init__(self) :
        pass

    @staticmethod
    def npImg_windowing(npImg, minValue, maxValue) :
        return np.clip(npImg, minValue, maxValue)

    @staticmethod
    def load_dicom(path) :
        sitkReader = sitk.ImageSeriesReader()
        seriesIDs = sitkReader.GetGDCMSeriesIDs(path)
        seriesFileNames = sitkReader.GetGDCMSeriesFileNames(path, seriesIDs[0])
        sitkReader.SetFileNames(seriesFileNames)
        dicoms = sitkReader.Execute()

        return dicoms

    @staticmethod
    def load_image(path, type=None) :
        if type == None :
            sitkImg = sitk.ReadImage(path)
            return sitkImg
        else :
            sitkImg = sitk.ReadImage(path, type)
            return sitkImg

    @staticmethod
    def save_image(path, sitkImg, imgType) :
        writer = sitk.ImageFileWriter()
        writer.SetImageIO(imgType)
        writer.SetFileName(path)
        writer.Execute(sitkImg)
        sitk.WriteImage(sitkImg, path)

    @staticmethod
    def save_nifti(path, sitkImg) :
        CScoUtilSimpleITK.save_image(path, sitkImg, "NiftiImageIO")
    @staticmethod
    def save_jpg(path, sitkImg) :
        CScoUtilSimpleITK.save_image(path, sitkImg, "JPEGImageIO")
    @staticmethod
    def save_png(path, sitkImg) :
        CScoUtilSimpleITK.save_image(path, sitkImg, "PNGImageIO")

    @staticmethod
    def sitkImg_to_npImg(sitkImg, type) :
        # sitkImg   : sitkImg
        #             order (width, height, slice)
        # type      : pixel type ("float32", "uint8" ..)
        # ret       : numpy array (slice, height, width)

        arrImg = sitk.GetArrayViewFromImage(sitkImg).astype(type)

        return arrImg
    
    @staticmethod
    def sitkImg_to_npImg_deepcopy(sitkImg, type) :
        # sitkImg   : sitkImg
        #             order (width, height, slice)
        # type      : pixel type ("float32", "uint8" ..)
        # ret       : numpy array (slice, height, width)

        arrImg = sitk.GetArrayFromImage(sitkImg).astype(type)

        return arrImg

    @staticmethod
    def npImg_to_sitkImg(npImg) :
        sitkImg = sitk.GetImageFromArray(npImg)

        return sitkImg

    @staticmethod
    def npImg_nomalized_uint8(npImg) :
        # npImg : numpy array (slice, height, width)

        copyImg = npImg.copy().astype(np.float32)
        min = np.min(copyImg)
        max = np.max(copyImg)

        fRatio = max - min
        copyImg = (copyImg - min) / fRatio
        copyImg *= 255

        return copyImg.astype(np.uint8)
    @staticmethod
    def npImg_nomalized_float(npImg) :
        # npImg : numpy array (slice, height, width)

        copyImg = npImg.copy().astype(np.float32)
        min = np.min(copyImg)
        max = np.max(copyImg)

        fRatio = max - min
        copyImg = (copyImg - min) / fRatio

        return copyImg

    @staticmethod
    def get_min_max(sitkImg) :
        arrImg = sitk.GetArrayViewFromImage(sitkImg)
        min = np.min(arrImg)
        max = np.max(arrImg)

        return (min, max)
    @staticmethod
    def get_center_index(sitkImg) :
        center = np.array(sitkImg.GetSize()) // 2.0
        return [int(value) for value in center]
    @staticmethod
    def get_target_index_from_src_index(targetSitkImg, srcSitkImg, arrInx) :
        phyCoord = srcSitkImg.TransformIndexToPhysicalPoint(arrInx)
        retArrInx = targetSitkImg.TransformPhysicalPointToIndex(phyCoord)
        return [int(value) for value in retArrInx]
    @staticmethod    
    def get_physical_from_index(refSitkImg, inx) :
        return refSitkImg.TransformIndexToPhysicalPoint(inx)
    @staticmethod
    def get_nifti_cc(niftiPath : str, type : str) :
        sitkImg = CScoUtilSimpleITK.load_image(niftiPath, None)
        spacing = sitkImg.GetSpacing()

        npBuf = CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, type).transpose((2, 1, 0))
        xVoxel, yVoxel, zVoxel = np.where(npBuf > 0)
        voxelCnt = len(xVoxel)

        # volume 구하기 단위 cm3
        volume = spacing[0] * spacing[1] * spacing[2] * voxelCnt * 0.001
        return volume

    @staticmethod
    def print_sitk_img_info(sitkImg) : 
        print(f"size:{sitkImg.GetSize()}")
        print(f"origin:{sitkImg.GetOrigin()}")
        print(f"direction:{sitkImg.GetDirection()}")
        print(f"spacing:{sitkImg.GetSpacing()}")
        print("-"*30)
    @staticmethod
    def cv2_render_image(title, sitkImg) :
        if sitkImg.GetDimension() != 2 :
            print("dim != 2")
            return

        arrImg = sitk.GetArrayViewFromImage(sitkImg)
        arrImg = cv2.cvtColor(arrImg, cv2.COLOR_RGB2BGR)
        cv2.imshow(title, arrImg)

    # resampling
    @staticmethod
    def resamping_img(refSitkImg, inputSitkImg, transform, defaultValue) :
        resampleInst = sitk.ResampleImageFilter()
        resampleInst.SetReferenceImage(refSitkImg)
        resampleInst.SetInterpolator(sitk.sitkLinear)
        resampleInst.SetDefaultPixelValue(defaultValue)
        resampleInst.SetTransform(transform)
        return resampleInst.Execute(inputSitkImg)
    @staticmethod
    def resampling_img(targetImg, transform) :
        outSize = targetImg.GetSize()
        outSpacing = targetImg.GetSpacing()
        outDirection = targetImg.GetDirection()
        outOrigin = targetImg.GetOrigin()
        return sitk.Resample(targetImg, outSize, transform, sitk.sitkLinear, outOrigin, outSpacing, outDirection)

    # registration
    @staticmethod
    def command_iteration(method):
        print(
            f"{method.GetOptimizerIteration():3} "
            + f"= {method.GetMetricValue():10.5f} "
            + f": {method.GetOptimizerPosition()}"
        )
    @staticmethod
    def registration_translate_with_mse(sitkImgFixed, sitkImgMoving) :
        regInst = sitk.ImageRegistrationMethod()
        regInst.AddCommand(sitk.sitkIterationEvent, lambda: CScoUtilSimpleITK.command_iteration(regInst))
        regInst.SetMetricAsMeanSquares()
        # learningRate, minStep, iteratorCnt
        regInst.SetOptimizerAsRegularStepGradientDescent(4.0, 0.01, 200)
        #regInst.SetOptimizerAsRegularStepGradientDescent(8.0, 0.01, 200)
        regInst.SetInitialTransform(sitk.TranslationTransform(sitkImgFixed.GetDimension()))
        regInst.SetInterpolator(sitk.sitkLinear)

        #regInst.SetOptimizerScalesFromPhysicalShift()
        #regInst.SetOptimizerScalesFromIndexShift()
        #regInst.SetOptimizerScalesFromJacobian()

        return regInst.Execute(sitkImgFixed, sitkImgMoving)

    # rotation이 적용될 때에는 SetOptimizerScalesFromPhysicalShift 또는 SetOptimizerScalesFromJacobian를
    # 고려해봐야 한다.
    @staticmethod
    def registration_centered_euler2d_translate_with_mse(sitkImgFixed, sitkImgMoving, centerInx) :
        regInst = sitk.ImageRegistrationMethod()
        regInst.AddCommand(sitk.sitkIterationEvent, lambda: CScoUtilSimpleITK.command_iteration(regInst))
        regInst.SetMetricAsMeanSquares()
        # learningRate, minStep, iteratorCnt
        regInst.SetOptimizerAsRegularStepGradientDescent(4.0, 0.01, 200)

        transform = sitk.Euler2DTransform()
        #centerInx[0] -= 100
        #centerInx[1] -= 100
        transform.SetCenter(CScoUtilSimpleITK.get_physical_from_index(sitkImgMoving, centerInx))

        # 여기에서 center를 수정해봤자 먹히지 않음 따라서 
        #initTransform = sitk.CenteredTransformInitializer(
        #    sitkImgFixed,
        #    sitkImgMoving,
        #    transform,
        #    sitk.CenteredTransformInitializerFilter.GEOMETRY,
        #    )

        #regInst.SetInitialTransform(initTransform)
        regInst.SetInitialTransform(transform)
        regInst.SetInterpolator(sitk.sitkLinear)
        regInst.SetOptimizerScalesFromPhysicalShift()
        #regInst.SetOptimizerScalesFromJacobian()
        retTransform = regInst.Execute(sitkImgFixed, sitkImgMoving)

        print('Final metric value: {0}'.format(regInst.GetMetricValue()))
        print('Optimizer\'s stopping condition, {0}'.format(regInst.GetOptimizerStopConditionDescription()))

        return retTransform

    # sample 수가 모자르다면 registeration이 실패한다. 
    # 따라서 fSampleRatio를 증가시켜보면서 튜닝을 해봐야 된다. 
    @staticmethod
    def registration_translate_with_mutual(sitkImgFixed, sitkImgMoving, iBinCnt, fSampleRatio) :
        regInst = sitk.ImageRegistrationMethod()
        regInst.AddCommand(sitk.sitkIterationEvent, lambda: CScoUtilSimpleITK.command_iteration(regInst))

        regInst.SetMetricAsMattesMutualInformation(iBinCnt)
        regInst.SetMetricSamplingPercentage(fSampleRatio, sitk.sitkWallClock)
        regInst.SetMetricSamplingStrategy(regInst.RANDOM)
        regInst.SetOptimizerAsRegularStepGradientDescent(1.0, 0.01, 200)
        # 조건이 있는지는 모르겠는데 결과는 무척 안좋다.
        # 어쩌면 preprocessor 절차와 관련이 있는 것일 수도 있다. 
        #regInst.SetOptimizerAsGradientDescentLineSearch(
        #    learningRate=1.0,
        #    numberOfIterations=200,
        #    convergenceMinimumValue=1e-5,
        #    convergenceWindowSize=5
        #    )

        regInst.SetInitialTransform(sitk.TranslationTransform(sitkImgFixed.GetDimension()))
        regInst.SetInterpolator(sitk.sitkLinear)
        return regInst.Execute(sitkImgFixed, sitkImgMoving)

    
    @staticmethod
    def registration_centered_euler2d_translate_with_mutual(sitkImgFixed, sitkImgMoving, iBinCnt, fSampleRatio, centerInx) :
        regInst = sitk.ImageRegistrationMethod()
        regInst.AddCommand(sitk.sitkIterationEvent, lambda: CScoUtilSimpleITK.command_iteration(regInst))

        regInst.SetMetricAsMattesMutualInformation(iBinCnt)
        #regInst.SetMetricSamplingStrategy(regInst.NONE)
        regInst.SetMetricSamplingPercentage(fSampleRatio, sitk.sitkWallClock)
        regInst.SetMetricSamplingStrategy(regInst.RANDOM)
        regInst.SetOptimizerAsRegularStepGradientDescent(1.0, 0.001, 200)
        #regInst.SetOptimizerAsGradientDescent(learningRate=1.0, numberOfIterations=1000, convergenceMinimumValue=1e-6, convergenceWindowSize=20)
        #regInst.SetOptimizerAsGradientDescent(
        #    learningRate=1.0,
        #    numberOfIterations=1000,
        #    convergenceMinimumValue=1e-6,
        #    convergenceWindowSize=20,
        #    )

        transform = sitk.Euler2DTransform()
        #centerInx[0] -= 100
        #centerInx[1] -= 100
        transform.SetCenter(CScoUtilSimpleITK.get_physical_from_index(sitkImgMoving, centerInx))

        initTransform = sitk.CenteredTransformInitializer(
            sitkImgFixed,
            sitkImgMoving,
            sitk.Euler2DTransform(),
            sitk.CenteredTransformInitializerFilter.GEOMETRY,
            )
        regInst.SetInitialTransform(initTransform)
        #regInst.SetInitialTransform(transform, inPlace=False)
        regInst.SetInterpolator(sitk.sitkLinear)
        #regInst.SetOptimizerScalesFromPhysicalShift()
        #regInst.SetOptimizerScalesFromJacobian()

        #final_transform_v4 = sitk.CompositeTransform([regInst.Execute(sitkImgFixed, sitkImgMoving), transform])
        #return final_transform_v4
        retTransform = regInst.Execute(sitkImgFixed, sitkImgMoving)

        print('Final metric value: {0}'.format(regInst.GetMetricValue()))
        print('Optimizer\'s stopping condition, {0}'.format(regInst.GetOptimizerStopConditionDescription()))

        return retTransform

    # mutual 방식으로 미세 각도 조절등은 어려울 수 있다. 
    @staticmethod
    def registration_centered_euler2d_translate_with_mutual_normal(sitkImgFixed, sitkImgMoving, centerInx) :
        regInst = sitk.ImageRegistrationMethod()
        regInst.AddCommand(sitk.sitkIterationEvent, lambda: CScoUtilSimpleITK.command_iteration(regInst))

        fixed = sitk.Normalize(sitkImgFixed)
        fixed = sitk.DiscreteGaussian(sitkImgFixed, 2.0)
        moving = sitk.Normalize(sitkImgMoving)
        moving = sitk.DiscreteGaussian(sitkImgMoving, 2.0)

        regInst.SetMetricAsJointHistogramMutualInformation()
        regInst.SetOptimizerAsGradientDescentLineSearch(
            learningRate=1.0,
            numberOfIterations=200,
            convergenceMinimumValue=1e-5,
            convergenceWindowSize=5,
            )

        transform = sitk.Euler2DTransform()
        #centerInx[0] -= 100
        #centerInx[1] -= 100
        transform.SetCenter(CScoUtilSimpleITK.get_physical_from_index(sitkImgMoving, centerInx))

        initTransform = sitk.CenteredTransformInitializer(
            sitkImgFixed,
            sitkImgMoving,
            sitk.Euler2DTransform(),
            sitk.CenteredTransformInitializerFilter.GEOMETRY,
            )
        regInst.SetInitialTransform(initTransform)
        #regInst.SetInitialTransform(transform, inPlace=False)
        regInst.SetInterpolator(sitk.sitkLinear)
        regInst.SetOptimizerScalesFromPhysicalShift()
        #regInst.SetOptimizerScalesFromJacobian()

        retTransform = regInst.Execute(sitkImgFixed, sitkImgMoving)

        print('Final metric value: {0}'.format(regInst.GetMetricValue()))
        print('Optimizer\'s stopping condition, {0}'.format(regInst.GetOptimizerStopConditionDescription()))

        return retTransform

    @staticmethod
    def registration_landmark_with_affine(vecFixedLandMark, vecMovingLandMark, dim) :
        landMarkInst = sitk.LandmarkBasedTransformInitializerFilter()
        landMarkInst.SetFixedLandmarks(vecFixedLandMark)
        landMarkInst.SetMovingLandmarks(vecMovingLandMark)

        transform = sitk.AffineTransform(dim)
        retTransform = landMarkInst.Execute(transform)

        return retTransform
    @staticmethod
    def registration_landmark_with_trans_rot(vecFixedLandMark, vecMovingLandMark) :
        landMarkInst = sitk.LandmarkBasedTransformInitializerFilter()
        landMarkInst.SetFixedLandmarks(vecFixedLandMark)
        landMarkInst.SetMovingLandmarks(vecMovingLandMark)

        transform = sitk.VersorRigid3DTransform()
        retTransform = landMarkInst.Execute(transform)

        return retTransform
    @staticmethod
    def registration_landmark_with_translate(vecFixedLandMark, vecMovingLandMark) :
        landMarkInst = sitk.LandmarkBasedTransformInitializerFilter()
        landMarkInst.SetFixedLandmarks(vecFixedLandMark)
        landMarkInst.SetMovingLandmarks(vecMovingLandMark)

        transform = sitk.Similarity3DTransform()
        retTransform = landMarkInst.Execute(transform)

        return retTransform


    @staticmethod
    def create_pcd_from_numpy(npImg, color) :
        """
        npImg : numpy array in the ordering (slice, y, x)
        color : point cloud color (r, g, b)
        """

        coord = np.array(np.where(npImg > 0)).T

        coordTrans = coord.copy()
        # order : slice, y, x -> x, y, slice
        coordTrans[:,0] = coord[:,2]
        coordTrans[:,2] = coord[:,0]

        coordColor = coord.copy()
        # order : r, g, b  range : 0.0 ~ 1.0
        coordColor[:,0] = color[0]
        coordColor[:,1] = color[1]
        coordColor[:,2] = color[2]

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(coordTrans)
        pcd.colors = o3d.utility.Vector3dVector(coordColor)

        return pcd

    @staticmethod
    def create_pcd_from_nifti(niftiPath, color) :
        """
        niftiPath : nifti full path that is binary mask type
        color : point cloud color (r, g, b)
        """

        sitkImg = CScoUtilSimpleITK.load_image(niftiPath, None)
        npImg = CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, "uint8")
        npImg[npImg > 0] = 255

        pcd = CScoUtilSimpleITK.create_pcd_from_numpy(npImg, color)

        return pcd
    
    @staticmethod
    def create_pcd_aabb(min : tuple, max : tuple, color : tuple) :
        # normalized organ aabb
        arr = np.array(
            [
                min,
                max
            ]
        )
        pcd = o3d.geometry.AxisAlignedBoundingBox.create_from_points(open3d.utility.Vector3dVector(arr))
        pcd.color = color

        return pcd
    
    @staticmethod
    def get_pcd_from_list(listCoord : list, color) :
        """
        listCoord : coordination list in ordering (slice, y, x)
        color : point cloud color (r, g, b)
        """

        coord = np.array(listCoord)
        coordTrans = coord.copy()
        # order : slice, y, x -> x, y, slice
        coordTrans[:,0] = coord[:,2]
        coordTrans[:,2] = coord[:,0]

        coordColor = coord.copy()
        # order : r, g, b  range : 0.0 ~ 1.0
        coordColor[:,0] = color[0]
        coordColor[:,1] = color[1]
        coordColor[:,2] = color[2]

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(coordTrans)
        pcd.colors = o3d.utility.Vector3dVector(coordColor)

        return pcd
    @staticmethod
    def get_pcd_sphere_from_list(listCoord : list, radius, color):
        """
        listCoord : coordination list in ordering (slice, y, x)
        radius : sphere radius
        color : point cloud color (r, g, b)
        """

        pcd = CScoUtilSimpleITK.get_pcd_from_list(listCoord, color)
        geometries = o3d.geometry.TriangleMesh()

        for point in pcd.points:
            sphere = o3d.geometry.TriangleMesh.create_sphere(radius=radius) #create a small sphere to represent point
            sphere.translate(point)
            geometries += sphere

        geometries.paint_uniform_color(color)

        return geometries
    @staticmethod
    def create_pcd_origin(scale : float) :
        """
        scale : origin axis scale
        """

        pcd = o3d.geometry.TriangleMesh.create_coordinate_frame()
        pcd.scale(scale, center=(0, 0, 0))
        
        #mesh.translate((1, 0, 0))
        #mesh.scale(0.5, center=(0, 0, 0))
        
        return pcd
    @staticmethod
    def get_aabb_from_point_cloud(pcd, color) :
        """
        pcd : o3d point cloud type
        color : axis aligned bounding box color in order (r, g, b)
        """

        aabb = pcd.get_axis_aligned_bounding_box()
        aabb.color = color

        return aabb



class CScoUtilOS :
    def __init__(self) :
        pass

    @staticmethod
    def create_directory(dirPath) :
        try :
            if not os.path.exists(dirPath) :
                os.makedirs(dirPath)
        except OSError :
            print("failed to create directory")

    @staticmethod
    def get_abs_path() :
        return os.path.abspath(".")
    @staticmethod
    def get_file_name_except_ext(fullPath : str) :
        dir, ext = os.path.splitext(fullPath)
        dir = dir.replace('\\', '/')
        fileName = dir.split('/')[-1]
        return fileName
    @staticmethod
    def get_file_name(fullPath : str) :
        fullPath = fullPath.replace('\\', '/')
        fileName = fullPath.split('/')[-1]
        return fileName
    @staticmethod
    def get_ext(fullPath : str) :
        dir, ext = os.path.splitext(fullPath)
        return ext
    
    @staticmethod
    def get_patient_reference_path(patientFullPath) :
        listDir = os.listdir(patientFullPath)
        if len(listDir) < 1 :
            print("not found time path")
            return ("", "", "")
        
        patientTimePath = ""
        for dir in listDir :
            if dir != ".DS_Store" :
                patientTimePath = dir
                break
        if patientTimePath == "" :
            print("not found time path")
            return ("", "", "")

        patientTimeFullPath = os.path.join(patientFullPath, patientTimePath) 
        listDir = os.listdir(patientTimeFullPath)
        if len(listDir) < 2 :
            print("not found EAP, PP path")
            return ("", "", "")
        listDir.sort()

        patientEAPPath = listDir[-2]
        patientPPPath = listDir[-1]
        patientEAPPath = os.path.join(patientEAPPath, "stor/objects")
        patientPPPath = os.path.join(patientPPPath, "stor/objects")

        return (patientTimePath, patientEAPPath, patientPPPath)
    def get_patient_path(patientFullPath) :
        listDir = os.listdir(patientFullPath)
        if len(listDir) < 1 :
            print("not found time path")
            return ("", "", "")
        
        patientTimePath = ""
        for dir in listDir :
            if dir != ".DS_Store" :
                patientTimePath = dir
                break
        if patientTimePath == "" :
            print("not found time path")
            return ("", "", "")

        patientTimeFullPath = os.path.join(patientFullPath, patientTimePath) 
        listDir = os.listdir(patientTimeFullPath)
        if len(listDir) < 2 :
            print("not found EAP, PP path")
            return ("", "", "")
        listDir.sort()

        patientEAPPath = listDir[-2]
        patientPPPath = listDir[-1]

        return (patientTimePath, patientEAPPath, patientPPPath)



from scipy.spatial.transform import Rotation as R
import math

class CScoMath :
    def __init__(self) :
        pass

    @staticmethod
    def make_vec4(x, y, z, w) :
        npVec = np.array([x, y, z, w])
        return npVec.reshape(1, 4)
    @staticmethod
    def make_vec3(x, y, z) :
        npVec = np.array([x, y, z])
        return npVec.reshape(1, 3)
    @staticmethod
    def vec_add(v0 : np.ndarray, v1 : np.ndarray) :
        return v0 + v1
    @staticmethod
    def vec_sub(v0 : np.ndarray, v1 : np.ndarray) :
        return v0 - v1
    @staticmethod
    def vec_length(v : np.ndarray) :
        return np.linalg.norm(v)
    @staticmethod
    def vec_dot(v0 : np.ndarray, v1 : np.ndarray) :
        return np.dot(v0, v1)
    @staticmethod
    def vec_cross(v0 : np.ndarray, v1 : np.ndarray) :
        return np.cross(v0, v1)
    
    @staticmethod
    def make_mat4x4_identity() :
        npMat = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        return npMat
    @staticmethod
    def make_mat4x4_inverse(npMat : np.ndarray) :
        return np.linalg.inv(npMat)
    @staticmethod
    def make_mat4x4_translate_3d(x, y, z) :
        npMat = np.array([
            [1.0, 0.0, 0.0, x],
            [0.0, 1.0, 0.0, y],
            [0.0, 0.0, 1.0, z],
            [0.0, 0.0, 0.0, 1.0],
        ])
        return npMat
    @staticmethod
    def make_mat4x4_scale(x, y, z) :
        npMat = np.array([
            [x, 0.0, 0.0, 0.0],
            [0.0, y, 0.0, 0.0],
            [0.0, 0.0, z, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        return npMat
    @staticmethod
    def make_mat4x4_rot_from_row(listRot : tuple) :
        npMat = np.array([
            [listRot[0], listRot[1], listRot[2], 0.0],
            [listRot[3], listRot[4], listRot[5], 0.0],
            [listRot[6], listRot[7], listRot[8], 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])
        return npMat
    @staticmethod
    def make_mat4x4_rot_from_column(listRot : tuple) :
        npMat = np.array([
            [listRot[0], listRot[3], listRot[6], 0.0],
            [listRot[1], listRot[4], listRot[7], 0.0],
            [listRot[2], listRot[5], listRot[8], 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])
        return npMat
    @staticmethod
    def make_mat4x4_rot_from_axis(xAxis, yAxis, zAxis) :
        npMat = np.array([
            [xAxis[0], yAxis[0], zAxis[0], 0.0],
            [xAxis[1], yAxis[1], zAxis[1], 0.0],
            [xAxis[2], yAxis[2], zAxis[2], 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ])
        return npMat
    @staticmethod
    def make_mat4x4_rot_from_axis_radian(axis : np.ndarray, radian : float) :
        theta = radian / 2.0
        qAxis = axis * np.sin(theta)
        r = R.from_quat([qAxis[0], qAxis[1], qAxis[2], np.cos(theta)])
        npMat = r.as_matrix()
        npMat = np.hstack([npMat, np.array([0.0, 0.0, 0.0]).reshape(3, 1)])
        npMat = np.vstack([npMat, np.array([0.0, 0.0, 0.0, 1.0])])
        return npMat
    @staticmethod
    def make_mat4x4_rot_from_quaternion(quaternion : np.ndarray) :
        r = R.from_quat([quaternion[0], quaternion[1], quaternion[2], quaternion[3]])
        npMat = r.as_matrix()
        npMat = np.hstack([npMat, np.array([0.0, 0.0, 0.0]).reshape(3, 1)])
        npMat = np.vstack([npMat, np.array([0.0, 0.0, 0.0, 1.0])])
        return npMat
    @staticmethod
    def make_quaternion_from_mat3x3(npMat : np.ndarray) :
        r = R.from_matrix(npMat)
        return r.as_quat()
    
    @staticmethod
    def mul_mat4x4(npMat1 : np.ndarray, npMat2 : np.ndarray) :
        return np.dot(npMat1, npMat2)
    @staticmethod
    def mul_mat4x4_vec3(npMat : np.ndarray, npVec3 : np.ndarray) :
        if npVec3.ndim == 1 :
            n = npVec3.shape[0]
            npVec3 = npVec3.reshape(n, 1)
        
        npVec3 = npVec3.reshape(3, 1)
        npVec4 = np.vstack([npVec3, np.array([1.0])])
        return np.dot(npMat, npVec4).reshape(1, 4)
    @staticmethod
    def mul_mat4x4_vec4(npMat : np.ndarray, npVec4 : np.ndarray) :
        if npVec4.ndim == 1 :
            n = npVec4.shape[0]
            npVec4 = npVec4.reshape(n, 1)
        
        npVec4 = npVec4.reshape(4, 1)
        
        return np.dot(npMat, npVec4).reshape(1, 4)

    @staticmethod
    def convert_mat4x4_from_sitk_versor_rigid3d_transform(transform : sitk.Transform) :
        tr = sitk.VersorRigid3DTransform(transform)

        center = tr.GetCenter()
        translation = tr.GetTranslation()
        rot = tr.GetMatrix()

        npMatCenter = CScoMath.make_mat4x4_translate_3d(center[0], center[1], center[2])
        npMatInvCenter = CScoMath.make_mat4x4_inverse(npMatCenter)
        npMatTrans = CScoMath.make_mat4x4_translate_3d(translation[0], translation[1], translation[2])
        npMatRot = CScoMath.make_mat4x4_rot_from_row(rot)

        # npMatTrans * npMatCenter * npMatRot * npMatInvCenter
        retNpMat = CScoMath.mul_mat4x4(npMatTrans, npMatCenter)
        retNpMat = CScoMath.mul_mat4x4(retNpMat, npMatRot)
        retNpMat = CScoMath.mul_mat4x4(retNpMat, npMatInvCenter)

        return retNpMat
    @staticmethod
    def convert_mat4x4_from_sitk_translate_transform(transform : sitk.Transform) :
        tr = sitk.Similarity3DTransform(transform)

        center = tr.GetCenter()
        scale = tr.GetScale()
        translation = tr.GetTranslation()
        rot = tr.GetMatrix()

        npMatCenter = CScoMath.make_mat4x4_translate_3d(center[0], center[1], center[2])
        npMatInvCenter = CScoMath.make_mat4x4_inverse(npMatCenter)
        npMatTrans = CScoMath.make_mat4x4_translate_3d(translation[0], translation[1], translation[2])
        npMatRot = CScoMath.make_mat4x4_rot_from_row(rot)
        npMatScale = CScoMath.make_mat4x4_scale(scale, scale, scale)
        
        # npMatTrans * npMatCenter * npMatRot npMatScale * npMatInvCenter
        retNpMat = CScoMath.mul_mat4x4(npMatTrans, npMatCenter)
        retNpMat = CScoMath.mul_mat4x4(retNpMat, npMatRot)
        retNpMat = CScoMath.mul_mat4x4(retNpMat, npMatScale)
        retNpMat = CScoMath.mul_mat4x4(retNpMat, npMatInvCenter)

        return npMatTrans
    @staticmethod
    def convert_mat4x4_from_sitk_affine_transform(transform : sitk.Transform) :
        tr = sitk.AffineTransform(transform)

        center = tr.GetCenter()
        translation = tr.GetTranslation()
        rot = tr.GetMatrix()

        npMatCenter = CScoMath.make_mat4x4_translate_3d(center[0], center[1], center[2])
        npMatInvCenter = CScoMath.make_mat4x4_inverse(npMatCenter)
        npMatTrans = CScoMath.make_mat4x4_translate_3d(translation[0], translation[1], translation[2])
        npMatRot = CScoMath.make_mat4x4_rot_from_row(rot)

        # npMatTrans * npMatCenter * npMatRot * npMatInvCenter
        retNpMat = CScoMath.mul_mat4x4(npMatTrans, npMatCenter)
        retNpMat = CScoMath.mul_mat4x4(retNpMat, npMatRot)
        retNpMat = CScoMath.mul_mat4x4(retNpMat, npMatInvCenter)

        return retNpMat


class STLUtils:
    def __init__(self) -> None :
        self.material = 0 

        try :
            self.material = int(self.material)
            if self.material < 1 or self.material > 18 :
                self.material = 1
        except ValueError:
            self.material = 1
        self.materials = {
            1: {'name': 'ABS', 'mass': 1.04},
            2: {'name': 'PLA', 'mass': 1.25},
            3: {'name': '3k CFRP', 'mass': 1.79},
            4: {'name': 'Plexiglass', 'mass': 1.18},
            5: {'name': 'Alumide', 'mass': 1.36},
            6: {'name': 'Aluminum', 'mass': 2.68},
            7: {'name': 'Brass', 'mass': 8.6},
            8: {'name': 'Bronze', 'mass': 9.0},
            9: {'name': 'Copper', 'mass': 9.0},
            10: {'name': 'Gold_14K', 'mass': 13.6},
            11: {'name': 'Gold_18K', 'mass': 15.6},
            12: {'name': 'Polyamide_MJF', 'mass': 1.01},
            13: {'name': 'Polyamide_SLS', 'mass': 0.95},
            14: {'name': 'Rubber', 'mass': 1.2},
            15: {'name': 'Silver', 'mass': 10.26},
            16: {'name': 'Steel', 'mass': 7.86},
            17: {'name': 'Titanium', 'mass': 4.41},
            18: {'name': 'Resin', 'mass': 1.2}
        }
    def resetVariables(self):
        self.normals = []
        self.points = []
        self.triangles = []
        self.bytecount = []
        self.fb = []  # debug list

    def signedVolumeOfTriangle(self, p1, p2, p3):
        v321 = p3[0] * p2[1] * p1[2]
        v231 = p2[0] * p3[1] * p1[2]
        v312 = p3[0] * p1[1] * p2[2]
        v132 = p1[0] * p3[1] * p2[2]
        v213 = p2[0] * p1[1] * p3[2]
        v123 = p1[0] * p2[1] * p3[2]
        return (1.0 / 6.0) * (-v321 + v231 + v312 - v132 - v213 + v123)
    
    def unpack(self, sig, l):
        s = self.f.read(l)
        self.fb.append(s)
        return struct.unpack(sig, s)
    
    def read_triangle(self):
        n = self.unpack("<3f", 12)
        p1 = self.unpack("<3f", 12)
        p2 = self.unpack("<3f", 12)
        p3 = self.unpack("<3f", 12)
        b = self.unpack("<h", 2)

        self.normals.append(n)
        l = len(self.points)
        self.points.append(p1)
        self.points.append(p2)
        self.points.append(p3)
        self.triangles.append((l, l + 1, l + 2))
        self.bytecount.append(b[0])
        return self.signedVolumeOfTriangle(p1, p2, p3)
    def read_length(self):
        length = struct.unpack("@i", self.f.read(4))
        return length[0]
    def read_header(self):
        self.f.seek(self.f.tell() + 80)
    def cm3_To_inch3Transform(self, v):
        return v * 0.0610237441
    def calculateMassCM3(self, totalVolume):
        if self.material in self.materials:
            material_mass = self.materials[self.material]['mass']
            return totalVolume * material_mass
        return 0
    def calculateVolume(self, infilename, unit):
        print(infilename)
        self.resetVariables()
        totalVolume = 0
        totalMass = 0
        try:
            self.f = open(infilename, "rb")
            self.read_header()
            l = self.read_length()
            print("Total triangles:", l)
            try:
                while True:
                    totalVolume += self.read_triangle()
            except Exception as e:
                #print("End calculate triangles volume")
                #print("")
                True
            totalVolume = totalVolume / 1000
            totalMass = self.calculateMassCM3(totalVolume)
            if totalMass <= 0:
                print('Total mass could not be calculated')
            else:
                #print('Total mass:', totalMass, 'g') # by JK
                if unit == "mm":
                    #print("Total volume:", totalVolume, "mm^3")
                    print("Total volume: {:.5f} mm^3".format(totalVolume))
                else:
                    totalVolume = self.cm3_To_inch3Transform(totalVolume)
                    print("Total volume:", totalVolume, "inch^3")
        except Exception as e:
            print(e)
        
        print("")
        return totalVolume


class CScoUtilVTK :
    s_contourS = int(0)
    s_contourE = int(0)
    s_stddev = float(0.0)
    s_noi = int(0)          # numberofiteration
    s_refa = float(0.0)     # relaxationfactor
    s_deci = float(0.0)     # targetreduce
    

    def __init__(self) -> None:
        pass


    @staticmethod
    def recon_with_param(inputFilePath : str, outputFilePath : str, bGauss : bool, resamplingFactor = 1) :
        CScoUtilVTK._process_recon(
            inputFilePath, outputFilePath,
            CScoUtilVTK.s_stddev, CScoUtilVTK.s_contourS, CScoUtilVTK.s_contourE,
            CScoUtilVTK.s_noi, CScoUtilVTK.s_refa, CScoUtilVTK.s_deci,
            bGauss, resamplingFactor
        )
    @staticmethod
    def recon_with_param_phy(inputFilePath : str, outputFilePath : str, bGauss : bool, npMatPhy = None, resamplingFactor = 1) :
        CScoUtilVTK._process_recon_with_phy(
            inputFilePath, outputFilePath,
            CScoUtilVTK.s_stddev, CScoUtilVTK.s_contourS, CScoUtilVTK.s_contourE,
            CScoUtilVTK.s_noi, CScoUtilVTK.s_refa, CScoUtilVTK.s_deci,
            bGauss, npMatPhy, resamplingFactor
        )
    @staticmethod
    def recon_flying_with_param(inputFilePath : str, outputFilePath : str, bGauss : bool, resamplingFactor = 1) :
        CScoUtilVTK._process_recon_flying(
            inputFilePath, outputFilePath,
            CScoUtilVTK.s_stddev, CScoUtilVTK.s_contourS, CScoUtilVTK.s_contourE,
            CScoUtilVTK.s_noi, CScoUtilVTK.s_refa, CScoUtilVTK.s_deci,
            bGauss, resamplingFactor
        )
    @staticmethod
    def recon_flying_with_param_phy(inputFilePath : str, outputFilePath : str, bGauss : bool, npMatPhy = None, resamplingFactor = 1) :
        CScoUtilVTK._process_recon_flying_with_phy(
            inputFilePath, outputFilePath,
            CScoUtilVTK.s_stddev, CScoUtilVTK.s_contourS, CScoUtilVTK.s_contourE,
            CScoUtilVTK.s_noi, CScoUtilVTK.s_refa, CScoUtilVTK.s_deci,
            bGauss, npMatPhy, resamplingFactor
        )
    
    @staticmethod
    def recon_set_param_contour(contourS : int, contourE : int) :
        CScoUtilVTK.s_contourS = contourS
        CScoUtilVTK.s_contourE = contourE
    @staticmethod
    def recon_set_param_gaussian_stddev(stddev : float) :
        CScoUtilVTK.s_stddev = stddev
    @staticmethod
    def recon_set_param_polygon_smoothing(iterCnt : int, relaxationFactor : float, decimation : float) :
        CScoUtilVTK.s_noi = iterCnt
        CScoUtilVTK.s_refa = relaxationFactor
        CScoUtilVTK.s_deci = decimation
    
    @staticmethod
    def get_stl_volume(stlPath : str, unit : str) :
        """
        unit : "inch" or "mm"
        """
        stlUtil = STLUtils()
        return stlUtil.calculateVolume(stlPath, unit)
        


    # protected
    @staticmethod
    def _process_recon( 
                      inputFilePath : str, outputFilePath : str, 
                      stddev : float, contourS : int, contourE : int, 
                      noi : int, refa : float, deci : float,
                      bGauss = True, resamplingFactor = 1
                      ) :
        reader = vtk.vtkNIFTIImageReader()
        reader.SetFileName(inputFilePath)
        reader.Update()

        inputData = reader
        if resamplingFactor > 1 :
            resampler = vtk.vtkImageResample()
            resampler.SetInputData(reader.GetOutput())
            resampler.SetMagnificationFactors([resamplingFactor,resamplingFactor,resamplingFactor])
            resampler.Update()
            reader.GetOutput().ReleaseData()
            inputData = resampler

        dims = reader.GetOutput().GetDimensions()
        spacing = reader.GetOutput().GetSpacing()
        origin = reader.GetOutput().GetOrigin()
        direction = reader.GetOutput().GetDirectionMatrix()
        physical = reader.GetOutput().GetIndexToPhysicalMatrix()

        flip1 = vtk.vtkImageFlip()
        flip1.SetInputData(inputData.GetOutput())
        flip1.SetFilteredAxis(2)
        flip1.Update()
        inputData.GetOutput().ReleaseData()

        flip2 = vtk.vtkImageFlip()
        flip2.SetInputData(flip1.GetOutput())
        flip2.SetFilteredAxis(1)
        flip2.Update()
        flip1.GetOutput().ReleaseData()

        surf = None
        if bGauss == True :
            surf = CScoUtilVTK._process_marching_cube_with_gaussian(flip2, stddev, contourS, contourE)
        else :
            surf = CScoUtilVTK._process_marching_cube(flip2, contourS, contourE)

        decima = vtk.vtkQuadricDecimation()
        decima.SetInputData(surf.GetOutput())
        decima.SetTargetReduction(deci)             #decimaprop
        decima.Update()
        surf.GetOutput().ReleaseData()

        smoother = vtk.vtkSmoothPolyDataFilter()
        smoother.SetInputData(decima.GetOutput())
        smoother.SetNumberOfIterations(noi)         #3dsmoothprop
        smoother.SetRelaxationFactor(refa)          #3dsmoothprop
        smoother.FeatureEdgeSmoothingOff()
        smoother.BoundarySmoothingOn()
        smoother.Update()
        decima.GetOutput().ReleaseData()

        #center aligment\n",
        transForm = vtk.vtkTransform()
        transForm.Translate(-dims[0] * spacing[0]/2.0, -dims[1] * spacing[1]/2.0, -dims[2] * spacing[2]/2.0)
        transFilter=vtk.vtkTransformFilter()
        transFilter.SetInputData(smoother.GetOutput())
        transFilter.SetTransform(transForm)
        transFilter.Update()
        smoother.GetOutput().ReleaseData()

        writer = vtk.vtkSTLWriter()
        writer.SetInputData(transFilter.GetOutput())
        writer.SetFileTypeToBinary()
        writer.SetFileName(f'{outputFilePath}')
        writer.Write()
        transFilter.GetOutput().ReleaseData()
        writer = None
    @staticmethod
    def _process_recon_with_phy( 
                      inputFilePath : str, outputFilePath : str, 
                      stddev : float, contourS : int, contourE : int, 
                      noi : int, refa : float, deci : float,
                      bGaussMarching = True, npMatPhy = None, resamplingFactor = 1
                      ) :
        reader = vtk.vtkNIFTIImageReader()
        reader.SetFileName(inputFilePath)
        reader.Update()

        inputData = reader
        if resamplingFactor > 1 :
            resampler = vtk.vtkImageResample()
            resampler.SetInputData(reader.GetOutput())
            resampler.SetMagnificationFactors([resamplingFactor,resamplingFactor,resamplingFactor])
            resampler.Update()
            reader.GetOutput().ReleaseData()
            inputData = resampler

        dims = reader.GetOutput().GetDimensions()
        spacing = reader.GetOutput().GetSpacing()
        origin = reader.GetOutput().GetOrigin()
        direction = reader.GetOutput().GetDirectionMatrix()
        physical = reader.GetOutput().GetIndexToPhysicalMatrix()

        # print(f"vtk dims : {dims}")
        # print(f"vtk spacing : {spacing}")

        surf = None
        if bGaussMarching == True :
            gaussian = vtk.vtkImageGaussianSmooth()
            gaussian.SetInputData(inputData.GetOutput())
            gaussian.SetStandardDeviation(stddev)       #2dsmoothprop
            gaussian.Update()
            inputData.GetOutput().ReleaseData()

            surf = vtk.vtkImageMarchingCubes()
            surf.SetInputData(gaussian.GetOutput())
            surf.SetValue(contourS, contourE)           #contourprop
            surf.ComputeNormalsOn()
            surf.Update()
            gaussian.GetOutput().ReleaseData()
        else :
            surf = vtk.vtkImageMarchingCubes()
            surf.SetInputData(inputData.GetOutput())
            surf.SetValue(contourS, contourE)           #contourprop
            surf.ComputeNormalsOn()
            surf.Update()
            inputData.GetOutput().ReleaseData()

        decima = vtk.vtkQuadricDecimation()
        decima.SetInputData(surf.GetOutput())
        decima.SetTargetReduction(deci)             #decimaprop
        decima.Update()
        surf.GetOutput().ReleaseData()

        smoother = vtk.vtkSmoothPolyDataFilter()
        smoother.SetInputData(decima.GetOutput())
        smoother.SetNumberOfIterations(noi)         #3dsmoothprop
        smoother.SetRelaxationFactor(refa)          #3dsmoothprop
        smoother.FeatureEdgeSmoothingOff()
        smoother.BoundarySmoothingOn()
        smoother.Update()
        decima.GetOutput().ReleaseData()

        # transform physical coordinate
        transForm = vtk.vtkTransform()
        if npMatPhy is None :
            transForm.SetMatrix(
                [
                    1, 0, 0, 0,
                    0, 1, 0, 0,
                    0, 0, 1, 0,
                    0, 0, 0, 1
                ]
            )
        else :
            transForm.SetMatrix(
                [
                    npMatPhy[0, 0], npMatPhy[0, 1], npMatPhy[0, 2], npMatPhy[0, 3],
                    npMatPhy[1, 0], npMatPhy[1, 1], npMatPhy[1, 2], npMatPhy[1, 3],
                    npMatPhy[2, 0], npMatPhy[2, 1], npMatPhy[2, 2], npMatPhy[2, 3],
                    npMatPhy[3, 0], npMatPhy[3, 1], npMatPhy[3, 2], npMatPhy[3, 3]
                ]
            )
        transFilter=vtk.vtkTransformFilter()
        transFilter.SetInputData(smoother.GetOutput())
        transFilter.SetTransform(transForm)
        transFilter.Update()
        smoother.GetOutput().ReleaseData()

        writer = vtk.vtkSTLWriter()
        writer.SetInputData(transFilter.GetOutput())
        writer.SetFileTypeToBinary()
        writer.SetFileName(f'{outputFilePath}')
        writer.Write()
        transFilter.GetOutput().ReleaseData()
        writer = None
    @staticmethod
    def _process_recon_flying( 
                      inputFilePath : str, outputFilePath : str, 
                      stddev : float, contourS : int, contourE : int, 
                      noi : int, refa : float, deci : float,
                      bGauss = True, resamplingFactor = 1
                      ) :
        reader = vtk.vtkNIFTIImageReader()
        reader.SetFileName(inputFilePath)
        reader.Update()

        inputData = reader
        if resamplingFactor > 1 :
            resampler = vtk.vtkImageResample()
            resampler.SetInputData(reader.GetOutput())
            resampler.SetMagnificationFactors([resamplingFactor,resamplingFactor,resamplingFactor])
            resampler.Update()
            reader.GetOutput().ReleaseData()
            inputData = resampler

        dims = reader.GetOutput().GetDimensions()
        spacing = reader.GetOutput().GetSpacing()
        origin = reader.GetOutput().GetOrigin()
        direction = reader.GetOutput().GetDirectionMatrix()
        physical = reader.GetOutput().GetIndexToPhysicalMatrix()

        # print(f"dims : {dims}")
        # print(f"spacing : {spacing}")
        # print(f"origin : {origin}")
        # print(f"direction : {direction}")
        # print(f"physical : {physical}")

        flip1 = vtk.vtkImageFlip()
        flip1.SetInputData(inputData.GetOutput())
        flip1.SetFilteredAxis(2)
        flip1.Update()
        inputData.GetOutput().ReleaseData()

        flip2 = vtk.vtkImageFlip()
        flip2.SetInputData(flip1.GetOutput())
        flip2.SetFilteredAxis(1)
        flip2.Update()
        flip1.GetOutput().ReleaseData()

        surf = None
        if bGauss == True :
            gaussian = vtk.vtkImageGaussianSmooth()
            gaussian.SetInputData(flip2.GetOutput())
            gaussian.SetStandardDeviation(stddev)       #2dsmoothprop
            gaussian.Update()
            flip2.GetOutput().ReleaseData()

            surf = vtk.vtkFlyingEdges3D()
            surf.SetInputData(gaussian.GetOutput())
            surf.ComputeNormalsOn()
            surf.ComputeGradientsOn()
            surf.InterpolateAttributesOn()
            surf.SetValue(contourS, contourE)
            surf.Update()
            gaussian.GetOutput().ReleaseData()
        else :
            surf = vtk.vtkFlyingEdges3D()
            surf.SetInputData(flip2.GetOutput())
            surf.ComputeNormalsOn()
            surf.ComputeGradientsOn()
            surf.InterpolateAttributesOn()
            surf.SetValue(contourS, contourE)
            surf.Update()
            flip2.GetOutput().ReleaseData()

        decima = vtk.vtkQuadricDecimation()
        decima.SetInputData(surf.GetOutput())
        decima.SetTargetReduction(deci)             #decimaprop
        decima.Update()
        surf.GetOutput().ReleaseData()

        smoother = vtk.vtkSmoothPolyDataFilter()
        smoother.SetInputData(decima.GetOutput())
        smoother.SetNumberOfIterations(noi)         #3dsmoothprop
        smoother.SetRelaxationFactor(refa)          #3dsmoothprop
        smoother.FeatureEdgeSmoothingOff()
        smoother.BoundarySmoothingOn()
        smoother.Update()
        decima.GetOutput().ReleaseData()

        #center aligment\n",
        transForm = vtk.vtkTransform()
        transForm.Translate(-dims[0] * spacing[0]/2.0, -dims[1] * spacing[1]/2.0, -dims[2] * spacing[2]/2.0)
        transFilter=vtk.vtkTransformFilter()
        transFilter.SetInputData(smoother.GetOutput())
        transFilter.SetTransform(transForm)
        transFilter.Update()
        smoother.GetOutput().ReleaseData()

        writer = vtk.vtkSTLWriter()
        writer.SetInputData(transFilter.GetOutput())
        writer.SetFileTypeToBinary()
        writer.SetFileName(f'{outputFilePath}')
        writer.Write()
        transFilter.GetOutput().ReleaseData()
        writer = None
    @staticmethod
    def _process_recon_flying_with_phy( 
                      inputFilePath : str, outputFilePath : str, 
                      stddev : float, contourS : int, contourE : int, 
                      noi : int, refa : float, deci : float,
                      bGauss = True, npMatPhy = None, resamplingFactor = 1
                      ) :
        reader = vtk.vtkNIFTIImageReader()
        reader.SetFileName(inputFilePath)
        reader.Update()

        inputData = reader
        if resamplingFactor > 1 :
            resampler = vtk.vtkImageResample()
            resampler.SetInputData(reader.GetOutput())
            resampler.SetMagnificationFactors([resamplingFactor,resamplingFactor,resamplingFactor])
            resampler.Update()
            reader.GetOutput().ReleaseData()
            inputData = resampler

        dims = reader.GetOutput().GetDimensions()
        spacing = reader.GetOutput().GetSpacing()
        origin = reader.GetOutput().GetOrigin()
        direction = reader.GetOutput().GetDirectionMatrix()
        physical = reader.GetOutput().GetIndexToPhysicalMatrix()

        surf = None
        if bGauss == True :
            gaussian = vtk.vtkImageGaussianSmooth()
            gaussian.SetInputData(inputData.GetOutput())
            gaussian.SetStandardDeviation(stddev)       #2dsmoothprop
            gaussian.Update()
            inputData.GetOutput().ReleaseData()

            surf = vtk.vtkFlyingEdges3D()
            surf.SetInputData(gaussian.GetOutput())
            surf.ComputeNormalsOn()
            surf.ComputeGradientsOn()
            surf.InterpolateAttributesOn()
            surf.SetValue(contourS, contourE)
            surf.Update()
            gaussian.GetOutput().ReleaseData()
        else :
            surf = vtk.vtkFlyingEdges3D()
            surf.SetInputData(inputData.GetOutput())
            surf.ComputeNormalsOn()
            surf.ComputeGradientsOn()
            surf.InterpolateAttributesOn()
            surf.SetValue(contourS, contourE)
            surf.Update()
            inputData.GetOutput().ReleaseData()

        decima = vtk.vtkQuadricDecimation()
        decima.SetInputData(surf.GetOutput())
        decima.SetTargetReduction(deci)             #decimaprop
        decima.Update()
        surf.GetOutput().ReleaseData()

        smoother = vtk.vtkSmoothPolyDataFilter()
        smoother.SetInputData(decima.GetOutput())
        smoother.SetNumberOfIterations(noi)         #3dsmoothprop
        smoother.SetRelaxationFactor(refa)          #3dsmoothprop
        smoother.FeatureEdgeSmoothingOff()
        smoother.BoundarySmoothingOn()
        smoother.Update()
        decima.GetOutput().ReleaseData()

        # transform physical coordinate
        transForm = vtk.vtkTransform()
        if npMatPhy is None :
            transForm.SetMatrix(
                [
                    1, 0, 0, 0,
                    0, 1, 0, 0,
                    0, 0, 1, 0,
                    0, 0, 0, 1
                ]
            )
        else :
            transForm.SetMatrix(
                [
                    npMatPhy[0, 0], npMatPhy[0, 1], npMatPhy[0, 2], npMatPhy[0, 3],
                    npMatPhy[1, 0], npMatPhy[1, 1], npMatPhy[1, 2], npMatPhy[1, 3],
                    npMatPhy[2, 0], npMatPhy[2, 1], npMatPhy[2, 2], npMatPhy[2, 3],
                    npMatPhy[3, 0], npMatPhy[3, 1], npMatPhy[3, 2], npMatPhy[3, 3]
                ]
            )
        transFilter = vtk.vtkTransformFilter()
        transFilter.SetInputData(smoother.GetOutput())
        transFilter.SetTransform(transForm)
        transFilter.Update()
        smoother.GetOutput().ReleaseData()

        writer = vtk.vtkSTLWriter()
        writer.SetInputData(transFilter.GetOutput())
        writer.SetFileTypeToBinary()
        writer.SetFileName(f'{outputFilePath}')
        writer.Write()
        transFilter.GetOutput().ReleaseData()
        writer = None

    @staticmethod
    def _process_marching_cube_with_gaussian(flip : vtk.vtkImageFlip, stddev : float, contourS : int, contourE : int) -> vtk.vtkImageMarchingCubes :
        gaussian = vtk.vtkImageGaussianSmooth()
        gaussian.SetInputData(flip.GetOutput())
        gaussian.SetStandardDeviation(stddev)       #2dsmoothprop
        gaussian.Update()
        flip.GetOutput().ReleaseData()

        surf = vtk.vtkImageMarchingCubes()
        surf.SetInputData(gaussian.GetOutput())
        surf.SetValue(contourS, contourE)           #contourprop
        surf.ComputeNormalsOn()
        surf.Update()
        gaussian.GetOutput().ReleaseData()
        return surf
    @staticmethod
    def _process_marching_cube(flip : vtk.vtkImageFlip, contourS : int, contourE : int) -> vtk.vtkImageMarchingCubes :
        surf = vtk.vtkImageMarchingCubes()
        surf.SetInputData(flip.GetOutput())
        surf.SetValue(contourS, contourE)           #contourprop
        surf.ComputeNormalsOn()
        surf.Update()
        flip.GetOutput().ReleaseData()
        return surf
    @staticmethod
    def _param_vessel() :
        CScoUtilVTK.recon_set_param_contour(0, 10)
        CScoUtilVTK.recon_set_param_gaussian_stddev(1.0)
        CScoUtilVTK.recon_set_param_polygon_smoothing(15, 0.2, 0.8)
    @staticmethod
    def _param_organ() :
        CScoUtilVTK.recon_set_param_contour(0, 10)
        CScoUtilVTK.recon_set_param_gaussian_stddev(1.0)
        CScoUtilVTK.recon_set_param_polygon_smoothing(20, 0.5, 0.9)



