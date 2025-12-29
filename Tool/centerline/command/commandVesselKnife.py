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



'''
desc 
    - cylinder knife mesh를 이용한 vessel cutting 
'''
class CCommandSepVesselKM(commandInterface.CCommand) :
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
            nowCnt = algVTK.CVTK.check_in_polydata(subPolyData, vertex)
            if  nowCnt > maxCnt :
                maxInx = inx
                maxCnt = nowCnt
        
        if maxInx == -1 :
            return None
        return listPolyData[maxInx]
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
        
        meshlibKnife = CCommandSepVesselKM.get_meshlib(knifePolydata)

        append_filter = vtk.vtkAppendPolyData()
        for subPolydata in listSubPolydata :
            subPolydata = CCommandSepVesselKM.dilation_polydata2(subPolydata, margin)
            append_filter.AddInputData(subPolydata)
        append_filter.Update()
        subPolydata = append_filter.GetOutput()

        meshlibSub = CCommandSepVesselKM.get_meshlib(subPolydata)
        meshlibKnife = algMeshLib.CMeshLib.meshlib_boolean_subtraction(meshlibKnife, meshlibSub)

        return CCommandSepVesselKM.get_vtkmesh(meshlibKnife)
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

        self.m_meshlibWholeVessel = CCommandSepVesselKM.get_meshlib(self.m_inputWholeVessel)
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

        meshlibKnife = CCommandSepVesselKM.get_meshlib(knifeMesh)
        meshlibRet = algMeshLib.CMeshLib.meshlib_boolean_intersection(self.m_meshlibWholeVessel, meshlibKnife)
        interMesh = CCommandSepVesselKM.get_vtkmesh(meshlibRet)

        retListMesh = algVTK.CVTK.get_sub_polydata(interMesh)
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
        
        meshlibKnife = CCommandSepVesselKM.get_meshlib(knifeMesh)
        meshlibRet = algMeshLib.CMeshLib.meshlib_boolean_subtraction(self.m_meshlibWholeVessel, meshlibKnife)
        vesselMesh = CCommandSepVesselKM.get_vtkmesh(meshlibRet)
        return algVTK.CVTK.get_sub_polydata(vesselMesh)
    def _check_valid_sub(self, subVessel : vtk.vtkPolyData) -> bool :
        if self.m_npCheckVertx is None :
            return True
        nowCnt = algVTK.CVTK.check_in_polydata(subVessel, self.m_npCheckVertx)
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
        clCurve = curveInfo.CCLCurve()
        clCurve.process(cl.Vertex, None, None, None)
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
            tangent = clCurve.Tangent[inx]
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
        sub = CCommandSepVesselKM.find_polydata_include_vertex(listPolydata, cl.Vertex[vertexIndex : ].reshape(-1, 3))
        if sub is None :
            print("not found sub")
            return None
        if self._check_valid_sub(sub) == False :
            return None
        # find whole
        whole = CCommandSepVesselKM.find_polydata_include_vertex(listPolydata, cl.Vertex[ : vertexIndex].reshape(-1, 3))
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
    def __init__(self, mediator) :
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
        sub = CCommandSepVesselKM.find_polydata_include_vertex(listPolydata, cl.Vertex[vertexIndex : ].reshape(-1, 3))
        # find whole
        whole = CCommandSepVesselKM.find_polydata_include_vertex(listPolydata, cl.Vertex[ : vertexIndex].reshape(-1, 3))
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
    def __init__(self, mediator) :
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
        whole = CCommandSepVesselKM.find_polydata_include_vertex(listPolydata, rootCL.Vertex)
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



'''
desc 
    - mesh 부위에 여러개의 centerline이 있어도 knife 절단이 가능 
    - 여러개의 centerline이 절단된 경우 m_inputWorldC와 가장 가까운 centerline을 기준으로 cutting 함 
    - m_inputWorldC는 보통 camera pos나 시점에 해당되는 좌표를 세팅해야 된다. 
'''
class CCommandMeshCutting(CCommandSepVesselKM) :
    @staticmethod
    def create_thick_triangle(A : np.ndarray, B : np.ndarray, C : np.ndarray, tangent : np.ndarray, thickness = 0.01) -> vtk.vtkPolyData :
        centroid = (A + B + C) / 3.0
        centroid = centroid.reshape(-1)
        A = A.reshape(-1)
        B = B.reshape(-1)
        C = C.reshape(-1)
        tangent = tangent.reshape(-1)

        half_t = thickness / 2.0

        # 2) Top / Bottom vertices
        A_top = A + tangent * half_t
        B_top = B + tangent * half_t
        C_top = C + tangent * half_t

        A_bottom = A - tangent * half_t
        B_bottom = B - tangent * half_t
        C_bottom = C - tangent * half_t

        # ccw 판단 
        AB = B - A
        AC = C - A
        normal = np.cross(AB, AC)
        normal /= np.linalg.norm(normal)
        # print(f"normal : {normal}")

        # dirToA = centroid - A
        dirToA = A_bottom - A_top
        dirToA /= np.linalg.norm(dirToA)
        # print(f"dirToA : {dirToA}")

        d = np.dot(normal, dirToA)
        # print(f"dot : {d}")
        if d >= -1e-8 : 
            A, B = B.copy(), A.copy()
            A_top = A + tangent * half_t
            B_top = B + tangent * half_t

            A_bottom = A - tangent * half_t
            B_bottom = B - tangent * half_t
            # print("check reverse")

        # 6 vertices
        vertices = np.vstack([
            A_top,
            B_top,
            C_top,
            A_bottom,
            B_bottom,
            C_bottom
        ])

        # 8 faces
        faces = np.array([
            # top
            [0, 1, 2],

            # bottom (reversed)
            [3, 5, 4],

            # sides
            [0, 1, 3],
            [1, 4, 3],

            [1, 4, 2],
            [2, 4, 5],

            [2, 5, 0],
            [0, 5, 3]
        ], dtype=int)

        return algVTK.CVTK.create_poly_data_triangle(vertices, faces)
    

    def __init__(self, mediator) :
        super().__init__(mediator)
        self.m_inputWorldA = None
        self.m_inputWorldB = None
        self.m_inputWorldC = None
    def clear(self) :
        self.m_inputWorldA = None
        self.m_inputWorldB = None
        self.m_inputWorldC = None
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
        
        knifeMesh = CCommandMeshCutting.create_thick_triangle(self.InputWorldA, self.InputWorldB, self.InputWorldC, tangent, 0.01)
        p0, p1 = CCommandSepVesselKM.get_normal_shifted_points(pt, tangent)

        meshlibKnife = CCommandSepVesselKM.get_meshlib(knifeMesh)
        meshlibRet = algMeshLib.CMeshLib.meshlib_boolean_intersection(self.m_meshlibWholeVessel, meshlibKnife)
        if meshlibRet is None :
            print("failed mesh boolean intersectiion")
            return
        interMesh = CCommandSepVesselKM.get_vtkmesh(meshlibRet)

        retListMesh = algVTK.CVTK.get_sub_polydata(interMesh)
        if retListMesh is None  :
            print("not found sub-polydata")
            return
        subCnt = len(retListMesh)

        if subCnt > 1 :
            meshInfo = CCommandSepVesselKM.find_intersected_polydata(retListMesh, p0, p1)
            # 교차된 mesh가 없다. 
            if meshInfo[0] is None :
                print("not found knife mesh")
                return
            knifeMesh = CCommandSepVesselKM.enhanced_knife(knifeMesh, meshInfo[1], margin=0.5)
        
        meshlibKnife = CCommandSepVesselKM.get_meshlib(knifeMesh)
        meshlibRet = algMeshLib.CMeshLib.meshlib_boolean_subtraction(self.m_meshlibWholeVessel, meshlibKnife)
        vesselMesh = CCommandSepVesselKM.get_vtkmesh(meshlibRet)
        self.m_outputListPolydata = algVTK.CVTK.get_sub_polydata(vesselMesh)

    
    # protected
    

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


if __name__ == '__main__' :
    pass


# print ("ok ..")

