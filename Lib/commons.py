import os
import csv
import numpy as np
from typing import List, Dict, Any, Union, Tuple, Optional
from openpyxl.styles import PatternFill
from copy import copy
from pathlib import Path

# Use Path for better cross-platform compatibility
DEFAULT_DIR = Path('C:/git/DevEnv/webUnitTest')
SETTING_YAML = DEFAULT_DIR / 'data/setting.yaml'
LAST_SETTING_YAML = DEFAULT_DIR / 'data/old/last_setting.yaml'
UPLOAD_PATH = DEFAULT_DIR / 'data/upload'
STUB_PATH = DEFAULT_DIR / 'data/stub'
TEST_CASE_FILE = DEFAULT_DIR / 'data/SW_TestCase.xlsx'
LAST_TEST_CASE_FILE = DEFAULT_DIR / 'data/old/Last_SW_TestCase.xlsx'
RESULT_PATH = DEFAULT_DIR / 'data/result'
DOWNLOAD_ZIP = DEFAULT_DIR / 'data/download.zip'

# Ensure directories exist
for path in [UPLOAD_PATH, STUB_PATH, RESULT_PATH, DEFAULT_DIR / 'data/old']:
    path.mkdir(parents=True, exist_ok=True)


def git_checkout(project_dir: str, branch: str) -> None:
    """
    Switch to the specified git branch in the project directory

    Args:
        project_dir: repo location to be installed via git
        branch: repo branch
    """
    current_dir = os.getcwd()
    try:
        os.chdir(project_dir)
        os.system(f"git checkout {branch}")
    finally:
        os.chdir(current_dir)  # Always return to original directory


def copy_style(cell: Any, new_cell: Any) -> None:
    """
    Copy cell styles from one cell to another

    Args:
        cell: Source cell to copy style from
        new_cell: Target cell to copy style to
    """
    if cell.has_style:
        new_cell.font = copy(cell.font)
        new_cell.border = copy(cell.border)  # Fixed typo: boarder -> border
        new_cell.fill = copy(cell.fill)
        new_cell.number_format = copy(cell.number_format)
        new_cell.protection = copy(cell.protection)
        new_cell.alignment = copy(cell.alignment)


def add_col_data(worksheet: Any, index: int, title: str, data: List[str], res: bool = False) -> None:
    """
    Add a column of data to a worksheet

    Args:
        worksheet: The worksheet to modify
        index: Column index to insert at
        title: Column title
        data: List of data values to insert
        res: Whether this is a result column (for styling)
    """
    worksheet.insert_cols(index)
    worksheet.cell(row=1, column=index).value = title
    copy_style(worksheet.cell(row=1, column=3), worksheet.cell(row=1, column=index))

    for i, val in enumerate(data):
        worksheet.cell(row=i + 2, column=index).value = val
        copy_style(worksheet.cell(row=i + 2, column=3), worksheet.cell(row=i + 2, column=index))
        if res:
            color = None
            if val == 'Pass':
                color = 'D3E6D6'
            elif val == 'Fail':
                color = 'E86A75'

            if color:
                worksheet.cell(row=i + 2, column=index).fill = PatternFill(
                    start_color=color, end_color=color, fill_type='solid'
                )


def colorize(val: str) -> Optional[str]:
    """
    Return CSS style for coloring result cells

    Args:
        val: result Pass, Fail, Skip..
    Returns:
        CSS color string or None
    """
    if val == "Pass":
        return 'background-color: #5CE65C; color:black'
    elif val == "Fail":
        return 'background-color: #FF6666; color:black'  # Fixed: Used consistent red color for "Fail"
    return None


def get_2d_list(divider: int, path: str) -> np.ndarray:
    """
    Organize a list of files into a 2D grid

    Args:
        divider: the number of second dimension
        path: file path
    Returns:
        np array 2 dimension of file path list
    """
    path = Path(path)
    lst_f = [f for f in os.listdir(path) if f.endswith('.csv')]  # Only consider CSV files

    row_num, remainder = divmod(len(lst_f), divider)

    if remainder == 0:
        dummy = []
    else:
        dummy = ['nan' for _ in range(divider - remainder)]
        row_num += 1

    return np.array(lst_f + dummy).reshape(row_num, divider)


def load_csv_list(file_path: Union[str, Path]) -> List[List[str]]:
    """
    Load data from a CSV file with automatic encoding detection

    Args:
        file_path: file path to load
    Returns:
        CSV data as a list of lists
    """
    file_path = Path(file_path)
    encodings = ['utf-8', 'cp949', 'cp1252']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.reader(f)
                return list(reader)
        except UnicodeDecodeError:
            continue

    # If all encodings fail, try binary mode as last resort
    with open(file_path, 'rb') as f:
        content = f.read()
        try:
            decoded = content.decode('utf-8', errors='replace')
            reader = csv.reader(decoded.splitlines())
            return list(reader)
        except Exception as e:
            raise IOError(f"Failed to read CSV file {file_path}: {str(e)}")