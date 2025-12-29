import matplotlib.pyplot as plt
import SimpleITK as sitk
import cv2
import numpy as np
import os
import open3d as o3d
import open3d.core
import open3d.visualization

import scoUtil
import scoBuffer
import scoMath
import scoSkeleton
from abc import abstractmethod

import open3d as o3d
import open3d.visualization.gui as gui
import open3d.visualization.rendering as rendering

from skimage.morphology import skeletonize
# from skimage.morphology import skeletonize, skeletonize_3d
from skimage import data
from skimage.util import invert



'''
- blood vessel segment의 voxel 기준 precision 계산 
- blood vessel segment 기준 precision 계산 
- vessel과 organ을 나누어 관리한다. 
- 결과는 CScoBuffer3D로 나온다. 
'''

class CDataPatient : 
    eDataPatientType_None = 0
    eDataPatientType_Arterial = 1
    eDataPatientType_Vein = 2
    eDataPatientType_Organ = 3

    s_maskClearValue = -1


    def __init__(self) -> None :
        self.m_type = self.eDataPatientType_None
        self.m_patientPath = ""
        self.m_mask = None
    def clear(self) :
        self.m_type = self.eDataPatientType_None
        self.m_patientPath = ""
        if self.m_mask is not None :
            self.m_mask.clear()
            self.m_mask = None


    def add_nifti(self, fullPath : str, voxel : int) :
        sitkImg = scoUtil.CScoUtilSimpleITK.load_image(fullPath, None)
        npImg = scoUtil.CScoUtilSimpleITK.sitkImg_to_npImg(sitkImg, "uint8").transpose((2, 1, 0))

        if self.m_mask is None :
            self.m_mask = scoBuffer.CScoBuffer3D(npImg.shape, "int8")
            self.m_mask.all_set_voxel(self.s_maskClearValue)
        
        xInx, yInx, zInx = np.where(npImg > 0)
        self.m_mask.set_voxel((xInx, yInx, zInx), voxel)

        npImg = None
        sitkImg = None


    @property
    def Type(self) :
        return self.m_type
    @property
    def PatientPath(self) :
        return self.m_patientPath
    @property
    def Mask(self) -> scoBuffer.CScoBuffer3D :
        return self.m_mask


class CDataArterial(CDataPatient) :
    eEAPAorta = 0
    eEAPCT = 1
    eEAPCHA = 2
    eEAPSA = 3
    eEAPLGA = 4
    eEAPPHA = 5
    eEAPGDA = 6
    eEAPRGA = 7
    eEAPLGEA = 8
    eEAPRHA = 9
    eEAPLHA = 10
    eEAPASPDA = 11
    eEAPRGEA = 12
    eEAPIPA = 13
    eEAPSGA = 14
    eEAPExtra = 15
    eEAPVesselTotal = 16

    s_mainArteryName = "Main_Artery.nii.gz"
    s_extraArteryName = "Extra_Artery.nii.gz"
    s_wholeArteryName = "Whole_Artery.nii.gz"
    s_rootArteryName = "Aorta.nii.gz"

    # key : enumIndex
    # value : list
    #           0 : nifti fileName
    #           1 : vessel mask
    #           2 : vessel name
    #           3 : vessel branch group name
    #           4 : vessel end point name
    #           5 : vessel max radius 
    s_dicArterial = {
        eEAPAorta : ["Aorta.nii.gz", eEAPAorta, "Aorta", "AortaBranchGroup", "AortaEndPoint", -1],
        eEAPCT : ["CT.nii.gz", eEAPCT, "CT", "CTBranchGroup", "CTEndPoint", 3.01],
        eEAPCHA : ["CHA.nii.gz", eEAPCHA, "CHA", "CHABranchGroup", "CHAEndPoint", -1],
        eEAPSA : ["SA.nii.gz", eEAPSA, "SA", "SABranchGroup", "SAEndPoint", -1],
        eEAPLGA : ["LGA.nii.gz", eEAPLGA, "LGA", "LGABranchGroup", "LGAEndPoint", -1],
        eEAPRGA : ["RGA.nii.gz", eEAPRGA, "RGA", "RGABranchGroup", "RGAEndPoint", -1],
        eEAPPHA : ["PHA.nii.gz", eEAPPHA, "PHA", "PHABranchGroup", "PHAEndPoint", -1],
        eEAPGDA : ["GDA.nii.gz", eEAPGDA, "GDA", "GDABranchGroup", "GDAEndPoint", -1],
        eEAPLGEA : ["LGEA.nii.gz", eEAPLGEA, "LGEA", "LGEABranchGroup", "LGEAEndPoint", -1],
        eEAPRHA : ["RHA.nii.gz", eEAPRHA, "RHA", "RHABranchGroup", "RHAEndPoint", -1],
        eEAPLHA : ["LHA.nii.gz", eEAPLHA, "LHA", "LHABranchGroup", "LHAEndPoint", -1],
        eEAPASPDA : ["ASPDA.nii.gz", eEAPASPDA, "ASPDA", "ASPDABranchGroup", "ASPDAEndPoint", -1],
        eEAPRGEA : ["RGEA.nii.gz", eEAPRGEA, "RGEA", "RGEABranchGroup", "RGEAEndPoint", -1],
        eEAPIPA : ["IPA.nii.gz", eEAPIPA, "IPA", "IPABranchGroup", "IPAEndPoint", -1],
        eEAPSGA : ["SGA.nii.gz", eEAPSGA, "SGA", "SGABranchGroup", "SGAEndPoint", -1],
        eEAPExtra : ["Extra_Artery.nii.gz", eEAPExtra, "ExtraArtery", "ExtraArteryBranchGroup", "ExtraArteryEndPoint", -1],
    }


    @staticmethod
    def get_arterial_file_name(eArterial : int) :
        return CDataArterial.s_dicArterial[eArterial][0]
    @staticmethod
    def get_arterial_mask(eArterial : int) :
        return CDataArterial.s_dicArterial[eArterial][1]
    @staticmethod
    def get_arterial_name(eArterial : int) :
        return CDataArterial.s_dicArterial[eArterial][2]
    @staticmethod
    def get_arterial_branch_group_name(eArterial : int) :
        return CDataArterial.s_dicArterial[eArterial][3]
    @staticmethod
    def get_arterial_end_point_name(eArterial : int) :
        return CDataArterial.s_dicArterial[eArterial][4]
    @staticmethod
    def get_arterial_max_radius(eArterial : int) :
        return CDataArterial.s_dicArterial[eArterial][5]
    @staticmethod
    def find_arterial_id(arterialName : str) :
        for key, value in CDataArterial.s_dicArterial.items() :
            if arterialName == CDataArterial.get_arterial_name(key) :
                return key
        return -1


    def __init__(self) -> None:
        super().__init__()
        # input your code
        self.m_type = self.eDataPatientType_Arterial
    def load(self, patientPath : str) :
        self.m_patientPath = patientPath

        # loading arterial vessel
        for eEAP in range(0, self.eEAPVesselTotal) :
            fileName = self.get_arterial_file_name(eEAP)
            fullPath = os.path.join(self.m_patientPath, fileName)

            if os.path.exists(fullPath) == True :
                self.add_nifti(fullPath, eEAP)
                print(f"attached vessel nifti : {fileName}")
            else :
                print(f"not found {fullPath}")
    def clear(self) :
        # input your code

        super().clear()


class CDataVein(CDataPatient) :
    ePPPV = 0
    ePPSV = 1
    ePPSMV = 2
    ePPLGV = 3
    ePPLGEV = 4
    ePPGCT = 5
    ePPASPDV = 6
    ePPARCV = 7
    ePPRGEV = 8
    ePPIPV = 9
    ePPExtra = 10
    ePPTotal = 11

    s_mainVeinName = "Main_Vein.nii.gz"
    s_extraVeinName = "Extra_Vein.nii.gz"
    s_wholeVeinName = "Whole_Vein.nii.gz"
    s_rootVeinName = "PV.nii.gz"

    # key : enumIndex
    # value : list
    #           0 : nifti fileName
    #           1 : vessel mask  
    #           2 : vessel name
    #           3 : vessel branch group name
    #           4 : vessel end point name
    #           5 : vessel max radius 
    s_dicVein = {
        ePPPV : ["PV.nii.gz", ePPPV, "PV", "PVBranchGroup", "PVEndPoint", -1],
        ePPSV : ["SV.nii.gz", ePPSV, "SV", "SVBranchGroup", "SVEndPoint", -1],
        ePPSMV : ["SMV.nii.gz", ePPSMV, "SMV", "SMVBranchGroup", "SMVEndPoint", -1],
        ePPLGV : ["LGV.nii.gz", ePPLGV, "LGV", "LGVBranchGroup", "LGVEndPoint", -1],
        ePPLGEV : ["LGEV.nii.gz", ePPLGEV, "LGEV", "LGEVBranchGroup", "LGEVEndPoint", -1],
        ePPGCT : ["GCT.nii.gz", ePPGCT, "GCT", "GCTBranchGroup", "GCTEndPoint", -1],
        ePPASPDV : ["ASPDV.nii.gz", ePPASPDV, "ASPDV", "ASPDVBranchGroup", "ASPDVEndPoint", -1],
        ePPARCV : ["ARCV.nii.gz", ePPARCV, "ARCV", "ARCVBranchGroup", "ARCVEndPoint", -1],
        ePPRGEV : ["RGEV.nii.gz", ePPRGEV, "RGEV", "RGEVBranchGroup", "RGEVEndPoint", -1],
        ePPIPV : ["IPV.nii.gz", ePPIPV, "IPV", "IPVBranchGroup", "IPVEndPoint", -1],
        ePPExtra : ["Extra_Vein.nii.gz", ePPExtra, "ExtraVein", "ExtraVeinBranchGroup", "ExtraVeinEndPoint", -1],
    }


    @staticmethod
    def get_vein_file_name(eVein : int) :
        return CDataVein.s_dicVein[eVein][0]
    @staticmethod
    def get_vein_mask(eVein : int) :
        return CDataVein.s_dicVein[eVein][1]
    @staticmethod
    def get_vein_name(eVein : int) :
        return CDataVein.s_dicVein[eVein][2]
    @staticmethod
    def get_vein_branch_group_name(eVein : int) :
        return CDataVein.s_dicVein[eVein][3]
    @staticmethod
    def get_vein_end_point_name(eVein : int) :
        return CDataVein.s_dicVein[eVein][4]
    @staticmethod
    def get_vein_max_radius(eVein : int) :
        return CDataVein.s_dicVein[eVein][5]
    @staticmethod
    def find_vein_id(veinName : str) :
        for key, value in CDataVein.s_dicVein.items() :
            if veinName == CDataVein.get_vein_name(key) :
                return key
        return -1


    def __init__(self) -> None:
        super().__init__()
        # input your code
        self.m_type = self.eDataPatientType_Vein
    def load(self, patientPath : str) :
        self.m_patientPath = patientPath

        # loading vein vessel
        for ePP in range(0, self.ePPTotal) :
            fileName = self.get_vein_file_name(ePP)
            fullPath = os.path.join(self.m_patientPath, fileName)

            if os.path.exists(fullPath) == True :
                self.add_nifti(fullPath, ePP)
                print(f"attached vessel nifti : {fileName}")
            else :
                print(f"not found {fullPath}")
    def clear(self) :
        # input your code

        super().clear()


class CDataOrgan(CDataPatient) :
    eOrganLiver = 0
    eOrganStomach = 1
    eOrganSpleen = 2
    eOrganPancreas = 3
    eOrganGallBladder = 4
    eOrganTotal = 5

    # key : enumIndex
    # value : list
    #           0 : nifti fileName
    #           1 : organ mask
    #           2 : organ name
    s_dicOrgan = {
        eOrganLiver : ["Liver.nii.gz", eOrganLiver, "Liver"],
        eOrganStomach : ["Stomach.nii.gz", eOrganStomach, "Stomach"],
        eOrganSpleen : ["Spleen.nii.gz", eOrganSpleen, "Spleen"],
        eOrganPancreas : ["Pancreas.nii.gz", eOrganPancreas, "Pancreas"],
        eOrganGallBladder : ["GallBladder.nii.gz", eOrganGallBladder, "GallBladder"],
    }


    @staticmethod
    def get_organ_file_name(eOrgan : int) :
        return CDataOrgan.s_dicOrgan[eOrgan][0]
    @staticmethod
    def get_organ_mask(eOrgan : int) :
        return CDataOrgan.s_dicOrgan[eOrgan][1]
    @staticmethod
    def get_organ_name(eOrgan : int) :
        return CDataOrgan.s_dicOrgan[eOrgan][2]
    @staticmethod
    def find_organ_id(organName : str) :
        for key, value in CDataOrgan.s_dicOrgan.items() :
            if organName == CDataOrgan.get_organ_name(key) :
                return key
        return -1


    def __init__(self) -> None:
        super().__init__()
        # input your code
        self.m_type = self.eDataPatientType_Organ
    def load(self, patientPath : str) :
        self.m_patientPath = patientPath

        # loading organ vessel
        for eOrgan in range(0, self.eOrganTotal) :
            fileName = self.get_organ_file_name(eOrgan)
            fullPath = os.path.join(self.m_patientPath, fileName)

            if os.path.exists(fullPath) == True :
                self.add_nifti(fullPath, eOrgan)
                print(f"attached organ nifti : {fileName}")
            else :
                print(f"not found {fullPath}")
    def clear(self) :
        # input your code

        super().clear()


class CPatient :
    @staticmethod
    def find_mask_id(dataPatientType : int, name : str) :
        maskID = -1
        if dataPatientType == CDataPatient.eDataPatientType_Arterial :
            maskID = CDataArterial.find_arterial_id(name)
        elif dataPatientType == CDataPatient.eDataPatientType_Vein :
            maskID = CDataVein.find_vein_id(name)
        elif dataPatientType == CDataPatient.eDataPatientType_Organ :
            maskID = CDataOrgan.find_organ_id(name)
        return maskID
    @staticmethod
    def get_labeling_name(dataPatientType : int, maskInx : int) :
        if dataPatientType == CDataPatient.eDataPatientType_Arterial :
            return CDataArterial.get_arterial_name(maskInx)
        elif dataPatientType == CDataPatient.eDataPatientType_Vein :
            return CDataVein.get_vein_name(maskInx)
        elif dataPatientType == CDataPatient.eDataPatientType_Organ :
            return CDataOrgan.get_organ_name(maskInx)
        else :
            return ""
    @staticmethod
    def get_labeling_cnt(dataPatientType : int) :
        if dataPatientType == CDataPatient.eDataPatientType_Arterial :
            return CDataArterial.eEAPVesselTotal
        elif dataPatientType == CDataPatient.eDataPatientType_Vein :
            return CDataVein.ePPTotal
        elif dataPatientType == CDataPatient.eDataPatientType_Organ :
            return CDataOrgan.eOrganTotal
        else :
            return 0
    @staticmethod
    def get_file_name(dataPatientType : int, maskID : int) -> str:
        if dataPatientType == CDataPatient.eDataPatientType_Arterial :
            return CDataArterial.get_arterial_file_name(maskID)
        elif dataPatientType == CDataPatient.eDataPatientType_Vein :
            return CDataVein.get_vein_file_name(maskID)
        elif dataPatientType == CDataPatient.eDataPatientType_Organ :
            return CDataOrgan.get_organ_file_name(maskID)
        else :
            return ""
    
    
    
    def __init__(self) -> None :
        self.m_arterial = CDataArterial()
        self.m_vein = CDataVein()
        self.m_organ = CDataOrgan()


    def load_arterial(self, arterialPath : str) :
        self.m_arterial.clear()
        self.m_arterial.load(arterialPath)
    def load_vein(self, veinPath : str) :
        self.m_vein.clear()
        self.m_vein.load(veinPath)
    def load_organ(self, organPath : str) :
        self.m_organ.clear()
        self.m_organ.load(organPath)
    def clear(self) :
        self.m_arterial.clear()
        self.m_vein.clear()
        self.m_organ.clear()


    def get_mask(self, dataPatientType : int) -> scoBuffer.CScoBuffer3D :
        if dataPatientType == CDataPatient.eDataPatientType_Arterial :
            return self.ArterialMask
        elif dataPatientType == CDataPatient.eDataPatientType_Vein :
            return self.VeinMask
        elif dataPatientType == CDataPatient.eDataPatientType_Organ :
            return self.OrganMask
        else :
            return None


    @property
    def ValidArterial(self) :
        return self.m_arterial.Mask is not None
    @property
    def ValidVein(self) :
        return self.m_vein.Mask is not None
    @property
    def ValidOrgan(self) :
        return self.m_organ.Mask is not None
    @property
    def Artial(self) -> CDataArterial :
        return self.m_arterial
    @property
    def Vein(self) -> CDataVein :
        return self.m_vein
    @property
    def Organ(self) -> CDataOrgan :
        return self.m_organ
    @property
    def ArterialMask(self) -> scoBuffer.CScoBuffer3D :
        return self.m_arterial.Mask
    @property
    def VeinMask(self) -> scoBuffer.CScoBuffer3D :
        return self.m_vein.Mask
    @property
    def OrganMask(self) -> scoBuffer.CScoBuffer3D :
        return self.m_organ.Mask







