import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import SimpleITK as sitk

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileToolPath = os.path.dirname(fileAbsPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algMeshLib as algMeshLib

import Block.optionInfo as optionInfo

import command.curveInfo as curveInfo

import data as data
import clMask as clMask



class CDataGroupLabeling :
    '''
    desc
        centerline을 label별로 grouping 한다. 
    
    m_dic 
        key : label
        value : [centerline0, centerline1, .. ]
    '''
    def __init__(self) :
        self.m_dic = {}
        self.m_skeleton = None
    def clear(self) :
        self.m_dic.clear()
        self.m_skeleton = None
    def process(self, skeleton : algSkeletonGraph.CSkeleton) :
        self.m_skeleton = skeleton

        iCnt = self.m_skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = self.m_skeleton.get_centerline(inx)
            self.attach_cl(cl)

    def get_label_count(self) -> int :
        return len(self.m_dic)
    def get_all_label(self) -> list :
        return list(self.m_dic.keys())
    def attach_cl(self, cl : algSkeletonGraph.CSkeletonCenterline) :
        label = cl.Name
        if label not in self.m_dic :
            self.m_dic[label] = []
        self.m_dic[label].append(cl)
    def find_list_cl(self, label : str) -> list :
        '''
        ret : [cl0, cl1, ..]
        '''
        if label in self.m_dic :
            return self.m_dic[label]
        else : 
            return None

class CDataGroupLabelingVertex(CDataGroupLabeling) :
    '''
    desc
        centerline을 label별로 grouping 한 후, centerline point들을 label별로 얻어온다.
    '''
    def __init__(self) :
        super().__init__()
        self.m_inputCLMask = None
    def clear(self) :
        self.m_inputCLMask = None
        super().clear()
    def process(self, skeleton : algSkeletonGraph.CSkeleton) :
        if self.InputCLMask is None :
            return
        super().process(skeleton)

    def get_vertex(self, label : str) -> np.ndarray :
        listCL = self.find_list_cl(label)
        if listCL is None :
            return None
        
        retVertex = []
        for cl in listCL : 
            iVertexCnt = cl.get_vertex_count()
            for vertexInx in range(1, iVertexCnt) :
                vertex = cl.get_vertex(vertexInx)
                if self.InputCLMask.get_flag(cl, vertexInx) == True :
                    vertex = vertex.reshape(-1)
                    retVertex.append(vertex)
        if len(retVertex) == 0 :
            return None
        
        return np.array(retVertex)
    

    @property
    def InputCLMask(self) -> clMask.CCLMask :
        return self.m_inputCLMask
    @InputCLMask.setter
    def InputCLMask(self, clMaskInst : clMask.CCLMask) :
        self.m_inputCLMask = clMaskInst


class CDataGroupLabelingPolyData(CDataGroupLabeling) :
    '''
    desc
        centerline을 label별로 grouping 한 후, polydata를 label별로 얻어오거나 세팅한다.
    '''
    def __init__(self) :
        super().__init__()
        self.m_dicPolyData = {}
        self.m_listLabel = []
    def clear(self) :
        self.m_dicPolyData.clear()
        self.m_listLabel.clear()
        super().clear()
    def process(self, skeleton : algSkeletonGraph.CSkeleton) :
        super().process(skeleton)
        
        listLabel = self.get_all_label()
        if listLabel is None :
            print("CDataGroupLabelingPolyData : not found label list")
            return
        
        for label in listLabel :
            self.m_dicPolyData[label] = None
        self.m_listLabel = self.get_all_polydata_label()

    def get_all_polydata_label(self) -> list :
        return list(self.m_dicPolyData.keys()) 
    def get_polydata_label(self, inx : int) -> str :
        return self.m_listLabel[inx]
    def find_polydata_label_index(self, targetLabel : str) -> int :
        for inx, label in enumerate(self.m_listLabel) :
            if label == targetLabel :
                return inx
        return -1
    def get_polydata_label_count(self) -> int :
        return len(self.m_listLabel)
    def get_polydata(self, label : str) -> vtk.vtkPolyData :
        if label in self.m_dicPolyData :
            return self.m_dicPolyData[label]
    def set_polydata(self, label : str, polyData : vtk.vtkPolyData) :
        if label in self.m_dicPolyData :
            self.m_dicPolyData[label] = polyData

if __name__ == '__main__' :
    pass


# print ("ok ..")

