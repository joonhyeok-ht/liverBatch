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
#import trimesh
import sys, tempfile, shutil
import json

# # --- 작은 유틸 ---
# def _to_mat4(direction_rowmajor_3x3):
#     M = np.eye(4, dtype=float)
#     M[:3, :3] = np.asarray(direction_rowmajor_3x3, dtype=float)
#     return M

# def _translation_mat4(t3):
#     T = np.eye(4, dtype=float)
#     T[:3, 3] = np.asarray(t3, dtype=float)
#     return T

# def _scale_mat4(s3):
#     S = np.eye(4, dtype=float)
#     sx, sy, sz = np.asarray(s3, dtype=float)
#     S[0,0], S[1,1], S[2,2] = sx, sy, sz
#     return S

# def get_direction_np(itk_img):
#     """ITK Image의 Direction(itkMatrixD33) → numpy(3x3)"""
#     return np.asarray(itk.GetArrayFromMatrix(itk_img.GetDirection()), dtype=np.float64)

# # --- 핵심: build_mat_from_itk (yz 플립 포함) ---
# def build_mat_from_itk(itk_img,
#                        offset=(0.0, 0.0, 0.0),
#                        include_spacing=True,
#                        flip_yz=True,
#                        stride=1) -> np.ndarray:
#     """
#     ITK 이미지 메타(Origin/Spacing/Direction)를 사용하여
#     mat4 = Flip * Offset * (Trans(origin) * Rot(direction)) * [S(spacing)] * S(stride)
#     을 구성해 반환.
#     """
#     origin    = np.asarray(itk_img.GetOrigin(),  dtype=float)
#     spacing   = np.asarray(itk_img.GetSpacing(), dtype=float)
#     direction = get_direction_np(itk_img)  # row-major 3x3

#     R = _to_mat4(direction)
#     T = _translation_mat4(origin)
#     O = _translation_mat4(offset)

#     F = np.eye(4, dtype=float)
#     if flip_yz:
#         F[1,1] = -1.0
#         F[2,2] = -1.0

#     M = T @ R
#     M = O @ M
#     M = F @ M
#     if include_spacing:
#         M = M @ _scale_mat4(spacing)

#     s = int(max(1, int(stride)))
#     if s != 1:
#         M = M @ _scale_mat4((s, s, s))
#     return M

# # --- 인덱스 → 물리(mm) (M은 위에서 만든 4x4) ---
# def index_to_physical(i, j, k, M4x4):
#     v = np.array([i, j, k, 1.0], dtype=float)
#     p = M4x4 @ v
#     return p[:3]


# def get_direction_np(itk_img):
#     """ITK Image의 Direction을 numpy 3x3 행렬로 변환"""
#     M = itk_img.GetDirection()  # itkMatrixD33
#     try:
#         D = itk.GetArrayFromMatrix(M)  # (3,3) np.ndarray
#     except Exception:
#         # 혹시 SimpleITK식 튜플/리스트가 들어온 경우 대비
#         arr = np.array(M, dtype=np.float64)
#         D = arr.reshape(3, 3) if arr.size == 9 else arr
#     return np.asarray(D, dtype=np.float64)

# # -----------------------------
# # 변형장 얻기: transformix_deformation_field
# # -----------------------------
# def get_deformation_field(fixed_img, result_param_obj):
#     """
#     transformix_deformation_field를 사용해 3D VectorImage (dx,dy,dz; mm)를 반환.
#     """
#     # 일부 버전에서 인자명이 다를 수 있어 방어적으로 시도
#     try:
#         def_img = itk.transformix_deformation_field(fixed_img, result_param_obj)
#     except TypeError:
#         def_img = itk.transformix_deformation_field(
#             fixed_img, transform_parameter_object=result_param_obj
#         )
#     return def_img  # itk.Image[Vector<float,3>,3], fixed 격자 기준

# # -----------------------------
# # z축 -> dir_vec 회전행렬 (Rodrigues)
# # -----------------------------
# def rot_from_a_to_b(a: np.ndarray, b: np.ndarray) -> np.ndarray:
#     """
#     단위벡터 a를 b로 회전시키는 3x3 회전행렬 반환.
#     a,b는 3D unit vector 가정. (내부에서 정규화 수행)
#     """
#     a = np.asarray(a, dtype=np.float64)
#     b = np.asarray(b, dtype=np.float64)
#     na = np.linalg.norm(a); nb = np.linalg.norm(b)
#     if na < 1e-12 or nb < 1e-12:
#         return np.eye(3)
#     a = a / na; b = b / nb

#     v = np.cross(a, b)
#     c = float(np.dot(a, b))        # cos(theta)
#     s = np.linalg.norm(v)          # |a x b| = sin(theta)

#     if s < 1e-12:
#         # a와 b가 거의 평행(같은 방향 혹은 정반대)
#         if c > 0.0:
#             # 같은 방향 -> 회전 불필요
#             return np.eye(3)
#         else:
#             # 정반대 -> 임의의 직교축으로 180도 회전
#             # a에 직교하는 축을 하나 선택
#             axis = np.array([1.0, 0.0, 0.0])
#             if abs(a[0]) > 0.9:
#                 axis = np.array([0.0, 1.0, 0.0])
#             axis = axis - a * np.dot(axis, a)
#             axis_norm = np.linalg.norm(axis)
#             if axis_norm < 1e-12:
#                 return -np.eye(3)
#             axis = axis / axis_norm
#             # 180도 회전: R = I + 2*[axis]_x^2  (Rodrigues에서 s=0, c=-1 특수형)
#             K = np.array([[0, -axis[2], axis[1]],
#                           [axis[2], 0, -axis[0]],
#                           [-axis[1], axis[0], 0]], dtype=np.float64)
#             return np.eye(3) + 2 * (K @ K)

#     # 일반적 케이스: Rodrigues
#     K = np.array([[0, -v[2], v[1]],
#                   [v[2], 0, -v[0]],
#                   [-v[1], v[0], 0]], dtype=np.float64)
#     R = np.eye(3) + K + (K @ K) * ((1 - c) / (s * s))
#     return R


# # -----------------------------
# # 화살표 메쉬 생성
# # -----------------------------
# def make_arrow_trimesh(start, vec,
#                        shaft_radius=0.3,
#                        head_radius=1.1,
#                        head_length_ratio=0.3):
#     L = float(np.linalg.norm(vec))
#     if L < 1e-6:
#         return None

#     head_len = max(L * head_length_ratio, 0.5)
#     shaft_len = max(L - head_len, 0.5)

#     z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
#     dir_vec = (vec / L).astype(np.float64)

#     R = rot_from_a_to_b(z_axis, dir_vec)   # 3x3
#     T_shaft = np.eye(4); T_shaft[:3,:3] = R; T_shaft[:3,3] = start + dir_vec*(shaft_len*0.5)
#     T_head  = np.eye(4); T_head [:3,:3] = R; T_head [:3,3] = start + dir_vec*(shaft_len + head_len*0.5)

#     shaft = trimesh.creation.cylinder(radius=shaft_radius, height=shaft_len, sections=24, transform=T_shaft)
#     head  = trimesh.creation.cone    (radius=head_radius,  height=head_len,  sections=24, transform=T_head)
#     return trimesh.util.concatenate([shaft, head])
# # -----------------------------
# # 라벨 영역의 변위 벡터 → 화살표 STL
# # -----------------------------

# def load_phase_from_json(json_path: str, phase_name: str = "HVP"):
#     """
#     JSON 형식 예시(질문 제공):
#     [
#       {"Phase":"AP",  "Origin":[...], "Spacing":[...], "Direction":[9], "Size":[...], "Offset":[...]},
#       {"Phase":"HVP", "Origin":[...], "Spacing":[...], "Direction":[9], "Size":[...], "Offset":[...]},
#       ...
#     ]
#     반환: origin(3,), spacing(3,), direction_rowmajor(3x3), offset(3,)
#     """
#     with open(json_path, "r", encoding="utf-8") as f:
#         arr = json.load(f)
#     if not isinstance(arr, list):
#         raise ValueError("Phase JSON must be a list of entries.")
#     pick = None
#     for item in arr:
#         if str(item.get("Phase","")).upper() == str(phase_name).upper():
#             pick = item
#             break
#     if pick is None:
#         raise ValueError(f"Phase '{phase_name}' not found in {json_path}")

#     origin = np.asarray(pick["Origin"], dtype=float).reshape(3)
#     spacing = np.asarray(pick["Spacing"], dtype=float).reshape(3)
#     # Direction: 길이 9, row-major (r00,r01,r02, r10,r11,r12, r20,r21,r22)
#     direction = np.asarray(pick["Direction"], dtype=float).reshape(3,3)
#     offset = np.asarray(pick["Offset"], dtype=float).reshape(3)
#     return origin, spacing, direction, offset

# def deformation_to_arrows_stl_from_transformix(
#     fixed_img,                         # == targetDicomImageItk (elastix의 fixed와 동일)
#     result_transform_param,            # elastix 결과 파라미터 객체
#     deformed_label_img,                # deform된 라벨(= fixed 격자). 여러 라벨이 함께 있는 Label 이미지
#     label_value,                       # 화살표를 뽑을 특정 라벨 값(정수)
#     out_stl_path,
#     grid_step=6,                       # 샘플링 간격(voxel)
#     min_magnitude_mm=1.0,              # 최소 변위 크기(mm)
#     scale=1.0,                         # 벡터 길이 배율(시각화용)
#     shaft_radius=0.4, head_radius=1.0, head_ratio=0.28
# ):
#     # 1) 변형장 계산 (메모리)
#     def_img = get_deformation_field(fixed_img, result_transform_param)  # VectorImage
#     df_np   = itk.array_view_from_image(def_img)           # (z,y,x,3)
#     lab_np  = itk.array_view_from_image(deformed_label_img)# (z,y,x)

#     if df_np.shape[:3] != lab_np.shape:
#         raise ValueError("deformation field와 deformed_label_img의 격자(shape)가 다릅니다.")
    
#     phase_json = os.path.join(
#         os.path.dirname(os.path.dirname(out_stl_path)),  # 상위의 상위 폴더
#         "phaseInfo.json"
#     )
    
#     origin, spacing, direction_row, offset = load_phase_from_json(phase_json, "HVP")
#     Z, Y, X, _ = df_np.shape
#     parts = []
    
#     M_idx2phys = build_mat_from_itk(
#     def_img,
#     offset=offset,   # 필요 시 Phase JSON의 Offset을 넣어도 됨
#     include_spacing=True,
#     flip_yz=True,             # ← 여기서 yz 플립 적용
#     stride=1
# )    
#     # 2) 라벨 영역만 서브샘플링하며 화살표 생성
#     for k in range(0, Z, grid_step):
#         if not np.any(lab_np[k] == label_value):
#             continue
#         for j in range(0, Y, grid_step):
#             # 빠른 프루닝
#             if label_value not in lab_np[k, j]:
#                 continue
#             for i in range(0, X, grid_step):
#                 if lab_np[k, j, i] != label_value:
#                     continue
#                 vec = df_np[k, j, i].astype(np.float64)
#                 mag = float(np.linalg.norm(vec))
#                 if mag < min_magnitude_mm:
#                     continue
#                 start = index_to_physical(i, j, k, M_idx2phys)
#                 arrow = make_arrow_trimesh(
#                     start=start,
#                     vec=vec * scale,
#                     shaft_radius=shaft_radius,
#                     head_radius=head_radius,
#                     head_length_ratio=head_ratio
#                 )
#                 if arrow is not None:
#                     parts.append(arrow)

#     if not parts:
#         print(f"[WARN] 라벨={label_value} 에 해당하고 크기>{min_magnitude_mm}mm 인 변위가 없습니다.", file=sys.__stdout__)
#         return False

#     mesh = trimesh.util.concatenate(parts)
#     mesh.export(out_stl_path)
#     print(f"[SAVED] arrows STL -> {out_stl_path} (count={len(parts)})", file=sys.__stdout__)
#     return True

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
        self.m_inputNiftiContainer = None
        self.m_outputListWarpedNifti = None
        self.m_outputPath = ""
        self.m_inputDicomePath = ""
        self.m_organList = ["Gallbladder", "Liver", "kidney_right", "Stomach", "spleen", "adrenal_gland_right"]

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

        TargetPhase = None

        for inx in range(0, iRegInfoCnt):
            regInfo = self.InputOptionInfo.get_reginfo(inx)
            fixedTargetName = regInfo.Target
            targetNiftiInfo = self.InputNiftiContainer.find_nifti_info_list_by_name(
                fixedTargetName
            )
            TargetPhase = targetNiftiInfo[0].MaskInfo.Phase

            src = regInfo.Src
            srcNiftiInfo = self.InputNiftiContainer.find_nifti_info_list_by_name(src)
            srcPhase = srcNiftiInfo[0].MaskInfo.Phase
            
            if srcPhase == "MR":
                continue
            
            targetPhaseInfo = self.InputNiftiContainer.find_phase_info(
                            TargetPhase
                        )
            
            srcPhaseInfo = self.InputNiftiContainer.find_phase_info(
                            srcPhase
                        )
            
            srcPhaseInfo.m_origin = targetPhaseInfo.m_origin
            srcPhaseInfo.m_spacing = targetPhaseInfo.m_spacing
            srcPhaseInfo.m_direction = targetPhaseInfo.m_direction
            srcPhaseInfo.m_size = targetPhaseInfo.m_size
        
            

        if TargetPhase is None:
            print(f"not found registration target")
            return
        
        targetDicomNiftiPath = (
            str(self.OutputPath) + "/DICOM_" + TargetPhase + ".nii.gz"
        )
        if os.path.exists(targetDicomNiftiPath):
            pass
        else:
            targetDcmPath = os.path.join(self.InputDicomPath, TargetPhase)
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
            
            if srcPhase == TargetPhase:
                continue
            if srcPhase == "MR":
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
