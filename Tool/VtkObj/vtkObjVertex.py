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



class CVTKObjVertex(vtkObj.CVTKObj) :
    def __init__(self, vertex : np.ndarray, size : float = 1.0) -> None:
        super().__init__()
        # input your code
        self.m_vertex = vertex.copy()
        self.m_size = size
        self.m_polyData = algVTK.CVTK.create_poly_data_point(vertex)
        self.m_mapper.SetInputData(self.m_polyData)

        self.set_size(size)
    def clear(self) :
        # input your code
        self.m_vertex = None
        self.m_size = 1.0
        self.m_polyData = None
        super().clear()  

    def set_size(self, size : float) :
        self.m_actor.GetProperty().SetPointSize(size)
        self.m_size = size
    



if __name__ == '__main__' :
    pass


# print ("ok ..")

