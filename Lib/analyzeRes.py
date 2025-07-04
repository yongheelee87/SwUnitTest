import os
import pandas as pd
import openpyxl
from pathlib import Path
from typing import List, Dict, Tuple
from Lib.commons import add_col_data, RESULT_PATH, TEST_CASE_FILE, ERROR_LOG


class AnalyzeRes:
    """테스트 결과 분석 및 보고서 생성 클래스

    테스트 결과 CSV 파일을 분석하고, 예상 값과 비교하여 결과 보고서를 생성합니다.

    Attributes:
        res_path: 결과 파일이 저장된 경로
        meas_out: 측정된 출력값 목록
        result: 테스트 결과 목록 ('Pass' 또는 'Fail')
        fail_index: 실패한 테스트 케이스의 인덱스 목록
    """

    def __init__(self, time: str, exp_res: List[Dict[int, List[str]]]):
        """AnalyzeRes 클래스 초기화

        Args:
            time: 테스트 실행 시간 (결과 폴더명)
            exp_res: 테스트 예상값 리스트 (다차원 딕셔너리)
        """
        self.res_path: Path = Path(RESULT_PATH) / time

        # 결과 폴더가 존재하는지 확인
        if not self.res_path.exists():
            raise FileNotFoundError(f"결과 폴더가 존재하지 않습니다: {self.res_path}")

        # 결과 분석 수행
        self.meas_out: List[str]
        self.result: List[str]
        self.fail_index: List[str]
        self.meas_out, self.result, self.fail_index = self.analyze_res(exp_res)

        # 결과 보고서 생성
        self.make_res_xlsx()

    def load_csv_files(self) -> List[Path]:
        """결과 CSV 파일에서 데이터 로드

        Returns:
            각 CSV 파일 경로
        """
        csv_files = [file for file in self.res_path.iterdir() if file.suffix.lower() == '.csv']

        if not csv_files:
            print(f"Warning: No CSV files found in {self.res_path}")
            os.startfile(ERROR_LOG)
            return []

        return csv_files

    def analyze_res(self, exp_res: List[Dict[int, List[str]]]) -> Tuple[List[str], List[str], List[str]]:
        """결과 분석 수행

        Args:
            exp_res: 테스트 예상값 리스트 (다차원 딕셔너리)

        Returns:
            Tuple[List[str], List[str], List[str]]: 측정값, 결과, 실패 인덱스 목록
        """
        # 측정 결과 로드
        meas_files = self.load_csv_files()

        # 결과가 없거나 갯수 일치 하지 않으면 빈 결과 반환
        if not meas_files or len(meas_files) != len(exp_res):
            return [], [], []

        # 측정 출력 포맷팅
        meas_out = []

        # 결과 판정 (Pass/Fail)
        result = []

        for dict_exp, meas_file in zip(exp_res, meas_files):
            meas_res = pd.read_csv(meas_file, dtype=str)
            # 변수=값 형식으로 포맷팅
            output_lines = []
            pass_fail = 'Pass'
            if 255 in dict_exp:
                for exp in dict_exp[255]:
                    var, val = exp[0], exp[1]
                    meas_val = meas_res[var].iloc[-1]
                    output_lines.append(f"{var} = {meas_val}")

                    # 결과 판정 (Pass/Fail)
                    if val != meas_val or pass_fail != 'Pass':
                        pass_fail = 'Fail'
            else:
                for key, exp_value in dict_exp.items():
                    for exp in exp_value:
                        order, var, val = key, exp[0], exp[1]
                        meas_val = meas_res[var].iloc[order-1]
                        output_lines.append(f"{order}) {var} = {meas_val}")

                        # 결과 판정 (Pass/Fail)
                        if val != meas_val or pass_fail != 'Pass':
                            pass_fail = 'Fail'

            meas_out.append('\n'.join(output_lines))
            result.append(pass_fail)

        # 실패한 케이스 인덱스 추출
        fail_index = [str(i + 1) for i, res in enumerate(result) if res == 'Fail']

        return meas_out, result, fail_index

    def make_res_xlsx(self) -> None:
        """결과 보고서 Excel 파일 생성"""
        try:
            # 결과 파일 경로 설정
            result_xlsx = f"{self.res_path}_testcase.xlsx"

            # 테스트 케이스 파일 로드
            wb = openpyxl.load_workbook(TEST_CASE_FILE)
            ws = wb.active

            # 결과 데이터 추가
            add_col_data(ws, 10, 'Measured(산출값)', self.meas_out)
            add_col_data(ws, 11, 'Result(결과)', self.result, True)

            # 파일 저장 (덮어쓰기)
            wb.save(result_xlsx)
            wb.close()

            print(f"Results saved to: {result_xlsx}")

            # 실패 케이스 요약 출력
            if self.fail_index:
                print(f"Failed test cases: {', '.join(self.fail_index)}")
            else:
                print("All test cases passed!")

        except Exception as e:
            print(f"Error creating result Excel file: {e}")
