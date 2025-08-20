import sys
import os
import numpy as np

import vtk
from vmtk import vtkvmtk
from vmtk import vmtkcenterlines, vmtkcenterlinestonumpy, vmtknetworkextraction, vmtkdelaunayvoronoi, vmtknumpytocenterlines, vmtksurfacecapper
from vmtk import vmtklineresampling

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(fileAbsPath)
import algVTK

'''
- remove_duplicated_vertex는 open3d에 비해 성능이 안 좋다.
'''

class CVMTK :
    # centerline
    @staticmethod
    def poly_data_center_line(polyData : vtk.vtkPolyData, startVertexInx : int, endVertexInx : int) :
        radiusArrayName = "MaximumInscribedSphereRadius"
        costFunction = "1/R"

        sourceSeedIds = vtk.vtkIdList()
        targetSeedIds = vtk.vtkIdList()

        sourceSeedIds.InsertNextId(startVertexInx)
        targetSeedIds.InsertNextId(endVertexInx)

        centerlineFilter = vtkvmtk.vtkvmtkPolyDataCenterlines()
        centerlineFilter.SetInputData(polyData)
        centerlineFilter.SetSourceSeedIds(sourceSeedIds)
        centerlineFilter.SetTargetSeedIds(targetSeedIds)
        centerlineFilter.SetRadiusArrayName(radiusArrayName)
        centerlineFilter.SetCostFunction(costFunction)
        centerlineFilter.Update()
        return centerlineFilter.GetOutput()
    @staticmethod
    def poly_data_center_line_network(
        polyData : vtk.vtkPolyData, startCellInx : int, 
        advancementRatio=1.0,
        resamplingLength=1.0,
        smoothingIter=10, smoothingFactor=0.1
        ) -> list :
        '''
        advancement_ratio : 1.0 (default), 1.001 (기존)
        resamplingLength : 1.0 (default)
            - centerline point들을 resamplingLength 간격으로 균일하게 나눈다.
        smoothingIter : 10 (default)
        smoothingFactor : 0.1 (default)

        retSkelInfo : 
            [
                npTopology,
                [npVertex, npRadius],
                ..
            ]
        '''
        polyData.BuildLinks()
        polyData.DeleteCell(startCellInx)
        polyData.RemoveDeletedCells()

        radiusArrayName = 'Radius'
        topologyArrayName = 'Topology'
        marksArrayName = 'Marks'

        networkExtraction = vtkvmtk.vtkvmtkPolyDataNetworkExtraction()
        networkExtraction.SetInputData(polyData)
        networkExtraction.SetAdvancementRatio(advancementRatio)
        networkExtraction.SetRadiusArrayName(radiusArrayName)
        networkExtraction.SetTopologyArrayName(topologyArrayName)
        networkExtraction.SetMarksArrayName(marksArrayName)
        networkExtraction.Update()

        network = networkExtraction.GetOutput()
        graphLayout = networkExtraction.GetGraphLayout()

        lineResampling = vmtklineresampling.vmtkLineResampling()
        lineResampling.Surface = network
        lineResampling.Length = resamplingLength
        lineResampling.Execute()
        resamplenetwork = lineResampling.Surface

        centerlineSmoothing = vtkvmtk.vtkvmtkCenterlineSmoothing()
        centerlineSmoothing.SetInputData(resamplenetwork)
        centerlineSmoothing.SetNumberOfSmoothingIterations(smoothingIter)
        centerlineSmoothing.SetSmoothingFactor(smoothingFactor)
        centerlineSmoothing.Update()
        centerline = centerlineSmoothing.GetOutput()

        convert = vmtkcenterlinestonumpy.vmtkCenterlinesToNumpy()
        convert.Centerlines = centerline
        convert.LogOn = False
        convert.Execute()
        ad = convert.ArrayDict
        # print(ad['CellData']['Topology'])
        cellDataTopology = ad['CellData']['Topology']
        newPoints = ad['Points']
        newRadius = ad['PointData']['Radius']

        retSkelInfo = []
        retSkelInfo.append(cellDataTopology)
        for cell in ad['CellData']['CellPointIds']:
            tmp = convert.ArrayDict
            npIndex = cell
            npVertex = newPoints[npIndex].reshape(-1, 3)
            npRadius = newRadius[npIndex].reshape(-1)

            retSkelInfo.append([npVertex, npRadius])
        return retSkelInfo
    @staticmethod
    def poly_data_enhanced_center_line_network(polyData : vtk.vtkPolyData, startCellInx : int) -> list :
        '''
        retSkelInfo : 
            [
                npTopology,
                [npVertex, npRadius],
                ..
            ]
        '''
        polyData.BuildLinks()
        polyData.DeleteCell(startCellInx)
        polyData.RemoveDeletedCells()

        radiusArrayName = 'Radius'
        topologyArrayName = 'Topology'
        marksArrayName = 'Marks'
        advancementRatio = 1.001

        networkExtraction = vtkvmtk.vtkvmtkPolyDataNetworkExtraction()
        networkExtraction.SetInputData(polyData)
        networkExtraction.SetAdvancementRatio(advancementRatio)
        networkExtraction.SetRadiusArrayName(radiusArrayName)
        networkExtraction.SetTopologyArrayName(topologyArrayName)
        networkExtraction.SetMarksArrayName(marksArrayName)
        networkExtraction.Update()

        network = networkExtraction.GetOutput()
        graphLayout = networkExtraction.GetGraphLayout()

        convert = vmtkcenterlinestonumpy.vmtkCenterlinesToNumpy()
        convert.Centerlines = network
        convert.LogOn = False
        convert.Execute()
        ad = convert.ArrayDict
        # print(ad['CellData']['Topology'])
        cellDataTopology = ad['CellData']['Topology']
        newPoints = ad['Points']
        newRadius = ad['PointData']['Radius']

        # nodeIndexToIgnore = np.where(cellDataTopology[:,0] == 0)[0][0]
        # keepCellConnectivityList = []
        # pointIdxToKeep = np.array([])
        # removeCellLength = 0
        
        # for loopIdx, cellConnectivityList in enumerate(ad['CellData']['CellPointIds']):
        #     if loopIdx == nodeIndexToIgnore:
        #         removeCellStartIdx = cellConnectivityList[0]
        #         removeCellEndIdx = cellConnectivityList[-1]
        #         removeCellLength = cellConnectivityList.size
        #         if (removeCellEndIdx + 1) - removeCellStartIdx != removeCellLength:
        #             raise(ValueError)
        #         continue
        #     else:
        #         rescaledCellConnectivity = np.subtract(cellConnectivityList, removeCellLength, where=cellConnectivityList >= removeCellLength)
        #         keepCellConnectivityList.append(rescaledCellConnectivity)
        #         pointIdxToKeep = np.concatenate((pointIdxToKeep, cellConnectivityList)).astype(int)
        # newPoints = ad['Points'][pointIdxToKeep]
        # newRadius = ad['PointData']['Radius'][pointIdxToKeep]

        tessalation = vmtkdelaunayvoronoi.vmtkDelaunayVoronoi()
        tessalation.Surface = polyData
        tessalation.Execute()

        retSkelInfo = []
        retSkelInfo.append(cellDataTopology)
        for cell in ad['CellData']['CellPointIds']:
            cl = CVMTK._compute_centerline_branch(
                polyData, 
                tessalation.DelaunayTessellation, 
                tessalation.VoronoiDiagram,
                tessalation.PoleIds, 
                cell, newPoints
                )
            convert = vmtkcenterlinestonumpy.vmtkCenterlinesToNumpy()
            convert.Centerlines = cl
            convert.LogOn = False
            convert.Execute()

            tmp = convert.ArrayDict
            npIndex = tmp['CellData']['CellPointIds']
            npVertex = tmp['Points'][npIndex].reshape(-1, 3)
            npRadius = tmp['PointData']['MaximumInscribedSphereRadius'][npIndex].reshape(-1)

            retSkelInfo.append([npVertex, npRadius])
        return retSkelInfo
        
        
    


    # static private
    @staticmethod
    def _compute_centerlines_network(surfaceAddress, delaunayAddress, voronoiAddress, poleIdsAddress, cell, points):
        surface = vtk.vtkPolyData(surfaceAddress)
        delaunay = vtk.vtkUnstructuredGrid(delaunayAddress)
        voronoi = vtk.vtkPolyData(voronoiAddress)
        poleIds = vtk.vtkIdList(poleIdsAddress)

        cl = CVMTK._compute_centerline_branch(surface, delaunay, voronoi, poleIds, cell, points)

        clConvert = vmtkcenterlinestonumpy.vmtkCenterlinesToNumpy()
        clConvert.Centerlines = cl
        clConvert.LogOn = 0
        clConvert.Execute()
        return clConvert.ArrayDict
    @staticmethod
    def _compute_centerline_branch(surface, delaunay, voronoi, poleIds, cell, points):
        cellStartIdx = cell[0]
        cellEndIdx = cell[-1]
        cellStartPoint = points[cellStartIdx].tolist()
        cellEndPoint = points[cellEndIdx].tolist()
        cl = vmtkcenterlines.vmtkCenterlines()
        cl.Surface = surface
        cl.DelaunayTessellation = delaunay
        cl.VoronoiDiagram = voronoi
        cl.PoleIds = poleIds
        cl.SeedSelectorName = 'pointlist'
        cl.StopFastMarchingOnReachingTarget = 1
        cl.SourcePoints = cellStartPoint
        cl.TargetPoints = cellEndPoint
        cl.LogOn = 0
        cl.Execute()
        return cl.Centerlines



    def __init__(self) -> None:
        pass

