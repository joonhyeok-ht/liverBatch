import sys
import os
import numpy as np
import shutil
import vtk
import subprocess
import math

from scipy.spatial import KDTree

from PySide6.QtCore import Qt, QEvent, QObject, QPoint
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QLabel, QSizePolicy, QListWidget, QFileDialog, QFrame, QCheckBox, QTabWidget, QComboBox, QListWidgetItem, QMenu, QSpinBox, QMessageBox, QDoubleSpinBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

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
import AlgUtil.algVTK as algVTK
import AlgUtil.algSkeletonGraph as algSkeletonGraph
import AlgUtil.algMeshLib as algMeshLib


import data as data

import operation as operation

import tabState as tabState

import VtkObj.vtkObjLine as vtkObjLine
import vtkObjInterface as vtkObjInterface

import command.commandExtractionCL as commandExtractionCL

import remodeling.remodelingNode as remodelingNode
import remodeling.remodelingVessel as remodelingVessel
import remodeling.commandRemodeling as commandRemodeling
import remodeling.subStateRemodeling as subStateRemodeling
import remodeling.subStateRemodelingCutting as subStateRemodelingCutting
import remodeling.subStateRemodelingExtractionEnCL as subStateRemodelingExtractionEnCL
import remodeling.subStateRemodelingRemodeling as subStateRemodelingRemodeling

from collections import deque

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
parentDirPath = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

class CTabStateVesselRemodeling(tabState.CTabState) :
    s_dbgType = "dbgType"
    s_skelGroupID = 1000

    @staticmethod
    def get_meshlib(vtkMeshInst : vtk.vtkPolyData) :
        npVertex = algVTK.CVTK.poly_data_get_vertex(vtkMeshInst)
        npIndex = algVTK.CVTK.poly_data_get_triangle_index(vtkMeshInst)
        meshLibInst = algMeshLib.CMeshLib.meshlib_create(npVertex, npIndex)
        return meshLibInst
    @staticmethod
    def get_vtkmesh(meshlibInst) -> vtk.vtkPolyData :
        npVertex = algMeshLib.CMeshLib.meshlib_get_vertex(meshlibInst)
        npIndex = algMeshLib.CMeshLib.meshlib_get_index(meshlibInst)
        vtkMesh = algVTK.CVTK.create_poly_data_triangle(npVertex, npIndex)
        return vtkMesh
    @staticmethod
    def dilate_polydata(polydata: vtk.vtkPolyData, offset=0.05) :
        # vertex normal 계산
        normalsGen = vtk.vtkPolyDataNormals()
        normalsGen.SetInputData(polydata)
        normalsGen.ComputePointNormalsOn()
        normalsGen.ComputeCellNormalsOff()
        normalsGen.SplittingOff()
        normalsGen.Update()
        normals = normalsGen.GetOutput().GetPointData().GetNormals()

        newPoints = vtk.vtkPoints()
        for i in range(polydata.GetNumberOfPoints()):
            p = np.array(polydata.GetPoint(i))
            n = np.array(normals.GetTuple(i))
            newPoints.InsertNextPoint(p + offset * n)

        dilated = vtk.vtkPolyData()
        dilated.DeepCopy(polydata)
        dilated.SetPoints(newPoints)
        return dilated
    @staticmethod
    def refresh_radius(refMesh : vtk.vtkPolyData, skeleton : algSkeletonGraph.CSkeleton) :
        distCalculator = vtk.vtkImplicitPolyDataDistance()
        distCalculator.SetInput(refMesh)

        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            dist = np.zeros(len(cl.Vertex))
            for ptInx, point in enumerate(cl.Vertex) :
                radius = abs(distCalculator.EvaluateFunction(point))
                dist[ptInx] = radius
            cl.Radius = dist
            inx = 0
    @staticmethod
    def check_in_polydata(polyData : vtk.vtkPolyData, vertex : np.ndarray) -> np.ndarray :
        '''
        desc : polygon 내부에 존재하는 vertex들의 갯수 반환
        '''
        iCnt = vertex.shape[0]
        testPt = vtk.vtkPoints()
        for inx in range(0, iCnt) :
            testPt.InsertNextPoint(vertex[inx, 0], vertex[inx, 1], vertex[inx, 2])
        
        retList = [False for inx in range(0, vertex.shape[0])]

        testPolyData = vtk.vtkPolyData()
        testPolyData.SetPoints(testPt)

        selEnPt = vtk.vtkSelectEnclosedPoints()
        selEnPt.SetSurfaceData(polyData)
        selEnPt.SetInputData(testPolyData)
        selEnPt.Update()

        for i in range(testPt.GetNumberOfPoints()) :
            bInside = selEnPt.IsInside(i)
            if bInside == 1 :
                retList[i] = True

        return np.array(retList)
    @staticmethod
    def get_vertex(polydata : vtk.vtkPolyData, cellID : int) -> np.ndarray :
        cell = polydata.GetCell(cellID)
        pointId = cell.GetPointId(0)
        return np.array(polydata.GetPoint(pointId)).reshape(-1, 3)
    @staticmethod
    def find_closest_cell_id(
        polyData: vtk.vtkPolyData,
        point3d_np: np.ndarray
        ) -> int :
        point3d_np = point3d_np.reshape(-1)
        point3d = point3d_np.astype(float).tolist()

        locator = vtk.vtkCellLocator()
        locator.SetDataSet(polyData)
        locator.BuildLocator()

        closestPoint = [0.0, 0.0, 0.0]
        cellId = vtk.mutable(0)
        subId = vtk.mutable(0)
        dist2 = vtk.mutable(0.0)

        locator.FindClosestPoint(
            point3d,       # [x, y, z]
            closestPoint,
            cellId,
            subId,
            dist2
        )

        return int(cellId)


    def __init__(self, mediator) :
        super().__init__(mediator)
        # input your code
        color = [
            [1.0, 1.0, 0.0],
            [1.0, 0.5, 0.0],
            [0.5, 0.5, 0.0],

            [1.0, 0.0, 1.0],
            [1.0, 0.0, 0.5],
            [0.5, 0.0, 0.5],

            [0.0, 1.0, 1.0],
            [0.0, 1.0, 0.5],
            [0.0, 0.5, 0.5],

            [1.0, 1.0, 1.0],
            [1.0, 1.0, 0.5],
            [1.0, 0.5, 1.0],
            [0.5, 1.0, 1.0],
            [1.0, 0.5, 0.5],
            [0.5, 0.5, 1.0],
            [0.5, 0.5, 0.5],

            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.5, 0.0, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, 0.0, 0.5],
        ]
        self.m_color = np.array(color)


        self.m_opSelectionCL = operation.COperationSelectionCL(mediator)
        self.m_state = -1
        self.m_listSubState = []
        self.m_listSubState.append(subStateRemodelingCutting.CSubStateRemodelingCutting(self))
        self.m_listSubState.append(subStateRemodelingExtractionEnCL.CSubStateRemodelingExtractionEnCL(self))
        self.m_listSubState.append(subStateRemodelingRemodeling.CSubStateRemodelingRemodeling(self))


        self.m_cuttedMeshID = 0
        self.m_nodeNameID = 0
        self.m_mainNode = None

        self.m_listCmd = []
    def clear(self) :
        # input your code
        self.m_opSelectionCL.clear()
        self.m_opSelectionCL = None

        self.m_listSubState.clear()
        self.m_state = -1

        self.m_cuttedMeshID = 0
        self.m_nodeNameID = 0
        self.m_mainNode = None

        for cmd in self.m_listCmd :
            cmd.clear()
        self.m_listCmd.clear()
        super().clear()

    def process_init(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is None :
            return 
        
        skelinfo = dataInst.get_skelinfo(clinfoInx)
        
        opSelectionCL = self.m_opSelectionCL
        opSelectionCL.Skeleton = skeleton

        self.m_cuttedMeshID = 0
        self.m_nodeNameID = 0
        self.m_listRemodelingNode = []

        # 원본 vessel loading
        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
        vesselObj = dataInst.find_obj_by_key(vesselKey)
        vesselPolydata = vesselObj.PolyData
        vertex = algVTK.CVTK.poly_data_get_vertex(vesselPolydata)
        index = algVTK.CVTK.poly_data_get_triangle_index(vesselPolydata)
        cuttedMesh = algVTK.CVTK.create_poly_data_triangle(vertex, index)
        cuttedMeshKey = self.create_cuttedmesh_key(cuttedMesh)

        self.m_mainNode = remodelingNode.CRemodelingNode()
        self.m_mainNode.Name = f"{skelinfo.BlenderName}_Main"
        self.m_mainNode.Key = cuttedMeshKey
        self.m_listRemodelingNode.append(self.m_mainNode)
        self.setui_lv_cuttednode_add_node(self.m_mainNode)

        # visible
        self._refresh_visible_vessel()
        self._refresh_visible_vessel_cl()

        if self.m_state == -1 :
            self.m_state = 0
            self._get_substate(self.m_state).process_init()
        else :
            self.m_tabUI.setCurrentIndex(0)

        self.m_mediator.update_viewer()
    def process(self) :
        pass
    def process_end(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        opSelectionCL = self.m_opSelectionCL
        opSelectionCL.process_reset()

        # self._get_substate(self.m_state).process_end()
        # self.m_state = 0
        self.m_tabUI.setCurrentIndex(0)
        # self._get_substate(self.m_state).process_init()

        self.m_mediator.remove_key_type(subStateRemodeling.CSubStateRemodeling.s_cuttingMeshType)
        self.m_cuttedMeshID = 0
        self.m_nodeNameID = 0
        self.m_mainNode = None

        for cmd in self.m_listCmd :
            cmd.clear()
        self.m_listCmd.clear()

        self.setui_lv_cuttednode_remove_all()
        for node in self.m_listRemodelingNode :
            if node.SkelGroupID >= 0 :
                self.m_mediator.remove_key_type_groupID(data.CData.s_skelTypeCenterline, node.SkelGroupID)
            node.clear()
        self.m_listRemodelingNode.clear()

    def init_ui(self) :
        tabLayout = QVBoxLayout()
        self.Tab.setLayout(tabLayout)

        label = QLabel("-- Visible --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        layout, listCB = self.m_mediator.create_layout_checkbox_array(["Mesh", "Centerline"])
        self.m_cbVisibleMesh = listCB[0]
        self.m_cbVisibleMesh.setChecked(True)
        self.m_cbVisibleMesh.stateChanged.connect(self._on_check_visible_mesh)
        self.m_cbVisibleCL = listCB[1]
        self.m_cbVisibleCL.setChecked(True)
        self.m_cbVisibleCL.stateChanged.connect(self._on_check_visible_cl)
        tabLayout.addLayout(layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        label = QLabel("-- Cutted Mesh --")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        tabLayout.addWidget(label)

        self.m_lvCuttedNode = QListWidget()
        self.m_lvCuttedNode.currentItemChanged.connect(self._on_lb_clicked_node)
        self.m_lvCuttedNode.setContextMenuPolicy(Qt.CustomContextMenu)
        tabLayout.addWidget(self.m_lvCuttedNode)

        self.m_tabUI = self.init_ui_tab()
        tabLayout.addWidget(self.m_tabUI)
        # self.m_tabUI.setCurrentIndex(0)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tabLayout.addWidget(line)

        lastUI = line
        tabLayout.setAlignment(lastUI, Qt.AlignmentFlag.AlignTop)
    def init_ui_tab(self) -> QTabWidget :
        tabUI = QTabWidget()


        title = "Cutting"
        tab = QWidget()
        subTabLayout = QVBoxLayout(tab)

        layout, self.m_editLabelName = self.m_mediator.create_layout_label_editbox("Label Name", False)
        self.m_editLabelName.returnPressed.connect(self._on_return_pressed_label_name)
        subTabLayout.addLayout(layout)

        subTabLayout.addStretch()
        tabUI.addTab(tab, title)


        title = "Extraction Enhanced-CL"
        tab = QWidget()
        subTabLayout = QVBoxLayout(tab)

        # input your code
        self.m_checkSelectionStartCell = QCheckBox("Selection Start Cell ")
        self.m_checkSelectionStartCell.setChecked(False)
        self.m_checkSelectionStartCell.stateChanged.connect(self._on_check_sel_cell)

        layout = QHBoxLayout()
        label = QLabel("CellID ")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.m_editBoxCellID = QLineEdit()
        layout.addWidget(self.m_checkSelectionStartCell)
        layout.addWidget(label)
        layout.addWidget(self.m_editBoxCellID)
        subTabLayout.addLayout(layout)


        layout = QHBoxLayout()
        label = QLabel("Dilation Pass Count ")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.m_spinDilationPass = QSpinBox()
        self.m_spinDilationPass.setRange(1, 7)
        self.m_spinDilationPass.setValue(5)
        self.m_spinDilationPass.setSingleStep(1)
        layout.addWidget(label)
        layout.addWidget(self.m_spinDilationPass)
        subTabLayout.addLayout(layout)

        btn = QPushButton("Extraction Centerline")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_extraction_centerline)
        subTabLayout.addWidget(btn)

        subTabLayout.addStretch()
        tabUI.addTab(tab, title)


        title = "Remodeling"
        tab = QWidget()
        subTabLayout = QVBoxLayout(tab)

        layout, retList = self.m_mediator.create_layout_label_radio("SelectionMode", ["Single", "Descendant"])
        self.m_rbSingle = retList[0]
        self.m_rbDescendant = retList[1]
        self.m_rbSingle.toggled.connect(self._on_rb_single)
        self.m_rbDescendant.toggled.connect(self._on_rb_descendant)
        self.m_rbSingle.setChecked(True)
        subTabLayout.addLayout(layout)


        nodeLayout = QHBoxLayout()
        leftLayout = QVBoxLayout()
        rightLayout = QVBoxLayout()

        subTabLayout.addLayout(nodeLayout)
        nodeLayout.addLayout(leftLayout)
        nodeLayout.addLayout(rightLayout)

        label = QLabel("Anchor")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.m_lvAnchor = QListWidget()

        labelFloat = QLabel("Radius-Margin ")
        labelFloat.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        labelFloat.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.m_spinStrength = QDoubleSpinBox()
        self.m_spinStrength.setRange(-1.0, 1.0)
        self.m_spinStrength.setSingleStep(0.1)
        self.m_spinStrength.setDecimals(1)
        self.m_spinStrength.setValue(0.0)

        layout, retList = self.m_mediator.create_layout_checkbox_array(["Fill Missing Vessels"])
        self.m_checkMissingVessel = retList[0]

        leftLayout.addWidget(label)
        leftLayout.addWidget(self.m_lvAnchor)
        leftLayout.addWidget(labelFloat)
        leftLayout.addWidget(self.m_spinStrength)
        leftLayout.addLayout(layout)
        leftLayout.addStretch()
        
        labelDepth = QLabel("Max Depth")
        labelDepth.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        labelDepth.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.m_minorVelsselMaxDepth = QSpinBox()
        self.m_minorVelsselMaxDepth.setRange(0, 99)
        self.m_minorVelsselMaxDepth.setSingleStep(1)
        self.m_minorVelsselMaxDepth.setValue(4)
        
        rightLayout.addWidget(labelDepth)
        rightLayout.addWidget(self.m_minorVelsselMaxDepth)
        
        btn = QPushButton("Select Minor")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_minor_selection)
        rightLayout.addWidget(btn) 

        btn = QPushButton("Attach Centerline")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_attach_centerline)
        rightLayout.addWidget(btn) 

        btn = QPushButton("Refresh Centerline")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_refresh_centerline)
        rightLayout.addWidget(btn) 

        label = QLabel("Skel-Node List ")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.m_lvSubNode = QListWidget()
        rightLayout.addWidget(label) 
        rightLayout.addWidget(self.m_lvSubNode) 
        rightLayout.addStretch() 

        btn = QPushButton("Remodeling")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_remodeling)
        subTabLayout.addWidget(btn)

        btn = QPushButton("Save")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_remodeling_save)
        subTabLayout.addWidget(btn)
        
        btn = QPushButton("Blender Save")
        btn.setStyleSheet(self.get_btn_stylesheet())
        btn.clicked.connect(self._on_btn_blender_save)
        subTabLayout.addWidget(btn)


        subTabLayout.addStretch()
        tabUI.addTab(tab, title)

        tabUI.currentChanged.connect(self._on_tab_changed)

        return tabUI
    

    def get_node_name(self) -> str :
        nodeName = f"noname_{self.m_nodeNameID}"
        self.m_nodeNameID += 1
        return nodeName
    def create_cuttedmesh_key(self, polydata : vtk.vtkPolyData) -> str :
        cuttingKey = data.CData.make_key(subStateRemodeling.CSubStateRemodeling.s_cuttingMeshType, 0, self.m_cuttedMeshID)
        cuttingObj = vtkObjInterface.CVTKObjInterface()
        cuttingObj.KeyType = subStateRemodeling.CSubStateRemodeling.s_cuttingMeshType
        cuttingObj.Key = cuttingKey
        cuttingObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        cuttingObj.Opacity = 0.3
        cuttingObj.PolyData = polydata

        dataInst = self.get_data()
        dataInst.add_vtk_obj(cuttingObj)

        self.m_cuttedMeshID += 1
        return cuttingKey
    def remove_cuttedmesh(self, cuttedMeshKey : str) :
        self.m_mediator.remove_key(cuttedMeshKey)
    def get_cuttedmesh_polydata(self, cuttedMeshKey : str) -> vtk.vtkPolyData:
        dataInst = self.get_data()
        obj = dataInst.find_obj_by_key(cuttedMeshKey)
        return obj.PolyData
    def select_index_cuttedmesh(self, selectionInx : int) :
        prevNode = self.getui_lv_cuttednode_selected_node()
        if selectionInx >= 0 :
            nowNode = self.m_listRemodelingNode[selectionInx]
        else :
            nowNode= None

        self.swap_selected_cutting_node(prevNode, nowNode)
        self.setui_lv_cuttednode_selection_inx(selectionInx)
        self._get_substate(self.m_state).changed_cutting_mesh(prevNode, nowNode)
    def refresh_remodeling_node_list(self, listRemodelingNode : list) :
        selectedNode = self.getui_lv_cuttednode_selected_node()
        if selectedNode is not None :
            self.swap_selected_cutting_node(selectedNode, None)

        self.m_listRemodelingNode = listRemodelingNode
        self.setui_lv_cuttednode_add_listnode(self.m_listRemodelingNode)
    def swap_selected_cutting_node(self, prevNode : remodelingNode.CRemodelingNode, nowNode : remodelingNode.CRemodelingNode) :
        if prevNode is not None :
            self.m_mediator.unref_key_type(subStateRemodeling.CSubStateRemodeling.s_cuttingMeshType)
            if prevNode.SkelGroupID >= 0 :
                self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeCenterline, prevNode.SkelGroupID)
        
        if nowNode is None :
            return
        
        self.m_mediator.ref_key(nowNode.Key)
        if nowNode.SkelGroupID >= 0 :
            self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, nowNode.SkelGroupID)
    def undo(self) :
        if len(self.m_listCmd) == 0 :
            return
        cmd = self.m_listCmd.pop()
        cmd.undo()
        self.m_mediator.update_viewer()

    # command 
    def command_cutting_mesh(self, startX : int, startY : int, endX : int, endY : int) :
        cmd = commandRemodeling.CCommandRemodelingCutting(self)
        bRet = cmd.process(startX, startY, endX, endY)
        if bRet == True :
            self.m_listCmd.append(cmd)
    def command_remove_node(self) :
        if self.getui_lv_cuttednode_selected_node() == self.MainNode :
            QMessageBox.information(self.m_mediator, "Alarm", "The Main Node cannot be deleted")
            return
        cmd = commandRemodeling.CCommandRemodelingRemove(self)
        bRet = cmd.process()
        if bRet == True :
            self.m_listCmd.append(cmd)
        self.m_mediator.update_viewer()
    def command_extraction_cl(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        clOutPath = dataInst.get_cl_out_path()
        if os.path.exists(clOutPath) == False :
            print("not found clOutPath")
            return 
        clInPath = dataInst.get_cl_in_path()
        if os.path.exists(clInPath) == False :
            print("not found clInPath")
            return 
        
        node = self.getui_lv_cuttednode_selected_node()
        if node.SkeletonEn is not None :
            self.m_mediator.remove_skeleton_cl_obj(node.SkelGroupID)
            node.SkelGroupID = -1
            node.SkeletonEn = None

        vtpName = node.Name
        clOutputFullPath = os.path.join(clOutPath, f"{vtpName}.json")
        if os.path.exists(clOutputFullPath) == True :
            os.remove(clOutputFullPath)

        startCellID = self.getui_cellID()
        if startCellID < 0 :
            startCellID = 0
        
        vesselObj = dataInst.find_obj_by_key(node.Key)
        if vesselObj is None :
            print("not found vessel polydata")
            return
        
        vesselPolyData = vesselObj.PolyData
        startVertex = CTabStateVesselRemodeling.get_vertex(vesselPolyData, startCellID)

        dilatiionPassCnt = self.getui_spin_dilation_pass_count()
        for inx in range(0, dilatiionPassCnt) :
            vesselPolyData = CTabStateVesselRemodeling.dilate_polydata(vesselPolyData, 0.1)

            # healing 추가 
            meshlib = CTabStateVesselRemodeling.get_meshlib(vesselPolyData)
            meshlib = algMeshLib.CMeshLib.meshlib_healing(meshlib)
            vesselPolyData = CTabStateVesselRemodeling.get_vtkmesh(meshlib)

        # centerline 추출용 mesh의 startCellID와 startVertex를 얻어옴 
        vesselPolyData = algVTK.CVTK.laplacian_smoothing(vesselPolyData, 5, 0.1)

        startCellID = CTabStateVesselRemodeling.find_closest_cell_id(vesselPolyData, startVertex)
        startVertex = CTabStateVesselRemodeling.get_vertex(vesselPolyData, startCellID)

        vertex = algVTK.CVTK.poly_data_get_vertex(vesselPolyData)
        index = algVTK.CVTK.poly_data_get_triangle_index(vesselPolyData)
        print(f"Main InputVTPName : {vtpName}")
        print(f"Main cnt : {vertex.shape[0]}, {index.shape[0]}")
        print(f"Main process start : {startCellID}, {startVertex}")

        vtpFullPath = os.path.join(clInPath, f"{vtpName}.vtp")
        algVTK.CVTK.save_poly_data_vtp(vtpFullPath, vesselPolyData)

        cmd = commandExtractionCL.CCommandExtractionCL(self.m_mediator)
        cmd.InputData = dataInst
        cmd.InputIndex = dataInst.CLInfoIndex
        cmd.InputVTPName = vtpName
        cmd.InputCellID = startCellID
        cmd.InputEn = 1
        cmd.CaptureMode = False
        cmd.process()

        if os.path.exists(clOutputFullPath) == False :
            QMessageBox.information(self.m_mediator, "Alarm", "failed to enhanced extraction centerline, please change startCellID")
            return 

        skeleton = algSkeletonGraph.CSkeleton()
        skeleton.load(clOutputFullPath)
        CTabStateVesselRemodeling.refresh_radius(vesselObj.PolyData, skeleton)

        # startVertex를 root에 삽입. 
        rootCL = skeleton.RootCenterline
        rootCL.reverse_by_nn_vertex(startVertex)
        maxRadius = np.max(rootCL.Radius)
        newVertex = np.vstack((startVertex.reshape(-1, 3), rootCL.Vertex))
        newRadius = np.hstack((maxRadius, rootCL.Radius))
        rootCL.Vertex = newVertex
        rootCL.Radius = newRadius

        # max radius refinement 수행 
        self.__refine_max_radius(skeleton)

        node.SkeletonEn = skeleton
        skelID = dataInst.get_id_from_key(node.Key)
        groupID = CTabStateVesselRemodeling.s_skelGroupID + skelID
        node.SkelGroupID = groupID
        self.m_mediator.add_skeleton_cl_obj(node.SkeletonEn, node.SkelGroupID)
        self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, node.SkelGroupID)

        if os.path.exists(vtpFullPath) :
            os.remove(vtpFullPath)
        if os.path.exists(clOutputFullPath) :
            os.remove(clOutputFullPath)
        QMessageBox.information(self.m_mediator, "Alarm", "completed extraction centerline")
    def command_attach_anchor(self) :
        selectedNode = self.getui_lv_cuttednode_selected_node()
        if selectedNode is None :
            QMessageBox.information(self.m_mediator, "Alarm", "Please Select a Node in CuttedList")
            return
        findInx = self.getui_lv_anchor_find_index_by_node(selectedNode)
        if findInx >= 0 :
            QMessageBox.information(self.m_mediator, "Alarm", "Already Anchor Node")
            return
        self.setui_lv_anchor_add(selectedNode)
    def command_remodeling(self) :
        retListMergedMesh = []
        dataInst = self.get_data()

        # anchor remodeling
        listNode = self.getui_lv_anchor_all()
        for anchorNode in listNode :
            key = anchorNode.Key
            obj = dataInst.find_obj_by_key(key)
            mergedMesh = obj.PolyData
            retListMergedMesh.append(mergedMesh)
        
        # skel-node remodeling
        resampledVertex = None
        resampledRadius = None
        listNode = self.getui_lv_subnode_all_node()
        for skelNode in listNode :
            remodelingNodeInst = skelNode.RemodelingNode
            listCLID = skelNode.m_listCLID.copy()
            mainSkeleton = remodelingNodeInst.SkeletonEn
            subToMainClID = dict()
            if mainSkeleton is None :
                continue

            rootCL = mainSkeleton.find_root_cl(listCLID)[0]
            rootID = rootCL.ID
            subToMainClID[0] = rootID
            listCLID.remove(rootID)

            subSkeleton = algSkeletonGraph.CSkeleton()
            clTmp = algSkeletonGraph.CSkeletonCenterline(0)
            clTmp.Vertex = rootCL.Vertex.copy()
            clTmp.Radius = rootCL.Radius.copy()
            subSkeleton.m_listCenterline.append(clTmp)
            for inx, clID in enumerate(listCLID) :
                if clID == mainSkeleton.m_rootCenterline.ID:
                    continue
                cl = mainSkeleton.get_centerline(clID)
                subToMainClID[inx + 1] = cl.ID
                clTmp = algSkeletonGraph.CSkeletonCenterline(inx + 1)
                clTmp.Vertex = cl.Vertex.copy()
                clTmp.Radius = cl.Radius.copy()
                subSkeleton.m_listCenterline.append(clTmp)
            subSkeleton.rebuild_centerline_related_data()
            subSkeleton.build_tree(0)
            bCheck = subSkeleton.check_root_reverse()
            if bCheck == False :
                print("Invalid root-child connection")
                continue

            tmpRemodelingNode = remodelingNode.CRemodelingNode()
            tmpRemodelingNode.m_skeletonEn = subSkeleton

            cmd = commandRemodeling.CCommandRemodelingTreeVessel()
            cmd.InputNode = tmpRemodelingNode
            cmd.InputRadiusMargin = self.getui_spin_radius_margin()
            if self.getui_cb_missing_vessel() == False:
                cmd.m_mainSkeleton = mainSkeleton
                cmd.subToMainClID = subToMainClID
            cmd.process()
            mergedMesh = cmd.OutputRemodelingMesh
            retListMergedMesh.append(mergedMesh)

            if resampledVertex is None :
                resampledVertex = cmd.TreeVesselRemodeling.m_listResampleVertex
                resampledRadius = cmd.TreeVesselRemodeling.m_listResampleRadius
            else :
                resampledVertex = np.concatenate((resampledVertex, cmd.TreeVesselRemodeling.m_listResampleVertex), axis=0)
                resampledRadius = np.concatenate((resampledRadius, cmd.TreeVesselRemodeling.m_listResampleRadius), axis=0)
                
        # merged mesh union 
        mergedMesh = None 
        for remodelingMesh in retListMergedMesh :
            if remodelingMesh is None :
                continue

            if mergedMesh is None :
                mergedMesh = remodelingMesh
            else :
                meshA = CTabStateVesselRemodeling.get_meshlib(mergedMesh)
                meshB = CTabStateVesselRemodeling.get_meshlib(remodelingMesh)

                mesh = algMeshLib.CMeshLib.meshlib_boolean_union(meshA, meshB)
                if mesh is None :
                    print("failed remodeling union")
                else :
                    mesh = algMeshLib.CMeshLib.meshlib_healing(mesh)
                    mergedMesh = CTabStateVesselRemodeling.get_vtkmesh(mesh)
        
        if mergedMesh is None :
            QMessageBox.information(self.m_mediator, "Alarm", "failed Remodeling anchorNode")
            return
        
        if self.getui_cb_missing_vessel() == True and resampledVertex is not None :
            self.m_resampledVertex = resampledVertex
            self.m_resampledRadius = resampledRadius
            self.m_kdTree = KDTree(resampledVertex)
            skeleton = dataInst.get_skeleton(self.get_clinfo_index())
            mergedMesh = self._command_remodeling_undetected_vessel(mergedMesh, skeleton)
        
        # clean merged mesh
        mergedMesh = algVTK.CVTK.laplacian_smoothing(mergedMesh, 5, 0.2)
        mergedMesh = algVTK.CVTK.laplacian_smoothing(mergedMesh, 5, 0.1)

        dataInst = self.get_data()
        clinfoinx = dataInst.CLInfoIndex
        optioninfo = dataInst.OptionInfo

        skelinfo = dataInst.get_skelinfo(clinfoinx)
        blenderName = skelinfo.BlenderName
        triCnt = optioninfo.find_tricnt_of_blendername(blenderName)

        if triCnt > -1 :
            meshlib = CTabStateVesselRemodeling.get_meshlib(mergedMesh)
            meshlib = algMeshLib.CMeshLib.meshlib_decimation(meshlib, triCnt)
            meshlib = algMeshLib.CMeshLib.meshlib_healing(meshlib)
            mergedMesh = CTabStateVesselRemodeling.get_vtkmesh(meshlib)

        cmd = commandRemodeling.CCommandRemodelingAdd(self)
        # cmd.InputAnchorNode = anchorNode
        cmd.InputAnchorNode = self.m_mainNode
        cmd.InputRemodelingMesh = mergedMesh
        bRet = cmd.process()
        if bRet == True :
            self.m_listCmd.append(cmd)
    def command_remodeling_save(self) :
        selectedNode = self.getui_lv_cuttednode_selected_node()
        if selectedNode is None :
            QMessageBox.information(self.m_mediator, "Alarm", "Please Select a Node in CuttedList")
            return
        
        dataInst = self.get_data()
        key = selectedNode.Key
        obj = dataInst.find_obj_by_key(key)
        polydata = obj.PolyData

        terriOutPath = dataInst.get_terri_out_path()
        if os.path.exists(terriOutPath) == False :
            print(f"not found output path : {terriOutPath}")
            return
        
        stlName = selectedNode.Name
        saveFullPath = os.path.join(terriOutPath, f"{stlName}.stl")
        algVTK.CVTK.save_poly_data_stl(saveFullPath, polydata)

        QMessageBox.information(self.m_mediator, "Alarm", f"completed saving {os.path.basename(saveFullPath)}")
    def command_blender_save(self, outputFolder) :
        dataInst = self.get_data()
        stlOutPath = dataInst.get_terri_out_path()
        currPatientID = dataInst.PatientID
        
        #optionFullPath = ""
        
        optionFullPath = os.path.join(os.path.dirname(os.path.dirname(self.m_mediator.FilePath)), "option.json")
        
        meshcleanPath = os.path.join(
            dataInst.OptionInfo.DataRootPath, currPatientID, "02_SAVE", "02_BLENDER_SAVE",  "Auto03_MeshClean", f"{currPatientID}.blend"
        )
        cmd = f"{dataInst.OptionInfo.BlenderExe} -b --python {os.path.join(parentDirPath, 'liver', 'blenderScriptLiver.py')} -- \
        --func_mode RemodelingImportSave \
        --patient_id {currPatientID} \
        --option_path {optionFullPath} \
        --stl_path {stlOutPath} \
        --out_path {outputFolder} \
        --meshclean_path {meshcleanPath}"
        
        os.system(cmd)
        # self.m_mediator.show_dialog(f"Save Blender Done")
        # cmd = f'{dataInst.OptionInfo.BlenderExe} "{cleanupBlenderPath}"'
        # os.system(cmd)
        
        
        
        openPath = os.path.join(
            outputFolder, f"{currPatientID}.blend"
        )
        
        cmd = f"{dataInst.OptionInfo.BlenderExe} --python {os.path.join(parentDirPath, 'liver', 'blenderScriptLiver.py')} -- --patient_id {currPatientID} --stl_path '' --option_path {optionFullPath} --open_path {openPath} --out_path {outputFolder} --func_mode OpenBlend"
        os.system(cmd)
        
    def command_add_skelinfo(self) :
        selectedNode = self.getui_lv_cuttednode_selected_node()
        if selectedNode is None :
            QMessageBox.information(self.m_mediator, "Alarm", "Please Select a Node in CuttedList")
            return
        
        dataInst = self.get_data()
        clinfoinx = self.get_clinfo_index()

        nodeName = selectedNode.Name
        vessel = dataInst.find_obj_by_key(selectedNode.Key).PolyData
        nowSkelinfo = dataInst.get_skelinfo(clinfoinx)

        skelinfo = None
        findInx = -1
        iCnt = dataInst.get_skelinfo_count()
        for inx in range(0, iCnt) :
            tmp = dataInst.get_skelinfo(inx)
            if tmp.BlenderName == nodeName :
                findInx = inx
                break
        
        if findInx == -1 :
            skelinfo = data.CSkelInfo()
        else :
            skelinfo = dataInst.get_skelinfo(findInx)
            self.m_mediator.remove_skeleton_obj(findInx)
            self.m_mediator.remove_vessel_obj(findInx)

        skelinfo.AdvancementRatio = nowSkelinfo.AdvancementRatio
        skelinfo.ResamplingLength = nowSkelinfo.ResamplingLength
        skelinfo.SmoothingIter = nowSkelinfo.SmoothingIter
        skelinfo.SmoothingFactor = nowSkelinfo.SmoothingFactor
        skelinfo.BlenderName = nodeName
        skelinfo.JsonName = nodeName
        skelinfo.Skeleton = None

        clInPath = dataInst.get_cl_in_path()
        terriOutPath = dataInst.get_terri_out_path()
        stlName = nodeName
        saveFullPath = os.path.join(clInPath, f"{stlName}.stl")
        algVTK.CVTK.save_poly_data_stl(saveFullPath, vessel)
        saveFullPath = os.path.join(terriOutPath, f"{stlName}.stl")
        algVTK.CVTK.save_poly_data_stl(saveFullPath, vessel)

        if findInx == -1 :
            dataInst.add_skelinfo(skelinfo)
            findInx = dataInst.get_skelinfo_count() - 1

        self.m_mediator.add_vessel_obj(findInx, 0)

        fullPath = os.path.join(dataInst.OutputPatientPath, f"{data.CData.s_fileName}.json")
        dataInst.save(fullPath)

        QMessageBox.information(self.m_mediator, "Alarm", "Succeed Registrating centerline")
        

    def clicked_mouse_rb(self, clickX, clickY) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        self._get_substate(self.m_state).clicked_mouse_rb(clickX, clickY)
        self.m_mediator.update_viewer()
    def clicked_mouse_rb_shift(self, clickX, clickY) :
        self._get_substate(self.m_state).clicked_mouse_rb_shift(clickX, clickY)
        self.m_mediator.update_viewer()
    def release_mouse_rb(self) :
        self._get_substate(self.m_state).release_mouse_rb()
        self.m_mediator.update_viewer()
    def mouse_move(self, clickX, clickY) :
        self._get_substate(self.m_state).mouse_move(clickX, clickY)
    def mouse_move_rb(self, clickX, clickY) :
        self._get_substate(self.m_state).mouse_move_rb(clickX, clickY)
        self.m_mediator.update_viewer()
    def key_press(self, keyCode : str) :
        self._get_substate(self.m_state).key_press(keyCode)
        self.m_mediator.update_viewer()
    def key_press_with_ctrl(self, keyCode : str) : 
        self._get_substate(self.m_state).key_press_with_ctrl(keyCode)
        self.m_mediator.update_viewer()
    

    # protected
    def _get_color(self, inx : int) -> np.ndarray :
        colorInx = inx % self.m_color.shape[0]
        return self.m_color[colorInx].reshape(-1, 3)
    def _refresh_visible_vessel(self) :
        clinfoInx = self.get_clinfo_index()
        vesselKey = data.CData.make_key(data.CData.s_vesselType, clinfoInx, 0)
        if self.getui_cb_visiblemesh_checked() == False :
            self.m_mediator.unref_key(vesselKey)
        else :
            self.m_mediator.ref_key(vesselKey)
        self.m_mediator.update_viewer()
    def _refresh_visible_vessel_cl(self) :
        clinfoInx = self.get_clinfo_index()
        if self.getui_cb_visiblecl_checked() == False :
            self.m_mediator.unref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
        else :
            self.m_mediator.ref_key_type_groupID(data.CData.s_skelTypeCenterline, clinfoInx)
        self.m_mediator.update_viewer()

    def _select_minor_vessel(self, skeleton, maxDepth, segmentSet = []):
        startDepth = 0
        listcl = []
        visited = set()
        listcl.append(skeleton.RootCenterline.ID)
        visited.add(skeleton.RootCenterline.ID)
        queue = deque([(skeleton.RootCenterline.ID, startDepth)])
    

        iCLCnt = skeleton.get_centerline_count()
        radiusList = []
        for inx in range(0, iCLCnt) :
            cl = skeleton.get_centerline(inx)
            radiusList.append(np.mean(cl.Radius))
            
        q2 = np.percentile(radiusList, 50)  # median
        
        if len(segmentSet) ==  0:
            while queue:
                id, d = queue.popleft()
                # if d >= maxDepth:
                #     continue
                
                cl = skeleton.get_centerline(id)
                parentCLID, listChildCLID = skeleton.get_conn_centerline_id(id)

                for CID in listChildCLID:
                    if CID in visited:
                        continue
                    
                    childCL = skeleton.get_centerline(CID)
                    childMeanR = np.mean(childCL.Radius)
                    if d+1 > maxDepth and childMeanR < q2:
                        continue
                    visited.add(CID)
                    listcl.append(CID)
                    queue.append((CID, d+1))
        else:
            while queue:
                id, d = queue.popleft()
                # if d >= maxDepth:
                #     continue
                cl = skeleton.get_centerline(id)
                parentCLID, listChildCLID = skeleton.get_conn_centerline_id(id)

                for CID in listChildCLID:
                    if CID in visited:
                        continue
                    
                    childCL = skeleton.get_centerline(CID)
                    childMeanR = np.mean(childCL.Radius)
                    if d+1 > maxDepth and childMeanR < q2:
                        continue
                    
                    if childCL.Name in segmentSet and cl.Name in segmentSet and cl.Name == childCL.Name:
                        visited.add(CID)
                        listcl.append(CID)
                        queue.append((CID, d+1))
                    else:
                        visited.add(CID)
                        listcl.append(CID)
                        queue.append((CID, d))
                
        return set(listcl)

        
    def _command_remodeling_undetected_vessel(
        self, 
        mergedMesh : vtk.vtkPolyData, skeleton : algSkeletonGraph.CSkeleton
        ) -> vtk.vtkPolyData :
        if mergedMesh is None :
            return None
        
        # portalSegmentSet = set()
        # for i in range(1, 9):
        #     portalSegmentSet.add(str("S" + str(i)))
            
        # minorClSet = self._select_minor_vessel(skeleton, 3, portalSegmentSet)
        
        # 모든 cl 대상으로 포함 여부 판단 
        retFlag = CTabStateVesselRemodeling.check_in_polydata(mergedMesh, skeleton.KDTreeAnchorVertex)
        iCnt = skeleton.get_centerline_count()
        retListFlag = []
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)


            # 누락 혈관 catch 
            # 이 부분에서 loop를 해결하기 위한 고도화 알고리즘이 추가 되어야 함 
            indices = [i for i, v in enumerate(skeleton.m_listKDTreeAnchorID) if v == inx]
            trueCnt = int(np.count_nonzero(retFlag[indices]))
            falseCnt = len(indices) - trueCnt

            if falseCnt > trueCnt :
                retListFlag.append(False)
            else :
                retListFlag.append(True)
        
        # leaf -> root 경로를 따라 retListFlag가 False인 것만 cl 등록
        retUndetectdCLID = []
        iCnt = skeleton.get_leaf_centerline_count()
        for inx in range(0, iCnt) :
            leafCL = skeleton.get_leaf_centerline(inx)
            listPathCL = skeleton.find_ancestor_centerline_by_centerline_id(leafCL.ID)

            for pathCL in listPathCL :
                pathCLID = pathCL.ID
 
                if retListFlag[pathCLID] == False :
                    retUndetectdCLID.append(pathCLID)
                else :
                    break

        # 누락 혈관이 없음 
        if len(retUndetectdCLID) == 0 :
            return mergedMesh
        retUndetectdCLID = list(set(retUndetectdCLID))

        retListRoot = skeleton.find_root_cl(retUndetectdCLID)
        if retListRoot is None :
            return mergedMesh

        retListMergedMesh = []
        for rootCL in retListRoot :
            listGroupCL = skeleton.find_descendant_centerline_by_centerline_id(rootCL.ID)
            if listGroupCL is None :
                continue

            # for cl in listGroupCL:
            #     if cl.ID not in minorClSet:
            #         listGroupCL.remove(cl)

            subSkeleton = algSkeletonGraph.CSkeleton()
            for inx, cl in enumerate(listGroupCL) :

                clTmp = algSkeletonGraph.CSkeletonCenterline(inx)
                clTmp.Vertex = cl.Vertex.copy()
                clTmp.Radius = cl.Radius.copy()
                subSkeleton.m_listCenterline.append(clTmp)
            subSkeleton.rebuild_centerline_related_data()
            subSkeleton.build_tree(0)

            self.__attach_skeleton_bridge_point(subSkeleton)

            remodeling = remodelingVessel.CTreeVesselRemodeling()
            remodeling.InputSkeleton = subSkeleton
            #remodeling.m_mainSkeleton = subSkeleton
            remodeling.InputRadiusMargin = self.getui_spin_radius_margin()
            remodeling.process()

            if remodeling.MergedMesh is None :
                print(f"failed remodeling undetected vessel {rootCL.ID}")
            else :
                retListMergedMesh.append(remodeling.MergedMesh) 
        
        if len(retListMergedMesh) == 0 :
            return mergedMesh
        
        for remodelingMesh in retListMergedMesh :
            meshA = CTabStateVesselRemodeling.get_meshlib(mergedMesh)
            meshB = CTabStateVesselRemodeling.get_meshlib(remodelingMesh)

            mesh = algMeshLib.CMeshLib.meshlib_boolean_union(meshA, meshB)
            if mesh is None :
                print(f"failed remodeling merge undetected vessel")
            else :
                mesh = algMeshLib.CMeshLib.meshlib_healing(mesh)
                mergedMesh = CTabStateVesselRemodeling.get_vtkmesh(mesh)
        return mergedMesh


    def _get_substate(self, inx : int) -> subStateRemodeling.CSubStateRemodeling :
        return self.m_listSubState[inx]  


    # ui
    def getui_lv_cuttednode_selected_node(self) -> remodelingNode.CRemodelingNode :
        selectedItems = self.m_lvCuttedNode.selectedItems()
        if not selectedItems :
            return None
        
        item = selectedItems[0]
        text = item.text()
        node = item.data(Qt.UserRole) 
        return node
    def getui_lv_cuttednode_selected_index(self) -> int :
        selectedItems = self.m_lvCuttedNode.selectedItems()
        if not selectedItems :
            return -1
        
        item = selectedItems[0]
        index = self.m_lvCuttedNode.row(item)
        return index
    def getui_lv_cuttednode_find_node_by_name(self, nodeName : str) -> remodelingNode.CRemodelingNode :
        count = self.m_lvCuttedNode.count()
        for i in reversed(range(count)) :
            item = self.m_lvCuttedNode.item(i)
            node = item.data(Qt.UserRole)
            if node.Name == nodeName :
                return node
        return None
    def getui_lv_cuttednode_find_index_by_name(self, nodeName : str) -> int :
        count = self.m_lvCuttedNode.count()
        for i in reversed(range(count)) :
            item = self.m_lvCuttedNode.item(i)
            node = item.data(Qt.UserRole)
            if node.Name == nodeName :
                return i
        return -1
    def getui_lv_anchor_selected_node(self) -> remodelingNode.CRemodelingNode :
        selectedItems = self.m_lvAnchor.selectedItems()
        if not selectedItems :
            return None
        
        item = selectedItems[0]
        text = item.text()
        node = item.data(Qt.UserRole) 
        return node
    def getui_lv_anchor_selected_index(self) -> int :
        selectedItems = self.m_lvAnchor.selectedItems()
        if not selectedItems :
            return -1
        
        item = selectedItems[0]
        index = self.m_lvAnchor.row(item)
        return index
    def getui_lv_anchor_find_index_by_node(self, targetNode : remodelingNode.CRemodelingNode) -> int :
        count = self.m_lvAnchor.count()
        for i in reversed(range(count)) :
            item = self.m_lvAnchor.item(i)
            node = item.data(Qt.UserRole)
            if node == targetNode :
                return i
        return -1
    def getui_lv_anchor_all(self) -> list : 
        self.m_lvAnchor.blockSignals(True)
        retList = []

        count = self.m_lvAnchor.count()
        for i in reversed(range(count)) :
            item = self.m_lvAnchor.item(i)
            node = item.data(Qt.UserRole)
            retList.append(node)
    
        self.m_lvAnchor.blockSignals(False)
        return retList

    def getui_cb_visiblemesh_checked(self) -> bool :
        return self.m_cbVisibleMesh.isChecked()
    def getui_cb_visiblecl_checked(self) -> bool :
        return self.m_cbVisibleCL.isChecked()
    def getui_cb_visibleremodeling_checked(self) -> bool :
        return self.m_cbVisibleRemodeling.isChecked()
    def getui_check_sel_cell(self) -> bool :
        if self.m_checkSelectionStartCell.isChecked() :
            return True
        return False
    def getui_cellID(self) -> int :
        cellID = -1
        try :
            cellID = int(self.m_editBoxCellID.text())
        except ValueError:
            cellID = -1
        return cellID
    def getui_spin_dilation_pass_count(self) -> int :
        return self.m_spinDilationPass.value()
    def getui_spin_radius_margin(self) -> float :
        return self.m_spinStrength.value()
    def getui_lv_subnode_all_node(self) -> list : 
        self.m_lvSubNode.blockSignals(True)
        retList = []

        count = self.m_lvSubNode.count()
        for i in reversed(range(count)) :
            item = self.m_lvSubNode.item(i)
            node = item.data(Qt.UserRole)
            retList.append(node)
    
        self.m_lvSubNode.blockSignals(False)
        return retList
    def getui_lv_subnode_find_index(self, targetNode : remodelingNode.CSkelNode) -> int :
        count = self.m_lvCuttedNode.count()
        for i in reversed(range(count)) :
            item = self.m_lvCuttedNode.item(i)
            node = item.data(Qt.UserRole)
            if node == targetNode :
                return i
        return -1
    def getui_lv_subnode_selected_node(self) -> remodelingNode.CSkelNode :
        selectedItems = self.m_lvSubNode.selectedItems()
        if not selectedItems :
            return None
        
        item = selectedItems[0]
        text = item.text()
        node = item.data(Qt.UserRole) 
        return node
    def getui_lv_subnode_selected_index(self) -> int :
        selectedItems = self.m_lvSubNode.selectedItems()
        if not selectedItems :
            return -1
        
        item = selectedItems[0]
        index = self.m_lvSubNode.row(item)
        return index
    def getui_rb_selection_single(self) -> bool :
        return self.m_rbSingle.isChecked()
    def getui_rb_selection_descendant(self) -> bool :
        return self.m_rbDescendant.isChecked()
    def getui_cb_missing_vessel(self) -> bool :
        return self.m_checkMissingVessel.isChecked()

    def setui_lv_cuttednode_add_node(self, node : remodelingNode.CRemodelingNode) :
        self.m_lvCuttedNode.blockSignals(True)

        name = node.Name
        item = QListWidgetItem(f"{name}")
        item.setData(Qt.UserRole, node)
        self.m_lvCuttedNode.addItem(item)

        self.m_lvCuttedNode.blockSignals(False)
    def setui_lv_cuttednode_add_listnode(self, listNode : list) :
        self.m_lvCuttedNode.blockSignals(True)
        self.m_lvCuttedNode.clear()

        for node in listNode :
            name = node.Name
            item = QListWidgetItem(f"{name}")
            item.setData(Qt.UserRole, node)
            self.m_lvCuttedNode.addItem(item)

        self.m_lvCuttedNode.blockSignals(False)
    def setui_lv_cuttednode_remove_node(self, targetNode : remodelingNode.CRemodelingNode) :
        self.m_lvCuttedNode.blockSignals(True)

        self.m_lvCuttedNode.setCurrentItem(None)
        self.m_lvCuttedNode.clearSelection()

        count = self.m_lvCuttedNode.count()
        for i in reversed(range(count)):
            item = self.m_lvCuttedNode.item(i)
            node = item.data(Qt.UserRole)
            if node == targetNode :
                self.m_lvCuttedNode.takeItem(i)
                del item
                break
        
        self.m_lvCuttedNode.blockSignals(False)
    def setui_lv_cuttednode_remove_all(self) :
        self.m_lvCuttedNode.clear()
    def setui_lv_cuttednode_selection_inx(self, inx : int) :
        '''
        inx : 음수일 경우 selection을 해제 시킨다. 
        '''
        self.m_lvCuttedNode.blockSignals(True)

        self.m_lvCuttedNode.clearSelection()
        count = self.m_lvCuttedNode.count()
        if 0 <= inx < count :
            self.m_lvCuttedNode.setCurrentRow(inx)

        self.m_lvCuttedNode.blockSignals(False)
    def setui_lv_cuttednode_clear_selection(self) :
        self.m_lvCuttedNode.blockSignals(True)
        self.m_lvCuttedNode.setCurrentItem(None)
        self.m_lvCuttedNode.blockSignals(False)
    def setui_lv_cuttednode_update_node_name(self, targetNode : remodelingNode.CRemodelingNode) :
        for i in range(self.m_lvCuttedNode.count()):
            item = self.m_lvCuttedNode.item(i)
            storedNode = item.data(Qt.UserRole)
            if storedNode is targetNode :
                item.setText(targetNode.Name)
                break
    def setui_lv_anchor_add(self, node : remodelingNode.CRemodelingNode) :
        self.m_lvAnchor.blockSignals(True)

        name = node.Name
        item = QListWidgetItem(f"{name}")
        item.setData(Qt.UserRole, node)
        self.m_lvAnchor.addItem(item)

        self.m_lvAnchor.blockSignals(False)
    def setui_lv_anchor_remove(self, targetNode : remodelingNode.CRemodelingNode) :
        self.m_lvAnchor.blockSignals(True)

        self.m_lvAnchor.setCurrentItem(None)
        self.m_lvAnchor.clearSelection()

        count = self.m_lvAnchor.count()
        for i in reversed(range(count)):
            item = self.m_lvAnchor.item(i)
            node = item.data(Qt.UserRole)
            if node == targetNode :
                self.m_lvAnchor.takeItem(i)
                del item
                break
        
        self.m_lvAnchor.blockSignals(False)
    def setui_lv_anchor_remove_all(self) :
        self.m_lvAnchor.clear()
    def setui_lv_anchor_selection_inx(self, inx : int) :
        '''
        inx : 음수일 경우 selection을 해제 시킨다. 
        '''
        self.m_lvAnchor.blockSignals(True)

        self.m_lvAnchor.clearSelection()
        count = self.m_lvAnchor.count()
        if 0 <= inx < count :
            self.m_lvAnchor.setCurrentRow(inx)

        self.m_lvAnchor.blockSignals(False)
    def setui_lv_anchor_clear_selection(self) :
        self.m_lvAnchor.blockSignals(True)
        self.m_lvAnchor.setCurrentItem(None)
        self.m_lvAnchor.blockSignals(False)
    def setui_cellID(self, cellID : int) :
        self.m_editBoxCellID.setText(str(cellID))
    def setui_check_sel_cell(self, bCheck : bool) -> bool :
        self.m_checkSelectionStartCell.blockSignals(True)
        self.m_checkSelectionStartCell.setChecked(bCheck)
        self.m_checkSelectionStartCell.blockSignals(False)
    def setui_lv_subnode_add_node(self, node : remodelingNode.CSkelNode) :
        self.m_lvSubNode.blockSignals(True)

        name = node.Name
        item = QListWidgetItem(f"{name}")
        item.setData(Qt.UserRole, node)
        self.m_lvSubNode.addItem(item)

        self.m_lvSubNode.blockSignals(False)
    def setui_lv_subnode_remove_node(self, targetNode : remodelingNode.CSkelNode) :
        self.m_lvSubNode.blockSignals(True)

        self.m_lvSubNode.setCurrentItem(None)
        self.m_lvSubNode.clearSelection()

        count = self.m_lvSubNode.count()
        for i in reversed(range(count)):
            item = self.m_lvSubNode.item(i)
            node = item.data(Qt.UserRole)
            if node == targetNode :
                self.m_lvSubNode.takeItem(i)
                del item
                break
        
        self.m_lvSubNode.blockSignals(False)
    def setui_lv_subnode_remove_all(self) :
        self.m_lvSubNode.clear()
    def setui_lv_subnode_clear_selection(self) :
        self.m_lvSubNode.blockSignals(True)
        # self.m_lvSubNode.clearSelection()
        self.m_lvSubNode.setCurrentItem(None)
        self.m_lvSubNode.blockSignals(False)
    def setui_lv_subnode_selection_inx(self, inx : int) :
        '''
        inx : 음수일 경우 selection을 해제 시킨다. 
        '''
        self.m_lvSubNode.blockSignals(True)

        self.m_lvSubNode.clearSelection()
        count = self.m_lvSubNode.count()
        if 0 <= inx < count :
            self.m_lvSubNode.setCurrentRow(inx)

        self.m_lvSubNode.blockSignals(False)
    def setui_cb_missing_vessel(self, bFlag : bool) :
        self.m_checkMissingVessel.setChecked(bFlag)

    
    # event
    def _on_check_visible_mesh(self, state) :
        '''
        state
            - 0 : unchecked
            - 1 : partially checked
            - 2 : checked
        '''
        if state == 2 :
            bCheck = True
        else :
            bCheck = False
        self._refresh_visible_vessel()
    def _on_check_visible_cl(self, state) :
        '''
        state
            - 0 : unchecked
            - 1 : partially checked
            - 2 : checked
        '''
        if state == 2 :
            bCheck = True
        else :
            bCheck = False
        self._refresh_visible_vessel_cl()
    def _on_lb_clicked_node(self, item, prevItem) :
        prevNode = None
        nowNode = None

        prevNode = self.getui_lv_anchor_selected_node()
        self.setui_lv_anchor_clear_selection()
        if prevNode is None :
            if prevItem is not None :
                prevNode = prevItem.data(Qt.UserRole)
        if item is not None :
            nowNode = item.data(Qt.UserRole)

        self.swap_selected_cutting_node(prevNode, nowNode)
        self._get_substate(self.m_state).changed_cutting_mesh(prevNode, nowNode)
        self.m_mediator.update_viewer()
    def _on_tab_changed(self, index) :
        print(f"Tab changed: index={index}")
        if self.m_state >= 0 :
            self._get_substate(self.m_state).process_end()
        self.m_state = index
        if self.m_state >= 0 :
            self._get_substate(self.m_state).process_init()
        self.m_mediator.update_viewer()
    def _on_return_pressed_label_name(self) :
        labelName = self.m_editLabelName.text()
        self.m_editLabelName.setText("")

        if labelName == "" :
            return
        
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        clinfoInx = self.get_clinfo_index()
        skeleton = dataInst.get_skeleton(clinfoInx)
        if skeleton is None :
            return 
        skelinfo = dataInst.get_skelinfo(clinfoInx)
        if labelName == skelinfo.BlenderName :
            QMessageBox.information(self.m_mediator, "Alarm", f"Invalid Node Name")
            return

        
        selectedNode = self.getui_lv_cuttednode_selected_node()
        if selectedNode is None :
            return
        selectedNode.Name = labelName
        self.setui_lv_cuttednode_update_node_name(selectedNode)

        self.m_mediator.update_viewer()
    def _on_check_sel_cell(self, state) :
        '''
        state
            - 0 : unchecked
            - 1 : partially checked
            - 2 : checked
        '''
        bCheck = False
        if state == 2 :
            bCheck = True
        self._get_substate(self.m_state).checked_sel_cell(bCheck)
    def _on_btn_extraction_centerline(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        self.command_extraction_cl()
        self.m_mediator.update_viewer()
    def _on_btn_minor_selection(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        self._get_substate(self.m_state).btn_select_minor(self.m_minorVelsselMaxDepth.value())
        self.m_mediator.update_viewer()
    def _on_btn_attach_centerline(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        self._get_substate(self.m_state).btn_attach_centerline()
        self.m_mediator.update_viewer()
    def _on_btn_refresh_centerline(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        self._get_substate(self.m_state).btn_refresh_centerline()
        self.m_mediator.update_viewer()
    def _on_btn_remodeling(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        
        self.command_remodeling()
        self.m_mediator.update_viewer()
    def _on_btn_remodeling_save(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        self.command_remodeling_save()
    def _on_btn_blender_save(self):
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
        outputPath = QFileDialog.getExistingDirectory(self.get_main_widget(), "Selection Output Path")
        if outputPath == "" :
            return
        
        self.command_blender_save(outputPath)
        QMessageBox.information(self.m_mediator, "Alarm", "complete to save blender")
    def _on_rb_single(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return
    def _on_rb_descendant(self) :
        dataInst = self.get_data()
        if dataInst.Ready == False :
            return

    
    # private
    def __refine_branch_radius(self, skeleton : algSkeletonGraph.CSkeleton) :
        rootCL = skeleton.RootCenterline
        if rootCL is None :
            return
        
        iLeafCnt = skeleton.get_leaf_centerline_count()
        for leafInx in range(0, iLeafCnt) :
            leafCL = skeleton.get_leaf_centerline(leafInx)
            listAncestor = skeleton.find_ancestor_centerline_by_centerline_id(leafCL.ID)

            iAncestorCnt = len(listAncestor)
            if iAncestorCnt < 2 :
                continue
            
            childCL = leafCL
            for iAncestorInx in range(1, iAncestorCnt) :
                parentCL = listAncestor[iAncestorInx]
                childMaxRadius = np.max(childCL.Radius)
                if parentCL.Radius[-1] < childMaxRadius :
                    parentCL.Radius[-1] = childMaxRadius
                childCL = parentCL
                if childCL is None :
                    break
    def __refine_max_radius(self, skeleton : algSkeletonGraph.CSkeleton) :
        self.__refine_branch_radius(skeleton)

        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)

            branchRadius = cl.Radius[-1]
            cl.Radius = np.maximum(cl.Radius, branchRadius)
    def __refine_limit_radius(self, skeleton : algSkeletonGraph.CSkeleton, limitRadius : float) :
        iCnt = skeleton.get_centerline_count()
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)
            cl.Radius = np.minimum(cl.Radius, limitRadius)
    def __find_root_cl(self, skeleton : algSkeletonGraph.CSkeleton, listCL : list) -> list :
        retList = []

        for cl in listCL :
            clID = cl.ID
            flag = False
            for ancestorCL in listCL :
                ancestorCLID = ancestorCL.ID
                if clID == ancestorCLID :
                    continue
                if skeleton.is_ancestor(ancestorCLID, clID) == True :
                    flag = True
            if flag == False :
                retList.append(cl)

        if len(retList) == 0 :
            return None
        return retList
    def __get_nearest_pos_radius(self, vertex : np.ndarray) -> tuple :
        '''
        ret : (nearestPos, radius)
            None -> not found nearest point info
        '''
        if self.m_kdTree is None :
            return None
        _, npNNIndex = self.m_kdTree.query(vertex.reshape(-1, 3), k=1)
        nearestInx = npNNIndex[0]
        return (self.m_resampledVertex[nearestInx].reshape(-1, 3), self.m_resampledRadius[nearestInx])
    def __attach_skeleton_bridge_point(self, srcSkeleton : algSkeletonGraph.CSkeleton) :
        srcRootCL = srcSkeleton.RootCenterline
        startVertex = srcRootCL.get_vertex(0)

        ret = self.__get_nearest_pos_radius(startVertex)
        if ret is None :
            print("failed attach vessel")
            return
        
        spherePos = ret[0]
        sphereRadius = ret[1]

        outsideInx = remodelingVessel.CTreeVesselRemodeling.find_outside_inx(spherePos, sphereRadius, srcRootCL)
        # centerline이 온전히 내부에만 있을 경우 
        if outsideInx == -1 :
            return
        # centerline의 마지막 점만 나갈경우 
        # 이 경우에는 cylinder가 형성이 안되므로 종료한다. 
        if outsideInx == srcRootCL.get_vertex_count() - 1 :
            return
        
        mergedVertex = np.vstack((spherePos.reshape(-1, 3), srcRootCL.Vertex[outsideInx : ]))
        mergedRadius = np.hstack((sphereRadius, srcRootCL.Radius[outsideInx : ]))
        srcRootCL.Vertex = mergedVertex
        srcRootCL.Radius = mergedRadius

        self.__refine_max_radius(srcSkeleton)
        # self.__refine_limit_radius(srcSkeleton, sphereRadius)

        


    @property
    def MainNode(self) -> remodelingNode.CRemodelingNode :
        return self.m_mainNode



if __name__ == '__main__' :
    pass


# print ("ok ..")

