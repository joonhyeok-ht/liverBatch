import commandInterface as commandInterface
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import data as data
import numpy as np
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

import state.project.liver.userDataLiver as userDataLiver
import VtkObj.vtkObjText as vtkObjText
import VtkObj.vtkObj as vtkObj

class CCommandUpdateTP(commandInterface.CCommand) :
    def __init__(self, mediator, labelingTab):
        super().__init__(mediator)
        # input your code
        self.m_mediator = mediator
        self.m_inputTPKey = ""
        self.m_type = ""
        self.m_labelingTab = labelingTab
        self.m_tpVesselGroup = []
        self.m_inputTP = None
        self.m_inputText = None
        self.m_inputData = None
        self.m_matchedCLID = None
    def clear(self) :
        # input your code
        self.m_inputTPKey = ""
        self.m_type = ""
        self.m_tpVesselGroup = []
        self.m_inputTP = None
        self.m_inputText = None
        self.m_inputData = None
        self.m_matchedCLID = None
        super().clear()
    def process(self) :
        super().process()
        # input your code
        if self.m_inputTPKey == "" :
            print("not setting tp key")
            return
        if self.m_inputTPKey is None :
            print("not setting pos")
            return
        pass
        
        # br = self.InputSkeleton.get_branch(self.InputBrID)
        # self.m_undoPos = br.BranchPoint.copy()
        # br.BranchPoint = self.InputPos.copy()
        # self._refresh_changed_br_data(br.ID)
    def process_undo(self):
        super().process_undo()
        dataInst = self.m_mediator.Data
        
        if self.Type == "add":
            pass
        elif self.Type == "edit":
            pass
            # dataInst = self.m_mediator.Data
            # obj = dataInst.find_obj_by_key(self.InputTPKey)
            # if obj is None:
            #     return
            # obj.Pos = self.InputPos.copy()
        elif self.Type == "delete":
            groupID = data.CData.get_groupID_from_key(self.m_inputTPKey)
            userData = self.m_labelingTab._get_userdata()
            outDict = userData.get_tp_vessel_group(groupID)
            outDict[self.m_inputTPKey] = self.InputTP
            self.m_labelingTab.m_dicText[self.m_inputTPKey] = self.InputText.Key
            self.m_labelingTab.m_dicMatching[self.m_inputTPKey] = self.m_matchedCLID
            
            dataInst.add_vtk_obj(self.InputTP.TPVesselObj)
            dataInst.add_vtk_obj(self.InputText)
            self.m_mediator.ref_key_type_groupID(userDataLiver.CTPVessel.s_tpVesselKeyType, groupID)
            self.m_mediator.ref_key_type(data.CData.s_textType)
        
        # obj = dataInst.find_obj_by_key(self.InputTPKey)
        # if obj is None:
        #     return
        # obj.Pos = self.InputPos.copy()
        #self._refresh_changed_br_data(br.ID)


    @property
    def Type(self) -> str :
        return self.m_type
    @Type.setter
    def Type(self, Type : str) :
        self.m_type = Type
    @property
    def InputTP(self) -> userDataLiver.CTPVessel:
        return self.m_inputTP
    @InputTP.setter
    def InputTP(self, inputTP) :
        self.m_inputTP = inputTP
    @property
    def InputText(self) -> vtkObjText.CVTKObjText:
        return self.m_inputText
    @InputText.setter
    def InputText(self, inputText) :
        self.m_inputText = inputText
