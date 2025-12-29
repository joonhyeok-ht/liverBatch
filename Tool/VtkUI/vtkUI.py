import sys
import os
import numpy as np
import vtk

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
from PySide6.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileToolPath = os.path.dirname(fileAbsPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import AlgUtil.algVTK as algVTK
import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage

import VtkObj.vtkObj as vtkObj



class CVTKUI() :
    def __init__(self, layout, parentWidget : QWidget, mediator) -> None:
        self.m_mediator = mediator
        self.m_parentWidget = parentWidget
        self.m_renderer = vtk.vtkRenderer()
        self.m_widget = QVTKRenderWindowInteractor(parentWidget)
        layout.addWidget(self.m_widget)
        self.m_widget.GetRenderWindow().AddRenderer(self.m_renderer)
    def clear(self) :
        self.m_mediator = None
        self.m_renderer = None
        self.m_widget = None


    def set_interactor_style(self, interactorStyle) :
        interactor = self.m_widget.GetRenderWindow().GetInteractor()
        interactor.SetInteractorStyle(interactorStyle)
    def set_background(self, color : np.ndarray) :
        self.m_renderer.SetBackground(color[0, 0], color[0, 1], color[0, 2])
    def set_size(self, width : int, height : int) :
        self.m_widget.GetRenderWindow().SetSize(width, height)
        self.m_parentWidget.setFixedSize(width, height)
        


    def update_render(self) :
        self.m_widget.GetRenderWindow().Render()
    def start(self) :
        self.m_widget.GetRenderWindow().Render()
        self.m_widget.Start()

    def add_vtk_obj(self, vtkObj : vtkObj.CVTKObj) :
        self.m_renderer.AddActor(vtkObj.Actor)
    def get_vtk_obj_count(self) -> int :
        return self.m_renderer.GetActors().GetNumberOfItems()
    def is_registered_vtk_obj(self, vtkObj : vtkObj.CVTKObj) :
        actors = self.m_renderer.GetActors()
        actors.InitTraversal()
        for _ in range(actors.GetNumberOfItems()):
            existingActor = actors.GetNextActor()
            if existingActor == vtkObj.Actor :
                return True
        return False
    def remove_vtk_obj(self, vtkObj : vtkObj.CVTKObj) :
        self.m_renderer.RemoveActor(vtkObj.Actor)
    def remove_all_vtk_obj(self) :
        actors = self.m_renderer.GetActors()
        actors.InitTraversal()
        for _ in range(actors.GetNumberOfItems()):
            actor = actors.GetNextActor()
            self.m_renderer.RemoveActor(actor)

        

    @property
    def Mediator(self) :
        return self.m_mediator
    @property
    def Widget(self) -> QVTKRenderWindowInteractor :
        return self.m_widget
    @property
    def Renderer(self) -> vtk.vtkRenderer :
        interactor = self.m_widget.GetRenderWindow().GetInteractor()
        renderWindow = interactor.GetRenderWindow()
        renderer = renderWindow.GetRenderers().GetFirstRenderer()
        return renderer
    

    # protected


    # private
    




if __name__ == '__main__' :
    pass


# print ("ok ..")

