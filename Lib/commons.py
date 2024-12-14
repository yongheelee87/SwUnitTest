import os
import csv
import numpy as np
from openpyxl.styles import PatternFill
from copy import copy

DEFAULT_DIR = 'C:/git/DevEnv/webUnitTest'  # default 폴더 저장
SETTING_YAML = f'{DEFAULT_DIR}/data/setting.yaml'
LAST_SETTING_YAML = f'{DEFAULT_DIR}/data/old/last_setting.yaml'
UPLOAD_PATH = f'{DEFAULT_DIR}/data/upload'
STUB_PATH = f'{DEFAULT_DIR}/data/stub'  # stub 코드 폴더
TEST_CASE_FILE = f'{DEFAULT_DIR}/data/SW_TestCase.xlsx'  # 테스트케이스
LAST_TEST_CASE_FILE = f'{DEFAULT_DIR}/data/old/Last_SW_TestCase.xlsx'
RESULT_PATH = f'{DEFAULT_DIR}/data/result'
DOWNLOAD_ZIP = f'{DEFAULT_DIR}/data/download.zip'


def git_checkout(project_dir: str, branch: str):
    """
    :param project_dir: repo location to be installed via git
    :param branch: repo branch
    """
    os.chdir(project_dir)  # 프로젝트 있는 폴더로 변경
    os.system(f"git checkout {branch}")
    os.chdir(DEFAULT_DIR)  # default 폴더 복귀


def copy_style(cell, new_cell):
    if cell.has_style:
        new_cell.font = copy(cell.font)
        new_cell.boarder = copy(cell.boarder)
        new_cell.fill = copy(cell.fill)
        new_cell.number_format = copy(cell.number_format)
        new_cell.protection = copy(cell.protection)
        new_cell.alignment = copy(cell.alignment)


def add_col_data(worksheet, index, title, data, res: bool = False):
    worksheet.insert_cols(index)
    worksheet.cell(row=1, column=index).value = title
    copy_style(worksheet.cell(row=1, column=3), worksheet.cell(row=1, column=index))

    for i, val in enumerate(data):
        worksheet.cell(row=1, column=index).value = val
        copy_style(worksheet.cell(row=i+2, column=3), worksheet.cell(row=i+2, column=index))
        if res is True:
            if val == 'Pass':
                worksheet.cell(row=i+2, column=index).fill = PatternFill(start_color='D3E6D6', end_color='D3E6D6', fill_type='solid')
            elif val == 'Fail':
                worksheet.cell(row=i + 2, column=index).fill = PatternFill(start_color='E86A75', end_color='E86A75', fill_type='solid')


def colorize(val: str):
    """
    :param val: result Pass, Fail, Skip..
    :return: color map value
    """
    color = None
    if val == "Pass":
        color = f'background-color: #5CE65C; color:black'
    elif val == "Fail":
        color = f'background-color: #5CE65C; color:black'
    return color


def get_2d_list(divider: int, path: str) -> np.array:
    """
    :param divider: the number of second dimension
    :param path: file path
    :return: np array 2 dimension of file path list
    """
    lst_f = [f for f in os.listdir(path)]
    row_num, dum_num = divmod(len(lst_f), divider)
    if dum_num == 0:
        dummy = []
    else:
        dummy = ['nan' for _ in range(divider - dum_num)]
        row_num += 1
    return np.array(lst_f + dummy).reshape(row_num, divider)


def load_csv_list(file_path: str) -> list:
    """
    :param file_path: file path to load
    :return: csv list
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            csv_lst = list(reader)
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='cp949') as f:
            reader = csv.reader(f)
            csv_lst = list(reader)
    return csv_lst
