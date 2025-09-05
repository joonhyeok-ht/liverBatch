import sys
import os

import numpy as np

import vtk
from vtkmodules.util import numpy_support

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(fileAbsPath)
import algLinearMath

'''
- remove_duplicated_vertex는 open3d에 비해 성능이 안 좋다.
'''

class CVTK :
    @staticmethod
    def make_line_strip_index(vertexCnt : int) :
        index = np.zeros((vertexCnt - 1, 2), dtype=np.uint32)
        for i in range(0, vertexCnt - 1) :
            index[i, 0 : 2] = np.array([i, i + 1])
        return index

    @staticmethod 
    def load_poly_data_stl(stlFullPath : str) -> vtk.vtkPolyData :
        if os.path.exists(stlFullPath) == False :
            return None
        
        reader = vtk.vtkSTLReader()
        reader.SetFileName(stlFullPath)
        reader.Update()
        return reader.GetOutput()
    @staticmethod 
    def load_poly_data_obj(objFullPath : str) -> vtk.vtkPolyData :
        if os.path.exists(objFullPath) == False :
            return None
        
        reader = vtk.vtkOBJReader()
        reader.SetFileName(objFullPath)
        reader.Update()
        return reader.GetOutput()
    @staticmethod 
    def save_poly_data_stl(stlFullPath : str, polyData : vtk.vtkPolyData) :
        writer = vtk.vtkSTLWriter()
        writer.SetFileName(stlFullPath)
        writer.SetInputData(polyData)
        writer.SetFileTypeToBinary()
        writer.Write()
    @staticmethod 
    def save_poly_data_obj(objFullPath : str, polyData : vtk.vtkPolyData):
        writer = vtk.vtkOBJWriter()
        writer.SetFileName(objFullPath)
        writer.SetInputData(polyData)
        writer.Write()

    @staticmethod 
    def create_poly_data_point(vertex : np.ndarray) -> vtk.vtkPolyData :
        points = vtk.vtkPoints()
        for v in vertex:
            points.InsertNextPoint(v)

        index = vtk.vtkCellArray()
        for i in range(points.GetNumberOfPoints()):
            index.InsertNextCell(1)
            index.InsertCellPoint(i)
        
        polyData = vtk.vtkPolyData()
        polyData.SetPoints(points)
        polyData.SetVerts(index)
        return polyData
    # @staticmethod 
    # def create_poly_data_triangle(vertex : np.ndarray, index : np.ndarray) -> vtk.vtkPolyData :
    #     points = vtk.vtkPoints()
    #     for v in vertex:
    #         points.InsertNextPoint(v)
        
    #     cells = vtk.vtkCellArray()

    #     for inx in index:
    #         triangle = vtk.vtkTriangle()
    #         for i in range(3):
    #             triangle.GetPointIds().SetId(i, inx[i])
    #         cells.InsertNextCell(triangle)
        
    #     polyData = vtk.vtkPolyData()
    #     polyData.SetPoints(points)
    #     polyData.SetPolys(cells)
    #     return polyData
    @staticmethod 
    def create_poly_data_triangle(vertex : np.ndarray, index : np.ndarray) -> vtk.vtkPolyData :
        # Vertex 설정
        vtk_points = vtk.vtkPoints()
        vtk_array = numpy_support.numpy_to_vtk(vertex, deep=True)  # float32 또는 float64 자동 변환됨
        vtk_points.SetData(vtk_array)

        # Cell 설정 (triangle 당 4개 원소: [3, pt0, pt1, pt2])
        n_tri = index.shape[0]
        cells_np = np.hstack([np.full((n_tri, 1), 3, dtype=np.int64), index.astype(np.int64)])
        cells_flat = cells_np.flatten()

        vtk_cells = vtk.vtkCellArray()
        vtk_id_array = numpy_support.numpy_to_vtkIdTypeArray(cells_flat, deep=True)
        vtk_cells.SetCells(n_tri, vtk_id_array)

        # PolyData 구성
        polyData = vtk.vtkPolyData()
        polyData.SetPoints(vtk_points)
        polyData.SetPolys(vtk_cells)

        return polyData
    @staticmethod 
    def create_poly_data_line(vertex : np.ndarray, index : np.ndarray) -> vtk.vtkPolyData :
        points = vtk.vtkPoints()
        for v in vertex:
            points.InsertNextPoint(v)
        
        cells = vtk.vtkCellArray()

        for inx in index:
            line = vtk.vtkLine()
            for i in range(2):
                line.GetPointIds().SetId(i, inx[i])
            cells.InsertNextCell(line)
        
        polyData = vtk.vtkPolyData()
        polyData.SetPoints(points)
        polyData.SetLines(cells)
        return polyData
    @staticmethod
    def create_poly_data_cube(size : np.ndarray) -> vtk.vtkPolyData :
        '''
        size : vec3 : (1, 3)
        '''
        cube = vtk.vtkCubeSource()
        cube.SetXLength(size[0, 0])
        cube.SetYLength(size[0, 1])
        cube.SetZLength(size[0, 2])
        cube.Update()

        triangleFilter = vtk.vtkTriangleFilter()
        triangleFilter.SetInputData(cube.GetOutput())
        triangleFilter.Update()
        return triangleFilter.GetOutput()
    @staticmethod
    def create_poly_data_sphere(pos : np.ndarray, radius : float) -> vtk.vtkPolyData :
        sphere = vtk.vtkSphereSource()
        sphere.SetCenter(pos[0, 0], pos[0, 1], pos[0, 2])
        sphere.SetRadius(radius)
        # sphere.SetThetaResolution(100)
        # sphere.SetPhiResolution(100)
        sphere.Update()
        return sphere.GetOutput()
    @staticmethod
    def create_spline_cylinder_by_vertex(vertex : np.ndarray, radius : float, capFlag=False, numSide=20) -> vtk.vtkPolyData :
        iVertexCnt = vertex.shape[0]
        vtk_points = vtk.vtkPoints()
        for i in range(iVertexCnt):
            vtk_points.InsertNextPoint(vertex[i])

        # VTK PolyLine 생성
        polyline = vtk.vtkPolyLine()
        polyline.GetPointIds().SetNumberOfIds(iVertexCnt)
        for i in range(iVertexCnt):
            polyline.GetPointIds().SetId(i, i)

        # PolyData에 Points와 PolyLine 추가
        lines = vtk.vtkCellArray()
        lines.InsertNextCell(polyline)

        curvePolyData = vtk.vtkPolyData()
        curvePolyData.SetPoints(vtk_points)
        curvePolyData.SetLines(lines)

        cylinder = vtk.vtkTubeFilter()
        cylinder.SetInputData(curvePolyData)
        cylinder.SetRadius(radius)
        cylinder.SetNumberOfSides(numSide)
        if capFlag == True :
            cylinder.CappingOn()
        else :
            cylinder.CappingOff()
        cylinder.Update()
        return cylinder.GetOutput()
    @staticmethod
    def create_spline_cylinder_with_vary_radius(vertex : np.ndarray, radius : np.ndarray, capFlag=False, numSide=20) -> vtk.vtkPolyData :
        iVertexCnt = vertex.shape[0]
        vtk_points = vtk.vtkPoints()
        for i in range(iVertexCnt):
            vtk_points.InsertNextPoint(vertex[i])

        # VTK PolyLine 생성
        polyline = vtk.vtkPolyLine()
        polyline.GetPointIds().SetNumberOfIds(iVertexCnt)
        for i in range(iVertexCnt):
            polyline.GetPointIds().SetId(i, i)

        lines = vtk.vtkCellArray()
        lines.InsertNextCell(polyline)

        curvePolyData = vtk.vtkPolyData()
        curvePolyData.SetPoints(vtk_points)
        curvePolyData.SetLines(lines)

        radiusArray = vtk.vtkDoubleArray()
        radiusArray.SetName("TubeRadius")
        radiusArray.SetNumberOfComponents(1)
        radiusArray.SetNumberOfTuples(iVertexCnt)
        for i in range(iVertexCnt) :
            radiusArray.SetTuple1(i, radius[i])

        curvePolyData.GetPointData().AddArray(radiusArray)
        curvePolyData.GetPointData().SetActiveScalars("TubeRadius") 

        cylinder = vtk.vtkTubeFilter()
        cylinder.SetInputData(curvePolyData)
        cylinder.SetVaryRadiusToVaryRadiusByAbsoluteScalar()
        cylinder.SetNumberOfSides(numSide)
        if capFlag == True :
            cylinder.CappingOn()
        else :
            cylinder.CappingOff()
        cylinder.Update()

        triangleFilter = vtk.vtkTriangleFilter()
        triangleFilter.SetInputConnection(cylinder.GetOutputPort())
        triangleFilter.Update()
        return triangleFilter.GetOutput()
        # return cylinder.GetOutput()
    @staticmethod
    def create_normal_polydata(polyData : vtk.vtkPolyData) -> vtk.vtkPolyData :
        if not polyData.GetPointData().GetNormals():
            raise None
        # 화살표 소스 생성
        arrow_source = vtk.vtkArrowSource()

        # Glyph3D로 노멀 벡터를 화살표로 시각화
        glyph = vtk.vtkGlyph3D()
        glyph.SetSourceConnection(arrow_source.GetOutputPort())
        glyph.SetInputData(polyData)
        glyph.SetVectorModeToUseNormal()
        glyph.SetScaleModeToScaleByVector()
        glyph.SetScaleFactor(0.5)
        glyph.Update()

        return glyph.GetOutput()


    @staticmethod
    def poly_data_set_color(polyData : vtk.vtkPolyData, color : np.ndarray) :
        '''
        color : 1 x 3 vector
        '''
        npVertex = CVTK.poly_data_get_vertex(polyData)
        npColor = np.zeros(npVertex.shape)
        vertexCnt = npVertex.shape[0]
        for i in range(0, vertexCnt) :
            npColor[i, 0] = color[0, 0]
            npColor[i, 1] = color[0, 1]
            npColor[i, 2] = color[0, 2]

        colorData = vtk.vtkUnsignedCharArray()
        colorData.SetNumberOfComponents(3)
        colorData.SetName("Colors")
        for c in npColor :
            colorData.InsertNextTuple3(int(c[0] * 255), int(c[1] * 255), int(c[2] * 255))
        polyData.GetPointData().SetScalars(colorData)
    @staticmethod
    def poly_data_set_normal(polyData : vtk.vtkPolyData, normal : np.ndarray) :
        normalData = vtk.vtkFloatArray()
        normalData.SetNumberOfComponents(3)
        normalData.SetName("Normals")
        for n in normal :
            normalData.InsertNextTuple(n)
        polyData.GetPointData().SetNormals(normalData)
    # @staticmethod
    # def poly_data_get_vertex(polyData : vtk.vtkPolyData) -> np.ndarray :
    #     pointCnt = polyData.GetNumberOfPoints()
    #     npVert = np.zeros((pointCnt, 3), dtype=np.float32)
    #     for i in range(pointCnt) :
    #         npVert[i] = polyData.GetPoint(i)
    #     return npVert
    # @staticmethod
    # def poly_data_get_triangle_index(polyData : vtk.vtkPolyData) -> np.ndarray :
    #     cellCnt = polyData.GetNumberOfCells()
    #     npInx = np.zeros((cellCnt, 3), dtype=np.uint)
    #     for i in range(cellCnt) :
    #         ids = polyData.GetCell(i).GetPointIds()
    #         for j in range(ids.GetNumberOfIds()) :
    #             npInx[i, j] = ids.GetId(j)
    #     return npInx
    @staticmethod
    def poly_data_get_vertex(polyData : vtk.vtkPolyData) -> np.ndarray :
        vtk_points = polyData.GetPoints().GetData()
        npVert = numpy_support.vtk_to_numpy(vtk_points)
        return npVert
    @staticmethod
    def poly_data_get_triangle_index(polyData : vtk.vtkPolyData) -> np.ndarray :
        cellArray = polyData.GetPolys()
        conn = numpy_support.vtk_to_numpy(cellArray.GetConnectivityArray())
        offsets = numpy_support.vtk_to_numpy(cellArray.GetOffsetsArray())
        npInx = conn.reshape(-1, 3)
        return npInx
    @staticmethod
    def poly_data_get_line_index(polyData : vtk.vtkPolyData) -> np.ndarray :
        cellCnt = polyData.GetNumberOfCells()
        npInx = np.zeros((cellCnt, 2), dtype=np.uint)
        for i in range(cellCnt) :
            ids = polyData.GetCell(i).GetPointIds()
            for j in range(ids.GetNumberOfIds()) :
                npInx[i, j] = ids.GetId(j)
        return npInx
    @staticmethod
    def poly_data_get_normal(polyData : vtk.vtkPolyData) -> np.ndarray :
        normal = polyData.GetPointData().GetNormals()
        npNormal = np.array([normal.GetTuple3(i) for i in range(normal.GetNumberOfTuples())], dtype=np.float32)
        return npNormal
    @staticmethod
    def poly_data_get_info_vertcellid_by_min_axis(polyData : vtk.vtkPolyData, axisIndex : int) -> tuple :
        '''
        axisIndex : 0 - x-axis
                    1 - y-axis
                    2 - z-axis
        ret : (vertexIndex, cellIDIndex)
        '''
        polyVertex = CVTK.poly_data_get_vertex(polyData)
        polyIndex = CVTK.poly_data_get_triangle_index(polyData)

        startVertexInx = np.argmin(polyVertex[ : , axisIndex])
        ret = np.where(polyIndex == startVertexInx)
        startCellInx = ret[0][0]

        return (startVertexInx, startCellInx)
    @staticmethod
    def poly_data_get_info_vertcellid_by_max_axis(polyData : vtk.vtkPolyData, axisIndex : int) -> tuple :
        '''
        axisIndex : 0 - x-axis
                    1 - y-axis
                    2 - z-axis
        ret : (vertexIndex, cellIDIndex)
        '''
        polyVertex = CVTK.poly_data_get_vertex(polyData)
        polyIndex = CVTK.poly_data_get_triangle_index(polyData)

        startVertexInx = np.argmax(polyVertex[ : , axisIndex])
        ret = np.where(polyIndex == startVertexInx)
        startCellInx = ret[0][0]

        return (startVertexInx, startCellInx)
        
    @staticmethod
    def poly_data_voxelize(polyData : vtk.vtkPolyData, voxelSize : tuple, voxelValue : float, margin : int = 3) -> tuple :
        '''
        ret : (npImg, origin, spacing, direction, size)
        '''
        bounds = polyData.GetBounds()

        # # 각 축의 크기 계산
        # xDim = int((bounds[1] - bounds[0]) / voxelSize[0])
        # yDim = int((bounds[3] - bounds[2]) / voxelSize[1])
        # zDim = int((bounds[5] - bounds[4]) / voxelSize[2])

        xDim = int((bounds[1] - bounds[0]) / voxelSize[0]) + 2 * margin
        yDim = int((bounds[3] - bounds[2]) / voxelSize[1]) + 2 * margin
        zDim = int((bounds[5] - bounds[4]) / voxelSize[2]) + 2 * margin

        # 새로운 원점을 기존 원점에서 margin 만큼 빼서 설정
        originX = bounds[0] - margin * voxelSize[0]
        originY = bounds[2] - margin * voxelSize[1]
        originZ = bounds[4] - margin * voxelSize[2]


        imageData = vtk.vtkImageData()
        imageData.SetDimensions(xDim, yDim, zDim)
        imageData.SetSpacing(voxelSize[0], voxelSize[1], voxelSize[2])
        # imageData.SetOrigin(bounds[0], bounds[2], bounds[4])  # 원점 설정
        imageData.SetOrigin(originX, originY, originZ)  # 원점 설정
        imageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)

        for z in range(zDim):
            for y in range(yDim):
                for x in range(xDim):
                    imageData.SetScalarComponentFromFloat(x, y, z, 0, voxelValue)
        
        polyToStencil = vtk.vtkPolyDataToImageStencil()
        polyToStencil.SetInputData(polyData)
        polyToStencil.SetOutputOrigin(imageData.GetOrigin())
        polyToStencil.SetOutputSpacing(imageData.GetSpacing())
        polyToStencil.SetOutputWholeExtent(imageData.GetExtent())
        polyToStencil.Update()

        stencil = vtk.vtkImageStencil()
        stencil.SetInputData(imageData)
        stencil.SetStencilData(polyToStencil.GetOutput())
        stencil.ReverseStencilOff()
        stencil.SetBackgroundValue(0)
        stencil.Update()

        stencilData = stencil.GetOutput()
        npImg = numpy_support.vtk_to_numpy(stencilData.GetPointData().GetScalars())
        npImg = npImg.reshape(zDim, yDim, xDim)  # z, y, x 순서로 배열 형태 맞추기
        npImg = np.transpose(npImg, (2, 1, 0))

        # origin = (bounds[0], bounds[2], bounds[4])
        origin = (originX, originY, originZ)
        spacing = (voxelSize[0], voxelSize[1], voxelSize[2])
        direction = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
        size = npImg.shape

        return (npImg, origin, spacing, direction, size)
    
    # image
    @staticmethod
    def image_data_load_from_nifti(niftiFullPath : str) -> vtk.vtkImageData :
        reader = vtk.vtkNIFTIImageReader()
        reader.SetFileName(niftiFullPath)
        reader.Update()
        return reader.GetOutput()
    @staticmethod
    def image_data_set_from_np(npImg : np.ndarray) -> vtk.vtkImageData :
        imageData = vtk.vtkImageData()
        imageData.SetDimensions(npImg.shape[0], npImg.shape[1], npImg.shape[2])
        vtkArray = numpy_support.numpy_to_vtk(num_array=npImg.ravel(), deep=True, array_type=vtk.VTK_TYPE_UINT8)
        imageData.GetPointData().SetScalars(vtkArray)
        return imageData
    @staticmethod
    def image_data_get_np(imageData : vtk.vtkImageData) -> np.ndarray :
        w, h, d = imageData.GetDimensions()
        scalars = imageData.GetPointData().GetScalars()
        npImg = np.array(scalars, dtype=np.uint8)
        npImg = npImg.reshape(w, h, d)
        return npImg
    

    # vtk physical matrix 
    @staticmethod
    def rot_from_row(listRot : tuple) :
        mat = np.array([
            [listRot[0], listRot[1], listRot[2], 0.0],
            [listRot[3], listRot[4], listRot[5], 0.0],
            [listRot[6], listRot[7], listRot[8], 0.0],
            [0.0, 0.0, 0.0, 1.0]
        ],
        dtype=np.float32
        )
        return mat
    @staticmethod
    def get_phy_matrix(origin, spacing, direction) :
        mat4Scale = algLinearMath.CScoMath.scale_mat4(algLinearMath.CScoMath.to_vec3([spacing[0], spacing[1], spacing[2]]))
        mat4Rot = CVTK.rot_from_row(direction)
        mat4Trans = algLinearMath.CScoMath.translation_mat4(algLinearMath.CScoMath.to_vec3([origin[0], origin[1], origin[2]]))
        retMat4 = algLinearMath.CScoMath.mul_mat4_mat4(mat4Rot, mat4Scale)
        retMat4 = algLinearMath.CScoMath.mul_mat4_mat4(mat4Trans, retMat4)
        return retMat4
    @staticmethod
    def get_phy_matrix_without_scale(origin, direction) :
        mat4Rot = CVTK.rot_from_row(direction)
        mat4Trans = algLinearMath.CScoMath.translation_mat4(algLinearMath.CScoMath.to_vec3([origin[0], origin[1], origin[2]]))
        retMat4 = algLinearMath.CScoMath.mul_mat4_mat4(mat4Trans, mat4Rot)
        return retMat4
    @staticmethod
    def get_vtk_phy_matrix_with_offset(origin, spacing, direction, offset : np.ndarray) :
        mat4Rot = CVTK.rot_from_row(direction)
        mat4Trans = algLinearMath.CScoMath.translation_mat4(algLinearMath.CScoMath.to_vec3([origin[0], origin[1], origin[2]]))
        mat4Offset = algLinearMath.CScoMath.translation_mat4(offset)
        mat4Flip = algLinearMath.CScoMath.scale_mat4(algLinearMath.CScoMath.to_vec3([1.0, -1.0, -1.0]))
        # mat4Flip = algLinearMath.CScoMath.scale_mat4(algLinearMath.CScoMath.to_vec3([-1.0, -1.0, 1.0]))

        mat4VTK = algLinearMath.CScoMath.mul_mat4_mat4(mat4Trans, mat4Rot)
        mat4VTK = algLinearMath.CScoMath.mul_mat4_mat4(mat4Offset, mat4VTK)
        mat4VTK = algLinearMath.CScoMath.mul_mat4_mat4(mat4Flip, mat4VTK)
        return mat4VTK
    @staticmethod
    def get_vtk_phy_matrix_with_spacing(origin, spacing, direction, offset : np.ndarray) :
        mat4Scale = algLinearMath.CScoMath.scale_mat4(algLinearMath.CScoMath.to_vec3([spacing[0], spacing[1], spacing[2]]))
        mat4Rot = CVTK.rot_from_row(direction)
        mat4Trans = algLinearMath.CScoMath.translation_mat4(algLinearMath.CScoMath.to_vec3([origin[0], origin[1], origin[2]]))
        mat4Offset = algLinearMath.CScoMath.translation_mat4(offset)
        mat4Flip = algLinearMath.CScoMath.scale_mat4(algLinearMath.CScoMath.to_vec3([1.0, -1.0, -1.0]))
        # mat4Flip = algLinearMath.CScoMath.scale_mat4(algLinearMath.CScoMath.to_vec3([-1.0, -1.0, 1.0]))

        mat4VTK = algLinearMath.CScoMath.mul_mat4_mat4(mat4Rot, mat4Scale)
        mat4VTK = algLinearMath.CScoMath.mul_mat4_mat4(mat4Trans, mat4VTK)
        mat4VTK = algLinearMath.CScoMath.mul_mat4_mat4(mat4Offset, mat4VTK)
        mat4VTK = algLinearMath.CScoMath.mul_mat4_mat4(mat4Flip, mat4VTK)
        return mat4VTK
    
    
    # reconstruction
    @staticmethod
    def recon_marching_cube(
                      vtkImgData : vtk.vtkImageData, 
                      stddev : float, contourS : int, contourE : int, 
                      noi : int, refa : float, deci : float,
                      bGaussMarching = True, npMatPhy = None, resamplingFactor = 1
                      ) -> vtk.vtkPolyData :
        inputData = vtkImgData
        if resamplingFactor > 1 :
            resampler = vtk.vtkImageResample()
            resampler.SetInputData(inputData)
            resampler.SetMagnificationFactors([resamplingFactor,resamplingFactor,resamplingFactor])
            resampler.Update()
            inputData = resampler.GetOutput()

        surf = None
        if bGaussMarching == True :
            gaussian = vtk.vtkImageGaussianSmooth()
            gaussian.SetInputData(inputData)
            gaussian.SetStandardDeviation(stddev)       #2dsmoothprop
            gaussian.Update()

            surf = vtk.vtkImageMarchingCubes()
            surf.SetInputData(gaussian.GetOutput())
            surf.SetValue(contourS, contourE)           #contourprop
            surf.ComputeNormalsOn()
            surf.Update()
            gaussian.GetOutput().ReleaseData()
        else :
            surf = vtk.vtkImageMarchingCubes()
            surf.SetInputData(inputData)
            surf.SetValue(contourS, contourE)           #contourprop
            surf.ComputeNormalsOn()
            surf.Update()

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
        return transFilter.GetOutput()
    @staticmethod
    def recon_marching_cube_pro(
                      vtkImgData : vtk.vtkImageData, 
                      stddev : float, contourS : int, contourE : int, 
                      noi : int, refa : float, deci : float,
                      bGaussMarching = True, npMatPhy = None, resamplingFactor = 1
                      ) -> vtk.vtkPolyData :
        inputData = vtkImgData
        if resamplingFactor > 1 :
            resampler = vtk.vtkImageResample()
            resampler.SetInputData(inputData)
            resampler.SetMagnificationFactors([resamplingFactor,resamplingFactor,resamplingFactor])
            resampler.Update()
            inputData = resampler.GetOutput()

        surf = None
        if bGaussMarching == True :
            gaussian = vtk.vtkImageGaussianSmooth()
            gaussian.SetInputData(inputData)
            gaussian.SetStandardDeviation(stddev)       #2dsmoothprop
            gaussian.Update()

            surf = vtk.vtkImageMarchingCubes()
            surf.SetInputData(gaussian.GetOutput())
            surf.SetValue(contourS, contourE)           #contourprop
            surf.ComputeNormalsOn()
            surf.Update()
            gaussian.GetOutput().ReleaseData()
        else :
            surf = vtk.vtkImageMarchingCubes()
            surf.SetInputData(inputData)
            surf.SetValue(contourS, contourE)           #contourprop
            surf.ComputeNormalsOn()
            surf.Update()

        decima = vtk.vtkDecimatePro()
        decima.SetInputData(surf.GetOutput())
        decima.SetTargetReduction(deci)             #decimaprop
        decima.PreserveTopologyOn()  # 토폴로지 보존
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
        return transFilter.GetOutput()
    @staticmethod
    def recon_fly_edge3d( 
                      vtkImgData : vtk.vtkImageData, 
                      stddev : float, contourS : int, contourE : int, 
                      noi : int, refa : float, deci : float, 
                      bGauss = True, npMatPhy = None, resamplingFactor = 1
                      ) -> vtk.vtkPolyData :
        inputData = vtkImgData
        if resamplingFactor > 1 :
            resampler = vtk.vtkImageResample()
            resampler.SetInputData(inputData)
            resampler.SetMagnificationFactors([resamplingFactor,resamplingFactor,resamplingFactor])
            resampler.Update()
            inputData = resampler.GetOutput()

        surf = None
        if bGauss == True :
            gaussian = vtk.vtkImageGaussianSmooth()
            gaussian.SetInputData(inputData)
            gaussian.SetStandardDeviation(stddev)       #2dsmoothprop
            gaussian.Update()

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
            surf.SetInputData(inputData)
            surf.ComputeNormalsOn()
            surf.ComputeGradientsOn()
            surf.InterpolateAttributesOn()
            surf.SetValue(contourS, contourE)
            surf.Update()

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
        return transFilter.GetOutput()
    @staticmethod
    def recon_fly_edge3d_pro( 
                      vtkImgData : vtk.vtkImageData, 
                      stddev : float, contourS : int, contourE : int, 
                      noi : int, refa : float, deci : float, 
                      bGauss = True, npMatPhy = None, resamplingFactor = 1
                      ) -> vtk.vtkPolyData :
        inputData = vtkImgData
        if resamplingFactor > 1 :
            resampler = vtk.vtkImageResample()
            resampler.SetInputData(inputData)
            resampler.SetMagnificationFactors([resamplingFactor,resamplingFactor,resamplingFactor])
            resampler.Update()
            inputData = resampler.GetOutput()

        surf = None
        if bGauss == True :
            gaussian = vtk.vtkImageGaussianSmooth()
            gaussian.SetInputData(inputData)
            gaussian.SetStandardDeviation(stddev)       #2dsmoothprop
            gaussian.Update()

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
            surf.SetInputData(inputData)
            surf.ComputeNormalsOn()
            surf.ComputeGradientsOn()
            surf.InterpolateAttributesOn()
            surf.SetValue(contourS, contourE)
            surf.Update()

        decima = vtk.vtkDecimatePro()
        decima.SetInputData(surf.GetOutput())
        decima.SetTargetReduction(deci)             #decimaprop
        decima.PreserveTopologyOn()  # 토폴로지 보존
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
        return transFilter.GetOutput()
    @staticmethod
    def recon_marching_cube_sharpness(
                      vtkImgData : vtk.vtkImageData, 
                      contourS : int, contourE : int, 
                      noi : int, reduction : float, sharpnessAngle : float, sharpnessNormalAngle : float,
                      npMatPhy = None
                      ) -> vtk.vtkPolyData :
        '''
        0, 10, 
        15, 0.1, 120.0, 30.0
        '''
        # Marching Cubes 알고리즘 적용
        marching_cubes = vtk.vtkMarchingCubes()
        marching_cubes.SetInputData(vtkImgData)
        marching_cubes.SetValue(contourS, contourE)  # 등고선 값 설정
        marching_cubes.Update()

        smoothing_filter = vtk.vtkWindowedSincPolyDataFilter()
        smoothing_filter.SetInputConnection(marching_cubes.GetOutputPort())
        smoothing_filter.SetNumberOfIterations(noi)        # 적절한 반복 횟수 설정
        smoothing_filter.BoundarySmoothingOff()             # 경계 스무딩 끄기
        smoothing_filter.FeatureEdgeSmoothingOff()          # 날카로운 엣지 스무딩 끄기
        smoothing_filter.SetFeatureAngle(sharpnessAngle)    # 날카로운 부분을 보존할 각도 설정
        smoothing_filter.Update()

        decimate = vtk.vtkQuadricDecimation()
        decimate.SetInputConnection(smoothing_filter.GetOutputPort())
        decimate.SetTargetReduction(reduction)             #decimaprop
        decimate.Update()

        normals = vtk.vtkPolyDataNormals()
        normals.SetInputConnection(decimate.GetOutputPort())
        normals.SetFeatureAngle(sharpnessNormalAngle)  # 각도가 작은 부분은 날카롭게 유지
        normals.SplittingOff()  # 법선 분할 비활성화
        normals.Update()
        # 출력 폴리곤 데이터
        sharpPolyData = normals.GetOutput()

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
        transFilter.SetInputData(sharpPolyData)
        transFilter.SetTransform(transForm)
        transFilter.Update()
        return transFilter.GetOutput()
    @staticmethod
    def recon_marching_cube_sharpness_pro(
                      vtkImgData : vtk.vtkImageData, 
                      contourS : int, contourE : int, 
                      noi : int, reduction : float, sharpnessAngle : float, sharpnessNormalAngle : float,
                      npMatPhy = None
                      ) -> vtk.vtkPolyData :
        '''
        0, 10, 
        15, 0.1, 120.0, 30.0
        '''
        # Marching Cubes 알고리즘 적용
        marching_cubes = vtk.vtkMarchingCubes()
        marching_cubes.SetInputData(vtkImgData)
        marching_cubes.SetValue(contourS, contourE)  # 등고선 값 설정
        marching_cubes.Update()

        smoothing_filter = vtk.vtkWindowedSincPolyDataFilter()
        smoothing_filter.SetInputConnection(marching_cubes.GetOutputPort())
        smoothing_filter.SetNumberOfIterations(noi)        # 적절한 반복 횟수 설정
        smoothing_filter.BoundarySmoothingOff()             # 경계 스무딩 끄기
        smoothing_filter.FeatureEdgeSmoothingOff()          # 날카로운 엣지 스무딩 끄기
        smoothing_filter.SetFeatureAngle(sharpnessAngle)    # 날카로운 부분을 보존할 각도 설정
        smoothing_filter.Update()

        decimate = vtk.vtkDecimatePro()
        decimate.SetInputConnection(smoothing_filter.GetOutputPort())
        decimate.SetTargetReduction(reduction)  # 10%만 줄이기
        decimate.PreserveTopologyOn()  # 토폴로지 보존
        decimate.Update()

        normals = vtk.vtkPolyDataNormals()
        normals.SetInputConnection(decimate.GetOutputPort())
        normals.SetFeatureAngle(sharpnessNormalAngle)  # 각도가 작은 부분은 날카롭게 유지
        normals.SplittingOff()  # 법선 분할 비활성화
        normals.Update()
        # 출력 폴리곤 데이터
        sharpPolyData = normals.GetOutput()

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
        transFilter.SetInputData(sharpPolyData)
        transFilter.SetTransform(transForm)
        transFilter.Update()
        return transFilter.GetOutput()

    # algorithm
    @staticmethod
    def poly_data_make_triangle(polyData : vtk.vtkPolyData) -> vtk.vtkPolyData :
        triangleFilter = vtk.vtkTriangleFilter()
        triangleFilter.SetInputData(polyData)
        triangleFilter.PassLinesOff()
        triangleFilter.PassVertsOff()
        triangleFilter.Update()
        return triangleFilter.GetOutput()
    @staticmethod
    def poly_data_remove_duplicated_vertex(polyData : vtk.vtkPolyData) -> vtk.vtkPolyData :
        cleaner = vtk.vtkCleanPolyData()
        cleaner.SetInputData(polyData)
        cleaner.SetTolerance(0.001)
        cleaner.Update()

        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(cleaner.GetOutput())
        normals.ComputePointNormalsOn()
        # normals.ComputeCellNormalsOff()
        normals.ComputeCellNormalsOn()
        normals.Update()
        return normals.GetOutput()
    @staticmethod
    def poly_data_clip(polyData : vtk.vtkPolyData, planeV : np.ndarray, planeNor : np.ndarray) -> vtk.vtkPolyData :
        plane = vtk.vtkPlane()
        plane.SetOrigin(planeV[0, 0], planeV[0, 1], planeV[0, 2])
        plane.SetNormal(planeNor[0, 0], planeNor[0, 1], planeNor[0, 2])

        clipper = vtk.vtkClipPolyData()
        clipper.SetInputData(polyData)
        clipper.SetClipFunction(plane)
        clipper.Update()
        return clipper.GetOutput()
    @staticmethod
    def poly_data_find_boundary_edge(polyData : vtk.vtkPolyData) -> vtk.vtkPolyData:
        fedges = vtk.vtkFeatureEdges()
        fedges.BoundaryEdgesOn()
        fedges.FeatureEdgesOff()
        fedges.ManifoldEdgesOff()
        fedges.SetInputData(polyData)
        fedges.Update()
        return fedges.GetOutput()


    def __init__(self) -> None:
        pass

