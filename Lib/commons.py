import os
import csv
import re
import shutil

import numpy as np
import pandas as pd
import xlwings as xw
from openpyxl.styles import PatternFill
from copy import copy
from pathlib import Path
from typing import List, Optional, Any, Union

# Use Path for better cross-platform compatibility
DEFAULT_DIR = Path('C:/git/SwUnitTest')  # default 폴더 저장
SETTING_YAML = DEFAULT_DIR / 'data/setting.yaml'
LAST_SETTING_YAML = DEFAULT_DIR / 'data/old/last_setting.yaml'
UPLOAD_PATH = DEFAULT_DIR / 'data/upload'
STUB_PATH = DEFAULT_DIR / 'data/stub'  # stub 코드 폴더
TEST_CASE_FILE = DEFAULT_DIR / 'data/testcase.xlsx'  # 테스트케이스
LAST_TEST_CASE_FILE = DEFAULT_DIR / 'data/old/last_testcase.xlsx'
RESULT_PATH = DEFAULT_DIR / 'data/result'
DOWNLOAD_ZIP = DEFAULT_DIR / 'data/download.zip'


def git_checkout(project_dir: str, branch: str) -> None:
    """Git 브랜치 체크아웃 함수

    Args:
        project_dir: 레포지토리 경로
        branch: 체크아웃할 브랜치 이름
    """
    original_dir = os.getcwd()  # 현재 디렉토리 저장
    try:
        os.chdir(project_dir)  # 프로젝트 있는 폴더로 변경
        os.system(f"git checkout {branch}")
    finally:
        os.chdir(original_dir)  # 예외 발생해도 원래 폴더로 복귀 보장


def copy_style(cell: Any, new_cell: Any) -> None:
    """셀 스타일 복사 함수

    Args:
        cell: 원본 셀
        new_cell: 스타일을 적용할 대상 셀
    """
    if not hasattr(cell, 'has_style') or not cell.has_style:
        return

    style_attributes = [
        'font', 'border', 'fill', 'number_format',
        'protection', 'alignment'
    ]

    for attr in style_attributes:
        if hasattr(cell, attr):
            setattr(new_cell, attr, copy(getattr(cell, attr)))


def add_col_data(
        worksheet: Any,
        index: int,
        title: str,
        data: List[str],
        res: bool = False
) -> None:
    """워크시트에 컬럼 데이터 추가

    Args:
        worksheet: 데이터를 추가할 워크시트
        index: 데이터를 추가할 컬럼 인덱스
        title: 컬럼 제목
        data: 추가할 데이터 리스트
        res: 결과 컬럼 여부 (색상 처리)
    """
    worksheet.insert_cols(index)
    title_cell = worksheet.cell(row=1, column=index)
    title_cell.value = title

    # 스타일 복사
    reference_title_cell = worksheet.cell(row=1, column=3)
    copy_style(reference_title_cell, title_cell)

    # 데이터 및 색상 처리
    for i, val in enumerate(data):
        cell = worksheet.cell(row=i + 2, column=index)
        cell.value = val

        # 스타일 복사
        reference_cell = worksheet.cell(row=i + 2, column=3)
        copy_style(reference_cell, cell)

        # 결과에 따른 색상 처리
        if res:
            if val == 'Pass':
                cell.fill = PatternFill(
                    start_color='D3E6D6',
                    end_color='D3E6D6',
                    fill_type='solid'
                )
            elif val == 'Fail':
                cell.fill = PatternFill(
                    start_color='E86A75',
                    end_color='E86A75',
                    fill_type='solid'
                )


def colorize(val: str) -> Optional[str]:
    """값에 따라 스타일 색상 문자열 반환

    Args:
        val: 결과 값 ('Pass', 'Fail' 등)

    Returns:
        색상 CSS 문자열 또는 None
    """
    if val == "Pass":
        return 'background-color: #5CE65C; color:black'
    elif val == "Fail":
        return 'background-color: #FF6B6B; color:black'  # 색상 수정 (E86A75 → FF6B6B)
    return None


def get_2d_list(divider: int, path: str) -> np.ndarray:
    """디렉토리 파일 목록을 2D 배열로 변환

    Args:
        divider: 2차원 배열의 열 개수
        path: 파일 경로

    Returns:
        2차원 numpy 배열
    """
    path_obj = Path(path)
    if not path_obj.exists():
        return np.array([]).reshape(0, divider)

    # 디렉토리 파일 목록 가져오기
    lst_files = [f.name for f in path_obj.iterdir() if f.is_file()]

    # 행과 더미 값 계산
    total_files = len(lst_files)
    rows_needed = (total_files + divider - 1) // divider  # 올림 나눗셈

    # 필요한 더미 값 추가
    cells_needed = rows_needed * divider
    if cells_needed > total_files:
        dummy_count = cells_needed - total_files
        lst_files.extend(['nan'] * dummy_count)

    # 2D 배열로 변환
    return np.array(lst_files).reshape(rows_needed, divider)


def load_csv_list(file_path: str) -> List[List[str]]:
    """CSV 파일을 2D 리스트로 로드

    Args:
        file_path: CSV 파일 경로

    Returns:
        CSV 데이터의 2D 리스트
    """
    encodings = ['utf-8', 'cp949']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return list(csv.reader(f))
        except UnicodeDecodeError:
            continue

    # 모든 인코딩이 실패하면 빈 리스트 반환
    print(f"Warning: Could not decode CSV file {file_path}")
    return []


def read_excel_xw(file_path: str) -> pd.DataFrame:
    """xlwings를 사용한 Excel 파일 읽기

    Args:
        file_path: Excel 파일 경로

    Returns:
        Excel 데이터를 담은 DataFrame
    """
    with xw.App(visible=False) as app:
        try:
            wb = app.books.open(file_path)
            df = wb.sheets[0].used_range.options(pd.DataFrame, header=1, index=False).value
            wb.close()
            return df
        except Exception as e:
            print(f"Error reading Excel file {file_path}: {e}")
            return pd.DataFrame()


def is_same_path(path_str1: Union[str, Path], path_str2: Union[str, Path]) -> bool:
    """
    두 경로가 동일한 파일/디렉토리를 가리키는지 확인합니다.

    경로 문자열이나 Path 객체를 입력받아, resolve()를 통해 절대경로로 변환한 후 비교한다.

    Args:
        path_str1 (str | Path): 첫 번째 경로
        path_str2 (str | Path): 두 번째 경로

    Return:
         bool: 두 경로가 동일하면 True, 그렇지 않으면 False
    """
    # 문자열 또는 Path 객체를 절대 경로로 변환
    return Path(path_str1).resolve() == Path(path_str2).resolve()  # 정규화된 경로끼리 비교


def copyfile_if_different(src: Union[str, Path], dst: Union[str, Path]) -> None:
    """
    src와 dst 경로가 다르면 src를 dst로 복사한다.

    Args:
        src (str | Path): 원본 파일 경로
        dst (str | Path): 대상 파일 경로
    """
    if not is_same_path(src, dst):
        shutil.copyfile(src, dst)
    else:
        pass


def extract_key_value_pairs(s: str) -> List[str]:
    # 단어 = 단어 형태의 패턴을 찾아 리스트로 반환
    return re.findall(r'\w+\s*=\s*\w+', s)


def remove_leading_newlines(lst_lines: List[str]) -> str:
    """
    문자열 앞부분의 줄바꿈 문자(\n)만 제거한다.
    """
    return '\n'.join([(re.sub(r'^\n+', '', s)) for s in lst_lines])
