import sys
import os
import numpy as np
import vtk

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVMTK as algVMTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph

import niftiContainer as niftiContainer
import optionInfo as optionInfo
import reconstruction as reconstruction


class CCenterline() :
    @staticmethod
    def find_cell_index(findCellKey : str, polyData : vtk.vtkPolyData) -> tuple :
        '''
        ret : (vertexInx, cellInx)
        '''
        findCell = findCellKey
        if findCell == "minX" :
            vertexInx, cellInx = algVTK.CVTK.poly_data_get_info_vertcellid_by_min_axis(polyData, 0)
            return (vertexInx, cellInx)
        elif findCell == "maxX" :
            vertexInx, cellInx = algVTK.CVTK.poly_data_get_info_vertcellid_by_max_axis(polyData, 0)
            return (vertexInx, cellInx)
        elif findCell == "minY" :
            vertexInx, cellInx = algVTK.CVTK.poly_data_get_info_vertcellid_by_min_axis(polyData, 1)
            return (vertexInx, cellInx)
        elif findCell == "maxY" :
            vertexInx, cellInx = algVTK.CVTK.poly_data_get_info_vertcellid_by_max_axis(polyData, 1)
            return (vertexInx, cellInx)
        elif findCell == "minZ" :
            vertexInx, cellInx = algVTK.CVTK.poly_data_get_info_vertcellid_by_min_axis(polyData, 2)
            return (vertexInx, cellInx)
        elif findCell == "maxZ" :
            vertexInx, cellInx = algVTK.CVTK.poly_data_get_info_vertcellid_by_max_axis(polyData, 2)
            return (vertexInx, cellInx)
        else :
            print(f"centerline : {findCell} is not a valid findCell key")


    def __init__(self) -> None:
        self.m_inputOptionInfo = None
        self.m_inputNiftiContainer = None
        self.m_inputCLInfoIndex = -1
        self.m_inputPath = ""
        self.m_outputPath = ""

        self.m_clInfo = None
        self.m_clParam = None
        self.m_skeleton = None
    def clear(self) :
        # input your code
        self.m_inputOptionInfo = None
        self.m_inputNiftiContainer = None
        self.m_inputCLInfoIndex = -1
        self.m_inputPath = ""
        self.m_outputPath = ""

        self.m_clInfo = None
        self.m_clParam = None
        if self.m_skeleton is not None :
            self.m_skeleton.clear()
            self.m_skeleton = None
    def process(self) :
        if self.InputOptionInfo is None :
            print("centerline : not setting input optionInfo")
            return
        if self.InputNiftiContainer is None :
            print("centerline : not setting input nifti container")
            return 
        if self.InputCLInfoIndex == -1 :
            print("centerline : not setting input centerline index")
            return 
        if self.InputPath == "" :
            print("centerline : not setting input path")
            return 
        
        self.m_clInfo = self.InputOptionInfo.get_centerlineinfo(self.InputCLInfoIndex)
        self.m_clParam = self.InputOptionInfo.find_centerline_param(self.m_clInfo.CenterlineType)
        if self.m_clParam is None :
            print(f"centerline : not found centerline param {self.m_clInfo.CenterlineType}")
            return
        
        if os.path.exists(self.OutputPath) == False :
            print(f"centerline : not found output path {self.OutputPath}")
            return
        
        blenderName = self.m_clInfo.get_input_blender_name()
        stlFullPath = os.path.join(self.InputPath, f"{blenderName}.stl")
        if os.path.exists(stlFullPath) == False :
            print(f"centerline : not found {stlFullPath}")
            return
        polyData = algVTK.CVTK.load_poly_data_stl(stlFullPath)
        if polyData is None :
            print(f"centerline : failed loading {stlFullPath}")
            return

        print(f"centerline : Number of points {polyData.GetNumberOfPoints()}")
        print(f"centerline : Number of cells {polyData.GetNumberOfCells()}")

        findCell = self.m_clInfo.FindCell
        ret = self.find_cell_index(findCell, polyData)
        if ret is None :
            return
        
        # vertexInx = ret[0]
        cellInx = ret[1]
        advancementRatio = self.m_clParam.AdvancementRatio
        resamplingLength = self.m_clParam.ResamplingLength
        smoothingIter = self.m_clParam.SmoothingIter
        smoothingFactor = self.m_clParam.SmoothingFactor

        skelInfo = algVMTK.CVMTK.poly_data_center_line_network(polyData, cellInx, advancementRatio, resamplingLength, smoothingIter, smoothingFactor)
        self.m_skeleton = algSkeletonGraph.CSkeleton()
        self.m_skeleton.init_with_vtk_skel_info(skelInfo)

        # tree 구성 
        rootPos = self._get_root_pos(polyData)
        if rootPos is None :
            return
        rootCenterlineID = self.m_skeleton.find_nearest_centerline(rootPos).ID
        self.m_skeleton.build_tree(rootCenterlineID)

        # save skeleton 
        outputFileName = self.m_clInfo.OutputName
        outputFullPath = os.path.join(self.OutputPath, f"{outputFileName}.json")
        self.m_skeleton.save(outputFullPath, blenderName)
        print(f"centerline : saved skeleton {outputFileName}")
    

    # protected
    def _get_root_pos(self, polyData : vtk.vtkPolyData) -> np.ndarray :
        treeRoot = self.m_clInfo.TreeRootKey
        if treeRoot == "maskName" :
            maskName = self.m_clInfo.get_treeroot_mask_name()
            return self.__get_root_pos_by_mask_name(maskName)
        elif treeRoot == "blenderName" :
            blenderName = self.m_clInfo.get_treeroot_blender_name()
            return self.__get_root_pos_by_blender_name(blenderName)
        elif treeRoot == "axis" :
            findCell = self.m_clInfo.get_treeroot_axis()
            vertexInx, cellInx = self.find_cell_index(findCell, polyData)
            polyVertex = algVTK.CVTK.poly_data_get_vertex(polyData)
            return polyVertex[vertexInx].reshape(-1, 3)
        elif treeRoot == "nnPos" :
            return self.m_clInfo.get_treeroot_nnpos()
        else :
            print(f"centerline : {treeRoot} is not a valid treeRoot key.")
            return None


    # private
    def __get_root_pos_by_mask_name(self, maskName : str) -> np.ndarray :
        listNiftiInfo = self.InputNiftiContainer.find_nifti_info_list_by_name(maskName)
        if listNiftiInfo is None :
            print(f"centerline : not found nifti info {maskName}")
            return None
        
        niftiInfo = listNiftiInfo[0]
        niftiFullPath = niftiInfo.FullPath
        if niftiInfo.Valid == False :
            print(f"centerline : not found nifti {maskName}")
            return None
        
        phase = niftiInfo.MaskInfo.Phase
        phaseInfo = self.InputNiftiContainer.find_phase_info(phase)
        if phaseInfo is None :
            print(f"centerline : not found phaseInfo {phase}")
            return None
        
        vertex, origin, spacing, direction, size = algImage.CAlgImage.get_vertex_from_nifti(niftiFullPath)
        meanVector = algLinearMath.CScoMath.get_mean_vec3(vertex)
        matVTKPhy = algVTK.CVTK.get_vtk_phy_matrix_with_spacing(origin, spacing, direction, phaseInfo.Offset)
        meanVector = algLinearMath.CScoMath.mul_mat4_vec3(matVTKPhy, meanVector)

        return meanVector
    def __get_root_pos_by_blender_name(self, blenderName : str) -> np.ndarray :
        stlFullPath = os.path.join(self.m_inputStlPath, f"{blenderName}.stl")
        if os.path.exists(stlFullPath) == False :
            print(f"centerline : not found stl {blenderName}")
            return None
        
        polyData = algVTK.CVTK.load_poly_data_stl(stlFullPath)
        vertex = algVTK.CVTK.poly_data_get_vertex(polyData)
        meanVector = algLinearMath.CScoMath.get_mean_vec3(vertex)

        return meanVector


    
    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, inputOptionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = inputOptionInfo
    @property
    def InputNiftiContainer(self) -> niftiContainer.CNiftiContainer :
        return self.m_inputNiftiContainer
    @InputNiftiContainer.setter
    def InputNiftiContainer(self, inputNiftiContainer : niftiContainer.CNiftiContainer) :
        self.m_inputNiftiContainer = inputNiftiContainer
    @property
    def InputCLInfoIndex(self) -> int :
        return self.m_inputCLInfoIndex
    @InputCLInfoIndex.setter
    def InputCLInfoIndex(self, inputCLInfoIndex : int) :
        self.m_inputCLInfoIndex = inputCLInfoIndex
    @property
    def InputPath(self) -> str :
        return self.m_inputPath
    @InputPath.setter
    def InputPath(self, inputPath : str) :
        self.m_inputPath = inputPath
    @property
    def OutputPath(self) -> str :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath
    @property
    def Skeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_skeleton


import pickle

# class CCenterlineFromPkl() :
#     @staticmethod
#     def load_inst(fullPath) :
#         if os.path.exists(fullPath) == False :
#             return None
        
#         with open(fullPath, "rb") as fp:
#             inst = pickle.load(fp)
#         return inst
    
#     def __init__(self) :
#         self.m_inputPklFullPath = ""
#         self.m_inputIndex = -1
#     def clear(self) :
#         self.m_inputPklFullPath = ""
#         self.m_inputIndex = -1
#     def process(self) :
#         if self.InputPklFullPath == "" :
#             print("not setting InputPklName")
#             return
#         if self.InputIndex == -1 :
#             print("not setting InputIndex")
#             return
#         if os.path.exists(self.InputPklFullPath) == False :
#             print("not found pkl file")
#             return
        
#         dataInfo = CCenterlineFromPkl.load_inst(self.InputPklFullPath)
#         self._extract_cl(dataInfo)

#     def _extract_cl(self, dataInfo : optionInfo.CCLDataInfo) :
#         clInfo = dataInfo.get_clinfo(self.InputIndex)
#         clParam = dataInfo.get_clparam(self.InputIndex)
#         reconParam = dataInfo.get_reconparam(self.InputIndex)

#         pklPath = os.path.dirname(self.InputPklFullPath)
#         skelInfoPath = os.path.dirname(pklPath)
#         clInPath = pklPath
#         clOutPath = os.path.join(skelInfoPath, "out")

#         # patientPath = dataInfo.PatientPath
#         # clInPath = optionInfo.COptionInfo.pass_in_path(optionInfo.COptionInfo.s_processCLName)
#         # clInPath = os.path.join(patientPath, clInPath)
#         # clOutPath = optionInfo.COptionInfo.pass_out_path(optionInfo.COptionInfo.s_processCLName)
#         # clOutPath = os.path.join(patientPath, clOutPath)

#         blenderName = clInfo.get_input_blender_name()
#         stlFullPath = os.path.join(clInPath, f"{blenderName}.stl")
#         if os.path.exists(stlFullPath) == False :
#             print(f"centerline : not found {stlFullPath}")
#             return
#         polyData = algVTK.CVTK.load_poly_data_stl(stlFullPath)
#         if polyData is None :
#             print(f"centerline : failed loading {stlFullPath}")
#             return
        
#         print(f"centerline : Number of points {polyData.GetNumberOfPoints()}")
#         print(f"centerline : Number of cells {polyData.GetNumberOfCells()}")

#         findCell = clInfo.FindCell
#         ret = CCenterline.find_cell_index(findCell, polyData)
#         if ret is None :
#             return
        
#         # vertexInx = ret[0]
#         cellInx = ret[1]
#         advancementRatio = clParam.AdvancementRatio
#         resamplingLength = clParam.ResamplingLength
#         smoothingIter = clParam.SmoothingIter
#         smoothingFactor = clParam.SmoothingFactor

#         skelInfo = algVMTK.CVMTK.poly_data_center_line_network(polyData, cellInx, advancementRatio, resamplingLength, smoothingIter, smoothingFactor)
#         skeleton = algSkeletonGraph.CSkeleton()
#         skeleton.init_with_vtk_skel_info(skelInfo)

#         # tree 구성 
#         # rootPos = self._get_root_pos(polyData)
#         # if rootPos is None :
#         #     return
#         rootCenterlineID = 0
#         skeleton.build_tree(rootCenterlineID)

#         # save skeleton 
#         outputFileName = clInfo.OutputName
#         outputFullPath = os.path.join(clOutPath, f"{outputFileName}.json")
#         skeleton.save(outputFullPath, blenderName)
#         print(f"centerline : saved skeleton {outputFileName}")



#     @property
#     def InputPklFullPath(self) -> str :
#         return self.m_inputPklFullPath
#     @InputPklFullPath.setter
#     def InputPklFullPath(self, inputPklFullPath : str) :
#         self.m_inputPklFullPath = inputPklFullPath
#     @property
#     def InputIndex(self) -> int :
#         return self.m_inputIndex
#     @InputIndex.setter
#     def InputIndex(self, inputIndex : int) :
#         self.m_inputIndex = inputIndex


class CCenterlineWithPklStartCellID :
    @staticmethod
    def load_inst(fullPath) :
        if os.path.exists(fullPath) == False :
            return None
        
        with open(fullPath, "rb") as fp:
            inst = pickle.load(fp)
        return inst
    @staticmethod
    def get_root_pos(polydata : vtk.vtkPolyData, cellID : int) -> np.ndarray :
        cell = polydata.GetCell(cellID)
        point_id = cell.GetPointId(0)
        pointCoord = polydata.GetPoint(point_id)
        return algLinearMath.CScoMath.to_vec3([pointCoord[0], pointCoord[1], pointCoord[2]])
    
    
    def __init__(self) :
        self.m_inputPklFullPath = ""
        self.m_inputIndex = -1
        self.m_inputCellID = -1
    def clear(self) :
        self.m_inputPklFullPath = ""
        self.m_inputIndex = -1
        self.m_inputCellID = -1
    def process(self) :
        if self.InputPklFullPath == "" :
            print("not setting InputPklName")
            return
        if self.InputIndex == -1 :
            print("not setting InputIndex")
            return
        if os.path.exists(self.InputPklFullPath) == False :
            print("not found pkl file")
            return
        
        dataInfo = CCenterlineWithPklStartCellID.load_inst(self.InputPklFullPath)
        if self.InputCellID == -1 :
            self._extract_cl(dataInfo)
        else :
            self._extract_cl_with_cellID(dataInfo)

    def _extract_cl(self, dataInfo : optionInfo.CCLDataInfo) :
        clInfo = dataInfo.get_clinfo(self.InputIndex)
        clParam = dataInfo.get_clparam(self.InputIndex)

        pklPath = os.path.dirname(self.InputPklFullPath)
        skelInfoPath = os.path.dirname(pklPath)
        clInPath = pklPath
        clOutPath = os.path.join(skelInfoPath, "out")

        blenderName = clInfo.get_input_blender_name()
        stlFullPath = os.path.join(clInPath, f"{blenderName}.stl")
        if os.path.exists(stlFullPath) == False :
            print(f"centerline : not found {stlFullPath}")
            return
        polyData = algVTK.CVTK.load_poly_data_stl(stlFullPath)
        if polyData is None :
            print(f"centerline : failed loading {stlFullPath}")
            return
        
        print(f"centerline : Number of points {polyData.GetNumberOfPoints()}")
        print(f"centerline : Number of cells {polyData.GetNumberOfCells()}")

        findCell = clInfo.FindCell
        ret = CCenterline.find_cell_index(findCell, polyData)
        if ret is None :
            return
        
        # vertexInx = ret[0]
        cellInx = ret[1]
        advancementRatio = clParam.AdvancementRatio
        resamplingLength = clParam.ResamplingLength
        smoothingIter = clParam.SmoothingIter
        smoothingFactor = clParam.SmoothingFactor

        skelInfo = algVMTK.CVMTK.poly_data_center_line_network(polyData, cellInx, advancementRatio, resamplingLength, smoothingIter, smoothingFactor)
        skeleton = algSkeletonGraph.CSkeleton()
        skeleton.init_with_vtk_skel_info(skelInfo)

        # tree 구성 
        # rootPos = self._get_root_pos(polyData)
        # if rootPos is None :
        #     return
        rootCenterlineID = 0
        skeleton.build_tree(rootCenterlineID)

        # save skeleton 
        outputFileName = clInfo.OutputName
        outputFullPath = os.path.join(clOutPath, f"{outputFileName}.json")
        skeleton.save(outputFullPath, blenderName)
        print(f"centerline : saved skeleton {outputFileName}")
    def _extract_cl_with_cellID(self, dataInfo : optionInfo.CCLDataInfo) :
        clInfo = dataInfo.get_clinfo(self.InputIndex)
        clParam = dataInfo.get_clparam(self.InputIndex)

        pklPath = os.path.dirname(self.InputPklFullPath)
        skelInfoPath = os.path.dirname(pklPath)
        clInPath = pklPath
        clOutPath = os.path.join(skelInfoPath, "out")

        blenderName = clInfo.get_input_blender_name()
        vtpFullPath = os.path.join(clInPath, f"{blenderName}.vtp")
        if os.path.exists(vtpFullPath) == False :
            print(f"centerline : not found {vtpFullPath}")
            return
        polyData = algVTK.CVTK.load_poly_data_vtp(vtpFullPath)
        if polyData is None :
            print(f"centerline : failed loading {vtpFullPath}")
            return
        
        print(f"centerline : Number of points {polyData.GetNumberOfPoints()}")
        print(f"centerline : Number of cells {polyData.GetNumberOfCells()}")
        
        cellInx = self.InputCellID
        advancementRatio = clParam.AdvancementRatio
        resamplingLength = clParam.ResamplingLength
        smoothingIter = clParam.SmoothingIter
        smoothingFactor = clParam.SmoothingFactor

        skelInfo = algVMTK.CVMTK.poly_data_center_line_network(polyData, cellInx, advancementRatio, resamplingLength, smoothingIter, smoothingFactor)
        skeleton = algSkeletonGraph.CSkeleton()
        skeleton.init_with_vtk_skel_info(skelInfo)

        # tree 구성 
        rootPos = CCenterlineWithPklStartCellID.get_root_pos(polyData, cellInx)
        rootCenterlineID = skeleton.find_nearest_centerline(rootPos).ID

        # print(f"rootPos : {rootPos}")
        # print(f"clCount : {skeleton.get_centerline_count()}   rootCenterlineID : {rootCenterlineID}")

        skeleton.build_tree(rootCenterlineID)

        # save skeleton 
        outputFileName = clInfo.OutputName
        outputFullPath = os.path.join(clOutPath, f"{outputFileName}.json")
        skeleton.save(outputFullPath, blenderName)
        print(f"centerline : saved skeleton {outputFileName}")



    @property
    def InputPklFullPath(self) -> str :
        return self.m_inputPklFullPath
    @InputPklFullPath.setter
    def InputPklFullPath(self, inputPklFullPath : str) :
        self.m_inputPklFullPath = inputPklFullPath
    @property
    def InputIndex(self) -> int :
        return self.m_inputIndex
    @InputIndex.setter
    def InputIndex(self, inputIndex : int) :
        self.m_inputIndex = inputIndex
    @property
    def InputCellID(self) -> int :
        return self.m_inputCellID
    @InputCellID.setter
    def InputCellID(self, inputCellID : int) :
        self.m_inputCellID = inputCellID


if __name__ == '__main__' :
    pass


# print ("ok ..")

