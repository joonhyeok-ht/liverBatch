import sys
import os
import numpy as np
import shutil
import multiprocessing

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAlgorithmPath = os.path.join(fileAbsPath, "Algorithm") 
fileAlgUtilPath = os.path.join(fileAbsPath, "AlgUtil")
fileBlockPath = os.path.join(fileAbsPath, "Block")
sys.path.append(fileAbsPath)
sys.path.append(fileAlgorithmPath)
sys.path.append(fileAlgUtilPath)
sys.path.append(fileBlockPath)


import Block.centerline as centerline



def find_param(args : list, paramName : str) :
    try:
        inx = args.index(paramName)
        return args[inx + 1]
    except ValueError:
        print(f"not found param : {paramName}")
    return None
def exist_param(args : list, paramName : str) -> bool :
    try:
        inx = args.index(paramName)
        return True
    except ValueError:
        print(f"not found param : {paramName}")
    return False


import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Process input file and index.")
    parser.add_argument('--file', type=str, help='The file to process')
    parser.add_argument('--index', type=int, help='The index value')
    parser.add_argument('--vtp', type=str, help='Targetted vtp filename (except ext)')
    parser.add_argument('--cellID', type=int, help='start cellID')
    parser.add_argument('--en', type=int, help='0 : default 1 : enhanced')
    return parser.parse_args()


if __name__ == '__main__' :
    args = parse_args()

    if args.index is None :
        multiprocessing.freeze_support()
        # app = CCommonPipelineCL()
        # app.init()
        # app.process()
        # app.clear()
    else :
        print(f"파일 : {args.file}")
        print(f"인덱스 : {args.index}")
        print(f"vtp : {args.vtp}")
        print(f"cellID : {args.cellID} {type(args.cellID)}")
        print(f"en : {args.en} {type(args.en)}")

        if args.en == 1 :
            block = centerline.CCenterlineEnhanced()
            block.InputFile = args.file
            block.InputIndex = args.index
            block.InputVTPName = args.vtp
            block.InputCellID = args.cellID
            block.process()
        else :
            block = centerline.CCenterlineNormal()
            block.InputFile = args.file
            block.InputIndex = args.index
            block.InputVTPName = args.vtp
            block.InputCellID = args.cellID
            block.process()


print ("ok ..")

