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



class CVTKObjLine(vtkObj.CVTKObj) :
    def __init__(self) -> None:
        super().__init__()
        # input your code
        self.m_lineRes = vtk.vtkLineSource()
        self.m_mapper.SetInputConnection(self.m_lineRes.GetOutputPort())
        self.m_start = None
        self.m_end = None
        self.m_width = 1.0
    def clear(self) :
        # input your code
        self.m_lineRes = None
        self.m_start = None
        self.m_end = None
        self.m_width = 1.0
        super().clear()


    def set_line_width(self, width : float) :
        self.m_actor.GetProperty().SetLineWidth(width)
        self.m_width = width
    def set_pos(self, start : np.ndarray, end : np.ndarray) :
        self.m_start = start.copy()
        self.m_end = end.copy()
        self.m_lineRes.SetPoint1(start[0,0], start[0,1], start[0,2])
        self.m_lineRes.SetPoint2(end[0,0], end[0,1], end[0,2])
        self.m_lineRes.Update()

    def get_line_width(self) -> float :
        return self.m_width
    def get_pos(self) -> tuple :
        '''
        ret : (startPos, endPos)
        '''
        return (self.m_start, self.m_end)
    

    @property
    def Start(self) -> np.ndarray :
        return self.m_start
    @property
    def End(self) -> np.ndarray :
        return self.m_end

    
    



if __name__ == '__main__' :
    pass


# print ("ok ..")

