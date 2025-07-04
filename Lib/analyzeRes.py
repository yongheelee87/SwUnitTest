import os
import pandas as pd
import openpyxl
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from Lib.commons import add_col_data, RESULT_PATH, TEST_CASE_FILE, ERROR_LOG

# 상수 정의
LAST_ROW_INDEX = 255
MEASURED_COL_INDEX = 10
RESULT_COL_INDEX = 11
PASS_RESULT = 'Pass'
FAIL_RESULT = 'Fail'


@dataclass
class TestResult:
    """테스트 결과 데이터 클래스"""
    measured_output: List[str]
    results: List[str]
    failed_indices: List[str]


class AnalyzeResError(Exception):
    """AnalyzeRes 관련 커스텀 예외"""
    pass


class AnalyzeRes:
    """테스트 결과 분석 및 보고서 생성 클래스

    테스트 결과 CSV 파일을 분석하고, 예상 값과 비교하여 결과 보고서를 생성합니다.

    Attributes:
        res_path: 결과 파일이 저장된 경로
        test_result: 테스트 결과 데이터
    """

    def __init__(self, time: str, exp_res: List[Dict[int, List[str]]]):
        """AnalyzeRes 클래스 초기화

        Args:
            time: 테스트 실행 시간 (결과 폴더명)
            exp_res: 테스트 예상값 리스트 (다차원 딕셔너리)

        Raises:
            AnalyzeResError: 결과 폴더가 존재하지 않거나 분석 실패 시
        """
        self.res_path: Path = Path(RESULT_PATH) / time
        self._validate_result_path()

        try:
            self.test_result = self._analyze_results(exp_res)
            self._generate_report()
        except Exception as e:
            print(f"Error: 테스트 결과 분석 중 오류 발생: {e}")
            raise AnalyzeResError(f"테스트 결과 분석 실패: {e}") from e

    def _validate_result_path(self) -> None:
        """결과 폴더 존재 여부 확인"""
        if not self.res_path.exists():
            error_msg = f"결과 폴더가 존재하지 않습니다: {self.res_path}"
            print(f"Error: {error_msg}")
            raise AnalyzeResError(error_msg)

    def _load_csv_files(self) -> List[Path]:
        """결과 CSV 파일 로드

        Returns:
            CSV 파일 경로 리스트

        Raises:
            AnalyzeResError: CSV 파일이 없는 경우
        """
        try:
            csv_files = [
                file for file in self.res_path.iterdir()
                if file.suffix.lower() == '.csv' and file.is_file()
            ]

            if not csv_files:
                print(f"Warning: CSV 파일을 찾을 수 없습니다: {self.res_path}")
                if ERROR_LOG.exists():
                    os.startfile(ERROR_LOG)
                raise AnalyzeResError(f"CSV 파일이 없습니다: {self.res_path}")

            return sorted(csv_files)  # 일관된 순서 보장

        except OSError as e:
            print(f"Error: 디렉토리 읽기 오류: {e}")
            raise AnalyzeResError(f"디렉토리 접근 실패: {e}") from e

    def _read_csv_safely(self, csv_path: Path) -> pd.DataFrame:
        """CSV 파일 안전하게 읽기

        Args:
            csv_path: CSV 파일 경로

        Returns:
            DataFrame 객체

        Raises:
            AnalyzeResError: CSV 읽기 실패 시
        """
        try:
            df = pd.read_csv(csv_path, dtype=str)
            if df.empty:
                raise AnalyzeResError(f"빈 CSV 파일: {csv_path}")
            return df
        except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
            print(f"Error: CSV 파싱 오류 ({csv_path}): {e}")
            raise AnalyzeResError(f"CSV 파일 읽기 실패: {csv_path}") from e

    def _process_last_row_case(self, exp_list: List[str], meas_df: pd.DataFrame) -> Tuple[List[str], bool]:
        """마지막 행 기준 테스트 케이스 처리

        Args:
            exp_list: 예상값 리스트
            meas_df: 측정값 DataFrame

        Returns:
            Tuple[출력 라인 리스트, 통과 여부]
        """
        output_lines = []
        is_pass = True

        for exp in exp_list:
            if len(exp) < 2:
                print(f"Warning: 잘못된 예상값 형식: {exp}")
                continue

            var, expected_val = exp[0], exp[1]

            if var not in meas_df.columns:
                print(f"Warning: 컬럼을 찾을 수 없습니다: {var}")
                is_pass = False
                continue

            measured_val = meas_df[var].iloc[-1]
            output_lines.append(f"{var} = {measured_val}")

            if expected_val != measured_val:
                is_pass = False

        return output_lines, is_pass

    def _process_indexed_case(self, exp_dict: Dict[int, List[str]], meas_df: pd.DataFrame) -> Tuple[List[str], bool]:
        """인덱스 기준 테스트 케이스 처리

        Args:
            exp_dict: 예상값 딕셔너리
            meas_df: 측정값 DataFrame

        Returns:
            Tuple[출력 라인 리스트, 통과 여부]
        """
        output_lines = []
        is_pass = True

        for order, exp_list in exp_dict.items():
            if order <= 0 or order > len(meas_df):
                print(f"Warning: 잘못된 행 인덱스: {order}")
                is_pass = False
                continue

            for exp in exp_list:
                if len(exp) < 2:
                    print(f"Warning: 잘못된 예상값 형식: {exp}")
                    continue

                var, expected_val = exp[0], exp[1]

                if var not in meas_df.columns:
                    print(f"Warning: 컬럼을 찾을 수 없습니다: {var}")
                    is_pass = False
                    continue

                measured_val = meas_df[var].iloc[order - 1]
                output_lines.append(f"{order}) {var} = {measured_val}")

                if expected_val != measured_val:
                    is_pass = False

        return output_lines, is_pass

    def _analyze_single_result(self, exp_dict: Dict[int, List[str]], meas_file: Path) -> Tuple[str, str]:
        """단일 테스트 결과 분석

        Args:
            exp_dict: 예상값 딕셔너리
            meas_file: 측정값 파일 경로

        Returns:
            Tuple[측정 출력, 결과 (Pass/Fail)]
        """
        meas_df = self._read_csv_safely(meas_file)

        if LAST_ROW_INDEX in exp_dict:
            output_lines, is_pass = self._process_last_row_case(exp_dict[LAST_ROW_INDEX], meas_df)
        else:
            output_lines, is_pass = self._process_indexed_case(exp_dict, meas_df)

        measured_output = '\n'.join(output_lines)
        result = PASS_RESULT if is_pass else FAIL_RESULT

        return measured_output, result

    def _analyze_results(self, exp_res: List[Dict[int, List[str]]]) -> TestResult:
        """테스트 결과 분석 수행

        Args:
            exp_res: 테스트 예상값 리스트

        Returns:
            TestResult 객체
        """
        meas_files = self._load_csv_files()

        if len(meas_files) != len(exp_res):
            error_msg = f"파일 수 불일치: CSV({len(meas_files)}) vs 예상값({len(exp_res)})"
            print(f"Error: {error_msg}")
            raise AnalyzeResError(error_msg)

        measured_outputs = []
        results = []

        for exp_dict, meas_file in zip(exp_res, meas_files):
            try:
                measured_output, result = self._analyze_single_result(exp_dict, meas_file)
                measured_outputs.append(measured_output)
                results.append(result)
            except Exception as e:
                print(f"Error: 파일 분석 오류 ({meas_file}): {e}")
                measured_outputs.append("분석 오류")
                results.append(FAIL_RESULT)

        # 실패한 케이스 인덱스 추출
        failed_indices = [
            str(i + 1) for i, result in enumerate(results)
            if result == FAIL_RESULT
        ]

        return TestResult(measured_outputs, results, failed_indices)

    def _generate_report(self) -> None:
        """결과 보고서 Excel 파일 생성

        Raises:
            AnalyzeResError: Excel 파일 생성 실패 시
        """
        try:
            result_xlsx = f"{self.res_path}_testcase.xlsx"

            # 테스트 케이스 파일 로드
            if not Path(TEST_CASE_FILE).exists():
                raise AnalyzeResError(f"테스트 케이스 파일이 없습니다: {TEST_CASE_FILE}")

            wb = openpyxl.load_workbook(TEST_CASE_FILE)
            ws = wb.active

            # 결과 데이터 추가
            add_col_data(ws, MEASURED_COL_INDEX, 'Measured(산출값)', self.test_result.measured_output)
            add_col_data(ws, RESULT_COL_INDEX, 'Result(결과)', self.test_result.results, True)

            # 파일 저장
            wb.save(result_xlsx)
            wb.close()

            self._print_summary(result_xlsx)

        except Exception as e:
            print(f"Error: Excel 파일 생성 오류: {e}")
            raise AnalyzeResError(f"보고서 생성 실패: {e}") from e

    def _print_summary(self, result_file: str) -> None:
        """결과 요약 출력

        Args:
            result_file: 결과 파일 경로
        """
        print(f"Results saved to: {result_file}")

        if self.test_result.failed_indices:
            print(f"Failed test cases: {', '.join(self.test_result.failed_indices)}")
            print(f"Info: 실패한 테스트 케이스: {len(self.test_result.failed_indices)}개")
        else:
            print("All test cases passed!")
            print("Info: 모든 테스트 케이스 통과")

    # 공용 프로퍼티 (기존 인터페이스 호환성)
    @property
    def meas_out(self) -> List[str]:
        """측정된 출력값 목록 (하위 호환성)"""
        return self.test_result.measured_output

    @property
    def result(self) -> List[str]:
        """테스트 결과 목록 (하위 호환성)"""
        return self.test_result.results

    @property
    def fail_index(self) -> List[str]:
        """실패한 테스트 케이스 인덱스 목록 (하위 호환성)"""
        return self.test_result.failed_indices