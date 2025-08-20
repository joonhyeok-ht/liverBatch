import sys
import os
import numpy as np
import shutil
import time
import vtk
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStateProjectPath = os.path.dirname(fileAbsPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import data as data
import clMask as clMask

import operation as operation

import tabState as tabState

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algMeshLib as algMeshLib
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algImage as algImage
import AlgUtil.algSegment as algSegment

import Block.reconstruction as reconstruction

import VtkObj.vtkObjLine as vtkObjLine
import vtkObjSTL as vtkObjSTL
import vtkObjInterface as vtkObjInterface
import vtkObjGuideCLBound as vtkObjGuideCLBound

import command.commandTerritory as commandTerritory
import command.commandTerritoryVessel as commandTerritoryVessel
import command.commandKnife as commandKnife 
import command.curveInfo as curveInfo

import geometry as geometry
        


class CCommandSepVessel :
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
        maxCnt = -1
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

    
    def __init__(self, mediator):
        self.m_mediator = mediator
        self.m_inputData = None
        self.m_inputSkeleton = None
        self.m_inputMeshLibWholeVessel = None

        self.m_outputCLID = -1
        self.m_outputVertexInx = -1
        self.m_outputWhole = None
        self.m_outputSub = None
    def clear(self) :
        pass
    def process(self) :
        self.m_outputCLID = -1
        self.m_outputVertexInx = -1
        self.m_outputWhole = None
        self.m_outputSub = None


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
        selGuideSub = CCommandSepVessel.find_polydata_include_vertex(listGuideSub, cl.Vertex[vertexIndex : ].reshape(-1, 3))
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
            print(f"invalide sub count : {len(listRet)}")
            return False

        return True
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
            print(f"invalide sub count : {len(listRet)}")
            return None
        sub = CCommandSepVessel.find_polydata_include_vertex(listRet, cl.Vertex[vertexIndex : ].reshape(-1, 3))
        if sub is None :
            print("not found whole")
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
    def InputData(self) -> data.CData :
        return self.m_inputData
    @property
    def InputSkeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_inputSkeleton


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
            self._state_1(self.m_inputCLID, startIndex, clCurve)


    def _find_outsideinx(self, clID : int) :
        connIDs = self.InputSkeleton.get_conn_centerline_id(clID)
        parentCLID = connIDs[0]
        if parentCLID == -1 :
            return 0
        
        parentCL = self.InputSkeleton.get_centerline(parentCLID)
        spherePos = parentCL.Vertex[-1]
        radius = parentCL.Radius[-1]

        cl = self.InputSkeleton.get_centerline(clID)
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

        def ray_plane_intersection(rayOrigin, rayDir, planePoint, planeNormal):
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
    



class CSubStateKnifeEn() :
    s_terriOrganColor = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.6])
    s_terriVesselColor = algLinearMath.CScoMath.to_vec3([0.5, 0.0, 0.5])
    

    def __init__(self, mediator):
        # input your code
        self.m_mediator = mediator
    def clear(self) :
        # input your code
        self.m_mediator = None

    def process_init(self) :
        pass
    def process(self) :
        pass
    def process_end(self) :
        pass

    def clicked_mouse_rb(self, clickX, clickY) :
        pass
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        listExceptKeyType = [
            data.CData.s_territoryType,
            data.CData.s_vesselType,
            data.CData.s_organType,
        ]
        key = self.App.picking(clickX, clickY, listExceptKeyType)
        if key == "" or data.CData.get_type_from_key(key) != data.CData.s_skelTypeCenterline :
            key = ""

        opSelectionCL = self._get_operator_selection_cl()

        self._set_whole_vessel(None)
        self.App.remove_key_type(data.CData.s_territoryType)
        operation.COperationSelectionCL.multi_clicked(opSelectionCL, key)
    def release_mouse_rb(self) :
        pass
    def mouse_move(self, clickX, clickY) :
        pass
    def mouse_move_rb(self, clickX, clickY) :
        pass
    def key_press(self, keyCode : str) :
        pass
    def key_press_with_ctrl(self, keyCode : str) :
        if keyCode == "z" :
            self.App.undo()
        if keyCode == "r" :
            self.App.redo()

    def on_btn_view_territory(self) :
        pass
    def on_btn_view_vessel(self) :
        pass
    def cl_hierarchy(self) :
        pass


    # protected
    def _get_data(self) -> data.CData :
        return self.m_mediator.get_data()
    def _get_operator_selection_cl(self) -> operation.COperationSelectionCL :
        return self.m_mediator.m_opSelectionCL
    def _get_clinfo_index(self) -> int :
        return self.m_mediator.get_clinfo_index()
    def _get_skeleton(self) -> algSkeletonGraph.CSkeleton :
        clinfoInx = self._get_clinfo_index()
        return self._get_data().get_skeleton(clinfoInx)
    def _get_clmask(self) -> clMask.CCLMask :
        return self.m_mediator.m_clMask
    def _get_organ_key(self) -> str :
        return self.m_mediator.m_organKey
    def _get_terriinfo(self) -> data.CTerritoryInfo :
        return self.m_mediator.m_terriInfo
    
    def _set_whole_vessel(self, wholeVessel : vtk.vtkPolyData) :
        self.m_mediator.m_wholeVesselPolyData = wholeVessel
    

    def _getui_terri_organ_name_index(self) -> int :
        return self.m_mediator.getui_terri_organ_name_index()
    def _getui_terri_organ_name(self) -> str :
        return self.m_mediator.getui_terri_organ_name()
    

    def _command_territory(self) :
        key = data.CData.make_key(data.CData.s_territoryType, 0, 0)
        self.App.remove_key(key)

        dataInst = self._get_data()
        if dataInst.Ready == False :
            return

        clinfoinx = self._get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoinx)
        if skeleton is None :
            return
        
        opSelectionCL = self._get_operator_selection_cl()
        retList = opSelectionCL.get_all_selection_cl()
        if retList is None :
            print("not selecting centerline")
            return
        
        terriInfo = self._get_terriinfo()
        if terriInfo is None :
            return
        
        startTime = time.perf_counter()
        cmd = commandTerritory.CCommandTerritory(self.App)
        cmd.InputData = dataInst
        cmd.InputSkeleton = skeleton
        cmd.InputCLMask = self._get_clmask()
        cmd.InputTerriInfo = terriInfo
        for id in retList :
            cmd.add_cl_id(id)
        cmd.process()
        terriPolyData = cmd.OutputTerriPolyData
        if terriPolyData is None :
            print("failed to territory")
            return
        endTime = time.perf_counter()
        elapsedTime = (endTime - startTime) * 1000
        print(f"territory elapsed time : {elapsedTime:.3f}ms")
        
        terriObj = vtkObjInterface.CVTKObjInterface()
        terriObj.KeyType = data.CData.s_territoryType
        terriObj.Key = key
        terriObj.Color = CSubStateKnifeEn.s_terriOrganColor
        terriObj.Opacity = 0.5
        terriObj.PolyData = terriPolyData
        dataInst.add_vtk_obj(terriObj)
        self.App.ref_key(key)
        self.App.update_viewer()

    def _command_vessel_pick(self) :
        key = data.CData.make_key(data.CData.s_territoryType, 0, 1)
        self.App.remove_key(key)
        self._set_whole_vessel(None)

        dataInst = self._get_data()
        clinfoInx = self._get_clinfo_index()
        skeleton = self._get_skeleton()

        opSelectionCL = self._get_operator_selection_cl()
        # selList = opSelectionCL.get_all_selection_cl()
        selList = opSelectionCL.get_selection_cl_list()
        if selList is None :
            print("not found selection cl")
            return

        # vessel territory
        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey)
        if vesselObj is None :
            print("not found vessel")
            return
        # vessel의 min-max 추출 및 정육면체 생성
        vesselPolyData = vesselObj.PolyData

        meshLibVessel = CCommandSepVessel.get_meshlib(vesselPolyData)
        meshLibVessel = algMeshLib.CMeshLib.meshlib_healing(meshLibVessel)

        cmd = CCommandSepVesselPick(self.App)
        cmd.m_inputData = dataInst
        cmd.m_inputSkeleton = skeleton
        cmd.m_inputMeshLibWholeVessel = meshLibVessel
        cmd.m_inputCLID = selList[0]
        cmd.process()

        if cmd.m_outputWhole is None :
            print("failed to separate whole")
            self.App.update_viewer()
            return
        if cmd.m_outputSub is None :
            print("failed to separate sub")
            self.App.update_viewer()
            return

        key = data.CData.make_key(data.CData.s_territoryType, 0, 1)
        terriObj = vtkObjInterface.CVTKObjInterface()
        terriObj.KeyType = data.CData.s_territoryType
        terriObj.Key = key
        terriObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])
        terriObj.Opacity = 0.5
        terriObj.PolyData = cmd.m_outputWhole
        dataInst.add_vtk_obj(terriObj)
        # self.App.ref_key(key)

        key = data.CData.make_key(data.CData.s_territoryType, 0, 2)
        terriObj = vtkObjInterface.CVTKObjInterface()
        terriObj.KeyType = data.CData.s_territoryType
        terriObj.Key = key
        terriObj.Color = algLinearMath.CScoMath.to_vec3([0.5, 0.0, 0.5])
        terriObj.Opacity = 0.5
        terriObj.PolyData = cmd.m_outputSub
        dataInst.add_vtk_obj(terriObj)
        self.App.ref_key(key)

        self.App.update_viewer()
    def _command_vessel_enhanced_knife(self, a : np.ndarray, b : np.ndarray, c : np.ndarray) :
        key = data.CData.make_key(data.CData.s_territoryType, 0, 1)
        self.App.remove_key(key)
        self._set_whole_vessel(None)

        dataInst = self._get_data()
        clinfoInx = self._get_clinfo_index()
        skeleton = self._get_skeleton()

        # vessel territory
        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey)
        if vesselObj is None :
            return
        # vessel의 min-max 추출 및 정육면체 생성
        vesselPolyData = vesselObj.PolyData

        meshLibVessel = CCommandSepVessel.get_meshlib(vesselPolyData)
        meshLibVessel = algMeshLib.CMeshLib.meshlib_healing(meshLibVessel)

        cmd = CCommandSepVesselKnife(self.App)
        cmd.m_inputData = dataInst
        cmd.m_inputSkeleton = skeleton
        cmd.m_inputMeshLibWholeVessel = meshLibVessel
        cmd.m_inputWorldA = a
        cmd.m_inputWorldB = b
        cmd.m_inputWorldC = c
        cmd.process()

        if cmd.m_outputWhole is None :
            print("failed to separate whole")
            self.App.update_viewer()
            return
        if cmd.m_outputSub is None :
            print("failed to separate sub")
            self.App.update_viewer()
            return

        key = data.CData.make_key(data.CData.s_territoryType, 0, 1)
        terriObj = vtkObjInterface.CVTKObjInterface()
        terriObj.KeyType = data.CData.s_territoryType
        terriObj.Key = key
        terriObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 1.0, 0.0])
        terriObj.Opacity = 0.5
        terriObj.PolyData = cmd.m_outputWhole
        dataInst.add_vtk_obj(terriObj)
        # self.App.ref_key(key)

        key = data.CData.make_key(data.CData.s_territoryType, 0, 2)
        terriObj = vtkObjInterface.CVTKObjInterface()
        terriObj.KeyType = data.CData.s_territoryType
        terriObj.Key = key
        terriObj.Color = algLinearMath.CScoMath.to_vec3([0.5, 0.0, 0.5])
        terriObj.Opacity = 0.5
        terriObj.PolyData = cmd.m_outputSub
        dataInst.add_vtk_obj(terriObj)
        self.App.ref_key(key)

        self.App.update_viewer()


    @property
    def App(self) : 
        return self.m_mediator.m_mediator



if __name__ == '__main__' :
    pass


# print ("ok ..")

