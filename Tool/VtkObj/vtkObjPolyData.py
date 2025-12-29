import sys
import os
import numpy as np
import vtk

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileToolPath = os.path.dirname(fileAbsPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage

import vtkObj as vtkObj



class CVTKObjPolyData(vtkObj.CVTKObj) :
    def __init__(self, polyData : vtk.vtkPolyData) -> None:
        super().__init__()
        # input your code
        self.m_polyData = polyData
        self.m_mapper.SetInputData(polyData)
    def clear(self) :
        # input your code
        self.m_polyData = None
        super().clear()

    
    @property
    def PolyData(self) -> vtk.vtkPolyData :
        return self.m_polyData
    @PolyData.setter
    def PolyData(self, polyData : vtk.vtkPolyData) :
        self.m_polyData = polyData
        self.m_mapper.SetInputData(polyData)



    





if __name__ == '__main__' :
    pass


# print ("ok ..")

