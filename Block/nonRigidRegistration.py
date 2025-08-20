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
from Algorithm import scoUtil

import multiProcessTask as multiProcessTask
import niftiContainer as niftiContainer
import optionInfo as optionInfo

import itk
import SimpleITK as sitk
from collections import defaultdict
import vtk
import shutil
from skimage.exposure import match_histograms

def mask_to_sdf(mask_img, inside_is_positive=True):
    # 0/255 -> 0/1 권장 (가독성용)
    dim = mask_img.GetImageDimension()
    U8 = itk.Image[itk.UC, dim]
    if itk.template(mask_img)[1][0] != itk.UC:
        mask_u8 = itk.cast_image_filter(mask_img, ttype=[type(mask_img), U8])
    else:
        mask_u8 = mask_img

    DM = itk.SignedMaurerDistanceMapImageFilter[U8, itk.Image[itk.F, dim]].New()
    DM.SetInput(mask_u8)
    DM.SetUseImageSpacing(True)          # ← SDF 단위를 mm로
    DM.SquaredDistanceOff()
    DM.SetInsideIsPositive(inside_is_positive)
    DM.Update()
    sdf = DM.GetOutput()
    
    return sdf

    # # ---- ★ 경계 바이어스 보정: -0.5 * min(spacing) mm ----
    # sp = np.array(itk.spacing(mask_u8), dtype=float)
    # #bias = -0.25 * float(sp.min())
    # shift = itk.ShiftScaleImageFilter[type(sdf), type(sdf)].New()
    # shift.SetInput(sdf)
    # #shift.SetShift(bias)                 # inward shift
    # shift.SetScale(2.0)
    # shift.Update()
    # return shift.GetOutput()



def sdf_to_mask(sdf_img, tau_mm=0.3, closing_radius_vox=0):
    """
    sdf_img: float 거리맵 (양수: 내부)
    threshold 0 으로 이진화 후, 필요 시 morphological closing.
    """
    dim = sdf_img.GetImageDimension()
    # 0-level 에서 바이너리화
    thresh = itk.BinaryThresholdImageFilter[type(sdf_img), itk.Image[itk.UC, dim]].New()
    thresh.SetInput(sdf_img)
    thresh.SetLowerThreshold(-0.1)
    thresh.SetUpperThreshold(float(tau_mm))
    thresh.SetInsideValue(255)
    thresh.SetOutsideValue(0)
    thresh.Update()
    mask = thresh.GetOutput()

    # 약한 끊김 보완용 closing (선택)
    if closing_radius_vox > 0:
        stype = itk.FlatStructuringElement[dim].Ball(closing_radius_vox)
        closing = itk.BinaryMorphologicalClosingImageFilter[
            type(mask), type(mask), type(stype)
        ].New()
        closing.SetInput(mask)
        closing.SetKernel(stype)
        closing.SetForegroundValue(255)
        closing.Update()
        mask = closing.GetOutput()

    return mask


def sdf_zero_band_mask(sdf_img, eps_vox=1.05, closing_radius_vox=1):
    dim = sdf_img.GetImageDimension()
    abs_sdf = itk.AbsImageFilter[type(sdf_img), type(sdf_img)].New()
    abs_sdf.SetInput(sdf_img); abs_sdf.Update()

    U8 = itk.Image[itk.UC, dim]
    th = itk.BinaryThresholdImageFilter[type(sdf_img), U8].New()
    th.SetInput(abs_sdf.GetOutput())
    th.SetLowerThreshold(0.0)
    th.SetUpperThreshold(float(eps_vox))   # 밴드 폭
    th.SetInsideValue(255); th.SetOutsideValue(0); th.Update()
    mask = th.GetOutput()

    if closing_radius_vox > 0:
        se = itk.FlatStructuringElement[dim].Ball(closing_radius_vox)
        cl = itk.BinaryMorphologicalClosingImageFilter[U8, U8, type(se)].New()
        cl.SetInput(mask); cl.SetKernel(se); cl.SetForegroundValue(255); cl.Update()
        mask = cl.GetOutput()
    return mask

def make_transformix_param_for_resampling(original_param, resample_interpolator="LinearInterpolator",
                                          result_pixel_type="float", default_pixel_value="-10.0"):
    new_param = itk.ParameterObject.New()
    for i in range(original_param.GetNumberOfParameterMaps()):
        new_param.AddParameterMap(original_param.GetParameterMap(i))
    # ---- ★ 모든 맵에 동일 적용 ----
    for i in range(new_param.GetNumberOfParameterMaps()):
        if "ResampleInterpolator" in new_param.GetParameterMap(i).keys():
            new_param.SetParameter(i, "ResampleInterpolator", [resample_interpolator])
        if "ResultImagePixelType" in new_param.GetParameterMap(i).keys():    
            new_param.SetParameter(i, "ResultImagePixelType", [result_pixel_type])
        if "DefaultPixelValue" in new_param.GetParameterMap(i).keys():
            new_param.SetParameter(i, "DefaultPixelValue", [default_pixel_value])
    return new_param






def make_transformix_param_for_resampling(
    original_param: itk.ParameterObject,
    resample_interpolator: str = "LinearInterpolator",
    result_pixel_type: str = "float",
    default_pixel_value: str = "-10.0" 
) -> itk.ParameterObject:
    
    # deep copy
    new_param = itk.ParameterObject.New()
    for i in range(original_param.GetNumberOfParameterMaps()):
        new_param.AddParameterMap(original_param.GetParameterMap(i))

    
    # 설정 덮어쓰기 (마지막 파라미터맵에만 적용)
    new_param.SetParameter(0, "ResampleInterpolator", [resample_interpolator])
    new_param.SetParameter(0, "ResultImagePixelType", [result_pixel_type])
    for i in range(new_param.GetNumberOfParameterMaps()):
        
        if "DefaultPixelValue" in new_param.GetParameterMap(i).keys():
            new_param.SetParameter(i, "DefaultPixelValue", [default_pixel_value])
    return new_param


def build_parameter_object():
    po = itk.ParameterObject.New()

    # Rigid
    rigid = po.GetDefaultParameterMap("rigid")
    rigid["Metric"] = ["AdvancedMattesMutualInformation"]
    rigid["NumberOfHistogramBins"] = ["70"]
    rigid["AutomaticParameterEstimation"] = ["true"]
    rigid["NumberOfResolutions"] = ["3"]
    po.AddParameterMap(rigid)

    # Affine
    affine = po.GetDefaultParameterMap("affine")
    affine["Metric"] = ["AdvancedMattesMutualInformation"]
    affine["NumberOfHistogramBins"] = ["70"]
    affine["AutomaticParameterEstimation"] = ["true"]
    affine["NumberOfResolutions"] = ["3"]
    po.AddParameterMap(affine)

    # B-spline (보수적)
    bspline = po.GetDefaultParameterMap("bspline")

    bspline["Metric"] = [
        "AdvancedMattesMutualInformation",
        "TransformBendingEnergyPenalty",
    ]
    bspline["Metric0Weight"] = ["1.0"]
    bspline["Metric1Weight"] = ["0.1"]

    bspline["NumberOfHistogramBins"] = ["80"]
    bspline["NumberOfResolutions"] = ["4"]
    bspline["GridSpacingSchedule"] = ["8", "4", "2", "1"] 
    bspline["MaximumNumberOfIterations"] = ["300"]
    bspline["BSplineTransformSplineOrder"] = ["3"]
    bspline["AutomaticTransformInitialization"] = ["false"]
    bspline["AutomaticParameterEstimation"] = ["true"]
    bspline["MaximumStepLength"] = ["0.6"]
    
    bspline["ResultImagePixelType"] = ["unsigned char"]
    bspline["FinalBSplineInterpolationOrder"] = ["0"]

    # 권장: 방향 코사인 사용
    bspline["UseDirectionCosines"] = ["true"]

    po.AddParameterMap(bspline)
    return po

class CNonRigidRegistration(multiProcessTask.CMultiProcessTask):
    def __init__(self) -> None:
        super().__init__()
        # input your code
        self.m_inputOptionInfo = None
        self.m_inputNiftiContainer = None
        self.m_outputListWarpedNifti = None
        self.m_outputPath = ""
        self.m_inputDicomePath = ""

    def clear(self):
        # input your code
        self.m_inputOptionInfo = None
        self.m_inputNiftiContainer = None
        if self.m_outputListWarpedNifti is not None:
            self.m_outputListWarpedNifti.clear()
            self.m_outputListWarpedNifti = None
        self.m_outputPath = ""
        super().clear()

    def process(self):
        if self.InputOptionInfo is None:
            print("nonrigid reg : not setting input optionInfo")
            return
        if self.InputNiftiContainer is None:
            print("nonrigid reg : not setting input nifti container")
            return

        phaseToID = dict()
        listParam = []

        iRegInfoCnt = self.InputOptionInfo.get_reginfo_count()
        iNiftiInfoCnt = self.InputNiftiContainer.get_nifti_info_count()

        for inx in range(0, iRegInfoCnt):
            regInfo = self.InputOptionInfo.get_reginfo(inx)
            fixedTargetName = regInfo.Target
            targetNiftiInfo = self.InputNiftiContainer.find_nifti_info_list_by_name(
                fixedTargetName
            )
            fixedTargetPhase = targetNiftiInfo[0].MaskInfo.Phase

            src = regInfo.Src
            srcNiftiInfo = self.InputNiftiContainer.find_nifti_info_list_by_name(src)
            srcPhase = srcNiftiInfo[0].MaskInfo.Phase

        if fixedTargetPhase is None:
            print(f"not found registration target")
            return
        
        targetDicomNiftiPath = (
            str(self.OutputPath) + "/DICOM_" + fixedTargetPhase + ".nii.gz"
        )
        if os.path.exists(targetDicomNiftiPath):
            pass
        else:
            targetDcmPath = os.path.join(self.InputDicomPath, fixedTargetPhase)
            targetDicomImageSitk = self.load_dicom_series(targetDcmPath)
            sitk.WriteImage(targetDicomImageSitk, targetDicomNiftiPath)

        for inx in range(0, iNiftiInfoCnt):
            niftiInfo = self.InputNiftiContainer.get_nifti_info(inx)
            if not niftiInfo.Valid:
                continue

            phaseInfo = self.InputNiftiContainer.find_phase_info(
                niftiInfo.MaskInfo.Phase
            )
            srcPhase = phaseInfo.Phase
            phaseOffset = phaseInfo.Offset
            
            if srcPhase == fixedTargetPhase:
                continue

            sourceDeformedDicomNiftiPath = (
                str(self.OutputPath) + "/DICOM_" + srcPhase + ".nii.gz"
            )

            dicomTargetImage = scoUtil.CScoUtilSimpleITK.load_image(
                targetDicomNiftiPath, None
            )
            targetOrigin = dicomTargetImage.GetOrigin()
            targetDirection = dicomTargetImage.GetDirection()
            targetSpacing = dicomTargetImage.GetSpacing()
            targetSize = dicomTargetImage.GetSize()

            transform = sitk.TranslationTransform(
                3,
                [
                    float(-phaseOffset[0, 0]),
                    float(-phaseOffset[0, 1]),
                    float(-phaseOffset[0, 2]),
                ],
            )

            if os.path.exists(sourceDeformedDicomNiftiPath):
                pass
            else:
                srcDcmPath = os.path.join(self.InputDicomPath, srcPhase)
                sourceDicomImage = self.load_dicom_series(srcDcmPath)
                sourceDicomImage = sitk.Resample(
                    sourceDicomImage,
                    targetSize,
                    transform,
                    sitk.sitkNearestNeighbor,
                    targetOrigin,
                    targetSpacing,
                    targetDirection,
                    0,
                    dicomTargetImage.GetPixelID(),
                )

                # source_np = sitk.GetArrayFromImage(sourceDicomImage)
                # source_norm = normalize_mr(source_np)
                # src_matched = match_histograms(source_norm, target_norm)
                # source_sitk = sitk.GetImageFromArray(src_matched)
                # source_sitk.CopyInformation(sourceDicomImage)

                # fixedSrcDicomImage = preprocess_image(sourceDicomImage, fixedTargetDicomImage)
                # sitk.WriteImage(fixedSrcDicomImage, sourceDeformedDicomNiftiPath)
                # sitk.WriteImage(source_sitk, sourceDeformedDicomNiftiPath)
                sitk.WriteImage(sourceDicomImage, sourceDeformedDicomNiftiPath)

                for i, phaseInfo in enumerate(self.InputNiftiContainer.m_listPhaseInfo):
                    if phaseInfo.Phase == srcPhase:
                        self.InputNiftiContainer.m_listPhaseInfo[i].m_origin = (
                            targetOrigin
                        )
                        self.InputNiftiContainer.m_listPhaseInfo[i].m_spacing = (
                            targetSpacing
                        )
                        self.InputNiftiContainer.m_listPhaseInfo[i].m_direction = (
                            targetDirection
                        )
                        self.InputNiftiContainer.m_listPhaseInfo[i].m_size = targetSize

            sitkSrc = scoUtil.CScoUtilSimpleITK.load_image(niftiInfo.FullPath, None)
            sitkSrc = sitk.Resample(
                sitkSrc,
                targetSize,
                transform,
                sitk.sitkNearestNeighbor,
                targetOrigin,
                targetSpacing,
                targetDirection,
                0,
                dicomTargetImage.GetPixelID(),
            )
            if not os.path.exists(self.OutputPath):
                os.mkdir(self.OutputPath)

            resampledSrcMaskPath = (
                self.OutputPath
                + "/resampled_"
                + str(os.path.basename(niftiInfo.FullPath))
            )
            sitk.WriteImage(sitkSrc, resampledSrcMaskPath)

            warpedSrcMaskPath = (
                self.OutputPath
                + "/warped_"
                + str(os.path.basename(resampledSrcMaskPath))
            )
            niftiInfo.FullPath = warpedSrcMaskPath

            if srcPhase in phaseToID.keys():
                phaseID = phaseToID[srcPhase]

                listParam[phaseID][2] = (
                    listParam[phaseID][2] + "~" + resampledSrcMaskPath
                )
            else:
                phaseToID[srcPhase] = len(phaseToID.keys())

                listParam.append(
                    [
                        targetDicomNiftiPath,
                        sourceDeformedDicomNiftiPath,
                        resampledSrcMaskPath,
                    ]
                )

        for i in range(len(listParam)):
            listParam[i] = tuple(listParam[i])

        super().process(self._task, listParam)

    def load_dicom_series(self, directory):
        
        try:
            reader = sitk.ImageSeriesReader()
            reader.SetImageIO("GDCMImageIO")
            dicomNames = reader.GetGDCMSeriesFileNames(directory)
            reader.SetFileNames(dicomNames)
            image = reader.Execute()
        except:
            print("CT load failed!\n\t", directory)
            return False
        
        return image
        # reader = sitk.ImageSeriesReader()
        # series_IDs = reader.GetGDCMSeriesIDs(directory)

        # if not series_IDs:
        #     raise ValueError(f"No DICOM series found in directory: {directory}")

        # series_file_names = reader.GetGDCMSeriesFileNames(directory, series_IDs[0])
        # reader.SetFileNames(series_file_names)
        # image = reader.Execute()
        # return image

    def _task(self, param: tuple):
        targetDicomPath = param[0]
        srcDicomPath = param[1]
        srcMaskPathList = param[2]

        if (
            os.path.exists(srcDicomPath) == False
            or os.path.exists(targetDicomPath) == False == False
        ):
            print("-" * 30)
            print(f"not found registration files")
            if os.path.exists(srcDicomPath) == False:
                print(f"src dicom path : {srcDicomPath}")
            if os.path.exists(targetDicomPath) == False:
                print(f"target dicom path : {targetDicomPath}")
            print("-" * 30)
        else:

            targetDicomImageSitk = itk.imread(targetDicomPath, itk.F)
            srcDicomImageItk = itk.imread(srcDicomPath, itk.F)

            parameter_object = build_parameter_object()
            result_img, result_transform_param = itk.elastix_registration_method(
                targetDicomImageSitk,
                srcDicomImageItk,
                parameter_object=parameter_object,
            )


            for srcMaskPath in srcMaskPathList.split("~"):
                srcMaskImageItk = itk.imread(srcMaskPath, itk.UC)
                
                # 마스크가 0/255인 경우 0/1로 정규화(선택)
                # (SignedMaurer는 0/1, 0/255 모두 처리 가능하지만 명확성을 위해 0/1로 맞추는 것도 좋음)
                # norm = itk.ShiftScaleImageFilter[type(srcMaskImageItk), type(srcMaskImageItk)].New()
                # norm.SetInput(srcMaskImageItk)
                # norm.SetShift(0.0)
                # norm.SetScale(1.0)  # 필요시 1/255.0
                # norm.Update()
                # srcMaskImageItk = norm.GetOutput()

                # sdf = mask_to_sdf(srcMaskImageItk, inside_is_positive=True)
                
                # tx_param = make_transformix_param_for_resampling(
                #     result_transform_param,
                #     resample_interpolator="LinearInterpolator",
                #     result_pixel_type="float",
                #     default_pixel_value="-100.0"
                # )

                # print("[*] Warp SDF with transformix (linear interpolation) ...")
                # warped_sdf = itk.transformix_filter(sdf, tx_param)
                # warped_mask = sdf_zero_band_mask(warped_sdf)
                
                
                
                
                # gaussian_filter = itk.SmoothingRecursiveGaussianImageFilter.New(Input=srcMaskImageItk)
                # gaussian_filter.SetSigma(0.25)  # sigma: mm 단위 (픽셀 spacing 기반)
                # gaussian_filter.Update()
                # smoothed_mask = gaussian_filter.GetOutput()
                                
                warped_mask = itk.transformix_filter(srcMaskImageItk, result_transform_param)

            
                resultMaskPath = (
                    self.OutputPath + "/warped_" + str(os.path.basename(srcMaskPath))
                )
                itk.imwrite(warped_mask, resultMaskPath)





            """
            
            targetDicomImageSitk = itk.imread(targetDicomPath, itk.F)
            srcDicomImageItk = itk.imread(srcDicomPath, itk.F)
            
            parameterObject = itk.ParameterObject.New()
            #rigidregistrationParam = parameterObject.GetDefaultParameterMap("rigid")                
            registrationParam = parameterObject.GetDefaultParameterMap("bspline")
            registrationParam["Metric"] = ["AdvancedMattesMutualInformation"]
            registrationParam["ResultImagePixelType"] = ["unsigned char"]
            registrationParam["FinalBSplineInterpolationOrder"] = ["0"]
            registrationParam["NumberOfHistogramBins"] = ["50"]
            #parameterObject.AddParameterMap(rigidregistrationParam)
            parameterObject.AddParameterMap(registrationParam)
                        
            resultMask, resultTransformParam = itk.elastix_registration_method(
                targetDicomImageSitk,
                srcDicomImageItk,
                parameter_object=parameterObject
            )
            
            for srcMaskPath in srcMaskPathList.split("~"):
                srcMaskImageItk = itk.imread(srcMaskPath, itk.F)
                resultMaskPath = self.OutputPath + "/warped_" + str(os.path.basename(srcMaskPath))

                warpedSrcImage = itk.transformix_filter(
                    srcMaskImageItk,
                    resultTransformParam)
                            
                itk.imwrite(warpedSrcImage, resultMaskPath)
                
                
            """

    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo:
        return self.m_inputOptionInfo

    @InputOptionInfo.setter
    def InputOptionInfo(self, inputOptionInfo: optionInfo.COptionInfo):
        self.m_inputOptionInfo = inputOptionInfo

    @property
    def InputNiftiContainer(self) -> niftiContainer.CNiftiContainer:
        return self.m_inputNiftiContainer

    @InputNiftiContainer.setter
    def InputNiftiContainer(self, inputNiftiContainer: niftiContainer.CNiftiContainer):
        self.m_inputNiftiContainer = inputNiftiContainer

    @property
    def OutputListOffset(self) -> list:
        return self.m_outputListWarpedNifti

    @property
    def OutputPath(self) -> str:
        return self.m_outputPath

    @OutputPath.setter
    def OutputPath(self, outputPath: str):
        self.m_outputPath = outputPath

    @property
    def InputDicomPath(self) -> str:
        return self.m_inputDicomePath

    @InputDicomPath.setter
    def InputDicomPath(self, InputDicomPath: str):
        self.m_inputDicomePath = InputDicomPath
