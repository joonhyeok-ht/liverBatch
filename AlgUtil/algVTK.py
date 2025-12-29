import sys
import os
import numpy as np

import SimpleITK as sitk

import vtk
from vtkmodules.util import numpy_support

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(fileAbsPath)
import algLinearMath
import algImage

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
    def load_poly_data_vtp(vtpFullPath : str) -> vtk.vtkPolyData :
        if os.path.exists(vtpFullPath) == False :
            return None
        
        reader = vtk.vtkXMLPolyDataReader()
        reader.SetFileName(vtpFullPath)
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
    def save_poly_data_vtp(vtpFullPath : str, polydata : vtk.vtkPolyData) :
        writer = vtk.vtkXMLPolyDataWriter()
        writer.SetInputData(polydata)
        writer.SetFileName(vtpFullPath)
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
    def create_poly_data_line_strip(vertex : np.ndarray) -> vtk.vtkPolyData :
        points = vtk.vtkPoints()
        lines = vtk.vtkCellArray()

        # 포인트 추가
        for p in vertex :
            points.InsertNextPoint(p)
        # LineStrip 생성
        lineStrip = vtk.vtkPolyLine()
        lineStrip.GetPointIds().SetNumberOfIds(len(vertex))
        for i in range(len(vertex)):
            lineStrip.GetPointIds().SetId(i, i)
        lines.InsertNextCell(lineStrip)

        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetLines(lines)
        return polydata
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

        cleaner = vtk.vtkCleanPolyData()
        cleaner.SetInputConnection(triangleFilter.GetOutputPort())
        cleaner.Update()

        return cleaner.GetOutput()
    @staticmethod
    def create_poly_data_sphere(pos : np.ndarray, radius : float, resolution=30) -> vtk.vtkPolyData :
        sphere = vtk.vtkSphereSource()
        sphere.SetCenter(pos[0, 0], pos[0, 1], pos[0, 2])
        sphere.SetRadius(radius)
        sphere.SetThetaResolution(resolution)
        sphere.SetPhiResolution(resolution)
        sphere.Update()

        triangle_filter = vtk.vtkTriangleFilter()
        triangle_filter.SetInputConnection(sphere.GetOutputPort())
        triangle_filter.Update()

        cleaner = vtk.vtkCleanPolyData()
        cleaner.SetInputConnection(triangle_filter.GetOutputPort())
        cleaner.Update()

        return cleaner.GetOutput()
    @staticmethod
    def create_poly_data_spheres(pos : np.ndarray, radius : float, resolution=30) -> vtk.vtkPolyData :
        cnt = pos.shape[0]
        append_filter = vtk.vtkAppendPolyData()
        for inx in range(0, cnt) :
            center = pos[inx].reshape(-1, 3)
            polydata = CVTK.create_poly_data_sphere(center, radius, resolution)
            append_filter.AddInputData(polydata)
        append_filter.Update()
        return append_filter.GetOutput()
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
    def create_wireframe_actor(
        polydata : vtk.vtkPolyData,
        color=(0.0, 0.0, 1.0),
        line_width=2.0,
        opacity=1.0
    ) -> vtk.vtkActor :
        vertex = CVTK.poly_data_get_vertex(polydata)
        index = CVTK.poly_data_get_triangle_index(polydata)
        copied_polydata = CVTK.create_poly_data_triangle(vertex, index)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(copied_polydata)
        mapper.SetResolveCoincidentTopologyToPolygonOffset()
        mapper.SetRelativeCoincidentTopologyPolygonOffsetParameters(1.0, 1.0)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetRepresentationToWireframe()
        actor.GetProperty().SetColor(color)
        actor.GetProperty().SetLineWidth(line_width)
        actor.GetProperty().SetOpacity(opacity)
        return actor
    @staticmethod
    def create_normal_actor(vertices : np.ndarray, normals : np.ndarray, scale=1.0) -> vtk.vtkActor :
        points = vtk.vtkPoints()
        for v in vertices:
            points.InsertNextPoint(v.tolist())

        # normals -> vtkFloatArray
        vtk_normals = vtk.vtkFloatArray()
        vtk_normals.SetNumberOfComponents(3)
        vtk_normals.SetName("Normals")
        for n in normals:
            vtk_normals.InsertNextTuple(n.tolist())

        # PolyData 생성
        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.GetPointData().SetNormals(vtk_normals)

        arrow_source = vtk.vtkArrowSource()

        glyph = vtk.vtkGlyph3D()
        glyph.SetSourceConnection(arrow_source.GetOutputPort())
        glyph.SetInputData(polydata)
        glyph.SetVectorModeToUseNormal()
        glyph.SetScaleFactor(scale)
        glyph.OrientOn()
        glyph.Update()

        # Mapper
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(glyph.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        return actor

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
    def poly_data_voxelize(polyData : vtk.vtkPolyData, voxelSize : tuple, voxelValue : float, margin=3) -> tuple :
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
    @staticmethod
    def poly_data_voxelize_to_phase(
            polydata : vtk.vtkPolyData,
            targetOrigin, targetSpacing, targetDirection, targetSize, targetOffset : np.ndarray,
            flipAxis=[1.0, -1.0, -1.0]
    ) -> np.ndarray :
        '''
        desc 
            - polydata를 원하는 phase로 voxelize 한다. 
        '''
        voxelSize = targetSpacing
        npImgDummy, originDummy, spacingDummy, directionDummy, sizeDummy = CVTK.poly_data_voxelize(polydata, voxelSize, 255.0)

        mat4Offset = algLinearMath.CScoMath.translation_mat4(targetOffset)
        mat4Flip = algLinearMath.CScoMath.scale_mat4(algLinearMath.CScoMath.to_vec3(flipAxis))
        resamplingTrans = algLinearMath.CScoMath.mul_mat4_mat4(mat4Flip, mat4Offset)

        # halfVoxel = np.array(spacingDummy) * 1.0
        # originDummy = tuple(np.array(originDummy) - halfVoxel)

        sitkSrc = algImage.CAlgImage.get_sitk_from_np(npImgDummy, originDummy, spacingDummy, directionDummy)
        sitkSrcResampled = algImage.CAlgImage.resampling_sitkimg_with_mat(
            sitkSrc, 
            targetOrigin, targetSpacing, targetDirection, targetSize, 
            sitkSrc.GetPixelID(), sitk.sitkNearestNeighbor, 
            resamplingTrans
            )
        
        npImgRet, originRet, scalingRet, directionRet, sizeRet = algImage.CAlgImage.get_np_from_sitk(sitkSrcResampled, np.uint8)
        return npImgRet
    

    # triangle polydata manipulation
    @staticmethod
    def get_sub_polydata(polyData : vtk.vtkPolyData) -> list :
        '''
        desc : polydata에서 분리된 영역, 각각의 polydata를 리스트 형태로 반환
               만약 없을 경우 None 반환
        '''
        connectivityFilter = vtk.vtkConnectivityFilter()
        connectivityFilter.SetInputData(polyData)
        connectivityFilter.SetExtractionModeToAllRegions()
        connectivityFilter.ColorRegionsOn()
        connectivityFilter.Update()

        labeledPolyData = connectivityFilter.GetOutput()
        numRegions = connectivityFilter.GetNumberOfExtractedRegions()

        listPolyData = []

        for regionId in range(numRegions):
            threshold = vtk.vtkThreshold()
            threshold.SetInputData(labeledPolyData)
            threshold.SetInputArrayToProcess(
                0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, "RegionId")
            
            # regionId만 걸러내기
            threshold.SetLowerThreshold(regionId)
            threshold.SetUpperThreshold(regionId)
            threshold.SetThresholdFunction(vtk.vtkThreshold.THRESHOLD_BETWEEN)
            threshold.Update()

            # PolyData로 변환
            surfaceFilter = vtk.vtkGeometryFilter()
            surfaceFilter.SetInputConnection(threshold.GetOutputPort())
            surfaceFilter.Update()

            region_polydata = surfaceFilter.GetOutput()
            listPolyData.append(region_polydata)
        
        if len(listPolyData) == 0 :
            return None
        return listPolyData
    @staticmethod
    def get_sub_polydata_by_face(polydata : vtk.vtkPolyData, listFaceID : list) -> vtk.vtkPolyData :
        '''
        desc : listFaceID 부분만 추출하여 polydata 생성 
        '''
        selected_cells = vtk.vtkCellArray()
        selected_points = vtk.vtkPoints()
        old_to_new_id = {}
        next_id = 0

        for cell_id in listFaceID :
            cell = polydata.GetCell(cell_id)
            pt_ids = cell.GetPointIds()

            new_cell_pt_ids = vtk.vtkIdList()

            for i in range(pt_ids.GetNumberOfIds()) :
                old_id = pt_ids.GetId(i)
                if old_id not in old_to_new_id :
                    new_id = next_id
                    old_to_new_id[old_id] = new_id
                    next_id += 1
                    selected_points.InsertNextPoint(polydata.GetPoint(old_id))
                else:
                    new_id = old_to_new_id[old_id]

                new_cell_pt_ids.InsertNextId(new_id)

            selected_cells.InsertNextCell(new_cell_pt_ids)

        new_polydata = vtk.vtkPolyData()
        new_polydata.SetPoints(selected_points)
        new_polydata.SetPolys(selected_cells)
        return new_polydata
    @staticmethod
    def get_sub_polydata_by_face_fast(polydata : vtk.vtkPolyData, listFaceID : list) -> vtk.vtkPolyData :
        ids = vtk.vtkIdList()
        for faceID in listFaceID :
            ids.InsertNextId(faceID)

        extractor = vtk.vtkExtractCells()
        extractor.SetInputData(polydata)
        extractor.SetCellList(ids)
        extractor.Update()

        geometry = vtk.vtkGeometryFilter()
        geometry.SetInputConnection(extractor.GetOutputPort())
        geometry.Update()

        return geometry.GetOutput()
    @staticmethod
    def get_sub_polydata_removing_face(polydata: vtk.vtkPolyData, cell_ids_to_remove: list) -> vtk.vtkPolyData:
        '''
        desc : cell_ids_remove face를 제거한 polydata 생성 
        '''
        copied_polydata = vtk.vtkPolyData()
        copied_polydata.DeepCopy(polydata)

        # 전체 셀 ID 목록 생성
        all_cell_ids = set(range(copied_polydata.GetNumberOfCells()))
        
        # 남길 셀 ID 목록 계산
        keep_cell_ids = list(all_cell_ids - set(cell_ids_to_remove))

        # VTK ID 리스트로 변환
        id_list = vtk.vtkIdList()
        for cid in keep_cell_ids :
            id_list.InsertNextId(cid)

        # 셀 추출기 초기화 및 설정
        extract_cells = vtk.vtkExtractCells()
        extract_cells.SetInputData(copied_polydata)
        extract_cells.SetCellList(id_list)
        extract_cells.Update()

        # 출력 polydata 가져오기
        geo_filter = vtk.vtkGeometryFilter()
        geo_filter.SetInputConnection(extract_cells.GetOutputPort())
        geo_filter.Update()

        triFilter = vtk.vtkTriangleFilter()
        triFilter.SetInputData(geo_filter.GetOutput())
        triFilter.Update()

        cleaner = vtk.vtkCleanPolyData()
        cleaner.SetInputData(triFilter.GetOutput())
        cleaner.Update()

        return cleaner.GetOutput()
    @staticmethod
    def get_boundary_vertinfo_manual(polydata : vtk.vtkPolyData) -> tuple :
        '''
        desc : boundary를 감지한 후 결과 반환 
        ret : ([vertexID0, vertexID1, ..], vertex : np.ndarray)
        '''
        edge_map = {}

        for i in range(polydata.GetNumberOfCells()) :
            cell = polydata.GetCell(i)
            pt_ids = [cell.GetPointId(j) for j in range(cell.GetNumberOfPoints())]
            for j in range(len(pt_ids)):
                edge = tuple(sorted((pt_ids[j], pt_ids[(j + 1) % len(pt_ids)])))
                edge_map[edge] = edge_map.get(edge, 0) + 1

        boundary_pts = set()
        for (p1, p2), count in edge_map.items() :
            if count == 1:
                boundary_pts.update([p1, p2])

        boundary_pts = list(boundary_pts)
        coords = np.array([polydata.GetPoint(pid) for pid in boundary_pts])
        return boundary_pts, coords
    @staticmethod
    def extract_faces_sharing_vertices(polydata : vtk.vtkPolyData, target_pt_ids : list) -> list :
        '''
        desc : vertexID와 연결된 faceID를 리턴
        ret : [faceID0, faceID1, .. ]
        '''
        if polydata.GetLinks() is None :
            polydata.BuildLinks()  # GetPointCells 사용을 위한 사전 구축
        used_cell_ids = set()

        for pt_id in target_pt_ids :
            cell_ids = vtk.vtkIdList()
            polydata.GetPointCells(pt_id, cell_ids)
            for i in range(cell_ids.GetNumberOfIds()) :
                used_cell_ids.add(cell_ids.GetId(i))
        
        return list(used_cell_ids)
    @staticmethod
    def extract_vertices_from_faces(polydata: vtk.vtkPolyData, target_face_ids: list) -> list :
        """
        desc : faceID 리스트가 참조하는 vertexID를 반환
        ret  : 중복 없는 vertexID 리스트
        """
        if polydata.GetLinks() is None :
            polydata.BuildLinks()  # GetPointCells 사용을 위한 사전 구축
        used_point_ids = set()

        id_list = vtk.vtkIdList()
        for cell_id in target_face_ids:
            polydata.GetCellPoints(cell_id, id_list)
            for i in range(id_list.GetNumberOfIds()):
                used_point_ids.add(id_list.GetId(i))

        return list(used_point_ids)
    @staticmethod
    def extract_connected_vertices(polydata: vtk.vtkPolyData, vertexID : int) -> list :
        '''
        desc : vertexID와 연결된 vertexID를 리턴
        ret : [vertexID0, vertexID1, .. ]
        '''
        if polydata.GetLinks() is None :
            polydata.BuildLinks()  # GetPointCells 사용을 위한 사전 구축
        connected_pt_ids = set()

        cell_ids = vtk.vtkIdList()
        polydata.GetPointCells(vertexID, cell_ids)

        for i in range(cell_ids.GetNumberOfIds()) :
            cell_id = cell_ids.GetId(i)
            cell = polydata.GetCell(cell_id)
            point_ids = cell.GetPointIds()

            for j in range(point_ids.GetNumberOfIds()) :
                neighbor_pt_id = point_ids.GetId(j)
                if neighbor_pt_id != vertexID :
                    connected_pt_ids.add(neighbor_pt_id)

        return list(connected_pt_ids)
    @staticmethod
    def check_in_polydata(polyData : vtk.vtkPolyData, vertex : np.ndarray) -> int :
        '''
        desc : polygon 내부에 존재하는 vertex들의 갯수 반환
        '''
        iCnt = vertex.shape[0]
        testPt = vtk.vtkPoints()
        for inx in range(0, iCnt) :
            testPt.InsertNextPoint(vertex[inx, 0], vertex[inx, 1], vertex[inx, 2])

        testPolyData = vtk.vtkPolyData()
        testPolyData.SetPoints(testPt)

        selEnPt = vtk.vtkSelectEnclosedPoints()
        selEnPt.SetSurfaceData(polyData)
        selEnPt.SetInputData(testPolyData)
        selEnPt.Update()

        retCnt = 0

        for i in range(testPt.GetNumberOfPoints()) :
            bInside = selEnPt.IsInside(i)
            if bInside == 1 :
                retCnt += 1

        return retCnt

    @staticmethod
    def get_intersecting_face(polydataA : vtk.vtkPolyData, polydataB : vtk.vtkPolyData) -> list :
        '''
        desc : polydataA의 face를 대상으로 polydataB와 교차된 face들을 추출
        '''
        obbTreeB = vtk.vtkOBBTree()
        obbTreeB.SetDataSet(polydataB)
        obbTreeB.BuildLocator()

        intersecting_cell_ids = []

        # polydataA의 각 cell에 대해
        for cellId in range(polydataA.GetNumberOfCells()):
            cell = polydataA.GetCell(cellId)
            points = cell.GetPoints()
            # 삼각형 면의 모든 edge를 선으로 놓고 polydataB와 교차 검사
            intersect_found = False
            for i in range(points.GetNumberOfPoints()):
                p1 = points.GetPoint(i)
                p2 = points.GetPoint((i + 1) % points.GetNumberOfPoints())

                # 두 점을 잇는 선분이 polydataB와 교차하는지 검사
                points_intersect = vtk.vtkPoints()
                obbTreeB.IntersectWithLine(p1, p2, points_intersect, None)
                if points_intersect.GetNumberOfPoints() > 0:
                    intersect_found = True
                    break

            if intersect_found:
                intersecting_cell_ids.append(cellId)

        return intersecting_cell_ids
    @staticmethod
    def polydata_subtract_with_nocap(polydataA : vtk.vtkPolyData, polydataB : vtk.vtkPolyData) -> vtk.vtkPolyData :
        '''
        desc : polydataA - polydataB 
               with no-cap
        '''
        findCellID = CVTK.get_intersecting_face(polydataA, polydataB)
        cuttedA = CVTK.get_sub_polydata_removing_face(polydataA, findCellID)
        listSubMesh = CVTK.get_sub_polydata(cuttedA)
        if listSubMesh is None :
            print("error : not found submesh")
            return None
        
        cuttedA = None
        for subMesh in listSubMesh :
            vertex = CVTK.poly_data_get_vertex(subMesh)
            cnt = CVTK.check_in_polydata(polydataB, vertex[0].reshape(-1, 3))
            if cnt < 1 :
                cuttedA = subMesh
        if cuttedA is None :
            print("error : not found cutted mesh")
            return None

        return cuttedA
    
    # smoothing
    @staticmethod
    def laplacian_smoothing(polydata : vtk.vtkPolyData, iter=20, relax=0.3) -> vtk.vtkPolyData :
        smoother = vtk.vtkSmoothPolyDataFilter()
        smoother.SetInputData(polydata)
        smoother.SetNumberOfIterations(iter)
        smoother.SetRelaxationFactor(relax)
        smoother.FeatureEdgeSmoothingOff()
        smoother.BoundarySmoothingOn()
        smoother.Update()
        return smoother.GetOutput()
    @staticmethod
    def laplacian_smoothing_selected(polydata : vtk.vtkPolyData, listVertexID : list, iter=20, relax=0.3) -> vtk.vtkPolyData :
        smoother = vtk.vtkSmoothPolyDataFilter()
        smoother.SetInputData(polydata)
        smoother.SetNumberOfIterations(iter)
        smoother.SetRelaxationFactor(relax)
        smoother.FeatureEdgeSmoothingOff()
        smoother.BoundarySmoothingOn()
        smoother.Update()

        smoothed = vtk.vtkPolyData()
        smoothed.DeepCopy(smoother.GetOutput())

        if listVertexID is not None and len(listVertexID) > 0 :
            original_points = vtk.vtkPoints()
            original_points.DeepCopy(polydata.GetPoints())

            # 선택되지 않은 vertex는 원래 좌표로 되돌리기
            for i in range(polydata.GetNumberOfPoints()):
                if i not in listVertexID:
                    smoothed.GetPoints().SetPoint(i, original_points.GetPoint(i))

            smoothed.GetPoints().Modified()
        return smoothed
    @staticmethod
    def winsinc_smoothing(polydata : vtk.vtkPolyData, listVertexID : list, iter=20, relax=0.3) -> vtk.vtkPolyData :
        """
        vtkWindowedSincPolyDataFilter를 이용해서
        선택된 vertex만 smoothing

        Parameters
        ----------
        polydata : vtk.vtkPolyData
            smoothing할 mesh
        target_ids : list[int]
            smoothing할 vertex index
        iterations : int
            반복 횟수
        relaxation : float
            smoothing 강도 (0~1)
        """
        # VTK Windowed Sinc smoother 생성
        smoother = vtk.vtkWindowedSincPolyDataFilter()
        smoother.SetInputData(polydata)
        smoother.SetNumberOfIterations(iter)
        smoother.BoundarySmoothingOff()
        smoother.FeatureEdgeSmoothingOff()
        smoother.NormalizeCoordinatesOn()
        smoother.SetPassBand(relax)
        smoother.Update()

        smoothed = vtk.vtkPolyData()
        smoothed.DeepCopy(smoother.GetOutput())

        if listVertexID is not None and len(listVertexID) > 0 :
            original_points = vtk.vtkPoints()
            original_points.DeepCopy(polydata.GetPoints())

            # 선택되지 않은 vertex는 원래 좌표로 되돌리기
            for i in range(polydata.GetNumberOfPoints()):
                if i not in listVertexID:
                    smoothed.GetPoints().SetPoint(i, original_points.GetPoint(i))

            smoothed.GetPoints().Modified()
        return smoothed

    # image
    @staticmethod
    def image_data_load_from_nifti(niftiFullPath : str) -> vtk.vtkImageData :
        reader = vtk.vtkNIFTIImageReader()
        reader.SetFileName(niftiFullPath)
        reader.Update()
        return reader.GetOutput()
    @staticmethod
    def image_data_set_from_np(npImg : np.ndarray, spacing=(1.0, 1.0, 1.0)) -> vtk.vtkImageData :
        # imageData = vtk.vtkImageData()
        # imageData.SetDimensions(npImg.shape[0], npImg.shape[1], npImg.shape[2])
        # vtkArray = numpy_support.numpy_to_vtk(num_array=npImg.ravel(), deep=True, array_type=vtk.VTK_TYPE_UINT8)
        # imageData.GetPointData().SetScalars(vtkArray)
        # return imageData
        flat = npImg.ravel(order='F')  # VTK는 column-major
        vtkDataArray = numpy_support.numpy_to_vtk(num_array=flat, deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)

        img = vtk.vtkImageData()
        img.SetDimensions(npImg.shape[::-1])  # (z, y, x) → (x, y, z)
        img.SetSpacing(spacing)
        img.GetPointData().SetScalars(vtkDataArray)
        return img

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
    def get_vtk_phy_matrix_with_offset(origin, spacing, direction, offset : np.ndarray, flipAxis=[1.0, -1.0, -1.0]) :
        mat4Rot = CVTK.rot_from_row(direction)
        mat4Trans = algLinearMath.CScoMath.translation_mat4(algLinearMath.CScoMath.to_vec3([origin[0], origin[1], origin[2]]))
        mat4Offset = algLinearMath.CScoMath.translation_mat4(offset)
        mat4Flip = algLinearMath.CScoMath.scale_mat4(algLinearMath.CScoMath.to_vec3(flipAxis))

        mat4VTK = algLinearMath.CScoMath.mul_mat4_mat4(mat4Trans, mat4Rot)
        mat4VTK = algLinearMath.CScoMath.mul_mat4_mat4(mat4Offset, mat4VTK)
        mat4VTK = algLinearMath.CScoMath.mul_mat4_mat4(mat4Flip, mat4VTK)
        return mat4VTK
    @staticmethod
    def get_vtk_phy_matrix_with_spacing(origin, spacing, direction, offset : np.ndarray, flipAxis=[1.0, -1.0, -1.0]) :
        mat4Scale = algLinearMath.CScoMath.scale_mat4(algLinearMath.CScoMath.to_vec3([spacing[0], spacing[1], spacing[2]]))
        mat4Rot = CVTK.rot_from_row(direction)
        mat4Trans = algLinearMath.CScoMath.translation_mat4(algLinearMath.CScoMath.to_vec3([origin[0], origin[1], origin[2]]))
        mat4Offset = algLinearMath.CScoMath.translation_mat4(offset)
        mat4Flip = algLinearMath.CScoMath.scale_mat4(algLinearMath.CScoMath.to_vec3(flipAxis))

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

