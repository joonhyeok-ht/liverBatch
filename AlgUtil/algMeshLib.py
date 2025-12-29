import sys
import os

import numpy as np

import meshlib.mrmeshpy as mrmesh
import meshlib.mrmeshnumpy as mrmeshnp

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(fileAbsPath)
import algLinearMath



class CMeshLib :
    @staticmethod
    def meshlib_create(npVertex : np.ndarray, npIndex : np.ndarray) :
        mesh = mrmeshnp.meshFromFacesVerts(npIndex, npVertex)
        mesh.packOptimally()
        return mesh
    @staticmethod
    def meshlib_get_vertex(mesh) -> np.ndarray :
        npVertex = mrmeshnp.getNumpyVerts(mesh)
        return npVertex
    @staticmethod
    def meshlib_get_index(mesh) -> np.ndarray :
        npFace = mrmeshnp.getNumpyFaces(mesh.topology).astype(np.int32)
        return npFace
    @staticmethod
    def meshlib_load_stl(stlFullPath : str) :
        if os.path.exists(stlFullPath) == False :
            return None
        mesh = mrmesh.loadMesh(stlFullPath)
        mesh.packOptimally()
        return mesh
    @staticmethod
    def meshlib_save_stl(stlFullPath : str, mesh) :
        mrmesh.saveMesh(mesh, stlFullPath)
    @staticmethod
    def meshlib_component_count(mesh) -> int :
        components = mrmesh.getAllComponents(mesh)
        return len(components)
    # @staticmethod
    # def meshlib_decimation(mesh, targetTriCnt : int, cpuCnt = 12) :
    #     npFace = mrmeshnp.getNumpyFaces(mesh.topology)
    #     targetTriCnt = targetTriCnt
    #     deletedFace = npFace.shape[0] - targetTriCnt

    #     settings = mrmesh.DecimateSettings()
    #     # settings.maxTriangleAspectRatio = 0.5
    #     settings.maxDeletedFaces = deletedFace
    #     settings.maxError = 0.05 # Maximum error when decimation stops
    #     settings.subdivideParts = cpuCnt
    #     mrmesh.decimateMesh(mesh, settings)
    #     mesh.pack()
    #     return mesh
    @staticmethod
    def meshlib_decimation(mesh, triangleCnt : int) :
        # maxError 셋팅을 위한 bbox 대각선 계산 ***
        diag = mesh.computeBoundingBox().diagonal()
        error_ratio = 0.005 # 0.5% 오차허용 (중간 절충)

        # 원래 삼각형 수 확인
        initial_triangles = mesh.topology.numValidFaces()
        print(f"Initial triangle count: {initial_triangles}")

        # Repack mesh optimally.
        # It's not necessary but highly recommended to achieve the best performance in parallel processing
        mesh.packOptimally()

        # Setup decimate parameters
        settings = mrmesh.DecimateSettings()

        # Decimation stop thresholds, you may specify one or both
        settings.maxDeletedFaces = initial_triangles - triangleCnt # Number of faces to be deleted (현재triangle수 - target triangle수) 로 셋팅
        settings.maxError = diag * error_ratio #0.5 # Maximum error when decimation stops : 너무 작게 설정하면 원하는 target에 도달하지 못하고 stop됨

        # Number of parts to simultaneous processing, greatly improves performance by cost of minor quality loss.
        # Recommended to set to number of CPU cores or more available for the best performance
        settings.subdivideParts = 64

        # Decimate mesh
        mrmesh.decimateMesh(mesh, settings)

        return mesh
    @staticmethod
    def meshlib_healing(mesh) :
        '''
        mesh : meshlib mesh type
        '''
        # remove small components first
        area = mesh.area()
        bigComps = mrmesh.MeshComponents.getLargeByAreaComponents(mesh,area * 0.002,None)
        mesh.deleteFaces(mesh.topology.getValidFaces() - bigComps)

        # fill all holes
        for e in mesh.topology.findHoleRepresentiveEdges():
            mrmesh.fillHole(mesh,e)

        # fix possible multiple edges
        mrmesh.fixMultipleEdges(mesh)

        # remove self-intersections
        selfIntersSettings = mrmesh.SelfIntersections.Settings()
        selfIntersSettings.method = mrmesh.SelfIntersections.Settings.Method.CutAndFill
        selfIntersSettings.maxExpand = 2
        selfIntersSettings.relaxIterations = 2
        mrmesh.SelfIntersections.fix(mesh,selfIntersSettings)

        # remove small components at the end again (self-inter fix may lead to new ones)
        bigComps = mrmesh.MeshComponents.getLargeByAreaComponents(mesh,area * 0.002,None)
        mesh.deleteFaces(mesh.topology.getValidFaces() - bigComps)

        # fix other degeneracies
        tolerance = mesh.computeBoundingBox().diagonal()*1e-2
        degFaces = mrmesh.findDegenerateFaces(mesh,1e3)
        shortEdges = mrmesh.findShortEdges(mesh,tolerance*1e-2)
        degFaces |= mrmesh.getIncidentFaces(mesh.topology,shortEdges)
        mrmesh.expand(mesh.topology,degFaces,3)

        dSettings = mrmesh.DecimateSettings()
        dSettings.strategy = mrmesh.DecimateStrategy.ShortestEdgeFirst
        dSettings.maxError = tolerance * 0.1
        dSettings.criticalTriAspectRatio = 1e3
        dSettings.tinyEdgeLength = tolerance*1e-2
        dSettings.stabilizer = mrmesh.ResolveMeshDegenSettings().stabilizer
        dSettings.optimizeVertexPos = False
        dSettings.region = degFaces
        dSettings.maxAngleChange = mrmesh.ResolveMeshDegenSettings().maxAngleChange
        mrmesh.decimateMesh(mesh,dSettings)

        # pack (required for back-import to blender)
        mesh.pack()
        return mesh
    @staticmethod
    def meshlib_fill_hole(mesh) :
        hole_edges = mesh.topology.findHoleRepresentiveEdges()
        for e in hole_edges:
            #  Setup filling parameters
            params = mrmesh.FillHoleParams()
            params.metric = mrmesh.getUniversalMetric(mesh)
            #  Fill hole represented by `e`
            mrmesh.fillHole(mesh, e, params)
        return mesh
    
    # boolean
    @staticmethod
    def meshlib_boolean_subtraction(mesh0, mesh1) :
        '''
        desc : mesh0 - mesh1
        '''
        result = mrmesh.boolean(mesh0, mesh1, mrmesh.BooleanOperation.DifferenceAB)
        retMesh = result.mesh
        if not result.valid():
            return None
        return retMesh
    @staticmethod
    def meshlib_boolean_intersection(mesh0, mesh1) :
        '''
        desc : mesh0, mesh1 intersection 
        '''
        result = mrmesh.boolean(mesh0, mesh1, mrmesh.BooleanOperation.Intersection)
        retMesh = result.mesh
        if not result.valid():
            return None
        return retMesh
    @staticmethod
    def meshlib_boolean_union(mesh0, mesh1) :
        '''
        desc : mesh0, mesh1 union 
        '''
        result = mrmesh.boolean(mesh0, mesh1, mrmesh.BooleanOperation.Union)
        retMesh = result.mesh
        if not result.valid():
            return None
        return retMesh
    @staticmethod
    def meshlib_boolean_inside(mesh0, mesh1) :
        '''
        desc : mesh0 inside of mesh1
        '''
        result = mrmesh.boolean(mesh0, mesh1, mrmesh.BooleanOperation.InsideA)
        retMesh = result.mesh
        if not result.valid():
            return None
        return retMesh
    @staticmethod
    def meshlib_boolean_outside(mesh0, mesh1) :
        '''
        desc : mesh0 outside of mesh1
        '''
        result = mrmesh.boolean(mesh0, mesh1, mrmesh.BooleanOperation.OutsideA)
        retMesh = result.mesh
        if not result.valid():
            return None
        return retMesh


    def __init__(self) -> None:
        pass

