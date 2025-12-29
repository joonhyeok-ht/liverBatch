import numpy as np
import matplotlib.pyplot as plt
import os, sys
import matplotlib.patches as patches
import pandas as pd
import vtk
import math
import json

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
dirPath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "../")
sys.path.append(dirPath)

import scoUtil
import scoData
import scoReg
import scoMath
import scoRenderObj
import scoSkeleton
import scoSkeletonVM
import scoBuffer
import scoBufferAlg


'''
Name
    - DetectingOveralpBlock (HuAlgKidOver_v1.0.1)
Input
    - "InputPath"       : overlap 검출 대상인 stl 파일들이 저장 된 폴더 
Output
    - "OutputPath"      : zz_overlap_xxxx.stl 파일들이 저장 될 폴더 
    - "OutputJsonPath"  : log가 기록 될 json 파일의 full 경로를 넣는다.  세팅하지 않는다면 log는 기록되지 않는다. 
Property
    - "Active"          : 0 or 1
    - "AddSrcStlFile"   : overlap 검출 대상인 src stl file name 추가 
    - "TargetStlFile"   : overlap 검출 대상인 target stl file name 추가
'''

class CDetectingOverlap() : 
    def __init__(self) -> None : 
        # input your code 
        self.m_inputPath = ""
        self.m_outputPath = ""
        self.m_outputJsonPath = ""
        self.m_listSrcStlFile = []
        self.m_targetStlFile = ""
    def process(self) :
        # input your code
        targetPolyData = None  
        listPolyData = []
        listSphere = []
        jsonData = {}
        jsonData["overlap count"] = 0
        jsonData["overlap list"] = []
        listOverlap = jsonData["overlap list"]

        for fileName in self.m_listSrcStlFile : 
            fullPath = os.path.join(self.m_inputPath, fileName)
            if os.path.exists(fullPath) == False :
                print(f"not found {fileName}")
                continue
            polyData = self._load_stl(fullPath)
            listPolyData.append(polyData)
        
        fullPath = os.path.join(self.m_inputPath, self.TargetStlFile)
        if os.path.exists(fullPath) == False :
            print(f"not found {self.TargetStlFile}")
            return
        targetPolyData = self._load_stl(fullPath)

        for srcPolyData in listPolyData :
            booleanOp = vtk.vtkBooleanOperationPolyDataFilter()
            booleanOp.SetOperationToIntersection()
            booleanOp.SetInputData(0, srcPolyData)
            booleanOp.SetInputData(1, targetPolyData)
            booleanOp.Update()

            listTmp = self._get_connectivity_poly_data(booleanOp.GetOutput())
            for polyData in listTmp :
                sphere, center, radius = self._get_sphere_poly_data(polyData)
                listSphere.append(sphere)

                dicOverlapInfo = {}
                dicOverlapInfo["center"] = center
                dicOverlapInfo["radius"] = radius
                listOverlap.append(dicOverlapInfo)

        jsonData["overlap count"] = len(listSphere)
        
        # Check the previously created zz_overlap_xxx.stl files.
        filelist = os.listdir(self.m_outputPath)
        overlap_det_file_cnt = 0
        for item in filelist :
            if "zz_" in item :
                overlap_det_file_cnt = overlap_det_file_cnt + 1

        for inx, sphere in enumerate(listSphere) :
            inx_new = inx + overlap_det_file_cnt
            fileName = "zz_overlap_{0:03d}.stl".format(inx_new)
            fullPath = os.path.join(self.m_outputPath, fileName)
            self._save_polydata_to_stl(fullPath, sphere)
            print(f"saved {fullPath}")
        
        # save overlap info 
        if self.OutputJsonPath == "" :
            return
        with open(self.OutputJsonPath, 'w') as f :
            json.dump(jsonData, f, indent = 4)
    def clear(self) :
        # input your code 
        self.m_inputPath = ""
        self.m_outputPath = ""
        self.m_outputJsonPath = ""
        self.m_listSrcStlFile.clear()
        self.m_targetStlFile = ""


    def add_src_stl_filename(self, niftiFileName : str) :
        self.m_listSrcStlFile.append(niftiFileName)
    def get_src_stl_filename_count(self) :
        return len(self.m_listSrcStlFile)
    def get_src_stl_filename(self, inx : int) :
        return self.m_listSrcStlFile[inx]
    

    # protected 
    def _load_stl(self, stlFileName : str) -> vtk.vtkPolyData :
        reader = vtk.vtkSTLReader()
        reader.SetFileName(stlFileName)
        reader.Update()
        return reader.GetOutput()
    def _save_polydata_to_stl(self, fileName : str, polyData) :
        writer = vtk.vtkSTLWriter()
        writer.SetInputData(polyData)
        writer.SetFileTypeToBinary()
        writer.SetFileName(fileName)
        writer.Write()
    def _get_connectivity_poly_data(self, polyData : vtk.vtkPolyData) -> list : 
        connectivity = vtk.vtkPolyDataConnectivityFilter()###
        connectivity.SetInputData(polyData)
        connectivity.SetExtractionModeToAllRegions()
        connectivity.Update()

        connectivity.SetExtractionModeToSpecifiedRegions()

        listPolyData = []
        iCnt = connectivity.GetNumberOfExtractedRegions()

        for i in range(0, iCnt) :
            connectivity.AddSpecifiedRegion(i)
            if i > 0 :
                connectivity.DeleteSpecifiedRegion(i - 1)
            connectivity.Update()
            
            polyData = vtk.vtkPolyData()
            polyData.ShallowCopy(connectivity.GetOutput())
            listPolyData.append(polyData)
        
        return listPolyData
    def _get_sphere_poly_data(self, polyData : vtk.vtkPolyData) -> vtk.vtkPolyData :
        '''
        ret : tuple
              (vtk.vtkPolyData, listCenter, radius)
        '''
        min = [100000.0, 100000.0, 100000.0]
        max = [-100000.0, -100000.0, -100000.0]
        for i in range(polyData.GetNumberOfCells()):
            cell = polyData.GetCell(i)
            for j in range(cell.GetNumberOfPoints()) :
                pointID = cell.GetPointId(j)
                point = polyData.GetPoint(pointID)
                for k in range(3) :
                    if point[k] < min[k] :
                        min[k] = point[k]
                    if point[k] > max[k] :
                        max[k] = point[k]
        center = [0.0, 0.0, 0.0]
        radius = [0.0, 0.0, 0.0]
        for i in range(3) :
            center[i] = (min[i] + max[i]) / 2.0
            radius[i] = math.fabs((max[i] - min[i]) / 2.0)
        radius.sort(reverse = True)
        radius = radius[0]

        # print(f"center : {center}, radius : {radius}")

        sphere = vtk.vtkSphereSource()
        sphere.SetRadius(radius)
        sphere.SetCenter(center[0], center[1], center[2])
        sphere.Update()
        return (sphere.GetOutput(), center, radius)


    @property
    def InputPath(self) :
        return self.m_inputPath
    @InputPath.setter
    def InputPath(self, inputPath : str) :
        self.m_inputPath = inputPath
    @property
    def OutputPath(self) :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath
        dirPath = outputPath
        if not os.path.exists(dirPath) :
            os.makedirs(dirPath)
    @property
    def OutputJsonPath(self) :
        return self.m_outputJsonPath
    @OutputJsonPath.setter
    def OutputJsonPath(self, outputJsonPath : str) :
        self.m_outputJsonPath = outputJsonPath
        dirPath = os.path.dirname(outputJsonPath)
        if not os.path.exists(dirPath) :
            os.makedirs(dirPath)
    @property
    def TargetStlFile(self) :
        return self.m_targetStlFile
    @TargetStlFile.setter
    def TargetStlFile(self, targetStlFile : str) :
        self.m_targetStlFile = targetStlFile


if __name__ == '__main__' :
    inputPath = "/nas124/output/Nep_0032/Save/Stl"
    outputPath = "/nas124/output/Nep_0032/Save/Stl"

    test = CDetectingOverlap()
    test.InputPath = inputPath
    test.OutputPath = outputPath
    test.add_src_stl_filename("Renal_artery.stl")
    test.add_src_stl_filename("Renal_vein.stl")
    test.TargetStlFile = "Ureter.stl"
    test.process()



