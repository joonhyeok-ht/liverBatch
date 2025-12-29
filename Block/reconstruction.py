import sys
import os
import numpy as np
import vtk
from vtkmodules.util import numpy_support

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algLinearMath as algLinearMath
import AlgUtil.algImage as algImage
import AlgUtil.algVTK as algVTK
import AlgUtil.algMeshLib as algMeshLib 

import multiProcessTask as multiProcessTask
import niftiContainer as niftiContainer
import optionInfo as optionInfo



class CReconstruction(multiProcessTask.CMultiProcessTask) :
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
    def reconstruction_territory(
        inputNiftiFullPath : str,
        origin, direction,
        contour : int, reconParam, algorithm : str, gaussian : int, resampling : int
    ) -> vtk.vtkPolyData :
        if algorithm == "MarchingSharpness" or algorithm == "MarchingSharpnessPro" :
            iter = reconParam[0]
            reduction = reconParam[1]
            sharpnessAngle = reconParam[2]
            sharpnessNormalAngle = reconParam[3]
        else :
            iter = reconParam[0]
            rel = reconParam[1]
            deci = reconParam[2]
        
        if gaussian == 1 :
            gaussian = True
        else :
            gaussian = False
 
        matPhy = algVTK.CVTK.get_phy_matrix_without_scale(origin, direction)
        vtkImg = algVTK.CVTK.image_data_load_from_nifti(inputNiftiFullPath)
        if algorithm == "Marching" :
            polyData = algVTK.CVTK.recon_marching_cube(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "MarchingPro" : 
            polyData = algVTK.CVTK.recon_marching_cube_pro(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "Flying" :
            polyData = algVTK.CVTK.recon_fly_edge3d(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "FlyingPro" :
            polyData = algVTK.CVTK.recon_fly_edge3d_pro(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "MarchingSharpness" :
            polyData = algVTK.CVTK.recon_marching_cube_sharpness(vtkImg, 0, contour, iter, reduction, sharpnessAngle, sharpnessNormalAngle, matPhy)
        elif algorithm == "MarchingSharpnessPro" : 
            polyData = algVTK.CVTK.recon_marching_cube_sharpness_pro(vtkImg, 0, contour, iter, reduction, sharpnessAngle, sharpnessNormalAngle, matPhy)
        return polyData
    @staticmethod
    def reconstruction_nifti(
        inputNiftiFullPath : str,
        origin, spacing, direction, phaseOffset : np.ndarray,
        contour : int, reconParam, algorithm : str, gaussian : int, resampling : int,
        bFlip = True
        ) -> vtk.vtkPolyData :
        if algorithm == "MarchingSharpness" or algorithm == "MarchingSharpnessPro" :
            iter = reconParam[0]
            reduction = reconParam[1]
            sharpnessAngle = reconParam[2]
            sharpnessNormalAngle = reconParam[3]
        else :
            iter = reconParam[0]
            rel = reconParam[1]
            deci = reconParam[2]
        
        if gaussian == 1 :
            gaussian = True
        else :
            gaussian = False

        if bFlip == True :
            matPhy = algVTK.CVTK.get_vtk_phy_matrix_with_offset(origin, spacing, direction, phaseOffset)
        else : 
            matPhy = algVTK.CVTK.get_phy_matrix_without_scale(origin, direction)
            mat4Offset = algLinearMath.CScoMath.translation_mat4(phaseOffset)
            matPhy = algLinearMath.CScoMath.mul_mat4_mat4(mat4Offset, matPhy)

        vtkImg = algVTK.CVTK.image_data_load_from_nifti(inputNiftiFullPath)
        if algorithm == "Marching" :
            polyData = algVTK.CVTK.recon_marching_cube(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "MarchingPro" : 
            polyData = algVTK.CVTK.recon_marching_cube_pro(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "Flying" :
            polyData = algVTK.CVTK.recon_fly_edge3d(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "FlyingPro" :
            polyData = algVTK.CVTK.recon_fly_edge3d_pro(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "MarchingSharpness" :
            polyData = algVTK.CVTK.recon_marching_cube_sharpness(vtkImg, 0, contour, iter, reduction, sharpnessAngle, sharpnessNormalAngle, matPhy)
        elif algorithm == "MarchingSharpnessPro" : 
            polyData = algVTK.CVTK.recon_marching_cube_sharpness_pro(vtkImg, 0, contour, iter, reduction, sharpnessAngle, sharpnessNormalAngle, matPhy)
        return polyData
    

    def __init__(self) -> None:
        super().__init__()

        self.m_inputOptionInfo = None
        self.m_inputPhase = None
        self.m_inputMaskPath = ""
        self.m_outputPath = ""
    def clear(self) :
        # input your code
        self.m_inputOptionInfo = None
        self.m_inputPhase = None
        self.m_inputMaskPath = ""
        self.m_outputPath = ""
        super().clear()
    def process(self) :
        if self.InputOptionInfo is None :
            print("recon : not setting input optionInfo")
            return
        if self.InputPhase is None :
            print("recon : not setting input phase")
            return 
        if self.InputMaskPath == "" :
            print("recon : not setting input mask path")
            return 
        if self.OutputPath == "" :
            print("recon : not setting output path")
            return 
        
        if not os.path.exists(self.InputMaskPath) :
            print("recon : not existing input mask path")
            return 
        if not os.path.exists(self.m_outputPath) :
            os.makedirs(self.m_outputPath)

        listParam = []

        iReconCnt = self.InputOptionInfo.get_recon_count()
        for reconInx in range(0, iReconCnt) :
            contour, gaussian, algorithm, resampling = self.InputOptionInfo.get_recon_info(reconInx)
            listReconParam = []
            iReconParamCnt = self.InputOptionInfo.get_recon_param_count(reconInx)
            for reconParamInx in range(0, iReconParamCnt) :
                iter, relax, deci = self.InputOptionInfo.get_recon_param(reconInx, reconParamInx)
                listReconParam.append((iter, relax, deci))
            
            if len(listReconParam) < 1 :
                print(f"recon : error recon param count")
                continue
            
            iReconListCnt = self.InputOptionInfo.get_recon_list_count(reconInx)
            for reconListInx in range(0, iReconListCnt) :
                maskName, blenderName, phase, triCnt = self.InputOptionInfo.get_recon_list(reconInx, reconListInx)
                phaseInfo = self.InputPhase.find_phaseinfo(phase)
                
                if phaseInfo is None or phaseInfo.is_valid() == False :
                    print(f"recon : not found phaseinfo {maskName}")
                    continue
                if blenderName == "" :
                    print(f"recon : skip {maskName}")
                    continue

                maskFullPath = os.path.join(self.InputMaskPath, f"{maskName}.nii.gz")
                blenderFullPath = os.path.join(self.OutputPath, f"{blenderName}.stl")
                if os.path.exists(maskFullPath) == False :
                    print(f"recon : not found {maskName}")
                    continue

                listParam.append((contour, gaussian, algorithm, resampling, listReconParam, maskFullPath, blenderFullPath, phaseInfo, triCnt))

        if len(listParam) == 0 :
            print("passed recon")
            return
        
        super().process(self._task, listParam)


    # param (contour, gaussian, algorithm, resampling, listReconParam, maskFullPath, blenderFullPath, phaseInfo, triCnt)
    def _task(self, param : tuple) :
        contour = param[0]
        gaussian = param[1]
        algorithm = param[2]
        resampling = param[3]
        listReconParam = param[4]
        maskFullPath = param[5]
        blenderFullPath = param[6]
        phaseinfo = param[7]
        triCnt = param[8]

        origin = phaseinfo.Origin
        spacing = phaseinfo.Spacing
        direction = phaseinfo.Direction
        size = phaseinfo.Size
        phaseOffset = phaseinfo.Offset
        matPhy = algVTK.CVTK.get_vtk_phy_matrix_with_offset(origin, spacing, direction, phaseOffset)

        reconParam = listReconParam[0]
        if algorithm == "MarchingSharpness" or algorithm == "MarchingSharpnessPro" :
            iter = reconParam[0]
            reduction = reconParam[1]
            sharpnessAngle = reconParam[2]
            sharpnessNormalAngle = reconParam[3]
        else :
            iter = reconParam[0]
            rel = reconParam[1]
            deci = reconParam[2]
        
        if gaussian == 1 :
            gaussian = True
        else :
            gaussian = False
        
        polydata = None
        vtkImg = algVTK.CVTK.image_data_load_from_nifti(maskFullPath)
        if algorithm == "Marching" :
            polydata = algVTK.CVTK.recon_marching_cube(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "MarchingPro" : 
            polydata = algVTK.CVTK.recon_marching_cube_pro(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "Flying" :
            polydata = algVTK.CVTK.recon_fly_edge3d(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "FlyingPro" :
            polydata = algVTK.CVTK.recon_fly_edge3d_pro(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "MarchingSharpness" :
            polydata = algVTK.CVTK.recon_marching_cube_sharpness(vtkImg, 0, contour, iter, reduction, sharpnessAngle, sharpnessNormalAngle, matPhy)
        elif algorithm == "MarchingSharpnessPro" : 
            polydata = algVTK.CVTK.recon_marching_cube_sharpness_pro(vtkImg, 0, contour, iter, reduction, sharpnessAngle, sharpnessNormalAngle, matPhy)
        
        if polydata is None :
            print(f"recon : failed to recon {os.path.basename(maskFullPath)}")
            return 
        if triCnt > 0 : 
            meshlib = CReconstruction.get_meshlib(polydata)
            meshlib = algMeshLib.CMeshLib.meshlib_healing(meshlib)
            meshlib = algMeshLib.CMeshLib.meshlib_decimation(meshlib, triCnt)
            meshlib = algMeshLib.CMeshLib.meshlib_healing(meshlib)
            polydata = CReconstruction.get_vtkmesh(meshlib)
        
        iCnt = len(listReconParam)
        for inx in range(1, iCnt) :
            reconParam = listReconParam[inx]
            if algorithm == "MarchingSharpness" or algorithm == "MarchingSharpnessPro" :
                iter = reconParam[0]
                rel = reconParam[1]
                sharpnessAngle = reconParam[2]
                sharpnessNormalAngle = reconParam[3]
            else :
                iter = reconParam[0]
                rel = reconParam[1]
                deci = reconParam[2]
            polydata = algVTK.CVTK.laplacian_smoothing(polydata, iter, rel)
        
        algVTK.CVTK.save_poly_data_stl(blenderFullPath, polydata)
        print(f"saved stl : {os.path.basename(blenderFullPath)}")

    
    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, inputOptionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = inputOptionInfo
    @property
    def InputPhase(self) -> niftiContainer.CPhase :
        return self.m_inputPhase
    @InputPhase.setter
    def InputPhase(self, inputPhase : niftiContainer.CPhase) :
        self.m_inputPhase = inputPhase
    @property
    def InputMaskPath(self) -> str :
        return self.m_inputMaskPath
    @InputMaskPath.setter
    def InputMaskPath(self, inputMaskPath : str) :
        self.m_inputMaskPath = inputMaskPath
    @property
    def OutputPath(self) -> str :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath


if __name__ == '__main__' :
    pass


# print ("ok ..")

