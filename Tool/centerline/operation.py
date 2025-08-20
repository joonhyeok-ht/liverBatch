import sys
import os
import numpy as np

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileToolPath = os.path.dirname(fileAbsPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)


import AlgUtil.algSkeletonGraph as algSkeletonGraph

import Block.optionInfo as optionInfo

import data as data
# import territory as territory


class COperation :
    def __init__(self, mediator) :
        self.m_mediator = mediator
    def clear(self) : 
        self.m_mediator = None
    

    @property
    def Data(self) -> data.CData :
        return self.m_mediator.Data
    @property
    def OptionInfo(self) -> optionInfo.COptionInfoSingle :
        return self.Data.OptionInfo


class COperationSelection(COperation) :
    def __init__(self, mediator) :
        super().__init__(mediator)
        self.m_mediator = mediator
        self.m_listSelectionKey = []
    def clear(self) : 
        self.m_listSelectionKey.clear()
        super().clear()


    def add_selection_key(self, key : str) :
        if key in self.m_listSelectionKey :
            return
        self.m_listSelectionKey.append(key)
    def get_selection_key_count(self) -> int :
        return len(self.m_listSelectionKey)
    def get_selection_key(self, inx : int) -> str :
        return self.m_listSelectionKey[inx]
    
class COperationSelectionBr(COperationSelection) :
    def __init__(self, mediator) :
        super().__init__(mediator)
    def clear(self) :
        super().clear()
    def process(self) :
        dataInst = self.Data
        self._color_setting(self.m_listSelectionKey, dataInst.SelectionBrColor)
    def process_reset(self) :
        dataInst = self.Data
        self._color_setting(self.m_listSelectionKey, dataInst.BrColor)
        self.m_listSelectionKey.clear()

    def _color_setting(self, listSelectionKey : list, color : np.ndarray) :
        dataInst = self.Data
        for selectionKey in listSelectionKey :
            clObj = dataInst.find_obj_by_key(selectionKey)
            if clObj is not None :
                clObj.Color = color
class COperationSelectionEP(COperationSelection) :
    def __init__(self, mediator) :
        super().__init__(mediator)
    def clear(self) :
        super().clear()
    def process(self) :
        dataInst = self.Data
        self._color_setting(self.m_listSelectionKey, dataInst.SelectionCLColor)
    def process_reset(self) :
        dataInst = self.Data
        self._color_setting(self.m_listSelectionKey, dataInst.CLColor)
        self.m_listSelectionKey.clear()

    def _color_setting(self, listSelectionKey : list, color : np.ndarray) :
        dataInst = self.Data
        for selectionKey in listSelectionKey :
            clObj = dataInst.find_obj_by_key(selectionKey)
            if clObj is not None :
                clObj.Color = color
class COperationSelectionCL(COperationSelection) :
    @staticmethod
    def clicked(selectionCL, clKey : str) :
        selectionCL.process_reset()
        if clKey == "" :
            pass
        else :
            selectionCL.add_selection_key(clKey)
            selectionCL.process()
    @staticmethod
    def multi_clicked(selectionCL, clKey : str) :
        if clKey == "" :
            return
        else :
            selectionCL.add_selection_key(clKey)
            selectionCL.process()
    @staticmethod
    def checked_hierarchy(selectionCL, bCheck : bool) :
        selectionCL.ChildSelectionMode = bCheck
        selectionCL.process()
    @staticmethod
    def checked_ancestor(selectionCL, bCheck : bool) :
        selectionCL.ParentSelectionMode = bCheck
        selectionCL.process()
    


    def __init__(self, mediator):
        super().__init__(mediator)
        self.m_skeleton = None
        self.m_listChildSelectionKey = []
        self.m_listParentSelectionKey = []
        self.m_bChildSelectionMode = False
        self.m_bParentSelectionMode = False
    def clear(self) :
        self.m_bChildSelectionMode = False
        self.m_bParentSelectionMode = False
        self.m_listChildSelectionKey.clear()
        self.m_listParentSelectionKey.clear()
        self.m_skeleton = None
        super().clear()


    def process(self) :
        dataInst = self.Data

        self._color_setting(self.m_listSelectionKey, dataInst.SelectionCLColor, dataInst.SelectionCLColor)

        if self.m_bChildSelectionMode == True :
            self._update_child_selection_key()
            self._color_setting(self.m_listChildSelectionKey, dataInst.SelectionCLColor, dataInst.SelectionCLColor)
        else :
            self._color_setting(self.m_listChildSelectionKey, dataInst.RootCLColor, dataInst.CLColor)
            self.m_listChildSelectionKey.clear()

        if self.m_bParentSelectionMode == True :
            self._update_parent_selection_key()
            self._color_setting(self.m_listParentSelectionKey, dataInst.SelectionCLColor, dataInst.SelectionCLColor)
        else :
            self._color_setting(self.m_listParentSelectionKey, dataInst.RootCLColor, dataInst.CLColor)
            self.m_listParentSelectionKey.clear()
    def process_reset(self) :
        dataInst = self.Data

        self._color_setting(self.m_listSelectionKey, dataInst.RootCLColor, dataInst.CLColor)
        if self.m_bChildSelectionMode == True :
            self._color_setting(self.m_listChildSelectionKey, dataInst.RootCLColor, dataInst.CLColor)
        if self.m_bParentSelectionMode == True :
            self._color_setting(self.m_listParentSelectionKey, dataInst.RootCLColor, dataInst.CLColor)
        self.m_listSelectionKey.clear()
        self.m_listChildSelectionKey.clear()
        self.m_listParentSelectionKey.clear()

    def get_selection_cl_list(self) -> list :
        retList = []

        iCnt = self.get_selection_key_count()
        for inx in range(0, iCnt) :
            key = self.get_selection_key(inx)
            clID = data.CData.get_id_from_key(key)
            retList.append(clID)
        
        if len(retList) == 0 :
            return None
        return list(set(retList))
    def get_all_selection_cl(self) -> list :
        retList = self.get_selection_cl_list()
        if retList is None : 
            return None
        
        for key in self.m_listChildSelectionKey :
            clID = data.CData.get_id_from_key(key)
            retList.append(clID)
        for key in self.m_listParentSelectionKey :
            clID = data.CData.get_id_from_key(key)
            retList.append(clID)
        return list(set(retList))
    
    def _update_child_selection_key(self) :
        self.m_listChildSelectionKey.clear()

        skeleton = self.Skeleton
        if skeleton is None :
            return

        for key in self.m_listSelectionKey :
            groupID = data.CData.get_groupID_from_key(key)
            clID = data.CData.get_id_from_key(key)
            listRet = skeleton.find_descendant_centerline_by_centerline_id(clID)

            iCnt = len(listRet)

            for i in range(1, iCnt) :
                childCL = listRet[i]
                childKey = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, childCL.ID)
                self.m_listChildSelectionKey.append(childKey)
    def _update_parent_selection_key(self) :
        self.m_listParentSelectionKey.clear()

        skeleton = self.Skeleton
        if skeleton is None :
            return
        
        for key in self.m_listSelectionKey :
            groupID = data.CData.get_groupID_from_key(key)
            clID = data.CData.get_id_from_key(key)
            listRet = skeleton.find_ancestor_centerline_by_centerline_id(clID)

            iCnt = len(listRet)

            for i in range(1, iCnt) :
                parentCL = listRet[i]
                parentKey = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, parentCL.ID)
                self.m_listParentSelectionKey.append(parentKey)

    def _color_setting(self, listSelectionKey : list, rootColor : np.ndarray, _color : np.ndarray) :
        dataInst = self.Data
        skeleton = self.Skeleton
        if skeleton is None :
            return
        
        for selectionKey in listSelectionKey :
            id = data.CData.get_id_from_key(selectionKey)
            if id == skeleton.RootCenterline.ID :
                color = rootColor
            else :
                color = _color

            clObj = dataInst.find_obj_by_key(selectionKey)
            if clObj is not None :
                clObj.Color = color


    @property
    def Skeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_skeleton
    @Skeleton.setter
    def Skeleton(self, skeleton) :
        self.m_skeleton = skeleton
    @property
    def ChildSelectionMode(self) -> bool :
        return self.m_bChildSelectionMode
    @ChildSelectionMode.setter
    def ChildSelectionMode(self, childSelectionMode : bool) :
        self.m_bChildSelectionMode = childSelectionMode
    @property
    def ParentSelectionMode(self) -> bool :
        return self.m_bParentSelectionMode
    @ParentSelectionMode.setter
    def ParentSelectionMode(self, parentSelectionMode : bool) :
        self.m_bParentSelectionMode = parentSelectionMode



class COperationDragSelectionCL(COperationSelection) :
    def __init__(self, mediator):
        super().__init__(mediator)
        self.m_skeleton = None
        self.m_bChildSelectionMode = False
    def clear(self) :
        self.m_bChildSelectionMode = False
        self.m_skeleton = None
        super().clear()


    def process(self) :
        dataInst = self.Data
        self._color_setting(self.m_listSelectionKey, dataInst.SelectionCLColor, dataInst.SelectionCLColor)
    def process_reset(self) :
        dataInst = self.Data
        self._color_setting(self.m_listSelectionKey, dataInst.RootCLColor, dataInst.CLColor)
        self.m_listSelectionKey.clear()


    def add_selection_keys(self, listSelectionKey : list) :
        if len(listSelectionKey) == 0 :
            return
        
        listRet = []
        if self.ChildSelectionMode == True :
            for key in listSelectionKey :
                listChild = self._get_child_key(key)
                if listChild is not None :
                    listRet += listChild
        
        self.m_listSelectionKey += listSelectionKey
        if len(listRet) > 0 :
            self.m_listSelectionKey += listRet
        self.m_listSelectionKey = list(set(self.m_listSelectionKey))
    def get_selection_cl_list(self) -> list :
        retList = []

        iCnt = self.get_selection_key_count()
        for inx in range(0, iCnt) :
            key = self.get_selection_key(inx)
            clID = data.CData.get_id_from_key(key)
            retList.append(clID)
        
        if len(retList) == 0 :
            return None
        return list(set(retList))
    def get_all_selection_cl(self) -> list :
        retList = self.get_selection_cl_list()
        if retList is None : 
            return None
        return retList
    

    # protected
    def _get_child_key(self, key : str) -> list :
        skeleton = self.Skeleton
        if skeleton is None :
            return None
    
        groupID = data.CData.get_groupID_from_key(key)
        clID = data.CData.get_id_from_key(key)
        listRetID = skeleton.find_descendant_centerline_by_centerline_id(clID)

        listRet = []
        iCnt = len(listRetID)
        for i in range(1, iCnt) :
            childCL = listRetID[i]
            childKey = data.CData.make_key(data.CData.s_skelTypeCenterline, groupID, childCL.ID)
            listRet.append(childKey)
        
        if len(listRet) == 0 :
            return None
        return listRet
    def _color_setting(self, listSelectionKey : list, rootColor : np.ndarray, _color : np.ndarray) :
        dataInst = self.Data
        skeleton = self.Skeleton
        if skeleton is None :
            return
        
        for selectionKey in listSelectionKey :
            id = data.CData.get_id_from_key(selectionKey)
            if id == skeleton.RootCenterline.ID :
                color = rootColor
            else :
                color = _color

            clObj = dataInst.find_obj_by_key(selectionKey)
            if clObj is not None :
                clObj.Color = color


    @property
    def Skeleton(self) -> algSkeletonGraph.CSkeleton :
        return self.m_skeleton
    @Skeleton.setter
    def Skeleton(self, skeleton) :
        self.m_skeleton = skeleton
    @property
    def ChildSelectionMode(self) -> bool :
        return self.m_bChildSelectionMode
    @ChildSelectionMode.setter
    def ChildSelectionMode(self, childSelectionMode : bool) :
        self.m_bChildSelectionMode = childSelectionMode


if __name__ == '__main__' :
    pass


# print ("ok ..")

