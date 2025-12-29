from typing import Any
import numpy as np
import matplotlib.pyplot as plt
import os, sys
import matplotlib.patches as patches
import json
import pandas as pd

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

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
    - ObserverVolumeCheckBlock
Input
    - "InputPhyInfo"        : conn(PhysicalInfoBlock -> OutputJson)
    - "InputSTLPath"        : stl path including reconstruction stl files
Output
    - "OutputCSV"           : csv file full path
Property
}
'''

class CSimpleDataFrame :
    def __init__(self, columnCount : int) -> None:
        self.m_listColumn = ["" for i in range(0, columnCount)]
        self.m_listIndex = []
        self.m_listRow = []
    def clear(self) :
        self.m_listColumn.clear()
        self.m_listIndex.clear()
        self.m_listRow.clear()


    def save(self, csvPath : str) :
        df = pd.DataFrame(self.m_listRow, columns=self.m_listColumn, index=self.m_listIndex)
        df.to_csv(csvPath)

    def set_column(self, columnInx : int, columnName) :
        self.m_listColumn[columnInx] = columnName
    def get_column(self, columnInx : int) :
        return self.m_listColumn[columnInx]
    def get_column_count(self) :
        return len(self.m_listColumn)
    def add_index_name(self, indexName) -> int:
        self.m_listIndex.append(indexName)
        self.m_listRow.append(["" for i in range(0, self.get_column_count())])
        return len(self.m_listIndex) - 1
    def get_index_name(self, index : int) :
        return self.m_listIndex[index]
    def set_index_name(self, index : int, indexName) :
        self.m_listIndex[index] = indexName
    def set_row(self, index, rowInx, value) :
        self.m_listRow[index][rowInx] = value
    def set_rows(self, index, listValue : list) :
        self.m_listRow[index] = listValue
    def get_row(self, index, rowInx) :
        return self.m_listRow[index][rowInx]
    def get_rows(self, index) :
        return self.m_listRow[index]


class CObserverVolumeCheck :
    def __init__(self) -> None:
        self.m_inputPhyInfo = ""
        self.m_inputSTLPath = ""
        self.m_outputCSV = ""
        self.m_json = None
    def process(self) :
        if os.path.exists(self.InputPhyInfo) == True :
            with open(self.InputPhyInfo, 'r') as fp :
                self.m_json = json.load(fp)
        else :
            print(f"not found {self.InputPhyInfo}")
            return
        if os.path.exists(self.InputSTLPath) == False :
            print(f"not found {self.InputSTLPath}")
            return

        simpleDataFrame = CSimpleDataFrame(3)
        simpleDataFrame.set_column(0, "Mask Volume")
        simpleDataFrame.set_column(1, "STL Volume")
        simpleDataFrame.set_column(2, "Error (0.0 ~ 1.0)")

        inputSTLPath = self.InputSTLPath
        listFileName = os.listdir(inputSTLPath)
        for fileName in listFileName :
            stlFullPath = os.path.join(inputSTLPath, fileName)
            ext = scoUtil.CScoUtilOS.get_ext(stlFullPath)
            if ext != ".stl" :
                continue

            stlVolume = scoUtil.CScoUtilVTK.get_stl_volume(stlFullPath, "mm")
            stlFileNameExpEst = scoUtil.CScoUtilOS.get_file_name_except_ext(stlFullPath)
            niftiVolume = self._get_nifti_volume(stlFileNameExpEst)
            error = self._get_error(niftiVolume, stlVolume)

            inx = simpleDataFrame.add_index_name(stlFileNameExpEst)
            simpleDataFrame.set_rows(inx, [niftiVolume, stlVolume, error])
        simpleDataFrame.save(self.OutputCSV)
    def clear(self) :
        self.m_inputPhyInfo = ""
        self.m_inputSTLPath = ""
        self.m_outputCSV = ""
        if self.m_json != None :
            self.m_json.clear()


    @property
    def InputPhyInfo(self) -> str :
        return self.m_inputPhyInfo
    @InputPhyInfo.setter
    def InputPhyInfo(self, inputPhyInfo : str) :
        self.m_inputPhyInfo = inputPhyInfo
    @property
    def InputSTLPath(self) -> str :
        return self.m_inputSTLPath
    @InputSTLPath.setter
    def InputSTLPath(self, inputSTLPath : str) :
        self.m_inputSTLPath = inputSTLPath
    @property
    def OutputCSV(self) -> str :
        return self.m_outputCSV
    @OutputCSV.setter
    def OutputCSV(self, outputCSV : str) :
        self.m_outputCSV = outputCSV
    

    def _get_nifti_volume(self, stlFileNameExceptExt : str) :
        dicNiftiInfo = self.m_json["NiftiList"]
        for key, value in dicNiftiInfo.items() :
            niftiFileNameExceptExt = key.split('.')[0]
            if niftiFileNameExceptExt == stlFileNameExceptExt :
                return value["Volume"]
        return 0
    def _get_error(self, maskCC : float, stlCC : float) :
        fRet = maskCC - stlCC
        if fRet < 0.0 :
            fRet = -fRet
        fRet = fRet / maskCC
        return fRet
    

