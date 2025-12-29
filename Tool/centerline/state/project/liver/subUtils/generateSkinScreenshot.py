import sys, os
import vtk
import numpy as np
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import AlgUtil.algVTK as algVTK
from vtk.util import numpy_support


def recon_fly_edge3d(
    vtkImgData: vtk.vtkImageData,
    stddev: float, contourS: int, contourE: int,
    noi: int, refa: float, deci: float,
    bGauss=True, npMatPhy=None, resamplingFactor=1
) -> vtk.vtkPolyData:

    inputData = vtkImgData
    if resamplingFactor and resamplingFactor > 1:
        resampler = vtk.vtkImageResample()
        resampler.SetInputData(inputData)
        resampler.SetMagnificationFactors(resamplingFactor, resamplingFactor, resamplingFactor)
        resampler.Update()
        inputData = resampler.GetOutput()

    if bGauss:
        gaussian = vtk.vtkImageGaussianSmooth()
        gaussian.SetInputData(inputData)
        gaussian.SetStandardDeviation(stddev) 
        gaussian.Update()
        srcImg = gaussian.GetOutput()
    else:
        srcImg = inputData

    surf = vtk.vtkFlyingEdges3D()
    surf.SetInputData(srcImg)
    surf.ComputeNormalsOn()
    surf.ComputeGradientsOn()
    surf.InterpolateAttributesOn()
    surf.SetValue(contourS, contourE)
    surf.Update()

    decima = vtk.vtkQuadricDecimation()
    decima.SetInputData(surf.GetOutput())
    decima.SetTargetReduction(deci)  
    decima.Update()

    smoother = vtk.vtkSmoothPolyDataFilter()
    smoother.SetInputData(decima.GetOutput())
    smoother.SetNumberOfIterations(noi)
    smoother.SetRelaxationFactor(refa)
    smoother.FeatureEdgeSmoothingOff()
    smoother.BoundarySmoothingOn()
    smoother.Update()

    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(smoother.GetOutput())
    normals.ConsistencyOn()
    normals.SplittingOff()
    normals.Update()

    return normals.GetOutput()

def capture_stl_orthographic_cropped(polyData, png_path, w=900, h=900, margin_px=12, pad_ratio=1.05):

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(polyData)

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(0.9, 0.9, 0.95)
    actor.GetProperty().SetInterpolationToPhong()

    # 2) Renderer / Window (transparent BG)
    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)
    renderer.SetBackground(1, 1, 1)
    renderer.SetBackgroundAlpha(0.0)

    renwin = vtk.vtkRenderWindow()
    renwin.AddRenderer(renderer)
    renwin.SetSize(w, h)
    renwin.SetAlphaBitPlanes(1)
    renwin.SetMultiSamples(0)
    renwin.OffScreenRenderingOn()

    # 3) Camera: ORTHOGRAPHIC
    renderer.ResetCamera()
    cam = renderer.GetActiveCamera()
    cam.SetParallelProjection(True)

    # 바라볼 방향: +Y 바깥에서 원점(모델 중심)을 본다
    bounds = actor.GetBounds()  # (xmin, xmax, ymin, ymax, zmin, zmax)
    cx = 0.5 * (bounds[0] + bounds[1])
    cy = 0.5 * (bounds[2] + bounds[3])
    cz = 0.5 * (bounds[4] + bounds[5])

    width_w  = bounds[1] - bounds[0]  # X 범위
    height_w = bounds[5] - bounds[4]  # Z 범위 (viewUp = Z 이므로 세로축)
    depth_y  = bounds[3] - bounds[2]  # Y 범위 (카메라 방향)

    # 카메라 배치(거리 자체는 orthographic에서 중요치 않지만 clipping에 필요)
    cam.SetFocalPoint(cx, cy, cz)
    cam.SetPosition(cx, cy - (depth_y + max(width_w, height_w)), cz)  # +Y 바깥
    cam.SetViewUp(0, 0, 1)

    # viewport 종횡비 고려해 평행 스케일 설정
    aspect = float(w) / float(h) if h > 0 else 1.0
    # 화면 세로(world)로 필요한 반경: max( Z범위/2, (X범위/aspect)/2 )
    needed_half_height = 0.5 * max(height_w, width_w / aspect)
    cam.SetParallelScale(needed_half_height * pad_ratio)

    renderer.ResetCameraClippingRange()
    renwin.Render()

    # 4) RGBA 캡처
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(renwin)
    w2i.SetInputBufferTypeToRGBA()
    w2i.ReadFrontBufferOff()
    w2i.Update()

    img = w2i.GetOutput()
    w0, w1, h0, h1, z0, z1 = img.GetExtent()
    width = w1 - w0 + 1
    height = h1 - h0 + 1

    # 5) 알파 마스크로 bbox 계산
    vtk_arr = img.GetPointData().GetScalars()
    np_rgba = numpy_support.vtk_to_numpy(vtk_arr).reshape(height, width, 4)
    alpha = np_rgba[:, :, 3]

    ys, xs = np.where(alpha > 0)
    if ys.size == 0 or xs.size == 0:
        # 오브젝트가 화면 밖이면 전체 저장
        clipped = img
    else:
        x_min = max(int(xs.min()) - margin_px, 0)
        x_max = min(int(xs.max()) + margin_px, width - 1)
        y_min = max(int(ys.min()) - margin_px, 0)
        y_max = min(int(ys.max()) + margin_px, height - 1)

        clip = vtk.vtkImageClip()
        clip.SetInputData(img)
        clip.SetOutputWholeExtent(x_min, x_max, y_min, y_max, 0, 0)
        clip.ClipDataOn()
        clip.Update()
        clipped = clip.GetOutput()

    # 6) PNG 저장 (투명 유지)
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(png_path)
    writer.SetInputData(clipped)
    writer.Write()
    
    
def generateSkinPng(skinNiftiFullPath):
    
    vtkImg = algVTK.CVTK.image_data_load_from_nifti(skinNiftiFullPath)
    
    iter_, rel_, deci_ = 16, 0.8, 0.01 
    resampling = 1                  
    iso_value = 10            
    gaussian_on = True    
    
    polyData = recon_fly_edge3d(
    vtkImg,
    stddev=1.0,
    contourS=0,          # iso 인덱스(보통 0)
    contourE=iso_value,  # iso 값
    noi=iter_,
    refa=rel_,
    deci=deci_,
    bGauss=gaussian_on,
    npMatPhy=None,
    resamplingFactor=resampling
    )
    
    capture_stl_orthographic_cropped(polyData, "skin.png", w=900, h=900, margin_px=12)
                 

# if __name__ == "__main__":
#     out_png = "skin.png"
    
    

#     capture_stl_orthographic_cropped(stl_path, out_png, w=900, h=900, margin_px=12)

#     # PySide6 미리보기
#     app = QApplication(sys.argv)
#     label = QLabel()
#     pixmap = QPixmap(out_png).scaled(600, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
#     label.setPixmap(pixmap)
#     label.setAlignment(Qt.AlignCenter)
#     label.setWindowTitle("STL Orthographic (Cropped, Transparent)")
#     label.resize(640, 640)
#     label.show()
#     sys.exit(app.exec())
