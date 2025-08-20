import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import SimpleITK as sitk
from matplotlib import cm

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStateProjectPath = os.path.dirname(fileAbsPath)
fileStatePath = os.path.dirname(fileStateProjectPath)
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStateProjectPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algMeshLib as algMeshLib

import Block.optionInfo as optionInfo

import command.curveInfo as curveInfo
import command.commandExport as commandExport
import command.commandVesselKnife as commandVesselKnife
import command.commandRecon as commandRecon

import vtkObjInterface as vtkObjInterface

import data as data
import operation as operation

import userData as userData
import userDataStomach as userDataStomach
import dragProcess as dragProcess


class CDragProcessCLLabeling(dragProcess.CDragProcess) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        self.m_rt = None
        self.m_actorRt = self._create_rt_actor()
        self.m_skeleton = None
    def clear(self) :
        # input your code
        self.m_rt = None
        self.m_actorRt = None
        self.m_skeleton = None
        super().clear()
    

    def click(self, clickX : int, clickY : int) :
        super().click(clickX, clickY)
        # input your code
        self.m_mediator.m_opSelectionCL.process_reset()

        renderer = self.m_app.get_viewercl_renderer()
        renderer.AddActor2D(self.m_actorRt)
        self._update_rt_actor()
    def click_with_shift(self, clickX : int, clickY : int) :
        super().click(clickX, clickY)

        renderer = self.m_app.get_viewercl_renderer()
        renderer.AddActor2D(self.m_actorRt)
        self._update_rt_actor()
    def release(self, clickX : int, clickY : int) :
        # input your code

        clinfoInx = self.m_mediator.get_clinfo_index()

        listCLID = self._find_selection_clid()
        if listCLID is not None :
            for clID in listCLID :
                if self.m_mediator.exist_matching_by_clID(clID) == True :
                    continue
                pickingKey = data.CData.make_key(data.CData.s_skelTypeCenterline, clinfoInx, clID)
                operation.COperationSelectionCL.multi_clicked(self.m_mediator.m_opSelectionCL, pickingKey)

        renderer = self.m_app.get_viewercl_renderer()
        renderer.RemoveActor2D(self.m_actorRt)
        self.m_mediator.m_stateDragProcessInx = -1
    def move(self, clickX : int, clickY : int) :
        super().move(clickX, clickY)
        self._update_rt_actor()
        
    # protected
    def _create_rt_actor(self):
        self.m_rt = vtk.vtkPoints()
        self.m_rt.SetNumberOfPoints(4)
        for i in range(4):
            self.m_rt.SetPoint(i, 0, 0, 0)

        rect_poly = vtk.vtkPolyData()
        rect_poly.SetPoints(self.m_rt)

        rect_cells = vtk.vtkCellArray()
        rect_cells.InsertNextCell(5)
        for i in [0, 1, 2, 3, 0]:
            rect_cells.InsertCellPoint(i)
        rect_poly.SetLines(rect_cells)

        mapper = vtk.vtkPolyDataMapper2D()
        mapper.SetInputData(rect_poly)

        actor = vtk.vtkActor2D()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.3, 1.0, 0.3)
        actor.GetProperty().SetLineWidth(2.0)
        return actor
    def _update_rt_actor(self) :
        x0 = self.m_startX
        y0 = self.m_startY
        x1 = self.m_endX
        y1 = self.m_endY
        self.m_rt.SetPoint(0, x0, y0, 0)
        self.m_rt.SetPoint(1, x1, y0, 0)
        self.m_rt.SetPoint(2, x1, y1, 0)
        self.m_rt.SetPoint(3, x0, y1, 0)
        self.m_rt.Modified()
    def _find_selection_clid(self) -> list :
        '''
        ret : [clID0, clID1, .. ]
        '''
        xmin, xmax = sorted([self.m_startX, self.m_endX])
        ymin, ymax = sorted([self.m_startY, self.m_endY])

        npPt = self.m_app.project_points_to_display(self.Skeleton.m_listKDTreeAnchor)
        inside = ((npPt[:,0] >= xmin) & (npPt[:,0] <= xmax) & (npPt[:,1] >= ymin) & (npPt[:,1] <= ymax))
        selectedIndex = np.where(inside)[0]

        listID = set()
        for inx in selectedIndex :
            listID.add(self.Skeleton.m_listKDTreeAnchorID[inx])
        
        listID = list(listID)
        if len(listID) == 0 :
            return None
        return listID
    def _get_userdata(self) -> userDataStomach.CUserDataStomach :
        return self.m_mediator.get_data().find_userdata(userDataStomach.CUserDataStomach.s_userDataKey)
    

    @property
    def Skeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_skeleton
    @Skeleton.setter
    def Skeleton(self, skeleton : algSkeletonGraph.CSkeleton) :
        self.m_skeleton = skeleton


class CDragProcessTPLabeling(dragProcess.CDragProcess) :
    s_pickingDepth = 1000.0

    def __init__(self, mediator):
        super().__init__(mediator)
        self.m_pickingKey = ""
        self.m_anchorObj = None
        self.m_ratio = 0.0
    def clear(self) :
        super().clear()
        self.m_pickingKey = ""
        self.m_anchorObj = None
        self.m_ratio = 0.0
    
    def click(self, clickX : int, clickY : int) :
        super().click(clickX, clickY)
        # input your code
        if self.m_pickingKey == "" :
            return
        listExceptKeyType = [
            data.CData.s_vesselType,
            data.CData.s_textType
        ]
        
        dataInst = self.m_mediator.get_data()
        obj = dataInst.find_obj_by_key(self.m_pickingKey)

        clickedPoint = self.m_app.picking_intersected_point(clickX, clickY, listExceptKeyType)
        if clickedPoint is not None :
            cameraInfo = self.m_app.get_active_camerainfo()
            cameraPos = cameraInfo[3]
            dist = algLinearMath.CScoMath.vec3_len(clickedPoint - cameraPos)
            self.m_ratio = dist / CDragProcessTPLabeling.s_pickingDepth

        self.m_anchorObj = obj
    def click_with_shift(self, clickX : int, clickY : int) :
        pass
    def release(self, clickX : int, clickY : int) :
        super().release(clickX, clickY)
        # input your code
        self.m_pickingKey == ""
        self.m_anchorObj = None
        self.m_mediator.m_stateDragProcessInx = -1
    def move(self, clickX : int, clickY : int) :
        super().move(clickX, clickY)
        if self.m_pickingKey == "" :
            return
        
        listExceptKeyType = [
            data.CData.s_vesselType,
            userDataStomach.CTPVessel.s_tpVesselKeyType,
            data.CData.s_textType
        ]

        cameraInfo = self.m_app.get_active_camerainfo()
        cameraPos = cameraInfo[3]

        self.m_mediator.clear_matching(self.m_anchorObj.Key)

        clickedPoint = self.m_app.picking_intersected_point(clickX, clickY, listExceptKeyType)
        if clickedPoint is not None :
            dist = algLinearMath.CScoMath.vec3_len(clickedPoint - cameraPos)
            self.m_ratio = dist / CDragProcessTPLabeling.s_pickingDepth
            # 이 부분에서 centerline도 감지 
            key = self.m_app.picking(clickX, clickY, listExceptKeyType)
            if key != "" and data.CData.get_type_from_key(key) == data.CData.s_skelTypeCenterline :
                '''
                # 기존 matching 정보 갱신
                    - anchorObj에 matching된 cl이 있다면 제거
                    - 현재 key의 cl을 anchorObj와 matching 
                '''
                clID = data.CData.get_id_from_key(key)
                if self.m_mediator.exist_matching_by_clID(clID) == False : 
                    self.m_mediator.set_matching(self.m_anchorObj.Key, clID)

        worldStart, pNearStart, pFarStart= self.m_app.get_world_from_mouse(clickX, clickY, CDragProcessTPLabeling.s_pickingDepth)
        dist = algLinearMath.CScoMath.vec3_len(worldStart - cameraPos)
        moveVec = cameraPos + (worldStart - cameraPos) * self.m_ratio
        self.m_anchorObj.Pos = moveVec

        pos = self.m_anchorObj.Pos.copy()
        pos[0, 1] = pos[0, 1] + userDataStomach.CTPVessel.s_tpRadius
        textObj = self.m_mediator.get_text_obj(self.m_anchorObj.Key)
        textObj.Pos = pos

        
    def _get_userdata(self) -> userDataStomach.CUserDataStomach :
        return self.m_mediator.get_data().find_userdata(userDataStomach.CUserDataStomach.s_userDataKey)

if __name__ == '__main__' :
    pass


# print ("ok ..")

