import sys
import os
import numpy as np
import shutil
import vtk
import subprocess

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PySide6.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.util import numpy_support

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algSegment as algSegment
import AlgUtil.algMeshLib as algMeshLib

import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.reconstruction as reconstruction

import data as data
import geometry as geometry

import commandInterface as commandInterface
import commandKnife as commandKnife
import curveInfo as curveInfo
# import territory as territory



class CCommandSepVessel(commandInterface.CCommand) :
    s_margin = 3.0

    @staticmethod
    def get_meshlib(vtkMeshInst : vtk.vtkPolyData) :
        npVertex = algVTK.CVTK.poly_data_get_vertex(vtkMeshInst)
        npIndex = algVTK.CVTK.poly_data_get_triangle_index(vtkMeshInst)
        meshLibInst = algMeshLib.CMeshLib.meshlib_create(npVertex, npIndex)
        return meshLibInst
    @staticmethod
    def get_vtkmesh(meshlibInst) -> vtk.vtkPolyData :
        npVertex = algMeshLib.CMeshLib.meshlib_get_vertex(meshlibInst)
        npIndex = algMeshLib.CMeshLib.meshlib_get_index(meshlibInst)
        vtkMesh = algVTK.CVTK.create_poly_data_triangle(npVertex, npIndex)
        return vtkMesh
    @staticmethod
    def find_polydata_include_vertex(listPolyData : list, vertex : np.ndarray) -> vtk.vtkPolyData :
        '''
        desc : polydata 리스트에서 vertex들을 포함하는 polydata를 반환한다.
               포함되는것이 없다면 None을 반환,
               vertex들이 여러개의 polydata 내부에 걸쳐 있다면 가장 많이 포함되는 polydata 리턴
        '''
        maxInx = -1
        maxCnt = 0
        for inx, subPolyData in enumerate(listPolyData) :
            nowCnt = CCommandSepVessel.check_in_polydata(subPolyData, vertex)
            if  nowCnt > maxCnt :
                maxInx = inx
                maxCnt = nowCnt
        
        if maxInx == -1 :
            return None
        return listPolyData[maxInx]
    @staticmethod
    def get_sub_polydata_count(polyData : vtk.vtkPolyData) -> int :
        '''
        desc : polydata에서 분리된 영역의 갯수 리턴
        '''
        connectivityFilter = vtk.vtkConnectivityFilter()
        connectivityFilter.SetInputData(polyData)
        connectivityFilter.SetExtractionModeToAllRegions()
        connectivityFilter.ColorRegionsOn()
        connectivityFilter.Update()

        labeledPolyData = connectivityFilter.GetOutput()
        numRegions = connectivityFilter.GetNumberOfExtractedRegions()
        return numRegions
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
    def dilation_polydata(polyData : vtk.vtkPolyData, scale : float = 1.0) -> vtk.vtkPolyData :
        '''
        desc : polyData를 scale 만큼 확장 (normal vector 기준)
        '''
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(polyData)
        normals.ComputePointNormalsOn()
        normals.Update()

        points = normals.GetOutput().GetPoints()
        normalsArray = normals.GetOutput().GetPointData().GetNormals()

        newPoints = vtk.vtkPoints()
        for i in range(points.GetNumberOfPoints()):
            p = points.GetPoint(i)
            n = normalsArray.GetTuple(i)
            moved = [p[j] + scale * n[j] for j in range(3)]
            newPoints.InsertNextPoint(moved)

        dilatedPoly = vtk.vtkPolyData()
        dilatedPoly.DeepCopy(polyData)
        dilatedPoly.SetPoints(newPoints)
        return dilatedPoly
    @staticmethod
    def dilation_polydata2(polydata : vtk.vtkPolyData, scale : float = 1.0) -> vtk.vtkPolyData :
        '''
        desc : polyData를 scale 만큼 확장 (normal vector 기준)
        '''
        # 1. Get points as NumPy array
        points = polydata.GetPoints()
        np_points = numpy_support.vtk_to_numpy(points.GetData())

        # 2. Compute center (mean of all points)
        center = np.mean(np_points, axis=0)

        # 3. Compute direction vectors and normalize
        vectors = np_points - center
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # To avoid division by zero
        unit_vectors = vectors / norms

        # 4. Apply dilation
        dilated_points = np_points + scale * unit_vectors

        # 5. Convert back to vtkPoints
        vtk_dilated_points = vtk.vtkPoints()
        vtk_dilated_points.SetData(numpy_support.numpy_to_vtk(dilated_points))

        # 6. Create new PolyData with updated points
        dilated_polydata = vtk.vtkPolyData()
        dilated_polydata.DeepCopy(polydata)
        dilated_polydata.SetPoints(vtk_dilated_points)

        return dilated_polydata
    @staticmethod
    def triangle_filter(polydata : vtk.vtkPolyData) -> vtk.vtkPolyData :
        triangle_filter = vtk.vtkTriangleFilter()
        triangle_filter.SetInputData(polydata)
        triangle_filter.Update()
        return triangle_filter.GetOutput()
    @staticmethod
    def merge_vtkmesh(polydata0 : vtk.vtkPolyData, polydata1 : vtk.vtkPolyData, tolerance=1e-6) : 
        append = vtk.vtkAppendPolyData()
        append.AddInputData(polydata0)
        append.AddInputData(polydata1)
        append.Update()

        cleaner = vtk.vtkCleanPolyData()
        cleaner.SetInputData(append.GetOutput())
        cleaner.SetTolerance(tolerance) 
        cleaner.PointMergingOn()
        cleaner.Update()
        return cleaner.GetOutput()
    @staticmethod
    def face_key(polydata, cell_id) :
        cell = polydata.GetCell(cell_id)
        pts = cell.GetPoints()
        coords = sorted([tuple(np.round(pts.GetPoint(i), 2)) for i in range(pts.GetNumberOfPoints())])
        return tuple(coords)
    # def face_key(polydata, cell_id):
    #     cell = polydata.GetCell(cell_id)
    #     ids = cell.GetPointIds()
    #     coords = sorted([
    #         tuple(np.round(polydata.GetPoint(ids.GetId(i)), 4)) 
    #         for i in range(ids.GetNumberOfIds())
    #     ])
    #     return tuple(coords)
    @staticmethod
    def remove_duplicate_faces(polydata) :
        face_dict = {}
        to_remove = set()

        num_cells = polydata.GetNumberOfCells()
        for i in range(num_cells):
            key = CCommandSepVessel.face_key(polydata, i)
            if key in face_dict:
                to_remove.add(i)
                to_remove.add(face_dict[key])
            else:
                face_dict[key] = i

        # 새로운 polygon 만들기 (중복 아닌 것만)
        new_polys = vtk.vtkCellArray()
        for i in range(num_cells):
            if i in to_remove:
                continue
            cell = polydata.GetCell(i)
            ids = cell.GetPointIds()
            new_polys.InsertNextCell(ids)

        # 새 PolyData 생성
        new_polydata = vtk.vtkPolyData()
        new_polydata.SetPoints(polydata.GetPoints())
        new_polydata.SetPolys(new_polys)

        return new_polydata

    
    def __init__(self, mediator) :
        super().__init__(mediator)
        self.m_inputSkeleton = None
        self.m_inputMeshLibWholeVessel = None

        self.m_outputCLID = -1
        self.m_outputVertexInx = -1
        self.m_outputWhole = None
        self.m_outputSub = None

        self.m_npCheckVertx = None
    def clear(self) :
        super().clear()
    def process(self) :
        super().process()
        self.m_outputCLID = -1
        self.m_outputVertexInx = -1
        self.m_outputWhole = None
        self.m_outputSub = None

        self.m_npCheckVertx = None


    def _process_sub(self, clID : int, vertexIndex : int, clCurve : curveInfo.CCLCurve) -> tuple :
        cl =  self.InputSkeleton.get_centerline(clID)

        tangent = clCurve.m_npZCoord[vertexIndex]
        pos = cl.get_vertex(vertexIndex)
        radius = cl.Radius[vertexIndex]

        retGuide = self._get_separated_guide_polydata(pos, tangent, radius + CCommandSepVessel.s_margin)
        if retGuide is None :
            print("failed to create guide mesh")
            return None
        
        return self._process_sub_with_guide(clID, vertexIndex, retGuide[0], retGuide[1])
    def _process_sub_with_guide(self, clID : int, vertexIndex : int, retGuide0 : vtk.vtkPolyData, retGuide1 : vtk.vtkPolyData) -> tuple :
        subGuide0 = retGuide0
        subGuide1 = retGuide1
        cl =  self.InputSkeleton.get_centerline(clID)

        listGuideSub = [subGuide0, subGuide1]
        selGuideSub = CCommandSepVessel.find_polydata_include_vertex(listGuideSub, cl.Vertex[vertexIndex : ].reshape(-1, 3))
        nonSelGuideSub = CCommandSepVessel.find_polydata_include_vertex(listGuideSub, cl.Vertex[ : vertexIndex].reshape(-1, 3))

        meshLibVessel = self.m_inputMeshLibWholeVessel
        meshLibSelSub = CCommandSepVessel.get_meshlib(selGuideSub)
        meshLibNonSelSub = CCommandSepVessel.get_meshlib(nonSelGuideSub)

        meshLibSelSub = self._get_enhanced_selsub(meshLibVessel, meshLibSelSub, cl.Vertex[vertexIndex : ].reshape(-1, 3))
        if meshLibSelSub is None :
            print("failed to create enhanced selection sub guide")
            return None
        
        meshLibSelSub = algMeshLib.CMeshLib.meshlib_healing(meshLibSelSub)
        meshLibNonSelSub = algMeshLib.CMeshLib.meshlib_healing(meshLibNonSelSub)

        meshLibWhole = algMeshLib.CMeshLib.meshlib_boolean_subtraction(meshLibVessel, meshLibSelSub)
        meshLibSub = algMeshLib.CMeshLib.meshlib_boolean_subtraction(meshLibVessel, meshLibNonSelSub)

        if meshLibWhole is None :
            print("meshLibWhole is None")
            return None
        if meshLibSub is None :
            print("meshLibSub is None")
            return None

        # find sub
        sub = CCommandSepVessel.get_vtkmesh(meshLibSub)
        listRet = CCommandSepVessel.get_sub_polydata(sub)
        if listRet is None :
            print("not found sub subpolydata")
            return None
        if len(listRet) <= 1 :
            print(f"invalid sub count : {len(listRet)}")
            return None
        sub = CCommandSepVessel.find_polydata_include_vertex(listRet, cl.Vertex[vertexIndex : ].reshape(-1, 3))
        if sub is None :
            print("not found sub")
            return None
        if self._check_valid_sub(sub, clID) == False :
            return None

        # find whole
        whole = CCommandSepVessel.get_vtkmesh(meshLibWhole)
        listRet = CCommandSepVessel.get_sub_polydata(whole)
        if listRet is None :
            print("not found whole subpolydata")
            return None
        whole = CCommandSepVessel.find_polydata_include_vertex(listRet, cl.Vertex[ : vertexIndex].reshape(-1, 3))
        if whole is None :
            print("not found whole")
            return None
        
        return (whole, sub)
    
    def _check_valid_cut(self, clID : int, vertexIndex : int, clCurve : curveInfo.CCLCurve) -> bool :
        cl =  self.InputSkeleton.get_centerline(clID)

        tangent = clCurve.m_npZCoord[vertexIndex]
        pos = cl.get_vertex(vertexIndex)
        radius = cl.Radius[vertexIndex]

        retGuide = self._get_separated_guide_polydata(pos, tangent, radius + CCommandSepVessel.s_margin)
        if retGuide is None :
            print("failed to create guide mesh")
            return False
        subGuide0 = retGuide[0]
        subGuide1 = retGuide[1]

        listGuideSub = [subGuide0, subGuide1]
        # selGuideSub = CCommandSepVessel.find_polydata_include_vertex(listGuideSub, cl.Vertex[vertexIndex : ].reshape(-1, 3))
        nonSelGuideSub = CCommandSepVessel.find_polydata_include_vertex(listGuideSub, cl.Vertex[ : vertexIndex].reshape(-1, 3))

        meshLibVessel = self.m_inputMeshLibWholeVessel
        meshLibNonSelSub = CCommandSepVessel.get_meshlib(nonSelGuideSub)
        meshLibNonSelSub = algMeshLib.CMeshLib.meshlib_healing(meshLibNonSelSub)

        meshLibSub = algMeshLib.CMeshLib.meshlib_boolean_subtraction(meshLibVessel, meshLibNonSelSub)
        if meshLibSub is None :
            print("meshLibSub is None")
            return False
        
        sub = CCommandSepVessel.get_vtkmesh(meshLibSub)
        listRet = CCommandSepVessel.get_sub_polydata(sub)
        if listRet is None :
            print("not found sub subpolydata")
            return False
        if len(listRet) <= 1 :
            print(f"invalid sub count : {len(listRet)}")
            return False

        return True
    def _check_valid_sub(self, subVessel : vtk.vtkPolyData, clID) -> bool :
        # connIDs = self.InputSkeleton.get_conn_centerline_id(clID)

        # # root가 분리될 일은 없다.
        # parentCLID = connIDs[0]
        # if parentCLID == -1 :
        #     return True
        
        # connIDs = self.InputSkeleton.get_conn_centerline_id(parentCLID)
        # listChild = connIDs[1]
        # cl = self.InputSkeleton.get_centerline(parentCLID)
        # vertex = cl.Vertex.copy()

        # for childCLID in listChild :
        #     if childCLID == clID :
        #         continue
        #     cl = self.InputSkeleton.get_centerline(childCLID)
        #     vertex = np.concatenate((vertex, cl.Vertex), axis=0)
        # nowCnt = CCommandSepVessel.check_in_polydata(subVessel, vertex)

        if self.m_npCheckVertx is None :
            return True
        nowCnt = CCommandSepVessel.check_in_polydata(subVessel, self.m_npCheckVertx)
        return nowCnt < 1



    def _get_separated_guide_polydata(self, pt : np.ndarray, tangent : np.ndarray, radius) :
        guidePolyData = self._create_guide_polydata(pt, radius)
        retList = self._get_separated_polydata_by_plane(guidePolyData, pt, tangent)
        if retList is None :
            return None
        return (retList[0], retList[1])
    def _create_guide_polydata(self, pos: np.ndarray, radius: float) -> vtk.vtkPolyData:
        centerX = pos[0, 0]
        centerY = pos[0, 1]
        centerZ = pos[0, 2]

        sphereSource = vtk.vtkSphereSource()
        sphereSource.SetCenter(centerX, centerY, centerZ)
        sphereSource.SetRadius(radius)
        sphereSource.SetThetaResolution(32)
        sphereSource.SetPhiResolution(32)
        sphereSource.Update()

        triangleFilter = vtk.vtkTriangleFilter()
        triangleFilter.SetInputData(sphereSource.GetOutput())
        triangleFilter.Update()

        clean = vtk.vtkCleanPolyData()
        clean.SetInputData(triangleFilter.GetOutput())
        clean.Update()

        return clean.GetOutput()
    def _get_separated_polydata_by_plane(self, polyData : vtk.vtkPolyData, planePt : np.ndarray, planeNormal : np.ndarray) -> tuple :
        '''
        ret : (subPolyData0, subPolyData1)
        '''
        listPlane = []
        retList = []

        planePt = planePt.reshape(-1)
        normal = planeNormal.reshape(-1)

        plane = vtk.vtkPlane()
        plane.SetOrigin(planePt[0], planePt[1], planePt[2])
        plane.SetNormal(normal[0], normal[1], normal[2])
        listPlane.append(plane)

        plane = vtk.vtkPlane()
        normal = planeNormal.reshape(-1)
        plane.SetOrigin(planePt[0], planePt[1], planePt[2])
        plane.SetNormal(-normal[0], -normal[1], -normal[2])
        listPlane.append(plane)

        for plane in listPlane :
            planeCollection = vtk.vtkPlaneCollection()
            planeCollection.AddItem(plane)

            clipper = vtk.vtkClipClosedSurface()
            clipper.SetInputData(polyData)
            clipper.SetClippingPlanes(planeCollection)
            clipper.SetGenerateFaces(True)
            clipper.Update()

            triangleFilter = vtk.vtkTriangleFilter()
            triangleFilter.SetInputData(clipper.GetOutput())
            triangleFilter.Update()

            retList.append(triangleFilter.GetOutput())
        if len(retList) == 0 :
            return None
        return retList
    def _get_enhanced_selsub(self, meshLibVessel, meshLibSelSub, selsubVertex : np.ndarray) :
        meshLibIntersected = algMeshLib.CMeshLib.meshlib_boolean_intersection(meshLibVessel, meshLibSelSub)
        intersected = CCommandSepVessel.get_vtkmesh(meshLibIntersected)
        listSubPolyData = CCommandSepVessel.get_sub_polydata(intersected)
        if listSubPolyData is None :
            return None
        
        iSubCnt = len(listSubPolyData)
        if iSubCnt == 1 :
            return meshLibSelSub
        
        exceptionPolyData = CCommandSepVessel.find_polydata_include_vertex(listSubPolyData, selsubVertex)
        if exceptionPolyData is None :
            return None
        
        for subPolyData in listSubPolyData :
            if subPolyData == exceptionPolyData : 
                continue

            subPolyData = CCommandSepVessel.dilation_polydata(subPolyData, 1.0)
            meshLibSubPolyData = CCommandSepVessel.get_meshlib(subPolyData)
            meshLibSubPolyData = algMeshLib.CMeshLib.meshlib_healing(meshLibSubPolyData)
            meshLibSelSub = algMeshLib.CMeshLib.meshlib_boolean_subtraction(meshLibSelSub, meshLibSubPolyData)
        return meshLibSelSub


    @property
    def InputSkeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_inputSkeleton
    @InputSkeleton.setter
    def InputSkeleton(self, inputSkeleton : algSkeletonGraph.CSkeleton) :
        self.m_inputSkeleton = inputSkeleton
    @property
    def InputMeshLibWholeVessel(self) :
        return self.m_inputMeshLibWholeVessel
    @InputMeshLibWholeVessel.setter
    def InputMeshLibWholeVessel(self, inputMeshLibWholeVessel) :
        self.m_inputMeshLibWholeVessel = inputMeshLibWholeVessel

    @property
    def OutputCLID(self) -> int :
        return self.m_outputCLID
    @property
    def OutputVertexInx(self) -> int :
        return self.m_outputVertexInx
    @property
    def OutputWhole(self) -> vtk.vtkPolyData :
        return self.m_outputWhole
    @property
    def OutputSub(self) -> vtk.vtkPolyData :
        return self.m_outputSub
    

class CCommandSepVesselPick(CCommandSepVessel) :
    def __init__(self, mediator):
        super().__init__(mediator)
        self.m_inputCLID = -1

    def clear(self) :

        super().clear()
    def process(self) :
        super().process()

        cl = self.InputSkeleton.get_centerline(self.m_inputCLID)
        clCurve = curveInfo.CCLCurve(cl)
        iCnt = cl.get_vertex_count()
        outSideIndex = self._find_outsideinx(self.m_inputCLID)

        # 이 부분에서 tracking 방향을 정해야 한다.
        # state : 0 -> 거슬러 올라감
        # state : 1 -> 거슬러 내려감 
        startIndex = 0

        # 마지막 지점이 포인트일 경우 거슬러 올라간다. 
        # 마지막 포인트만 벗어난 경우 or 모든 vertex가 parent radius 범위 내에 있을 경우 
        # 마지막 지점은 계산에서 제외한다. 
        if outSideIndex == iCnt - 1 or outSideIndex == -1 : 
            # centerline이 너무 짧아 parent radius에 centerline point들이 포함되어 버린 경우
            pass
            # startIndex = 1
            # self._state_1(self.m_inputCLID, startIndex, clCurve)
        else :
            startIndex = outSideIndex
            # bRet = self._check_valid_cut(self.m_inputCLID, startIndex, clCurve)
            # if bRet == True :
            #     if startIndex - 1 > 0 :
            #         self._state_0(self.m_inputCLID, startIndex - 1, clCurve)
            #     else :
            #         self._state_0(self.m_inputCLID, startIndex, clCurve)
            # else :

            listCL = self.InputSkeleton.find_descendant_centerline_by_centerline_id(self.InputCLID)
            listCLID = [clID for clID in listCL]
            listCheckedCLID = [clID for clID in range(0, self.InputSkeleton.get_centerline_count()) if clID not in listCLID]

            vertex = None
            for childCLID in listCheckedCLID :
                cl = self.InputSkeleton.get_centerline(childCLID)
                if self.m_npCheckVertx is None :
                    vertex = cl.Vertex.copy()
                else :
                    vertex = np.concatenate((vertex, cl.Vertex), axis=0)
            self.m_npCheckVertx = vertex

            self._state_1(self.m_inputCLID, startIndex, clCurve)


    def _find_outsideinx(self, clID : int) :
        connIDs = self.InputSkeleton.get_conn_centerline_id(clID)
        parentCLID = connIDs[0]
        if parentCLID == -1 :
            return 0
        
        parentCL = self.InputSkeleton.get_centerline(parentCLID)
        cl = self.InputSkeleton.get_centerline(clID)
        # spherePos = parentCL.Vertex[-1]
        # radius = parentCL.Radius[-1]
        spherePos = cl.Vertex[0]
        radius = cl.Radius[0]

        dist = np.linalg.norm(cl.Vertex - spherePos, axis=1)

        outSideInx = np.where(dist > radius)[0]
        if len(outSideInx) > 0 :
            return outSideInx[0]
        return -1
    
    # state
    # 
    # 거슬러 올라감
    def _state_0(self, clID : int, vertexIndex : int, clCurve : curveInfo.CCLCurve) :
        for inx in range(vertexIndex, 0, -1) :
            ret = self._check_valid_cut(clID, inx, clCurve)
            if ret == False :
                inx = inx + 1
                ret = self._process_sub(clID, inx, clCurve)
                if ret is not None :
                    self.m_outputCLID = clID
                    self.m_outputVertexInx = inx
                    self.m_outputWhole = ret[0]
                    self.m_outputSub = ret[1]
                    break
            if ret == True and inx == 1 :
                ret = self._process_sub(clID, inx, clCurve)
                if ret is not None :
                    self.m_outputCLID = clID
                    self.m_outputVertexInx = inx
                    self.m_outputWhole = ret[0]
                    self.m_outputSub = ret[1]
                    break
    # 거슬러 내려감
    def _state_1(self, clID : int, vertexIndex : int, clCurve : curveInfo.CCLCurve) :
        cl = self.InputSkeleton.get_centerline(clID)
        iCnt = cl.get_vertex_count()
        for inx in range(vertexIndex, iCnt - 1) :
            ret = self._check_valid_cut(clID, inx, clCurve)
            if ret == True :
                ret = self._process_sub(clID, inx, clCurve)
                if ret is not None :
                    self.m_outputCLID = clID
                    self.m_outputVertexInx = inx
                    self.m_outputWhole = ret[0]
                    self.m_outputSub = ret[1]
                    break
    

    @property
    def InputCLID(self) -> int : 
        return self.m_inputCLID
    @InputCLID.setter
    def InputCLID(self, inputCLID : int) :
        self.m_inputCLID = inputCLID


class CCommandSepVesselKnife(CCommandSepVessel) :
    def __init__(self, mediator):
        super().__init__(mediator)
        self.m_inputWorldA = None
        self.m_inputWorldB = None
        self.m_inputWorldC = None

    def clear(self) :

        super().clear()
    def process(self) :
        super().process()

        cmdKnife = commandKnife.CCommandKnifeCL(self.m_mediator)
        cmdKnife.InputData = self.m_inputData
        cmdKnife.InputSkeleton = self.m_inputSkeleton
        cmdKnife.InputWorldA = self.m_inputWorldA
        cmdKnife.InputWorldB = self.m_inputWorldB
        cmdKnife.InputWorldC = self.m_inputWorldC
        cmdKnife.process()

        clID = cmdKnife.OutputKnifedCLID
        vertexIndex = cmdKnife.OutputKnifedIndex
        tangent = cmdKnife.OutputTangent
        pt = cmdKnife.OutputIntersectedPt
        radius = self._get_projected_radius(self.m_inputWorldA, self.m_inputWorldB, self.m_inputWorldC, pt)

        self.m_outputCLID = clID
        self.m_outputVertexInx = vertexIndex
        retGuide = self._get_separated_guide_polydata(pt, tangent, radius + CCommandSepVessel.s_margin)
        if retGuide is None :
            print("failed to create guide")
            return 
        retGuide0 = retGuide[0]
        retGuide1 = retGuide[1]

        ret = self._process_sub_with_guide(clID, vertexIndex, retGuide0, retGuide1)
        if ret is None :
            self.m_outputWhole = None
            self.m_outputSub = None
        else :
            self.m_outputWhole = ret[0]
            self.m_outputSub = ret[1]

    
    # protected
    def _get_projected_radius(self, a : np.ndarray, b : np.ndarray, cameraPos : np.ndarray, intersectedPt : np.ndarray) :
        a = a.reshape(-1)
        b = b.reshape(-1)
        cameraPos = cameraPos.reshape(-1)
        intersectedPt = intersectedPt.reshape(-1)

        def ray_plane_intersection(rayOrigin, rayDir, planePoint, planeNormal) :
            rayDir = rayDir / np.linalg.norm(rayDir)
            planeNormal = planeNormal / np.linalg.norm(planeNormal)

            denom = np.dot(rayDir, planeNormal)
            if np.abs(denom) < 1e-6:
                return None  # 평면과 평행해서 교차 안 함

            t = np.dot(planePoint - rayOrigin, planeNormal) / denom
            if t < 0:
                return None  # 평면 뒤쪽과 교차 (원하면 제거 조건)
            
            return rayOrigin + t * rayDir
        
        normal = intersectedPt - cameraPos
        aProj = ray_plane_intersection(cameraPos, a - cameraPos, intersectedPt, normal)
        bProj = ray_plane_intersection(cameraPos, b - cameraPos, intersectedPt, normal)
        dist = np.abs(aProj - bProj)
        return np.max(dist) / 2.0
    


    @property
    def InputWorldA(self) -> np.ndarray : 
        return self.m_inputWorldA
    @InputWorldA.setter
    def InputWorldA(self, inputWorldA : np.ndarray) :
        self.m_inputWorldA = inputWorldA
    @property
    def InputWorldB(self) -> np.ndarray : 
        return self.m_inputWorldB
    @InputWorldB.setter
    def InputWorldB(self, inputWorldB : np.ndarray) :
        self.m_inputWorldB = inputWorldB
    @property
    def InputWorldC(self) -> np.ndarray : 
        return self.m_inputWorldC
    @InputWorldC.setter
    def InputWorldC(self, inputWorldC : np.ndarray) :
        self.m_inputWorldC = inputWorldC





'''
desc 
    - cylinder knife mesh를 이용한 vessel cutting 
'''
class CCommandSepVesselKM(commandInterface.CCommand) :
    s_margin = 3.0

    @staticmethod
    def merge_vtk_mesh(polyData0 : vtk.vtkPolyData, polyData1 : vtk.vtkPolyData) -> vtk.vtkPolyData :
        append_filter = vtk.vtkAppendPolyData()
        append_filter.AddInputData(polyData0)
        append_filter.AddInputData(polyData1)
        append_filter.Update()

        return append_filter.GetOutput()
    @staticmethod
    def create_knife(pos : np.ndarray, normal : np.ndarray, radius=1.0, height=10.0, resolution=30) -> vtk.vtkPolyData :
        cylinder = vtk.vtkCylinderSource()
        cylinder.SetRadius(radius)
        cylinder.SetHeight(height)
        cylinder.SetResolution(resolution)
        cylinder.SetCenter(0.0, 0.0, 0.0)
        cylinder.SetCapping(True)
        cylinder.Update()
        polydata = cylinder.GetOutput()

        default_normal = np.array([0.0, 1.0, 0.0])
        normal = normal.reshape(-1)
        pos = pos.reshape(-1)

        transform = vtk.vtkTransform()
        transform.Translate(*pos)

        dot = np.dot(default_normal, normal)
        if np.isclose(dot, 1.0):
            # 동일한 방향 → 회전 불필요
            pass
        elif np.isclose(dot, -1.0):
            # 정반대 → 180도 회전, 축은 아무 수직 벡터
            axis = np.array([1.0, 0.0, 0.0])  # Z축과 직교하는 임의 벡터
            angle = 180.0
            transform.RotateWXYZ(angle, *axis)
        else:
            # 일반적인 경우
            axis = np.cross(default_normal, normal)
            axis = axis / np.linalg.norm(axis)
            angle = np.degrees(np.arccos(np.clip(dot, -1.0, 1.0)))
            transform.RotateWXYZ(angle, *axis)
        
        transform_filter = vtk.vtkTransformPolyDataFilter()
        transform_filter.SetInputData(polydata)
        transform_filter.SetTransform(transform)
        transform_filter.Update()

        # 삼각형화 → 중복 제거
        triangle_filter = vtk.vtkTriangleFilter()
        triangle_filter.SetInputConnection(transform_filter.GetOutputPort())
        triangle_filter.Update()

        clean_filter = vtk.vtkCleanPolyData()
        clean_filter.SetInputConnection(triangle_filter.GetOutputPort())
        clean_filter.Update()

        return clean_filter.GetOutput()
    @staticmethod
    def check_line_intersection(polydata : vtk.vtkPolyData, p0 : np.ndarray, p1 : np.ndarray) -> bool :
        obbTree = vtk.vtkOBBTree()
        obbTree.SetDataSet(polydata)
        obbTree.BuildLocator()

        vtkPoints = vtk.vtkPoints()
        code = obbTree.IntersectWithLine(p0.tolist(), p1.tolist(), vtkPoints, None)
        return code == 1 and vtkPoints.GetNumberOfPoints() > 0
    @staticmethod
    def find_intersected_polydata(listPolydata : list, p0 : np.ndarray, p1 : np.ndarray) -> vtk.vtkPolyData :
        '''
        ret : (intersected mesh, [non-inter mesh0, ..])
        '''
        retInterMesh = None
        retListNonInterMesh = []
        p0 = p0.reshape(-1)
        p1 = p1.reshape(-1)
        for polydata in listPolydata :
            bRet = CCommandSepVesselKM.check_line_intersection(polydata, p0, p1)
            if bRet == True :
                retInterMesh = polydata
            else :
                retListNonInterMesh.append(polydata)
        return (retInterMesh, retListNonInterMesh)
    @staticmethod
    def enhanced_knife(knifePolydata : vtk.vtkPolyData, listSubPolydata : list, margin=0.1) :
        if len(listSubPolydata) == 0 :
            return None
        
        meshlibKnife = CCommandSepVessel.get_meshlib(knifePolydata)

        append_filter = vtk.vtkAppendPolyData()
        for subPolydata in listSubPolydata :
            subPolydata = CCommandSepVessel.dilation_polydata2(subPolydata, margin)
            append_filter.AddInputData(subPolydata)
        append_filter.Update()
        subPolydata = append_filter.GetOutput()

        meshlibSub = CCommandSepVessel.get_meshlib(subPolydata)
        meshlibKnife = algMeshLib.CMeshLib.meshlib_boolean_subtraction(meshlibKnife, meshlibSub)

        return CCommandSepVessel.get_vtkmesh(meshlibKnife)
    @staticmethod
    def get_normal_shifted_points(pos: np.ndarray, normal: np.ndarray, distance: float = 1.0) -> tuple[np.ndarray, np.ndarray] :
        """
        Returns:
            tuple: (pos_plus, pos_minus)
        """
        pos = pos.reshape(-1)
        normal = normal.reshape(-1)
        
        pos_plus = pos + distance * normal
        pos_minus = pos - distance * normal

        return pos_plus.reshape(-1, 3), pos_minus.reshape(-1, 3)
    @staticmethod
    def get_projected_radius(a : np.ndarray, b : np.ndarray, cameraPos : np.ndarray, intersectedPt : np.ndarray) :
        a = a.reshape(-1)
        b = b.reshape(-1)
        cameraPos = cameraPos.reshape(-1)
        intersectedPt = intersectedPt.reshape(-1)

        def ray_plane_intersection(rayOrigin, rayDir, planePoint, planeNormal) :
            rayDir = rayDir / np.linalg.norm(rayDir)
            planeNormal = planeNormal / np.linalg.norm(planeNormal)

            denom = np.dot(rayDir, planeNormal)
            if np.abs(denom) < 1e-6:
                return None  # 평면과 평행해서 교차 안 함

            t = np.dot(planePoint - rayOrigin, planeNormal) / denom
            if t < 0:
                return None  # 평면 뒤쪽과 교차 (원하면 제거 조건)
            
            return rayOrigin + t * rayDir
        
        normal = intersectedPt - cameraPos
        aProj = ray_plane_intersection(cameraPos, a - cameraPos, intersectedPt, normal)
        bProj = ray_plane_intersection(cameraPos, b - cameraPos, intersectedPt, normal)
        dist = np.abs(aProj - bProj)
        return np.max(dist) / 2.0
    
   
    def __init__(self, mediator) :
        super().__init__(mediator)
        self.m_inputSkeleton = None
        self.m_inputWholeVessel = None

        self.m_outputCLID = -1
        self.m_outputVertexInx = -1
        self.m_outputListPolydata = []

        self.m_npCheckVertx = None
        self.m_meshlibWholeVessel = None
    def clear(self) :
        self.m_inputSkeleton = None
        self.m_inputWholeVessel = None

        self.m_outputCLID = -1
        self.m_outputVertexInx = -1
        self.m_outputListPolydata.clear()

        self.m_npCheckVertx = None
        self.m_meshlibWholeVessel = None
        super().clear()
    def process(self) :
        super().process()

        if self.InputSkeleton is None :
            return
        if self.InputWholeVessel is None :
            return

        self.m_meshlibWholeVessel = CCommandSepVessel.get_meshlib(self.m_inputWholeVessel)
        if self.m_meshlibWholeVessel is not None :
            algMeshLib.CMeshLib.meshlib_healing(self.m_meshlibWholeVessel)

        self.m_outputCLID = -1
        self.m_outputVertexInx = -1
        self.m_outputListPolydata.clear()
        self.m_npCheckVertx = None


    def get_output_polydata_count(self) -> int :
        return len(self.m_outputListPolydata)
    def get_output_polydata(self, inx : int) -> vtk.vtkPolyData :
        return self.m_outputListPolydata[inx]
    

    def _process_cutting(self, clID : int, vertexIndex : int, normal : np.ndarray, radius : float) -> list :
        '''
        desc
            - radius : 가급적 margin을 적용시키는 것이 좋다. 하지만 knife에서는 margin을 적용하지 않는다. 
        ret 
            - [vtkPolyData0, vtkPolyData1, ..]
        '''
        cl =  self.InputSkeleton.get_centerline(clID)
        pos = cl.get_vertex(vertexIndex)

        knifeMesh = CCommandSepVesselKM.create_knife(
            pos,
            algLinearMath.CScoMath.vec3_normalize(normal),
            radius, 0.01
        )
        p0, p1 = CCommandSepVesselKM.get_normal_shifted_points(pos, normal)

        meshlibKnife = CCommandSepVessel.get_meshlib(knifeMesh)
        meshlibRet = algMeshLib.CMeshLib.meshlib_boolean_intersection(self.m_meshlibWholeVessel, meshlibKnife)
        interMesh = CCommandSepVessel.get_vtkmesh(meshlibRet)

        retListMesh = CCommandSepVessel.get_sub_polydata(interMesh)
        if retListMesh is None  :
            print("failed mesh boolean subtraction")
            return None
        subCnt = len(retListMesh)

        if subCnt > 1 :
            meshInfo = CCommandSepVesselKM.find_intersected_polydata(retListMesh, p0, p1)
            # 교차된 mesh가 없다. 
            if meshInfo[0] is None :
                print("not found knife mesh")
                return None
            knifeMesh = CCommandSepVesselKM.enhanced_knife(knifeMesh, meshInfo[1], margin=1.0)
        
        meshlibKnife = CCommandSepVessel.get_meshlib(knifeMesh)
        meshlibRet = algMeshLib.CMeshLib.meshlib_boolean_subtraction(self.m_meshlibWholeVessel, meshlibKnife)
        vesselMesh = CCommandSepVessel.get_vtkmesh(meshlibRet)
        return CCommandSepVessel.get_sub_polydata(vesselMesh)
    def _check_valid_sub(self, subVessel : vtk.vtkPolyData) -> bool :
        if self.m_npCheckVertx is None :
            return True
        nowCnt = CCommandSepVessel.check_in_polydata(subVessel, self.m_npCheckVertx)
        return nowCnt < 1


    @property
    def InputSkeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_inputSkeleton
    @InputSkeleton.setter
    def InputSkeleton(self, inputSkeleton : algSkeletonGraph.CSkeleton) :
        self.m_inputSkeleton = inputSkeleton
    @property
    def InputWholeVessel(self) :
        return self.m_inputWholeVessel
    @InputWholeVessel.setter
    def InputWholeVessel(self, inputWholeVessel) :
        self.m_inputWholeVessel = inputWholeVessel

    @property
    def OutputCLID(self) -> int :
        return self.m_outputCLID
    @property
    def OutputVertexInx(self) -> int :
        return self.m_outputVertexInx
    @property
    def OutputListPolydata(self) -> vtk.vtkPolyData :
        return self.m_outputListPolydata
    

class CCommandSepVesselKMTreeVessel(CCommandSepVesselKM) :
    def __init__(self, mediator):
        super().__init__(mediator)
        self.m_inputCLID = -1
        self.m_outputWhole = None
        self.m_outputSub = None

    def clear(self) :
        self.m_inputCLID = -1
        self.m_outputWhole = None
        self.m_outputSub = None
        super().clear()
    def process(self) :
        super().process()

        if self.InputCLID == -1 :
            print("CCommandSepVesselKMTreeVessel : not setting clID")
            return
        if self.m_meshlibWholeVessel is None :
            print("CCommandSepVesselKMTreeVessel : not setting whole vessel")
            return
        
        cl = self.InputSkeleton.get_centerline(self.m_inputCLID)
        clCurve = curveInfo.CCLCurve(cl)
        iCnt = cl.get_vertex_count()
        outSideIndex = self._find_outsideinx(self.m_inputCLID)

        startIndex = 0

        # 마지막 지점이 포인트일 경우 거슬러 올라간다. 
        # 마지막 포인트만 벗어난 경우 or 모든 vertex가 parent radius 범위 내에 있을 경우 
        # 마지막 지점은 계산에서 제외한다. 
        if outSideIndex == iCnt - 1 or outSideIndex == -1 : 
            # centerline이 너무 짧아 parent radius에 centerline point들이 포함되어 버린 경우
            pass
            # startIndex = 1
            # self._state_1(self.m_inputCLID, startIndex, clCurve)
        else :
            startIndex = outSideIndex

            listCL = self.InputSkeleton.find_descendant_centerline_by_centerline_id(self.InputCLID)
            listCLID = [clID for clID in listCL]
            listCheckedCLID = [clID for clID in range(0, self.InputSkeleton.get_centerline_count()) if clID not in listCLID]

            vertex = None
            for childCLID in listCheckedCLID :
                cl = self.InputSkeleton.get_centerline(childCLID)
                if self.m_npCheckVertx is None :
                    vertex = cl.Vertex.copy()
                else :
                    vertex = np.concatenate((vertex, cl.Vertex), axis=0)
            self.m_npCheckVertx = vertex

            self._process(self.InputCLID, startIndex, clCurve)
    
    def _process(self, clID : int, vertexIndex : int, clCurve : curveInfo.CCLCurve) :
        cl = self.InputSkeleton.get_centerline(clID)
        iCnt = cl.get_vertex_count()
        for inx in range(vertexIndex, iCnt - 1) :
            tangent = clCurve.m_npZCoord[inx]
            tangent = tangent.reshape(-1, 3)
            radius = cl.Radius[inx]

            retList = self._process_cutting(clID, inx, tangent, radius + CCommandSepVesselKM.s_margin)
            if retList is None :
                continue
            subCnt = len(retList)

            if subCnt <= 1 :
                print(f"cutting failed : subCnt {subCnt}, clID {clID}, vertexInx {inx}")
                continue
        
            ret = self._find_whole_sub(clID, inx, retList)
            if ret is not None :
                self.m_outputCLID = clID
                self.m_outputVertexInx = inx
                self.m_outputWhole = ret[0]
                self.m_outputSub = ret[1]
                self.m_outputListPolydata.append(self.m_outputWhole)
                self.m_outputListPolydata.append(self.m_outputSub)
                break

    def _find_outsideinx(self, clID : int) :
        connIDs = self.InputSkeleton.get_conn_centerline_id(clID)
        parentCLID = connIDs[0]
        if parentCLID == -1 :
            return 0
        
        parentCL = self.InputSkeleton.get_centerline(parentCLID)
        cl = self.InputSkeleton.get_centerline(clID)
        # spherePos = parentCL.Vertex[-1]
        # radius = parentCL.Radius[-1]
        spherePos = cl.Vertex[0]
        radius = cl.Radius[0]

        dist = np.linalg.norm(cl.Vertex - spherePos, axis=1)

        outSideInx = np.where(dist > radius)[0]
        if len(outSideInx) > 0 :
            return outSideInx[0]
        return -1
    def _find_whole_sub(self, clID : int, vertexIndex : int, listPolydata : list) -> tuple :
        '''
        ret : (whole, sub)
        '''
        cl = self.InputSkeleton.get_centerline(clID)
        # find sub
        sub = CCommandSepVessel.find_polydata_include_vertex(listPolydata, cl.Vertex[vertexIndex : ].reshape(-1, 3))
        if sub is None :
            print("not found sub")
            return None
        if self._check_valid_sub(sub) == False :
            return None
        # find whole
        whole = CCommandSepVessel.find_polydata_include_vertex(listPolydata, cl.Vertex[ : vertexIndex].reshape(-1, 3))
        if whole is None :
            print("not found whole")
            return None
        
        return (whole, sub)


    @property
    def InputCLID(self) -> int : 
        return self.m_inputCLID
    @InputCLID.setter
    def InputCLID(self, inputCLID : int) :
        self.m_inputCLID = inputCLID
    
    @property
    def OutputWhole(self) -> vtk.vtkPolyData :
        return self.m_outputWhole
    @property
    def OutputSub(self) -> vtk.vtkPolyData :
        return self.m_outputSub


class CCommandSepVesselKMTreeVesselKnife(CCommandSepVesselKM) :
    def __init__(self, mediator):
        super().__init__(mediator)
        self.m_inputWorldA = None
        self.m_inputWorldB = None
        self.m_inputWorldC = None
        self.m_outputWhole = None
        self.m_outputSub = None

    def clear(self) :
        self.m_inputWorldA = None
        self.m_inputWorldB = None
        self.m_inputWorldC = None
        self.m_outputWhole = None
        self.m_outputSub = None
        super().clear()
    def process(self) :
        super().process()

        if self.m_meshlibWholeVessel is None :
            print("CCommandSepVesselKMTreeVesselKnife : not setting whole vessel")
            return

        cmdKnife = commandKnife.CCommandKnifeCL(self.m_mediator)
        cmdKnife.InputData = self.m_inputData
        cmdKnife.InputSkeleton = self.m_inputSkeleton
        cmdKnife.InputWorldA = self.m_inputWorldA
        cmdKnife.InputWorldB = self.m_inputWorldB
        cmdKnife.InputWorldC = self.m_inputWorldC
        cmdKnife.process()

        clID = cmdKnife.OutputKnifedCLID
        vertexIndex = cmdKnife.OutputKnifedIndex
        tangent = cmdKnife.OutputTangent
        pt = cmdKnife.OutputIntersectedPt
        radius = CCommandSepVesselKM.get_projected_radius(self.m_inputWorldA, self.m_inputWorldB, self.m_inputWorldC, pt)

        self.m_outputCLID = clID
        self.m_outputVertexInx = vertexIndex

        retList = self._process_cutting(clID, vertexIndex, tangent, radius + CCommandSepVesselKM.s_margin)
        if retList is None :
            return
        subCnt = len(retList)

        if subCnt <= 1 :
            print(f"cutting failed : subCnt {subCnt}, clID {clID}, vertexInx {vertexIndex}")
            return
    
        ret = self._find_whole_sub(clID, vertexIndex, retList)
        if ret is not None :
            self.m_outputWhole = ret[0]
            self.m_outputSub = ret[1]
            self.m_outputListPolydata.append(self.m_outputWhole)
            self.m_outputListPolydata.append(self.m_outputSub)

    
    # protected
    def _find_whole_sub(self, clID : int, vertexIndex : int, listPolydata : list) -> tuple :
        '''
        ret : (whole, sub)
        '''
        cl = self.InputSkeleton.get_centerline(clID)
        # find sub
        sub = CCommandSepVessel.find_polydata_include_vertex(listPolydata, cl.Vertex[vertexIndex : ].reshape(-1, 3))
        # find whole
        whole = CCommandSepVessel.find_polydata_include_vertex(listPolydata, cl.Vertex[ : vertexIndex].reshape(-1, 3))
        if whole is None :
            print("not found whole")
            return None
        
        if sub is None :
            for polydata in listPolydata :
                if polydata == whole :
                    continue
                sub = polydata
        
        return (whole, sub)
    

    @property
    def InputWorldA(self) -> np.ndarray : 
        return self.m_inputWorldA
    @InputWorldA.setter
    def InputWorldA(self, inputWorldA : np.ndarray) :
        self.m_inputWorldA = inputWorldA
    @property
    def InputWorldB(self) -> np.ndarray : 
        return self.m_inputWorldB
    @InputWorldB.setter
    def InputWorldB(self, inputWorldB : np.ndarray) :
        self.m_inputWorldB = inputWorldB
    @property
    def InputWorldC(self) -> np.ndarray : 
        return self.m_inputWorldC
    @InputWorldC.setter
    def InputWorldC(self, inputWorldC : np.ndarray) :
        self.m_inputWorldC = inputWorldC
    
    @property
    def OutputWhole(self) -> vtk.vtkPolyData :
        return self.m_outputWhole
    @property
    def OutputSub(self) -> vtk.vtkPolyData :
        return self.m_outputSub



class CCommandSepVesselKMGraphVesselKnife(CCommandSepVesselKM) :
    def __init__(self, mediator):
        super().__init__(mediator)
        self.m_inputWorldA = None
        self.m_inputWorldB = None
        self.m_inputWorldC = None
        self.m_outputWhole = None
        self.m_outputSub = None

    def clear(self) :
        self.m_inputWorldA = None
        self.m_inputWorldB = None
        self.m_inputWorldC = None
        self.m_outputWhole = None
        self.m_outputSub = None
        super().clear()
    def process(self) :
        super().process()

        if self.m_meshlibWholeVessel is None :
            print("CCommandSepVesselKMTreeVesselKnife : not setting whole vessel")
            return

        cmdKnife = commandKnife.CCommandKnifeCL(self.m_mediator)
        cmdKnife.InputData = self.m_inputData
        cmdKnife.InputSkeleton = self.m_inputSkeleton
        cmdKnife.InputWorldA = self.m_inputWorldA
        cmdKnife.InputWorldB = self.m_inputWorldB
        cmdKnife.InputWorldC = self.m_inputWorldC
        cmdKnife.process()

        if cmdKnife.OutputKnifedCLID == -1 :
            return

        clID = cmdKnife.OutputKnifedCLID
        vertexIndex = cmdKnife.OutputKnifedIndex
        tangent = cmdKnife.OutputTangent
        pt = cmdKnife.OutputIntersectedPt
        radius = CCommandSepVesselKM.get_projected_radius(self.m_inputWorldA, self.m_inputWorldB, self.m_inputWorldC, pt)

        self.m_outputCLID = clID
        self.m_outputVertexInx = vertexIndex
        self.m_outputListPolydata = self._process_cutting(clID, vertexIndex, tangent, radius + CCommandSepVesselKM.s_margin)
        if self.m_outputListPolydata is None :
            self.m_outputListPolydata = []
            self.m_outputWhole = None
            self.m_outputSub = None
            return

        if len(self.m_outputListPolydata) > 1 :
            ret = self._find_whole(self.m_outputListPolydata)
            if ret is not None :
                self.m_outputWhole = ret[0]
                self.m_outputSub = ret[1]
        else :
            self.m_outputWhole = None
            self.m_outputSub = None

    
    # protected
    def _find_whole(self, listPolydata : list) -> tuple :
        '''
        ret : (whole, sub)
        '''
        rootCL = self.InputSkeleton.RootCenterline
        if rootCL is None :
            rootCL = self.InputSkeleton.get_centerline(0)

        # find whole
        whole = CCommandSepVessel.find_polydata_include_vertex(listPolydata, rootCL.Vertex)
        if whole is None :
            return None
        sub = None
        for polydata in listPolydata :
            if polydata == whole :
                continue
            sub = polydata
        
        return (whole, sub)
    

    @property
    def InputWorldA(self) -> np.ndarray : 
        return self.m_inputWorldA
    @InputWorldA.setter
    def InputWorldA(self, inputWorldA : np.ndarray) :
        self.m_inputWorldA = inputWorldA
    @property
    def InputWorldB(self) -> np.ndarray : 
        return self.m_inputWorldB
    @InputWorldB.setter
    def InputWorldB(self, inputWorldB : np.ndarray) :
        self.m_inputWorldB = inputWorldB
    @property
    def InputWorldC(self) -> np.ndarray : 
        return self.m_inputWorldC
    @InputWorldC.setter
    def InputWorldC(self, inputWorldC : np.ndarray) :
        self.m_inputWorldC = inputWorldC
    
    @property
    def OutputWhole(self) -> vtk.vtkPolyData :
        return self.m_outputWhole
    @property
    def OutputSub(self) -> vtk.vtkPolyData :
        return self.m_outputSub


if __name__ == '__main__' :
    pass


# print ("ok ..")

