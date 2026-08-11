'''
ReconTest.py

목적
----
Liver 마스크(nii.gz)를 여러 reconstruction 파라미터 조합으로 재구성하고,
각 결과 mesh 의 표면적(surface area)을 측정하여
목표 표면적(TARGET_AREA_CM2, 기본 1349 cm2, AVIEW 측정값)에 가장 가까운
파라미터 조합을 찾는다.

배경 (중요)
-----------
- AVIEW 가 보고하는 표면적(1349 cm2)은 marching cubes mesh 의 면적이 아니라
  "복셀의 노출면(staircase) 면적" 방식으로 측정된 값에 가깝다.
  (이 스크립트가 출력하는 voxel-face staircase 면적 참조 -> 실측 약 1360 cm2)
- marching cubes 는 복셀 모서리를 대각선으로 잘라 표면을 만들기 때문에
  스무딩/데시메이션을 모두 꺼도 면적이 staircase 값보다 낮게 나온다
  (이 마스크 기준 marching cubes 상한 약 1150~1165 cm2).
- 따라서 "1349 에 최대한 가깝게" = marching cubes 조합 중 면적이 가장 큰 조합을
  찾는 것이며, 그래도 남는 차이는 측정 방식 차이(staircase vs marching cubes)에서
  기인한다. 이 스크립트는 두 값을 함께 보여준다.

실행
----
conda 의 vtk + SimpleITK 가 있는 env 로 실행 (예: jh_test / regis_test)
    python Tool/centerline/ReconTest.py
'''

import sys
import os
import time
import itertools

import vtk
import SimpleITK as sitk

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileSolutionPath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileSolutionPath)

import AlgUtil.algVTK as algVTK


# ==========================================================================
# 설정
# ==========================================================================
MASK_PATH = "C:/Users/hutom/Desktop/jh_test/data/liver/surface_area_test/Liver.nii.gz"
TARGET_AREA_CM2 = 1349.0

# 결과 mesh 저장 여부 (가장 가까운 조합의 STL 을 저장)
SAVE_BEST_STL = True
BEST_STL_PATH = os.path.join(os.path.dirname(MASK_PATH), "Liver_best_recon.stl")

# --------------------------------------------------------------------------
# 파라미터 스윕 그리드
#   recon_marching_cube(vtkImg, stddev, contourS=0, contourE=contour,
#                       noi=laplacianIter, refa=laplacianRelax, deci,
#                       bGaussMarching=gaussian, npMatPhy=None, resamplingFactor)
#   면적을 키우는 방향: resampling factor 크게 / contour 낮게 / gaussian off /
#                     laplacian off / deci 0
#   factor 3 이상은 삼각형 수/메모리가 급격히 커지고 매우 느리다. 필요시 추가.
# --------------------------------------------------------------------------
GRID_RESAMPLING = [1, 2]           # 예: [1, 2, 3]
GRID_CONTOUR = [1, 5, 10, 20]      # 마스크가 0/255 이므로 iso 값(낮을수록 면적 증가)
GRID_GAUSSIAN = [False]            # 예: [False, True] (True 면 면적 감소)
GRID_GAUSS_STDDEV = [1.0]          # gaussian True 일 때만 의미
GRID_LAPLACIAN = [(0, 0.0)]        # (iterations, relaxation) - 예: [(0,0.0),(20,0.1)]
GRID_DECIMATION = [0.0]            # vtkQuadricDecimation target reduction (0~1)


# ==========================================================================
# 유틸
# ==========================================================================
def measure_area_cm2(polydata: vtk.vtkPolyData) -> float:
    '''mesh 표면적을 cm2 로 반환 (mesh 좌표는 mm 단위)'''
    if polydata is None or polydata.GetNumberOfPolys() == 0:
        return 0.0
    tri = vtk.vtkTriangleFilter()
    tri.SetInputData(polydata)
    tri.Update()
    mp = vtk.vtkMassProperties()
    mp.SetInputData(tri.GetOutput())
    mp.Update()
    return mp.GetSurfaceArea() / 100.0  # mm2 -> cm2


def voxel_face_area_cm2(maskPath: str) -> float:
    '''
    복셀의 노출면(staircase) 표면적. AVIEW 류 측정 방식의 참조값.
    경계 복셀에서 배경과 맞닿은 면의 넓이를 모두 더한다.
    '''
    img = sitk.ReadImage(maskPath)
    a = sitk.GetArrayFromImage(img) > 0          # (z, y, x)
    sx, sy, sz = img.GetSpacing()                # (x, y, z) mm

    area = 0.0
    # x 방향 면 (면 넓이 = sy*sz)
    area += (a[:, :, 1:] != a[:, :, :-1]).sum() * (sy * sz)
    area += (a[:, :, 0].sum() + a[:, :, -1].sum()) * (sy * sz)
    # y 방향 면 (면 넓이 = sx*sz)
    area += (a[:, 1:, :] != a[:, :-1, :]).sum() * (sx * sz)
    area += (a[:, 0, :].sum() + a[:, -1, :].sum()) * (sx * sz)
    # z 방향 면 (면 넓이 = sx*sy)
    area += (a[1:, :, :] != a[:-1, :, :]).sum() * (sx * sy)
    area += (a[0, :, :].sum() + a[-1, :, :].sum()) * (sx * sy)

    return float(area) / 100.0  # mm2 -> cm2


def run_recon(maskPath, resampling, contour, gaussian, gaussStddev, lapIter, lapRelax, deci):
    '''한 조합으로 재구성하고 polydata 반환'''
    vtkImg = algVTK.CVTK.image_data_load_from_nifti(maskPath)
    polydata = algVTK.CVTK.recon_marching_cube(
        vtkImg,
        gaussStddev,       # stddev
        0,                 # contourS
        contour,           # contourE
        lapIter,           # noi  (laplacian iterations)
        lapRelax,          # refa (laplacian relaxation)
        deci,              # vtkQuadricDecimation target reduction
        gaussian,          # bGaussMarching
        None,              # npMatPhy (면적은 회전/평행이동에 불변 -> None)
        resampling,        # resamplingFactor
    )
    return polydata


# ==========================================================================
# 메인
# ==========================================================================
def main():
    if not os.path.exists(MASK_PATH):
        print(f"[ERROR] mask not found: {MASK_PATH}")
        return

    img = algVTK.CVTK.image_data_load_from_nifti(MASK_PATH)
    print("=" * 78)
    print(f"mask          : {MASK_PATH}")
    print(f"dims          : {img.GetDimensions()}")
    print(f"spacing (mm)  : {img.GetSpacing()}")
    print(f"scalar range  : {img.GetScalarRange()}")
    print(f"target area   : {TARGET_AREA_CM2:.1f} cm2 (AVIEW)")
    print("=" * 78)

    # 참조: voxel-face staircase 면적 (AVIEW 측정 방식 근사)
    t = time.time()
    staircase = voxel_face_area_cm2(MASK_PATH)
    print(f"[reference] voxel-face staircase area = {staircase:.1f} cm2  "
          f"(AVIEW 방식 근사, {time.time()-t:.1f}s)")
    print(f"[reference] target - staircase diff   = {TARGET_AREA_CM2 - staircase:+.1f} cm2")
    print("-" * 78)

    # 파라미터 스윕
    combos = list(itertools.product(
        GRID_RESAMPLING, GRID_CONTOUR, GRID_GAUSSIAN,
        GRID_GAUSS_STDDEV, GRID_LAPLACIAN, GRID_DECIMATION))

    print(f"sweeping {len(combos)} combinations ...\n")
    results = []
    for i, (fac, contour, gauss, std, (lapIter, lapRelax), deci) in enumerate(combos):
        t = time.time()
        try:
            pd = run_recon(MASK_PATH, fac, contour, gauss, std, lapIter, lapRelax, deci)
            area = measure_area_cm2(pd)
            tris = pd.GetNumberOfPolys()
        except Exception as ex:
            print(f"  [{i+1}/{len(combos)}] FAILED "
                  f"fac={fac} contour={contour} gauss={gauss} lap=({lapIter},{lapRelax}) "
                  f"deci={deci} -> {ex}")
            continue

        diff = area - TARGET_AREA_CM2
        results.append(dict(
            factor=fac, contour=contour, gaussian=gauss, stddev=std,
            lapIter=lapIter, lapRelax=lapRelax, deci=deci,
            area=area, tris=tris, diff=diff, polydata=pd))
        print(f"  [{i+1}/{len(combos)}] "
              f"fac={fac} contour={contour:>3} gauss={int(gauss)} "
              f"lap=({lapIter},{lapRelax}) deci={deci} "
              f"-> area={area:7.1f} cm2  diff={diff:+7.1f}  "
              f"tris={tris:>9}  ({time.time()-t:.1f}s)")

    if not results:
        print("no results.")
        return

    # 목표에 가장 가까운 순으로 정렬
    results.sort(key=lambda r: abs(r["diff"]))

    print("\n" + "=" * 78)
    print(f"TOP results (closest to {TARGET_AREA_CM2:.1f} cm2)")
    print("=" * 78)
    print(f"{'rank':>4} {'factor':>6} {'contour':>7} {'gauss':>5} "
          f"{'lap(it,rx)':>12} {'deci':>5} {'area(cm2)':>10} {'diff':>8} {'tris':>10}")
    for rank, r in enumerate(results[:15], 1):
        print(f"{rank:>4} {r['factor']:>6} {r['contour']:>7} {int(r['gaussian']):>5} "
              f"{('('+str(r['lapIter'])+','+str(r['lapRelax'])+')'):>12} {r['deci']:>5} "
              f"{r['area']:>10.1f} {r['diff']:>+8.1f} {r['tris']:>10}")

    best = results[0]
    print("\n" + "-" * 78)
    print("BEST (marching cubes, closest to target):")
    print(f"  resampling factor : {best['factor']}")
    print(f"  contour (iso)     : {best['contour']}")
    print(f"  gaussian          : {best['gaussian']} (stddev {best['stddev']})")
    print(f"  laplacian         : iter={best['lapIter']}, relax={best['lapRelax']}")
    print(f"  decimation (deci) : {best['deci']}")
    print(f"  -> surface area   : {best['area']:.1f} cm2  (target {TARGET_AREA_CM2:.1f}, "
          f"diff {best['diff']:+.1f})")
    print(f"  -> triangles      : {best['tris']}")
    print("-" * 78)
    print("NOTE: staircase(=AVIEW 방식) 값과 marching cubes 값의 차이는 측정 방식 차이이며,")
    print("      marching cubes 로는 staircase 면적에 도달하기 어렵다.")
    print("=" * 78)

    if SAVE_BEST_STL:
        algVTK.CVTK.save_poly_data_stl(BEST_STL_PATH, best["polydata"])
        print(f"saved best mesh -> {BEST_STL_PATH}")


if __name__ == "__main__":
    main()
