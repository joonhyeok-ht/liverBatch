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


class RemodelingKeyFilter(QObject) :
    def __init__(self, callback) :
        super().__init__()
        self.callback = callback
    def eventFilter(self, obj, event) :
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Delete, Qt.Key_Backspace) :
            self.callback()
            return True
        return super().eventFilter(obj, event)


class CTabStateVesselRemodeling(tabState.CTabState) :
    s_dbgType = "dbgType"

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
        self.m_mainNode.Skeleton = skeleton
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
        self.m_mediator.remove_key_type(subStateRemodeling.CSubStateRemodeling.s_subSkelType)
        self.clear_render_entity()
        self.m_cuttedMeshID = 0
        self.m_nodeNameID = 0
        self.m_mainNode = None

        for cmd in self.m_listCmd :
            cmd.clear()
        self.m_listCmd.clear()

        self.setui_lv_cuttednode_remove_all()
        for node in self.m_listRemodelingNode :
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
        self.m_lvCuttedNode.itemClicked.connect(self._on_lb_clicked_node)
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

        nodeLayout = QHBoxLayout()
        leftLayout = QVBoxLayout()
        rightLayout = QVBoxLayout()

        subTabLayout.addLayout(nodeLayout)
        nodeLayout.addLayout(leftLayout)
        nodeLayout.addLayout(rightLayout)


        label = QLabel("Anchor-Node ")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.m_editAnchor = QLineEdit()
        self.m_editAnchor.setText("")
        self.m_editAnchor.setReadOnly(True)

        labelFloat = QLabel("Radius-Margin ")
        labelFloat.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        labelFloat.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.m_spinStrength = QDoubleSpinBox()
        self.m_spinStrength.setRange(-1.0, 1.0)
        self.m_spinStrength.setSingleStep(0.1)
        self.m_spinStrength.setDecimals(1)
        self.m_spinStrength.setValue(0.0)

        leftLayout.addWidget(label)
        leftLayout.addWidget(self.m_editAnchor)
        leftLayout.addWidget(labelFloat)
        leftLayout.addWidget(self.m_spinStrength)
        leftLayout.addStretch() 

        label = QLabel("Sub-Node ")
        label.setStyleSheet("QLabel { margin-top: 1px; margin-bottom: 1px; }")
        label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.m_lvSubNode = QListWidget()
        remodelingKeyFilter = RemodelingKeyFilter(self._on_lb_clicked_subnode_delete)
        self.m_lvSubNode.installEventFilter(remodelingKeyFilter)
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
        self.m_mediator.unref_key_type(subStateRemodeling.CSubStateRemodeling.s_cuttingMeshType)
        self.m_mediator.unref_key_type(subStateRemodeling.CSubStateRemodeling.s_subSkelType)
        self.clear_render_entity()

        node = self.m_listRemodelingNode[selectionInx]
        self.m_mediator.ref_key(node.Key)
        if node.SkelKey != "" :
            self.m_mediator.ref_key(node.SkelKey)
        if node.SkelEnKey != "" :
            self.m_mediator.ref_key(node.SkelEnKey)
        if node.RootEntity is not None :
            self.add_render_entity(node.RootEntity)

        self._get_substate(self.m_state).changed_cutting_mesh()
        self.setui_lv_cuttednode_selection_inx(selectionInx)
    def refresh_remodeling_node_list(self, listRemodelingNode : list) :
        self.m_mediator.unref_key_type(subStateRemodeling.CSubStateRemodeling.s_cuttingMeshType)
        self.m_mediator.unref_key_type(subStateRemodeling.CSubStateRemodeling.s_subSkelType)
        self.m_listRemodelingNode = listRemodelingNode
        self.setui_lv_cuttednode_add_listnode(self.m_listRemodelingNode)
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
            self.m_mediator.remove_key(node.SkelKey)
            self.m_mediator.remove_key(node.SkelEnKey)
            self.clear_render_entity()
            node.SkelKey = ""
            node.SkelEnKey = ""
            node.Skeleton = None
            node.SkeletonEn = None
            node.RootEntity = None

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

        skelID = dataInst.get_id_from_key(node.Key)
        groupID = 1
        skelKey = data.CData.make_key(subStateRemodeling.CSubStateRemodeling.s_subSkelType, groupID, skelID)
        skelPolyData = algVTK.CVTK.create_poly_data_spheres(skeleton.KDTreeAnchorVertex, data.CData.s_clSize)
        skelObj = vtkObjInterface.CVTKObjInterface()
        skelObj.KeyType = subStateRemodeling.CSubStateRemodeling.s_subSkelType
        skelObj.Key = skelKey
        skelObj.Color = algLinearMath.CScoMath.to_vec3([0.0, 1.0, 0.0])
        skelObj.Opacity = 0.3
        skelObj.PolyData = skelPolyData
        dataInst.add_vtk_obj(skelObj)

        rootCL = skeleton.RootCenterline
        rootMesh = algVTK.CVTK.create_poly_data_spheres(rootCL.Vertex, 0.6)
        rootEntity = tabState.CRenderEntity()
        rootEntity.PolyData = rootMesh
        rootEntity.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 0.0])
        node.RootEntity = rootEntity
        self.add_render_entity(rootEntity)

        node.SkelEnKey = skelKey
        node.SkeletonEn = skeleton
        self.m_mediator.ref_key(skelKey)

        if node.Skeleton is not None :
            if os.path.exists(vtpFullPath) :
                os.remove(vtpFullPath)
            if os.path.exists(clOutputFullPath) :
                os.remove(clOutputFullPath)
            QMessageBox.information(self.m_mediator, "Alarm", "completed extraction centerline")
            return
        
        print("-- normal skeleton extraction --")
        cmd = commandExtractionCL.CCommandExtractionCL(self.m_mediator)
        cmd.InputData = dataInst
        cmd.InputIndex = dataInst.CLInfoIndex
        cmd.InputVTPName = vtpName
        cmd.InputCellID = startCellID
        cmd.InputEn = 0
        cmd.CaptureMode = False
        cmd.process()

        skeleton = algSkeletonGraph.CSkeleton()
        skeleton.load(clOutputFullPath)
        CTabStateVesselRemodeling.refresh_radius(vesselObj.PolyData, skeleton)
        rootCL = skeleton.RootCenterline
        rootCL.reverse_by_nn_vertex(startVertex)

        skelID = dataInst.get_id_from_key(node.Key)
        groupID = 0
        skelKey = data.CData.make_key(subStateRemodeling.CSubStateRemodeling.s_subSkelType, groupID, skelID)
        skelPolyData = algVTK.CVTK.create_poly_data_spheres(skeleton.KDTreeAnchorVertex, data.CData.s_clSize)
        skelObj = vtkObjInterface.CVTKObjInterface()
        skelObj.KeyType = subStateRemodeling.CSubStateRemodeling.s_subSkelType
        skelObj.Key = skelKey
        skelObj.Color = algLinearMath.CScoMath.to_vec3([1.0, 0.0, 1.0])
        skelObj.Opacity = 1.0
        skelObj.PolyData = skelPolyData
        dataInst.add_vtk_obj(skelObj)
        self.m_mediator.ref_key(skelKey)

        node.SkelKey = skelKey
        node.Skeleton = skeleton

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
        self.setui_edit_anchor_name(selectedNode.Name)
    def command_attach_sub(self) :
        selectedNode = self.getui_lv_cuttednode_selected_node()
        if selectedNode is None :
            QMessageBox.information(self.m_mediator, "Alarm", "Please Select a Node in CuttedList")
            return
        anchorName = self.getui_edit_anchor_name()
        if anchorName == selectedNode.Name :
            QMessageBox.information(self.m_mediator, "Alarm", "The anchor node cannot be added as a sub-node")
            return
        self.setui_lv_subnode_add_node(selectedNode)
    def command_remodeling(self) :
        listNode = []
        retListMergedMesh = []
        dataInst = self.get_data()

        anchorNodeName = self.getui_edit_anchor_name()
        anchorNode = self.getui_lv_cuttednode_find_node_by_name(anchorNodeName)
        if anchorNode is None :
            QMessageBox.information(self.m_mediator, "Alarm", "Please Select AnchorNode")
            return

        listNode.append(anchorNode)
        listTmp = self.getui_lv_subnode_all_node()
        for node in listTmp :
            listNode.append(node)

        self.clear_render_entity()
        
        for node in listNode :
            mergedMesh = None
            if node.SkeletonEn is not None :
                mergedMesh = self._command_remodeling_node(node)
            else :
                key = node.Key
                obj = dataInst.find_obj_by_key(key)
                mergedMesh = obj.PolyData
            retListMergedMesh.append(mergedMesh)
        
        # retMesh union
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
        cmd.InputAnchorNode = anchorNode
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
    def _command_remodeling_node(self, node : remodelingNode.CRemodelingNode) -> vtk.vtkPolyData :
        if node.SkeletonEn is None :
            print(f"failed remodeling {node.Name}")
            return None
        
        cmd = commandRemodeling.CCommandRemodelingTreeVessel()
        cmd.InputNode = node
        cmd.InputRadiusMargin = self.getui_spin_radius_margin()
        cmd.process()
        mergedMesh = cmd.OutputRemodelingMesh

        if mergedMesh is None :
            print(f"failed remodeling {node.Name}")
            return None
        
        skeleton = node.Skeleton
        if skeleton is None :
            return mergedMesh
        
        cmd.TreeVesselRemodeling.build_kd_tree()
        return self._command_remodeling_undetected_vessel(mergedMesh, cmd.TreeVesselRemodeling, skeleton)
    def _command_remodeling_undetected_vessel(
        self, 
        mergedMesh : vtk.vtkPolyData, 
        cmd : remodelingVessel.CTreeVesselRemodeling,
        skeleton : algSkeletonGraph.CSkeleton
        ) -> vtk.vtkPolyData :
        if mergedMesh is None :
            return None
        
        retFlag = CTabStateVesselRemodeling.check_in_polydata(mergedMesh, skeleton.KDTreeAnchorVertex)
        iCnt = skeleton.get_centerline_count()
        retListCL = []
        for inx in range(0, iCnt) :
            cl = skeleton.get_centerline(inx)

            # 누락 혈관 catch 
            # 이 부분에서 loop를 해결하기 위한 고도화 알고리즘이 추가 되어야 함 
            indices = [i for i, v in enumerate(skeleton.m_listKDTreeAnchorID) if v == inx]
            trueCnt = int(np.count_nonzero(retFlag[indices]))
            falseCnt = len(indices) - trueCnt

            if falseCnt > trueCnt :
                retListCL.append(cl)
        
        # 누락 혈관이 없음 
        if len(retListCL) == 0 :
            return mergedMesh
        
        retListRoot = self.__find_root_cl(skeleton, retListCL)
        if retListRoot is None :
            return mergedMesh

        retListMergedMesh = []
        for rootCL in retListRoot :
            listGroupCL = skeleton.find_descendant_centerline_by_centerline_id(rootCL.ID)
            if listGroupCL is None :
                continue

            subSkeleton = algSkeletonGraph.CSkeleton()
            for inx, cl in enumerate(listGroupCL) :
                clTmp = algSkeletonGraph.CSkeletonCenterline(inx)
                clTmp.Vertex = cl.Vertex.copy()
                clTmp.Radius = cl.Radius.copy()
                subSkeleton.m_listCenterline.append(clTmp)
            subSkeleton.rebuild_centerline_related_data()
            subSkeleton.build_tree(0)

            self.__attach_skeleton_bridge_point(cmd, subSkeleton)

            remodeling = remodelingVessel.CTreeVesselRemodeling()
            remodeling.InputSkeleton = subSkeleton
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
    def getui_edit_anchor_name(self) -> str :
        return self.m_editAnchor.text()
    def getui_lv_subnode_all_node(self) -> list :
        self.m_lvSubNode.blockSignals(True)
        retList = []

        count = self.m_lvSubNode.count()
        for i in reversed(range(count)):
            item = self.m_lvSubNode.item(i)
            node = item.data(Qt.UserRole)
            retList.append(node)
    
        self.m_lvSubNode.blockSignals(False)
        return retList
    def getui_lv_subnode_selected_node(self) -> remodelingNode.CRemodelingNode :
        selectedItems = self.m_lvSubNode.selectedItems()
        if not selectedItems :
            return None
        
        item = selectedItems[0]
        text = item.text()
        node = item.data(Qt.UserRole) 
        return node

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
        self.m_lvCuttedNode.clearSelection()
        count = self.m_lvCuttedNode.count()
        if 0 <= inx < count :
            self.m_lvCuttedNode.setCurrentRow(inx)
    def setui_lv_cuttednode_update_node_name(self, targetNode : remodelingNode.CRemodelingNode) :
        for i in range(self.m_lvCuttedNode.count()):
            item = self.m_lvCuttedNode.item(i)
            storedNode = item.data(Qt.UserRole)
            if storedNode is targetNode :
                item.setText(targetNode.Name)
                break
    def setui_cellID(self, cellID : int) :
        self.m_editBoxCellID.setText(str(cellID))
    def setui_check_sel_cell(self, bCheck : bool) -> bool :
        self.m_checkSelectionStartCell.blockSignals(True)
        self.m_checkSelectionStartCell.setChecked(bCheck)
        self.m_checkSelectionStartCell.blockSignals(False)
    def setui_edit_anchor_name(self, anchorName : str) :
        self.m_editAnchor.setText(anchorName)
    def setui_lv_subnode_add_node(self, node : remodelingNode.CRemodelingNode) :
        self.m_lvSubNode.blockSignals(True)

        name = node.Name
        item = QListWidgetItem(f"{name}")
        item.setData(Qt.UserRole, node)
        self.m_lvSubNode.addItem(item)

        self.m_lvSubNode.blockSignals(False)
    def setui_lv_subnode_remove_node(self, targetNode : remodelingNode.CRemodelingNode) :
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
    def _on_lb_clicked_node(self, item) :
        node = item.data(Qt.UserRole)
        if node is None :
            print("not found node")
            return
        
        self.m_mediator.unref_key_type(subStateRemodeling.CSubStateRemodeling.s_cuttingMeshType)
        self.m_mediator.unref_key_type(subStateRemodeling.CSubStateRemodeling.s_subSkelType)
        self.clear_render_entity()
        self.m_mediator.ref_key(node.Key)
        if node.SkelKey != "" :
            self.m_mediator.ref_key(node.SkelKey)
        if node.SkelEnKey != "" :
            self.m_mediator.ref_key(node.SkelEnKey)
        if node.RootEntity is not None :
            self.add_render_entity(node.RootEntity)
        self._get_substate(self.m_state).changed_cutting_mesh()
        self.m_mediator.update_viewer()
    def _on_lb_clicked_subnode_node(self, item) :
        node = item.data(Qt.UserRole)
        if node is None :
            print("not found node")
            return
    def _on_lb_clicked_subnode_delete(self) :
        selectedNode = self.getui_lv_subnode_selected_node()
        if selectedNode is None :
            return 
        
        self.setui_lv_subnode_remove_node(selectedNode)
    def _on_tab_changed(self, index) :
        print(f"Tab changed: index={index}")
        if self.m_state >= 0 :
            self._get_substate(self.m_state).process_end()
        self.m_state = index
        if self.m_state >= 0 :
            self._get_substate(self.m_state).process_init()
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
    def __attach_skeleton_bridge_point(self, cmd : remodelingVessel.CTreeVesselRemodeling, srcSkeleton : algSkeletonGraph.CSkeleton) :
        srcRootCL = srcSkeleton.RootCenterline
        startVertex = srcRootCL.get_vertex(0)

        ret = cmd.get_nearest_pos_radius(startVertex)
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

