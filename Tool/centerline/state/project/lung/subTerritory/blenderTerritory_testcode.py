'''
'''
# import bpy

import os, sys
import json
import re
import shutil
import math
import time

tmpPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(tmpPath)

# import blenderScriptCleanUpMesh as clmsh

# def get_진짜이름_from_꽃표포함이름() :
def select_rightname_from_option() :
    # (in) 폴더내stl들
    # (in) option의 목록들 (*포함)
    pass
    
# def import_진짜이름(블랜더name)() :
#     pass


def extract_numbers(label_txt) : #sally  오류가 있음...
    return re.sub(r'/D', '', label_txt)
def extract_numbers2(string):
    # 숫자인 문자만 필터링하여 리스트로 만들고, 이를 합침
    return ''.join(char for char in string if char.isdigit())
def find_lowercase(string):
    # 소문자가 포함되었는지 여부와 소문자 리스트를 반환
    lowercase_letters = [char for char in string if char.islower()]
    contains_lowercase = bool(lowercase_letters)
    if contains_lowercase :
        return f"_{lowercase_letters[0]}"
    else :
        return ""
    # return contains_lowercase, lowercase_letters
def find_lowercase_with_underbar(string) -> str:
    # 소문자가 포함되었으면 첫 소문자를 언더바와 함께 리턴
    lowercase_letters = [char for char in string if char.islower()]
    contains_lowercase = bool(lowercase_letters)
    if contains_lowercase :
        return f"_{lowercase_letters[0]}"
    else :
        return ""
def rename_tp_to_lung() :
    input_str = "D:/jys/git_Solution/Solution/UnitTestPrev/CommonPipeline_10_0319_lung/lung_patient/huid_103/TerriInfo/out"

    stl_folder = input_str
    stl_name_list = os.listdir(stl_folder)
    print(f"stl_name_list = {stl_name_list}")

    #save 폴더에서 TP 들어간 stl만 가져오기
    stl_name_list = []
    for file_name in os.listdir(stl_folder):
        if "TP_" in file_name and file_name.endswith('.stl'):
            stl_name_list.append(file_name)
            name, _ = os.path.splitext(file_name) # name without extension
            
            digit = extract_numbers2(name)
            str1 = f"Lung_{name[3]}S{digit}{find_lowercase(name)}_{name[4]}_{name[3]}"
            print(f"in : {name} -> {str1}")

def rename_tp_to_vessel() :
    dicInitial = {"A":"Artery", "B":"Bronchus", "V":"Vein"}
    # input_str = "D:/jys/git_Solution/Solution/UnitTestPrev/CommonPipeline_10_0319_lung/lung_patient/huid_103/TerriInfo/out"
    # input_str = r"D:\jys\git_Solution\Solution\UnitTestPrev\CommonPipeline_10_0429_lung\myOutput\01011urk_39_new\vesselOut\Artery"
    input_str = r"D:\jys\git_Solution\Solution\UnitTestPrev\CommonPipeline_10_0429_lung\myOutput\01011urk_39_new\vesselOut\Bronchus"
    stl_folder = input_str
    stl_name_list = os.listdir(stl_folder)
    print(f"stl_name_list = {stl_name_list}")

    #save 폴더에서 TP 들어간 stl만 가져오기
    currWholeVesselName = ""
    directionName = ""
    for file_name in os.listdir(stl_folder):
        name, _ = os.path.splitext(file_name) # name without extension
        new_name = ""
        src = ""
        dst = ""
        do_flag = False
        if "TP_" in file_name and file_name.endswith('.stl'):            
            currWholeVesselName = dicInitial[name[4]]
            directionName = name[3]
            digit = extract_numbers2(name)
            new_name = f"{currWholeVesselName}_{directionName}{name[4]}{digit}{find_lowercase_with_underbar(name)}_{directionName}.stl"
            do_flag = True
        elif "Whole" in file_name :
            new_name = f"{currWholeVesselName}_{directionName}.stl"
            do_flag = True

        if do_flag :
            print(f"in : {name} -> {new_name}")
            src = os.path.join(stl_folder, file_name)
            dst = os.path.join(stl_folder, new_name)
            if os.path.exists(dst) :
                os.remove(dst)
            os.rename(src, dst)
            
# rename_tp_to_lung()
rename_tp_to_vessel()
