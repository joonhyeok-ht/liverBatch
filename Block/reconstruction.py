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

import multiProcessTask as multiProcessTask
import niftiContainer as niftiContainer
import optionInfo as optionInfo



class CReconstruction(multiProcessTask.CMultiProcessTask) :
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
        self.m_inputNiftiContainer = None
        self.m_outputPath = ""
    def clear(self) :
        # input your code
        self.m_inputOptionInfo = None
        self.m_inputNiftiContainer = None
        self.m_outputPath = ""
        super().clear()
    def process(self) :
        if self.InputOptionInfo is None :
            print("recon : not setting input optionInfo")
            return
        if self.InputNiftiContainer is None :
            print("recon : not setting input nifti container")
            return 
        
        if not os.path.exists(self.m_outputPath) :
            os.makedirs(self.m_outputPath)

        listParam = []
        iNiftiInfoCnt = self.InputNiftiContainer.get_nifti_info_count()
        for inx in range(0, iNiftiInfoCnt) :
            niftiInfo = self.InputNiftiContainer.get_nifti_info(inx)
            reconType = niftiInfo.MaskInfo.ReconType
            phaseInfo = self.InputNiftiContainer.find_phase_info(niftiInfo.MaskInfo.Phase)

            if self.InputOptionInfo.find_recon_param(reconType) is None :
                pass
                #print(f"not found recon type {reconType}")
            elif niftiInfo.Valid == False :
                pass
                #print(f"not found data {niftiInfo.MaskInfo.Name}")
            elif phaseInfo is None :
                pass
                #print(f"not found phase info {niftiInfo.MaskInfo.Name}")
            else :
                listParam.append((niftiInfo, phaseInfo))

        super().process(self._task, listParam)


    # param (vertex, reconType, outputStlName)
    def _task(self, param : tuple) :
        niftiInfo = param[0]
        phaseInfo = param[1]

        reconType = niftiInfo.MaskInfo.ReconType
        reconParam = self.InputOptionInfo.find_recon_param(reconType)
        contour = reconParam.Contour
        algorithm = reconParam.Algorithm
        param = reconParam.Param
        gaussian = reconParam.Gaussian
        resampling = reconParam.ResamplingFactor

        blenderName = niftiInfo.MaskInfo.BlenderName
        vertex = niftiInfo.Vertex

        origin = phaseInfo.Origin
        spacing = phaseInfo.Spacing
        direction = phaseInfo.Direction
        size = phaseInfo.Size
        phaseOffset = phaseInfo.Offset

        if algorithm == "MarchingSharpness" or algorithm == "MarchingSharpnessPro" :
            iter = param[0]
            reduction = param[1]
            sharpnessAngle = param[2]
            sharpnessNormalAngle = param[3]
        else :
            iter = param[0]
            rel = param[1]
            deci = param[2]
        
        if gaussian == 1 :
            gaussian = True
        else :
            gaussian = False
        
        inputNiftiFullPath = ""
        if vertex is not None :
            inputNiftiFullPath = os.path.join(self.OutputPath, f"{blenderName}.nii.gz")
            npImg = algImage.CAlgImage.create_np(size, np.uint8)
            algImage.CAlgImage.set_clear(npImg, 0)
            algImage.CAlgImage.set_value(npImg, vertex, 255)
            algImage.CAlgImage.save_nifti_from_np(inputNiftiFullPath, npImg, origin, spacing, direction, (2, 1, 0))
            print(f"saved nifti : {inputNiftiFullPath}")
            npImg = None
        else :
            inputNiftiFullPath = niftiInfo.FullPath


        outputStlFullPath = os.path.join(self.OutputPath, f"{blenderName}.stl")

        matPhy = algVTK.CVTK.get_vtk_phy_matrix_with_offset(origin, spacing, direction, phaseOffset)
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
        algVTK.CVTK.save_poly_data_stl(outputStlFullPath, polyData)
        #print(f"saved stl : {outputStlFullPath}")

    
    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, inputOptionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = inputOptionInfo
    @property
    def InputNiftiContainer(self) -> niftiContainer.CNiftiContainer :
        return self.m_inputNiftiContainer
    @InputNiftiContainer.setter
    def InputNiftiContainer(self, inputNiftiContainer : niftiContainer.CNiftiContainer) :
        self.m_inputNiftiContainer = inputNiftiContainer
    @property
    def OutputPath(self) -> str :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath





class CReconstructionRange(multiProcessTask.CMultiProcessTask) :
    def __init__(self) -> None:
        super().__init__()
        self.m_inputOptionInfo = None
        self.m_inputNiftiContainer = None
        self.m_inputNiftiInfo = None
        self.m_outputPath = ""
    def clear(self) :
        # input your code
        self.m_inputOptionInfo = None
        self.m_inputNiftiContainer = None
        self.m_inputNiftiInfo = None
        self.m_outputPath = ""
        super().clear()
    def process(self) :
        if self.InputOptionInfo is None :
            print("recon : not setting input optionInfo")
            return
        if self.InputNiftiContainer is None :
            print("recon : not setting input nifti container")
            return 
        
        if not os.path.exists(self.m_outputPath) :
            os.makedirs(self.m_outputPath)
        
        listParam = []
        niftiInfo = self.InputNiftiInfo

        outputPath = os.path.join(self.OutputPath, niftiInfo.MaskInfo.BlenderName)
        if not os.path.exists(outputPath) :
            os.makedirs(outputPath)
        
        reconType = niftiInfo.MaskInfo.ReconType
        reconParam = self.InputOptionInfo.find_recon_param(reconType)
        phaseInfo = self.InputNiftiContainer.find_phase_info(niftiInfo.MaskInfo.Phase)
        
        if reconParam is None :
            print(f"not found recon type {reconType}")
        elif phaseInfo is None :
            print(f"not found phase info {niftiInfo.MaskInfo.Name}")
        else :
            algorithm = reconParam.Algorithm

            if algorithm == "MarchingSharpness" or algorithm == "MarchingSharpnessPro" :
                deciRange = reconParam.DeciRange
                startDeci = deciRange[0]
                endDeci = deciRange[1]
                deltaDeci = deciRange[2]

                sharpnessAngleRange = reconParam.SharpnessAngleRange
                startSharpnessAngle = sharpnessAngleRange[0]
                endSharpnessAngle = sharpnessAngleRange[1]
                deltaSharpnessAngle = sharpnessAngleRange[2]

                sharpnessNormalAngleRange = reconParam.SharpnessNormalAngleRange
                startSharpnessNormalAngle = sharpnessNormalAngleRange[0]
                endSharpnessNormalAngle = sharpnessNormalAngleRange[1]
                deltaSharpnessNormalAngle = sharpnessNormalAngleRange[2]

                for deci in np.arange(startDeci, endDeci, deltaDeci) :
                    deci = float(deci)
                    for sharpnessAngle in np.arange(startSharpnessAngle, endSharpnessAngle, deltaSharpnessAngle) :
                        sharpnessAngle = float(sharpnessAngle)
                        for sharpnessNormalAngle in np.arange(startSharpnessNormalAngle, endSharpnessNormalAngle, deltaSharpnessNormalAngle) :
                            sharpnessNormalAngle = float(sharpnessNormalAngle)
                            listParam.append((niftiInfo, phaseInfo, deci, sharpnessAngle, sharpnessNormalAngle))
                super().process(self._task_sharp, listParam)
            else :
                relaxRange = reconParam.RelaxRange
                startRel = relaxRange[0]
                endRel = relaxRange[1]
                deltaRel = relaxRange[2]

                deciRange = reconParam.DeciRange
                startDeci = deciRange[0]
                endDeci = deciRange[1]
                deltaDeci = deciRange[2]

                for rel in np.arange(startRel, endRel, deltaRel) :
                    rel = float(rel)
                    for deci in np.arange(startDeci, endDeci, deltaDeci) :
                        deci = float(deci)
                        listParam.append((niftiInfo, phaseInfo, rel, deci))
                super().process(self._task, listParam)


    def _task(self, param : tuple) :
        niftiInfo = param[0]
        phaseInfo = param[1]

        reconType = niftiInfo.MaskInfo.ReconType
        reconParam = self.InputOptionInfo.find_recon_param(reconType)
        contour = reconParam.Contour
        algorithm = reconParam.Algorithm
        gaussian = reconParam.Gaussian
        resampling = reconParam.ResamplingFactor

        blenderName = niftiInfo.MaskInfo.BlenderName
        vertex = niftiInfo.Vertex

        origin = phaseInfo.Origin
        spacing = phaseInfo.Spacing
        direction = phaseInfo.Direction
        size = phaseInfo.Size
        phaseOffset = phaseInfo.Offset

        iter = reconParam.Iter
        rel = param[2]
        deci = param[3]

        if gaussian == 1 :
            gaussian = True
        else :
            gaussian = False
        
        relStr = f"{rel:.2f}"
        deciStr = f"{deci:.2f}"
        
        outputPath = os.path.join(self.OutputPath, blenderName)
        blenderName = f"{blenderName}__{str(iter).replace('.', '_')}xx{relStr.replace('.', '_')}xx{deciStr.replace('.', '_')}"
        outputNiftiFullPath = os.path.join(outputPath, f"{blenderName}.nii.gz")
        outputStlFullPath = os.path.join(outputPath, f"{blenderName}.stl")

        npImg = algImage.CAlgImage.create_np(size, np.uint8)

        algImage.CAlgImage.set_clear(npImg, 0)
        algImage.CAlgImage.set_value(npImg, vertex, 255)
        algImage.CAlgImage.save_nifti_from_np(outputNiftiFullPath, npImg, origin, spacing, direction, (2, 1, 0))
        print(f"saved nifti : {outputNiftiFullPath}")
        npImg = None

        matPhy = algVTK.CVTK.get_vtk_phy_matrix_with_offset(origin, spacing, direction, phaseOffset)
        vtkImg = algVTK.CVTK.image_data_load_from_nifti(outputNiftiFullPath)
        if algorithm == "Marching" :
            polyData = algVTK.CVTK.recon_marching_cube(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "MarchingPro" : 
            polyData = algVTK.CVTK.recon_marching_cube_pro(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "Flying" :
            polyData = algVTK.CVTK.recon_fly_edge3d(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        elif algorithm == "FlyingPro" :
            polyData = algVTK.CVTK.recon_fly_edge3d_pro(vtkImg, 1.0, 0, contour, iter, rel, deci, gaussian, matPhy, resampling)
        algVTK.CVTK.save_poly_data_stl(outputStlFullPath, polyData)
        print(f"saved stl : {outputStlFullPath}")
    def _task_sharp(self, param : tuple) :
        niftiInfo = param[0]
        phaseInfo = param[1]

        blenderName = niftiInfo.MaskInfo.BlenderName
        vertex = niftiInfo.Vertex

        origin = phaseInfo.Origin
        spacing = phaseInfo.Spacing
        direction = phaseInfo.Direction
        size = phaseInfo.Size
        phaseOffset = phaseInfo.Offset

        reconType = niftiInfo.MaskInfo.ReconType
        reconParam = self.InputOptionInfo.find_recon_param(reconType)
        contour = reconParam.Contour
        algorithm = reconParam.Algorithm
        iter = reconParam.Iter
        deci = param[2]
        sharpnessAngle = param[3]
        sharpnessNormalAngle = param[4]

        deciStr = f"{deci:.2f}"
        sharpnessAngleStr = f"{sharpnessAngle:.2f}"
        sharpnessNormalAngleStr = f"{sharpnessNormalAngle:.2f}"
        
        outputPath = os.path.join(self.OutputPath, blenderName)
        blenderName = f"{blenderName}__{str(iter).replace('.', '_')}xx{deciStr.replace('.', '_')}xx{sharpnessAngleStr.replace('.', '_')}xx{sharpnessNormalAngleStr.replace('.', '_')}"
        outputNiftiFullPath = os.path.join(outputPath, f"{blenderName}.nii.gz")
        outputStlFullPath = os.path.join(outputPath, f"{blenderName}.stl")

        npImg = algImage.CAlgImage.create_np(size, np.uint8)

        algImage.CAlgImage.set_clear(npImg, 0)
        algImage.CAlgImage.set_value(npImg, vertex, 255)
        algImage.CAlgImage.save_nifti_from_np(outputNiftiFullPath, npImg, origin, spacing, direction, (2, 1, 0))
        print(f"saved nifti : {outputNiftiFullPath}")
        npImg = None

        matPhy = algVTK.CVTK.get_vtk_phy_matrix_with_offset(origin, spacing, direction, phaseOffset)
        vtkImg = algVTK.CVTK.image_data_load_from_nifti(outputNiftiFullPath)
        if algorithm == "MarchingSharpness" :
            polyData = algVTK.CVTK.recon_marching_cube_sharpness(vtkImg, 0, contour, iter, deci, sharpnessAngle, sharpnessNormalAngle, matPhy)
        elif algorithm == "MarchingSharpnessPro" : 
            polyData = algVTK.CVTK.recon_marching_cube_sharpness_pro(vtkImg, 0, contour, iter, deci, sharpnessAngle, sharpnessNormalAngle, matPhy)
        algVTK.CVTK.save_poly_data_stl(outputStlFullPath, polyData)
        print(f"saved stl : {outputStlFullPath}")


    @property
    def InputOptionInfo(self) -> optionInfo.COptionInfo :
        return self.m_inputOptionInfo
    @InputOptionInfo.setter
    def InputOptionInfo(self, inputOptionInfo : optionInfo.COptionInfo) :
        self.m_inputOptionInfo = inputOptionInfo
    @property
    def InputNiftiContainer(self) -> niftiContainer.CNiftiContainer :
        return self.m_inputNiftiContainer
    @InputNiftiContainer.setter
    def InputNiftiContainer(self, inputNiftiContainer : niftiContainer.CNiftiContainer) :
        self.m_inputNiftiContainer = inputNiftiContainer
    @property
    def InputNiftiInfo(self) -> niftiContainer.CNiftiInfo :
        return self.m_inputNiftiInfo
    @InputNiftiInfo.setter
    def InputNiftiInfo(self, inputNiftiInfo : niftiContainer.CNiftiInfo) :
        self.m_inputNiftiInfo = inputNiftiInfo
    @property
    def OutputPath(self) -> str :
        return self.m_outputPath
    @OutputPath.setter
    def OutputPath(self, outputPath : str) :
        self.m_outputPath = outputPath


if __name__ == '__main__' :
    pass


# print ("ok ..")

