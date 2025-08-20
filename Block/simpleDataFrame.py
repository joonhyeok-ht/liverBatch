import sys
import os
import numpy as np

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)

import AlgUtil.algLinearMath as algLinearMath
# import example_vtk.frameworkVTK as frameworkVTK


import json
import pandas as pd


'''
CSimpleDataFrame <- CSimpleDataFrameHtml <- CSimpleDataFrameVolume
'''

class CSimpleDataFrame :
    def __init__(self, columnCount : int) -> None:
        self.m_listColumn = ["" for i in range(0, columnCount)]
        self.m_listIndex = []
        self.m_listRow = []
        self.m_df = None
    def clear(self) :
        self.m_listColumn.clear()
        self.m_listIndex.clear()
        self.m_listRow.clear()
        self.m_df = None
    def process(self) :
        self.m_df = pd.DataFrame(self.m_listRow, columns=self.m_listColumn, index=self.m_listIndex)


    def save_csv(self, csvPath : str) :
        self.m_df.to_csv(csvPath)

    def set_column(self, columnInx : int, columnName) :
        self.m_listColumn[columnInx] = columnName
    def get_column(self, columnInx : int) :
        return self.m_listColumn[columnInx]
    def get_column_count(self) :
        return len(self.m_listColumn)
    def add_index_name(self, indexName) -> int:
        self.m_listIndex.append(indexName)
        self.m_listRow.append(["" for i in range(0, self.get_column_count())])
        return len(self.m_listIndex) - 1
    def get_index_name(self, index : int) :
        return self.m_listIndex[index]
    def set_index_name(self, index : int, indexName) :
        self.m_listIndex[index] = indexName
    def set_row(self, index, rowInx, value) :
        self.m_listRow[index][rowInx] = value
    def set_rows(self, index, listValue : list) :
        self.m_listRow[index] = listValue
    def get_row(self, index, rowInx) :
        return self.m_listRow[index][rowInx]
    def get_rows(self, index) :
        return self.m_listRow[index]


class CSimpleDataFrameHtml(CSimpleDataFrame) :
    def __init__(self, columnCount: int) -> None:
        super().__init__(columnCount)
        self.m_htmlCode = ""
    def clear(self) :
        # input your code
        self.m_htmlCode = ""
        super().clear()
    def process(self) :
        super().process()
        # input your code


    def save_html(self, htmlPath : str) :
        with open(htmlPath, 'w') as f:
            f.write(self.m_htmlCode)
    def add_percentage_diff(self, colName : str, targetColName : str, srcColName : str) :
        def percentage_diff(row) :
            if row[targetColName] != 0.0 :
                return ((row[srcColName] - row[targetColName]) / row[targetColName]) * 100.0
            else :
                return 0.0
        self.m_df[colName] = self.m_df.apply(lambda row: percentage_diff(row), axis=1)
    

    def _css_col_color(self, style, colName : str, bgColor='red', fontColor='white') :
        def highlight(s):
            return [f'background-color: {bgColor}; color: {fontColor}' if s.name == colName else '' for _ in s]
        return style.apply(highlight, axis=0)
    def _css_row_color(self, style, rowName : str, bgColor='red', fontColor='white') :
        def highlight(s):
            return [f'background-color: {bgColor}; color: {fontColor}' if s.name == rowName else '' for _ in s]
        return style.apply(highlight, axis=1)
    def _css_row_col_color(self, style, rowName : str, colName : str, bgColor='red', fontColor='white') :
        def hightlight(data) :
            tmpStyle = pd.DataFrame('', index=data.index, columns=data.columns)
            if rowName in data.index and colName in data.columns :
                tmpStyle.loc[rowName, colName] = f'background-color: {bgColor}; color: {fontColor}'
            return tmpStyle
        return style.apply(lambda x: hightlight(self.m_df), axis=None)
    def _custom_css_table(self, width='100%', borderSize=1, color='black') -> str :
        customCSS = f"""
        <style>
        table {{
            border-collapse: collapse;
            width: {width};
        }}
        table, th, td {{
            border: {borderSize}px solid {color};
        }}
        </style>
        """
        return customCSS


class CSimpleDataFrameVolume(CSimpleDataFrameHtml) :
    def __init__(self, columnCount: int) -> None:
        super().__init__(columnCount)
        # input your code
    def clear(self) :
        # input your code
        super().clear()
    def process(self) :
        super().process()
        #input your code
        # 각 rows의 average
        # self.m_df['Avr'] = self.m_df.mean(axis=1)
        # 각 columns의 sum
        # columnSums = self.m_df.sum(axis=0)
        # self.m_df.loc['Sum'] = columnSums
        # self.add_percentage_diff("diff(%)", "TargetMaskCC", "SrcMaskCC")
        # condition = self.m_df["diff(%)"] > 0.0
        # rowNames = self.m_df[condition].index

        # style = self.m_df.style
        # colName = "Diff(%)"
        # for rowName in rowNames :
        #     style = self._css_row_col_color(style, rowName, colName, 'red', 'white')

        # html css 
        # style = self._css_col_color(self.m_df.style, 'A', 'blue', 'yellow')
        # style = self._css_row_color(style, 'Sum', 'red', 'white')
        # style = self._css_row_col_color(style, 'Row2', 'B', 'black', 'white')
        customCSS = self._custom_css_table("100%", 1, "black")

        html = self.m_df.style.to_html()
        self.m_htmlCode = customCSS + html



if __name__ == '__main__' :
    pass


# print ("ok ..")

