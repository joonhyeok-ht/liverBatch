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



class CVTKObjSphere(vtkObj.CVTKObj) :
    def __init__(self, center : np.ndarray, radius : float) -> None:
        super().__init__()
        # input your code
        self.m_radius = radius

        self.m_sphereSource = vtk.vtkSphereSource()
        self.m_sphereSource.SetCenter(center[0, 0], center[0, 1], center[0, 2])
        self.m_sphereSource.SetRadius(radius)
        self.m_sphereSource.Update()
        self.m_mapper.SetInputData(self.m_sphereSource.GetOutput())
    def clear(self) :
        # input your code
        self.m_sphereSource = None
        super().clear()


    
    @property
    def SphereSource(self) -> vtk.vtkSphereSource :
        return self.m_sphereSource
    @property
    def Radius(self) -> float :
        return self.m_radius
    @Radius.setter
    def Radius(self, radius : float) :
        self.m_radius = radius
        self.m_sphereSource.SetRadius(radius)
        self.m_sphereSource.Update()



    





if __name__ == '__main__' :
    pass


# print ("ok ..")

