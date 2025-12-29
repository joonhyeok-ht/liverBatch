import sys
import os
import numpy as np
import vtk
import json

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algVTK as algVTK
import AlgUtil.algVMTK as algVMTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph



class CCenterlineInterface : 
    def __init__(self) :
        self.m_inputFile = ""
        self.m_inputIndex = -1
        self.m_inputVTPName = ""
        self.m_inputCellID = -1

        self.m_advancementRatio = 1.001
        self.m_resamplingLength = 1.0
        self.m_smoothingIter = 10
        self.m_smoothingFactor = 0.1

        self.m_blenderName = ""
        self.m_jsonName = ""

        self.m_outputPatientPath = ""
        self.m_polydata = None
    def clear(self) :
        self.m_inputFile = ""
        self.m_inputIndex = -1
        self.m_inputVTPName = ""
        self.m_inputCellID = -1

        self.m_advancementRatio = 1.001
        self.m_resamplingLength = 1.0
        self.m_smoothingIter = 10
        self.m_smoothingFactor = 0.1

        self.m_blenderName = ""
        self.m_jsonName = ""

        self.m_outputPatientPath = ""
        self.m_polydata = None
    def process(self) -> bool :
        if self.InputIndex == -1 :
            return False
        if self.InputVTPName == "" :
            return False
        if self.InputCellID == -1 :
            return False
        
        if os.path.exists(self.InputFile) == False :
            print(f"not found file {os.path.basename(self.InputFile)}")
            return False
        with open(self.InputFile, 'r', encoding="utf-8") as fp :
            dicData = json.load(fp)
        
        listSkelInfo = dicData["skelInfo"]
        iSkelInfoCnt = len(listSkelInfo)
        if self.InputIndex >= iSkelInfoCnt :
            print(f"invalid skelinfo inde : {self.InputIndex}")
            return False
        
        skelInfo = listSkelInfo[self.InputIndex]
        self.m_advancementRatio = skelInfo[0]
        self.m_resamplingLength = skelInfo[1]
        self.m_smoothingIter = skelInfo[2]
        self.m_smoothingFactor = skelInfo[3]
        self.m_blenderName = self.InputVTPName
        self.m_jsonName = self.InputVTPName

        self.m_outputPatientPath = os.path.dirname(self.InputFile)

        clInPath = self.get_skelinfo_in_path()
        vtpFullPath = os.path.join(clInPath, f"{self.m_blenderName}.vtp")
        if os.path.exists(vtpFullPath) == False :
            print(f"centerline : not found {os.path.basename(vtpFullPath)}")
            return False
        self.m_polydata = algVTK.CVTK.load_poly_data_vtp(vtpFullPath)
        if self.m_polydata is None :
            print(f"centerline : failed loading {os.path.basename(vtpFullPath)}")
            return False
        
        return True
    
    def get_skelinfo_in_path(self) -> str :
        subPath = os.path.join("SkelInfo", "in")
        return os.path.join(self.OutputPatientPath, subPath)
    def get_skelinfo_out_path(self) -> str :
        subPath = os.path.join("SkelInfo", "out")
        return os.path.join(self.OutputPatientPath, subPath)
    def get_vertex(self, polydata : vtk.vtkPolyData, cellID : int) -> np.ndarray :
        cell = polydata.GetCell(cellID)
        pointId = cell.GetPointId(0)
        return np.array(polydata.GetPoint(pointId)).reshape(-1, 3)

    
    @property
    def InputFile(self) -> str :
        return self.m_inputFile
    @InputFile.setter
    def InputFile(self, file : str) :
        self.m_inputFile = file
    @property
    def InputIndex(self) -> int :
        return self.m_inputIndex
    @InputIndex.setter
    def InputIndex(self, index : int) :
        self.m_inputIndex = index
    @property
    def InputVTPName(self) -> str :
        return self.m_inputVTPName
    @InputVTPName.setter
    def InputVTPName(self, inputVTPName : str) :
        self.m_inputVTPName = inputVTPName
    @property
    def InputCellID(self) -> int :
        return self.m_inputCellID
    @InputCellID.setter
    def InputCellID(self, inputCellID : int) :
        self.m_inputCellID = inputCellID
    
    @property
    def OutputPatientPath(self) -> str :
        return self.m_outputPatientPath
    @property
    def PolyData(self) -> vtk.vtkPolyData :
        return self.m_polydata


class CCenterlineNormal(CCenterlineInterface) :
    def __init__(self) :
        super().__init__()
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) -> bool :
        if super().process() == False :
            return False
        
        cellInx = self.InputCellID
        advancementRatio = self.m_advancementRatio
        resamplingLength = self.m_resamplingLength
        smoothingIter = self.m_smoothingIter
        smoothingFactor = self.m_smoothingFactor
        polydata = self.PolyData
        rootPos = self.get_vertex(polydata, cellInx)

        skelInfo = algVMTK.CVMTK.poly_data_center_line_network(polydata, cellInx, advancementRatio, resamplingLength, smoothingIter, smoothingFactor)
        skeleton = algSkeletonGraph.CSkeleton()
        skeleton.init_with_vtk_skel_info(skelInfo)

        rootCenterlineID = skeleton.find_nearest_centerline(rootPos).ID
        skeleton.build_tree(rootCenterlineID)

        outputFileName = self.m_jsonName
        clOutPath = self.get_skelinfo_out_path()
        outputFullPath = os.path.join(clOutPath, f"{outputFileName}.json")
        skeleton.save(outputFullPath, self.m_blenderName)
        print(f"centerline : saved skeleton {os.path.basename(outputFileName)}")
        
        return True
class CCenterlineEnhanced(CCenterlineInterface) :
    @staticmethod
    def resampling_centerline(clPt : np.ndarray, clRadius : np.ndarray, spacing : float) :
        '''
        Returns
        -------
        newPts : np.ndarray
            (M, 3) 균일 간격으로 보간된 점들
        newRadius : np.ndarray
            (M,) 각 점에 대응되는 반경
        '''
        diffs = np.diff(clPt, axis=0)
        seg_lengths = np.linalg.norm(diffs, axis=1)
        dist = np.concatenate(([0], np.cumsum(seg_lengths)))
        total_length = dist[-1]

        new_dist = np.arange(0, total_length, spacing)
        if new_dist.size == 0 :
            return None
        if new_dist[-1] < total_length :
            new_dist = np.append(new_dist, total_length)
        
        newPts = np.zeros((len(new_dist), 3))
        for i in range(3) :
            newPts[:, i] = np.interp(new_dist, dist, clPt[:, i])
        
        newRadius = None
        if clRadius is not None :
            newRadius = np.interp(new_dist, dist, clRadius)

        return newPts, newRadius


    def __init__(self) :
        super().__init__()
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) -> bool :
        if super().process() == False :
            return False
        
        cellInx = self.InputCellID
        advancementRatio = self.m_advancementRatio
        resamplingLength = self.m_resamplingLength
        smoothingIter = self.m_smoothingIter
        smoothingFactor = self.m_smoothingFactor
        polydata = self.PolyData

        rootPos = self.get_vertex(polydata, cellInx)

        skelInfo = algVMTK.CVMTK.poly_data_enhanced_center_line_network(polydata, cellInx, advancementRatio)
        skeleton = algSkeletonGraph.CSkeleton()
        skeleton.init_with_vtk_skel_info(skelInfo)

        # rebuild skeleton
        iCnt = skeleton.get_centerline_count()
        # centerline resampling
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            ret = CCenterlineEnhanced.resampling_centerline(cl.Vertex, cl.Radius, resamplingLength)
            if ret is None :
                print(f"failed centerline extraction : {inx}")
                continue
            cl.Vertex = ret[0]
            cl.Radius = ret[1]
        skeleton.rebuild_centerline_related_data()

        rootCenterlineID = skeleton.find_nearest_centerline(rootPos).ID
        skeleton.build_tree(rootCenterlineID)

        vertex = algVTK.CVTK.poly_data_get_vertex(polydata)
        index = algVTK.CVTK.poly_data_get_triangle_index(polydata)
        print(f"Sub InputVTPName : {self.InputVTPName}")
        print(f"Sub cnt : {vertex.shape[0]}, {index.shape[0]}")
        print(f"Sub cellInx : {cellInx}")
        print(f"Sub rootPos : {rootPos}")
        print(f"Sub rootCLID : {rootCenterlineID}")

        outputFileName = self.m_jsonName
        clOutPath = self.get_skelinfo_out_path()
        outputFullPath = os.path.join(clOutPath, f"{outputFileName}.json")
        skeleton.save(outputFullPath, self.m_blenderName)
        print(f"centerline : saved skeleton {os.path.basename(outputFileName)}")
        
        return True


if __name__ == '__main__' :
    pass


# print ("ok ..")

