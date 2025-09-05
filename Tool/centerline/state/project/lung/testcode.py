import os
import sys

path1 = os.getcwd()
print(f"os.currdir() : {path1}")

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
print(f"fileAbsPath : {fileAbsPath}")

