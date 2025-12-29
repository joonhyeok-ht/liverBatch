import sys
import os
import numpy as np

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)



class CObjInfo : 
    def __init__(self) :
        self.m_vertex = None
        self.m_faces = []
        self.m_otherLines = []
    def clear(self) :
        self.m_vertex = None
        self.m_faces = []
        self.m_otherLines = []

    def load(self, objFullPath : str) -> bool :
        vertices = []
        faces = []

        if os.path.exists(objFullPath) == False :
            return False

        with open(objFullPath, 'r') as f :
            for line in f :
                if line.startswith('v ') :  # vertex 라인만 읽기
                    parts = line.strip().split()
                    coord = list(map(float, parts[1:4]))
                    vertices.append(coord)
                else :
                    if line.startswith('f ') : # face 별도 추출 
                        parts = line.strip().split()[1 : ]
                        face = [int(p.split('/')[0]) - 1 for p in parts]
                        faces.append(face)

                    self.m_otherLines.append(line)
        self.m_vertex = np.array(vertices)
        self.m_face = np.array(faces)
        return True
    def save(self, objFullPath : str) -> bool :
        with open(objFullPath, 'w') as f :
            # vertex 먼저 저장
            for v in self.m_vertex :
                f.write(f'v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n')

            # 그 다음에 나머지 라인 저장 (face, vt, vn 등)
            for line in self.m_otherLines :
                if not (line.startswith('v ') or line.startswith('mtllib ') or line.startswith('o ')) :
                    f.write(line)
        return True
    

    @property
    def Vertex(self) -> np.ndarray :
        return self.m_vertex
    @Vertex.setter
    def Vertex(self, vertex : np.ndarray) :
        self.m_vertex = vertex
    @property
    def Face(self) -> np.ndarray :
        return self.m_face


if __name__ == '__main__' :
    pass


# print ("ok ..")

