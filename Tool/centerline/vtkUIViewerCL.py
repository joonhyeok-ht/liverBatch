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
import VtkObj.vtkObjLine as vtkObjLine
import VtkObj.vtkObjSphere as vtkObjSphere
import VtkObj.vtkObjPolyData as vtkObjPolyData

import VtkUI.vtkUI as vtkUI

# class CViewerCLStyle(vtk.vtkInteractorStyleTrackballCamera):
#     def __init__(self, mediator):
#         super(CViewerCLStyle, self).__init__()

#         self.m_mediator = mediator
#         self.m_bMouseLeft = False
#         self.m_bMouseRight = False

#         self.AddObserver("LeftButtonPressEvent", self._on_click_mouse_left)
#         self.AddObserver("LeftButtonReleaseEvent", self._on_release_mouse_left)
#         self.AddObserver("RightButtonPressEvent", self._on_click_mouse_right)
#         self.AddObserver("RightButtonReleaseEvent", self._on_release_mouse_right)
#         self.AddObserver("MouseMoveEvent", self._on_mouse_move)
#         self.AddObserver("KeyPressEvent", self._on_key_press)

#     def _on_click_mouse_left(self, obj, event) :
#         self.m_bMouseLeft = True
#         self.m_bMouseRight = False
#         self.OnLeftButtonDown()
#     def _on_release_mouse_left(self, obj, event) :
#         self.m_bMouseLeft = False
#         self.OnLeftButtonUp()
#     def _on_click_mouse_right(self, obj, event) :
#         interactor = self.GetInteractor()
#         clickPos = interactor.GetEventPosition()
#         self.m_bMouseRight = True
#         self.m_bMouseLeft = False

#         if interactor.GetShiftKey() :
#             self.m_mediator.on_click_mouse_right_shift(clickPos[0], clickPos[1])
#         else :
#             self.m_mediator.on_click_mouse_right(clickPos[0], clickPos[1])
#     def _on_release_mouse_right(self, obj, event) :
#         self.m_bMouseRight = False
#         self.m_mediator.on_release_mouse_right()
#     def _on_mouse_move(self, obj, event) :
#         interactor = self.GetInteractor()
#         clickPos = interactor.GetEventPosition()

#         if self.m_bMouseRight == True :
#             self.m_mediator.on_mouse_move_right(clickPos[0], clickPos[1])
#         elif self.m_bMouseLeft == False and self.m_bMouseRight == False :
#             self.m_mediator.on_mouse_move(clickPos[0], clickPos[1])
#         else :
#             self.OnMouseMove()
#     def _on_key_press(self, obj, event) :
#         interactor = self.GetInteractor()
#         keySym = interactor.GetKeySym()
#         ctrlKey = interactor.GetControlKey()
#         # print(f"keySym : {keySym}")
#         if ctrlKey :
#             self.m_mediator.on_key_press_with_ctrl(keySym)
#         else :
#             self.m_mediator.on_key_press(keySym)



class CViewerCLStyle(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self, mediator):
        super(CViewerCLStyle, self).__init__()

        self.m_mediator = mediator
        self.m_bMouseLeft = False
        self.m_bMouseRight = False

        self.AddObserver("LeftButtonPressEvent", self._on_click_mouse_left)
        self.AddObserver("LeftButtonReleaseEvent", self._on_release_mouse_left)
        self.AddObserver("RightButtonPressEvent", self._on_click_mouse_right)
        self.AddObserver("RightButtonReleaseEvent", self._on_release_mouse_right)
        self.AddObserver("MouseMoveEvent", self._on_mouse_move)
        self.AddObserver("KeyPressEvent", self._on_key_press)

    def _on_click_mouse_left(self, obj, event) :
        interactor = self.GetInteractor()
        clickPos = interactor.GetEventPosition()
        self.m_bMouseLeft = True
        self.m_bMouseRight = False

        if interactor.GetShiftKey() :
            self.m_mediator.on_click_mouse_right_shift(clickPos[0], clickPos[1])
        else :
            self.m_mediator.on_click_mouse_right(clickPos[0], clickPos[1])
    def _on_release_mouse_left(self, obj, event) :
        self.m_bMouseLeft = False
        self.m_mediator.on_release_mouse_right()
    def _on_click_mouse_right(self, obj, event) :
        self.m_bMouseLeft = False
        self.m_bMouseRight = True
        self.OnLeftButtonDown()
    def _on_release_mouse_right(self, obj, event) :
        self.m_bMouseRight = False
        self.OnLeftButtonUp()
    def _on_mouse_move(self, obj, event) :
        interactor = self.GetInteractor()
        clickPos = interactor.GetEventPosition()

        # print(f"left : {self.m_bMouseLeft}, right : {self.m_bMouseRight}")

        if self.m_bMouseLeft == True :
            self.m_mediator.on_mouse_move_right(clickPos[0], clickPos[1])
        elif self.m_bMouseLeft == False and self.m_bMouseRight == False :
            self.m_mediator.on_mouse_move(clickPos[0], clickPos[1])
        else :
            self.OnMouseMove()
    def _on_key_press(self, obj, event) :
        interactor = self.GetInteractor()
        keySym = interactor.GetKeySym()
        ctrlKey = interactor.GetControlKey()
        # print(f"keySym : {keySym}")
        if ctrlKey :
            self.m_mediator.on_key_press_with_ctrl(keySym)
        else :
            self.m_mediator.on_key_press(keySym)


class CVTKUIViewerCL(vtkUI.CVTKUI) :
    def __init__(self, layout, parentWidget : QWidget, mediator) -> None:
        super().__init__(layout, parentWidget, mediator)
        # input your code
    def clear(self) :
        # input your code
        super().clear()


    def reset_camera(self) :
        # input your code
        self.m_renderer.ResetCamera()
        self.m_renderer.GetActiveCamera().Zoom(1.5)
        self.update_render()

    
    def on_click_mouse_left(self, clickX, clickY) :
        self.m_mediator.uiviewer_on_click_mouse_left(clickX, clickY)
    def on_click_mouse_left_shift(self, clickX, clickY) :
        self.m_mediator.uiviewer_on_click_mouse_left_shift(clickX, clickY)
    def on_release_mouse_left(self) :
        self.m_mediator.uiviewer_on_release_mouse_left()
    def on_click_mouse_right(self, clickX, clickY) :
        self.m_mediator.uiviewer_on_click_mouse_right(clickX, clickY)
    def on_click_mouse_right_shift(self, clickX, clickY) :
        self.m_mediator.uiviewer_on_click_mouse_right_shift(clickX, clickY)
    def on_release_mouse_right(self) :
        self.m_mediator.uiviewer_on_release_mouse_right()
    def on_mouse_move(self, clickX, clickY) :
        self.m_mediator.uiviewer_on_mouse_move(clickX, clickY)
    def on_mouse_move_left(self, clickX, clickY) :
        self.m_mediator.uiviewer_on_mouse_move_right(clickX, clickY)
    def on_mouse_move_right(self, clickX, clickY) :
        self.m_mediator.uiviewer_on_mouse_move_right(clickX, clickY)
    def on_key_press(self, keyCode : str) :
        self.m_mediator.uiviewer_on_key_press(keyCode)
    def on_key_press_with_ctrl(self, keyCode : str) :
        self.m_mediator.uiviewer_on_key_press_with_ctrl(keyCode)
        

    


    # protected


    # private
    




if __name__ == '__main__' :
    pass


# print ("ok ..")

