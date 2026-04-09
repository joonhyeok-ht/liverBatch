import os
import sys
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
#import trimesh
import sys, tempfile, shutil
import json

from collections import defaultdict


def _to_uc_binary(img_itk: itk.Image) -> itk.Image:
    """0/비0 → 0/255 (uint8)로 정리"""
    arr = itk.array_from_image(img_itk)
    bin_arr = (arr > 0).astype(np.uint8) * 255
    out = itk.image_from_array(bin_arr)
    out.CopyInformation(img_itk)
    return out

def _make_composite_label_mask(mask_paths: list[str]) -> tuple[itk.Image, dict[int, str]]:
    """
    여러 binary 마스크를 하나의 레이블(mask)로 합칩니다.
    라벨은 1..N (0=배경). 겹치면 '나중 것'이 우선(원하면 로직 바꿔도 됨).
    return: (label_img_itk, {label_id: 원래파일경로})
    """
    if not mask_paths:
        raise RuntimeError("mask_paths is empty")

    # 첫 마스크를 참조 그리드로
    ref = itk.imread(mask_paths[0], itk.UC)
    ref = _to_uc_binary(ref)
    base = itk.array_from_image(ref).astype(np.uint16)  # 여유롭게 16비트 버퍼
    base[:] = 0

    label_to_path = {}
    for li, mpath in enumerate(mask_paths, start=1):
        li*=10
        m = itk.imread(mpath, itk.UC)
        # 그리드 일치 여부(원점/간격/방향/크기) 확인 (다르면 여기서 예외 처리/리샘플 필요)
        if (m.GetLargestPossibleRegion().GetSize() != ref.GetLargestPossibleRegion().GetSize() or
            tuple(m.GetSpacing()) != tuple(ref.GetSpacing()) or
            tuple(m.GetOrigin())  != tuple(ref.GetOrigin())):
            #tuple(m.GetDirection().GetVnlMatrix().data_array()) != tuple(ref.GetDirection().GetVnlMatrix().data_array())):
            raise RuntimeError(f"Mask grid mismatch: {mpath} (모두 같은 공간에서 시작해야 합니다)")

        m = _to_uc_binary(m)
        arr = itk.array_from_image(m)
        # 겹침 처리: 나중 마스크가 덮어씀 (원하면 base[arr>0 & base==0] = li 로 바꾸면 '먼저 온 것 우선')
        base[arr > 0] = li
        label_to_path[li] = mpath

    label_img = itk.image_from_array(base)
    label_img.CopyInformation(ref)
    # 결과는 unsigned short로 보관(필요시 UC로 캐스팅 가능)
    return label_img, label_to_path

def _extract_label_binary(label_img_deformed: itk.Image, label_id: int) -> itk.Image:
    """변형된 레이블 이미지에서 특정 라벨만 binary(0/255, UC)로 추출"""
    arr = itk.array_from_image(label_img_deformed)
    bin_arr = (arr == label_id).astype(np.uint8) * 255
    out = itk.image_from_array(bin_arr)
    out.CopyInformation(label_img_deformed)
    return out

def _param_for_labels(reg_param_obj: itk.ParameterObject) -> itk.ParameterObject:
    po = itk.ParameterObject.New()
    for i in range(reg_param_obj.GetNumberOfParameterMaps()):
        pm = reg_param_obj.GetParameterMap(i)
        # 마스크용 출력/보간만 바꿔치기 (변형계수/행렬은 그대로 유지)
        pm["ResampleInterpolator"] = ["FinalNearestNeighborInterpolator"]
        pm["FinalBSplineInterpolationOrder"] = ["0"]
        pm["ResultImagePixelType"] = ["unsigned char"]   # 라벨 수가 많으면 "unsigned short"
        pm["DefaultPixelValue"] = ["0"]
        
        # 디버깅 산출물은 보통 불필요
        if "ComputeDeformationField" in pm:
            pm["ComputeDeformationField"] = ["false"]
        if "ComputeDeterminantOfSpatialJacobian" in pm:
            pm["ComputeDeterminantOfSpatialJacobian"] = ["false"]
        
        po.AddParameterMap(pm)
    return po

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
    bspline["MaximumNumberOfIterations"] = ["1000"]
    bspline["BSplineTransformSplineOrder"] = ["3"]
    bspline["AutomaticTransformInitialization"] = ["true"]
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
        self.m_inputPhase = None
        self.m_outputListWarpedNifti = None
        self.m_outputPath = ""
        self.m_inputDicomePath = ""
        self.m_originOffsetBlock = None
        self.m_organList = ["Gallbladder", "Liver", "kidney_right", "Stomach", "spleen", "adrenal_gland_right"]

    def clear(self):
        # input your code
        self.m_inputOptionInfo = None
        self.m_inputPhase = None
        self.m_originOffsetBlock = None
        if self.m_outputListWarpedNifti is not None:
            self.m_outputListWarpedNifti.clear()
            self.m_outputListWarpedNifti = None
        self.m_outputPath = ""
        super().clear()

    def process(self):
        if self.InputOptionInfo is None:
            print("nonrigid reg : not setting input optionInfo")
            return
        if self.InputPhase is None:
            print("nonrigid reg : not setting input nifti container")
            return
        phaseToID = dict()
        listParam = []
        
        targetPhaseInfo = self.find_target_phase_info()
        resampledDicomPath = self.write_resampled_dicom_to_nifti(targetPhaseInfo)
        phaseToWarpedPaths = self.write_resampled_mask(targetPhaseInfo)
        #self.set_src_phaseinfo_to_target_phase(targetPhaseInfo)
        #self.write_target_dicom_to_nifti(targetPhaseInfo.Phase)
        
        iPhaseCnt = self.InputPhase.get_phaseinfo_count()
        for inx in range(0, iPhaseCnt) :
            phaseInfo = self.InputPhase.get_phaseinfo(inx)
            
            phase = phaseInfo.Phase
            
            if phase == "MR" or phase == targetPhaseInfo.Phase:
                continue
            
            if phase not in phaseToWarpedPaths.keys():
                continue
            
            listParam.append(tuple([resampledDicomPath[targetPhaseInfo.Phase],
                                     resampledDicomPath[phase],
                                     phaseToWarpedPaths[phase]]))
        
        super().process(self._task, listParam)

        return

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
    
    def set_src_phaseinfo_to_target_phase(self, targetPhaseInfo : niftiContainer.CPhaseInfo):
        iPhaseCnt = self.InputPhase.get_phaseinfo_count()
        listPhaseInfo = []
        
        for inx in range(0, iPhaseCnt) :
            srcPhaseInfo = self.InputPhase.get_phaseinfo(inx)
            if srcPhaseInfo.Phase == targetPhaseInfo.Phase:
                continue

            #phase = phaseinfo.Phase
            if srcPhaseInfo.is_valid() == False or self.InputOptionInfo.find_rigid_aabb_of_phase(srcPhaseInfo.Phase) :
                continue
            
            srcPhaseInfo.m_origin = targetPhaseInfo.m_origin
            srcPhaseInfo.m_spacing = targetPhaseInfo.m_spacing
            srcPhaseInfo.m_direction = targetPhaseInfo.m_direction
            srcPhaseInfo.m_size = targetPhaseInfo.m_size
            srcPhaseInfo.m_offset = targetPhaseInfo.m_offset
            
            print(f"phase : {srcPhaseInfo.Phase}", file=sys.__stdout__, flush=True)
            print(f"srcPhaseInfo origin: {srcPhaseInfo.m_origin}", file=sys.__stdout__, flush=True)
            print(f"srcPhaseInfo spacing : {srcPhaseInfo.m_spacing}", file=sys.__stdout__, flush=True)
            print(f"srcPhaseInfo size : {srcPhaseInfo.m_size}", file=sys.__stdout__, flush=True)
            print(f"srcPhaseInfo offset : {srcPhaseInfo.m_offset}", file=sys.__stdout__, flush=True)
            
        return
    def write_resampled_mask(self, targetPhaseInfo : niftiContainer.CPhaseInfo):
        phaseToWarpedPaths = defaultdict(str)
        #regTargetMaskName, _, _ = self.InputOptionInfo.get_registrationinfo(0)
        iReconCnt = self.InputOptionInfo.get_recon_count()
        
        for ri in range(iReconCnt):
            iReconListCnt = self.InputOptionInfo.get_recon_list_count(ri)
            for rli in range(iReconListCnt):
                maskName, blenderName, phase, triCnt = self.InputOptionInfo.get_recon_list(ri, rli)
                if phase == targetPhaseInfo.Phase:
                    continue
                if phase == "MR":
                    continue
                if blenderName == "":
                    continue
                if maskName == "Skin" or maskName == "Abdominal_wall_liver":
                    continue
                
                maskFullPath = os.path.join(self.OutputPath, f"{maskName}.nii.gz")
                if phase == "" or phase == None:
                    continue
                if not os.path.exists(maskFullPath):
                    continue
                
                phaseInfo = self.InputPhase.find_phaseinfo(phase)

                targetOrigin = targetPhaseInfo.Origin
                targetDirection = targetPhaseInfo.Direction
                targetSpacing = targetPhaseInfo.Spacing
                targetSize = targetPhaseInfo.Size
                phaseOffset = phaseInfo.Offset + self.OriginOffsetBlock.OutputOriginOffset
                
                transform = sitk.TranslationTransform(
                    3,
                    [
                        float(-phaseOffset[0, 0]),
                        float(-phaseOffset[0, 1]),
                        float(-phaseOffset[0, 2]),
                    ],
                )

                sitkSrc = scoUtil.CScoUtilSimpleITK.load_image(maskFullPath, None)
                sitkSrc = sitk.Resample(
                    sitkSrc,
                    targetSize,
                    transform,
                    sitk.sitkNearestNeighbor,
                    targetOrigin,
                    targetSpacing,
                    targetDirection,
                    0,
                    sitkSrc.GetPixelID(),
                )

                resampledSrcMaskPath = (
                    self.OutputPath
                    + "/resampled_"
                    + str(os.path.basename(maskFullPath))
                )
                sitk.WriteImage(sitkSrc, resampledSrcMaskPath)

                warpedSrcMaskPath = (
                    self.OutputPath
                    + "/warped_"
                    + str(os.path.basename(resampledSrcMaskPath))
                )
                warpedMaskName = "warped_resampled_" + maskName
                self.InputOptionInfo.set_recon_phase(maskName, targetPhaseInfo.Phase)
                self.InputOptionInfo.set_recon_maskname(maskName, warpedMaskName)
                
                phaseToWarpedPaths[phase] = phaseToWarpedPaths[phase] + "~" + resampledSrcMaskPath
        return phaseToWarpedPaths
            
    
    def write_resampled_dicom_to_nifti(self, targetPhaseInfo : niftiContainer.CPhaseInfo):
        resampledDicomPath = defaultdict(str)
        
        if self.OriginOffsetBlock == None:
            return
        
        iPhaseCnt = self.InputPhase.get_phaseinfo_count()
        for inx in range(0, iPhaseCnt) :
            phaseInfo = self.InputPhase.get_phaseinfo(inx)
            
            phase = phaseInfo.Phase
            
            if phase == "MR":
                continue
            
            targetOrigin = targetPhaseInfo.Origin
            targetDirection = targetPhaseInfo.Direction
            targetSpacing = targetPhaseInfo.Spacing
            targetSize = targetPhaseInfo.Size
            phaseOffset = phaseInfo.Offset + self.OriginOffsetBlock.OutputOriginOffset
            
            transform = sitk.TranslationTransform(
                3,
                [
                    float(-phaseOffset[0, 0]),
                    float(-phaseOffset[0, 1]),
                    float(-phaseOffset[0, 2]),
                ],
            )

            resampledDicomNiftiPath = (
                str(self.OutputPath) + "/DICOM_" + phase + ".nii.gz"
            )

            dicomPath = os.path.join(self.InputDicomPath, phase)
            dicomImage = self.load_dicom_series(dicomPath)
            dicomImage = sitk.Resample(
                dicomImage,
                targetSize,
                transform,
                sitk.sitkNearestNeighbor, #sitk.sitkLinear
                targetOrigin,
                targetSpacing,
                targetDirection,
                0.0,
                dicomImage.GetPixelID(),
            )
            sitk.WriteImage(dicomImage, resampledDicomNiftiPath)
            resampledDicomPath[phase] = resampledDicomNiftiPath

        return resampledDicomPath
    
    def find_target_phase_info(self):
        targetPhaseInfo = None
        
        iReconListCnt = self.InputOptionInfo.get_recon_list_count(0)
        regTargetMaskName, _, _ = self.InputOptionInfo.get_registrationinfo(0)
        for reconListInx in range(0, iReconListCnt) :
            maskName, blenderName, phase, triCnt = self.InputOptionInfo.get_recon_list(0, reconListInx)
            
            if regTargetMaskName == maskName:
                targetPhaseInfo = self.InputPhase.find_phaseinfo(phase)
                
                if targetPhaseInfo is None:
                    print("targetPhaseInfo is not valid", file=sys.__stdout__, flush=True)
                    continue
                break 
            
        return targetPhaseInfo

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

            targetDicomImageItk = itk.imread(targetDicomPath, itk.F)
            srcDicomImageItk = itk.imread(srcDicomPath, itk.F)

            # parameter_object = itk.ParameterObject.New()
            # bspline_map = parameter_object.GetDefaultParameterMap('bspline')

            # bspline_map["Metric"] = ["AdvancedMattesMutualInformation"]
            
            # bspline_map["Metric"] = [
            #     "AdvancedMattesMutualInformation",
            #     "TransformBendingEnergyPenalty",
            # ]
            # bspline_map["Metric0Weight"] = ["1.0"]
            # bspline_map["Metric1Weight"] = ["0.1"]
            
            # #bspline_map["NumberOfHistogramBins"] = ["80"]
            # bspline_map["NumberOfResolutions"] = ["4"]
            # bspline_map["GridSpacingSchedule"] = ["8", "4", "2", "1"] 
            # bspline_map["MaximumNumberOfIterations"] = ["300"]
            # bspline_map["BSplineTransformSplineOrder"] = ["3"]
            
            # bspline_map["FinalBSplineInterpolationOrder"] = ["0"]
            # bspline_map["ResultImagePixelType"] = ["unsigned char"]

            # bspline_map["NumberOfHistogramBins"] = ["150"]
            # # bspline_map["ResultImagePixelType"] = ["float"]
            # # bspline_map["FinalBSplineInterpolationOrder"] = ["1"]
            


            #parameter_object.AddParameterMap(bspline_map)
            parameter_object = build_parameter_object()
            result_img, result_transform_param = itk.elastix_registration_method(
                targetDicomImageItk,
                srcDicomImageItk,
                parameter_object=parameter_object,
            )
            
            totalMaskPathList = [p for p in srcMaskPathList.split("~") if p]
            organMaskPathList = []
            
            for srcMaskPath in srcMaskPathList.split("~"):
                for organName in self.m_organList:
                    if organName in srcMaskPath:
                        organMaskPathList.append(srcMaskPath)
                        totalMaskPathList.remove(srcMaskPath)
                        
                        
            if organMaskPathList:
                label_img, label_map = _make_composite_label_mask(organMaskPathList)
                label_param = _param_for_labels(result_transform_param)
                deformed_label_img = itk.transformix_filter(label_img, label_param)

                os.makedirs(self.OutputPath, exist_ok=True)
                for li, orig_path in label_map.items():
                    out_name = os.path.join(self.OutputPath, "warped_" + os.path.basename(orig_path))
                    bin_img = _extract_label_binary(deformed_label_img, li)
                    itk.imwrite(bin_img, out_name)
                    print(f"[SAVED] {out_name}", file=sys.__stdout__, flush=True)
                    
                    # # 화살표 STL 경로
                    # if "ap" in out_name:
                    #     out_stl = os.path.join(self.OutputPath, f"defvec_label{li}.stl")
                    #     deformation_to_arrows_stl_from_transformix(
                    #         fixed_img=targetDicomImageItk,
                    #         result_transform_param=result_transform_param,
                    #         deformed_label_img=deformed_label_img,
                    #         label_value=li,
                    #         out_stl_path=out_stl,
                    #         grid_step=6, min_magnitude_mm=1.0, scale=1.0,
                    #         shaft_radius=0.20, head_radius=0.9, head_ratio=0.4
                    #     )
                
                itk.imwrite(deformed_label_img, os.path.join(self.OutputPath, "warped__ALL_organs.nii.gz"))
            else:
                pass

            for srcMaskPath in totalMaskPathList:
                if not os.path.exists(srcMaskPath):
                    continue
                
                resultMaskPath = (
                    self.OutputPath + "/warped_" + str(os.path.basename(srcMaskPath))
                )
                srcMaskImageItk = itk.imread(srcMaskPath, itk.UC)
                warped_mask = itk.transformix_filter(srcMaskImageItk, result_transform_param)
                itk.imwrite(warped_mask, resultMaskPath)
                print(f"[SAVED] {resultMaskPath}", file=sys.__stdout__, flush=True)


    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo:
        return self.m_inputOptionInfo

    @InputOptionInfo.setter
    def InputOptionInfo(self, inputOptionInfo: optionInfo.COptionInfo):
        self.m_inputOptionInfo = inputOptionInfo

    @property
    def InputPhase(self) -> niftiContainer.CPhase:
        return self.m_inputPhase

    @InputPhase.setter
    def InputPhase(self, inputPhase: niftiContainer.CPhase):
        self.m_inputPhase = inputPhase

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
        
    @property
    def OriginOffsetBlock(self):
        return self.m_originOffsetBlock
        
    @OriginOffsetBlock.setter
    def OriginOffsetBlock(self, originOffsetBlock):
        self.m_originOffsetBlock = originOffsetBlock
