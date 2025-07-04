import os
import time
import re
from collections import defaultdict
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import pandas as pd
from Lib.stubFile import StubFile
from Lib.commons import RESULT_PATH, STUB_PATH, TEST_CASE_FILE, copyfile_if_different, remove_leading_newlines

# Constants
DRIVER_CODE = 'test_driver.c'
DEFAULT_DEFINITIONS = ['OFF : 0', 'ON : 1', 'FALSE : 0', 'TRUE : 1', 'NULL_16 : 65535']
DEFAULT_CYCLE_NUMBER = 255

# Compiled regex patterns for better performance
EXPECT_PATTERN = re.compile(r"(\d+)\)\s*(\w+)\s*=\s*(\d+)")
VAR_VAL_PATTERN = re.compile(r"(\w+)\s*=\s*(\d+)")


@dataclass
class TestCase:
    """테스트 케이스 데이터 클래스"""
    test_num: str
    funcs: str
    pre_condition: Optional[str]
    inputs: str
    expect: str
    note: str
    cycle: int
    c_file: str


class GenSWTest(StubFile):
    def __init__(self, gcc_option: str, pjt: str, compil_option: str,
                 source: List[str], header: List[str], testcase: str = TEST_CASE_FILE):
        super().__init__(pjt=pjt, c_option=compil_option, source=source, header=header)
        copyfile_if_different(testcase, TEST_CASE_FILE)

        self.include: List[str] = self._get_header_files()
        self.time: str = time.strftime('%Y%m%d_%H%M%S', time.localtime())
        self.df_test: pd.DataFrame = pd.DataFrame()
        self.exp_result: List[Dict[int, List[str]]] = []

        code = self._generate_test_code()
        self._create_driver_file(code)
        self.status: bool = self._run_driver(gcc_option)

    def _get_header_files(self) -> List[str]:
        """헤더 파일 목록 생성"""
        try:
            return [f.replace('.c', '.h') for f in os.listdir(STUB_PATH) if f.endswith('.c')]
        except OSError as e:
            print(f"Warning: Could not read stub directory: {e}")
            return []

    def _run_driver(self, gcc_option: str) -> bool:
        """테스트 드라이버 실행"""
        result_time_path = Path(RESULT_PATH) / self.time
        result_time_path.mkdir(parents=True, exist_ok=True)

        current_dir = Path.cwd()
        stub_dir = current_dir / "data" / "stub"

        try:
            os.chdir(stub_dir)
            os.system(f"gcc {gcc_option}")

            # exe 파일 확인 및 실행
            test_exe = next((cmd for cmd in gcc_option.split() if cmd.endswith('.exe')), None)

            if test_exe and Path(test_exe).is_file():
                os.system(test_exe)
                return True

        except Exception as e:
            print(f"Error running driver: {e}")
        finally:
            os.chdir(current_dir)

        return False

    def _load_test_data(self) -> List[TestCase]:
        """테스트 데이터 로드 및 파싱"""
        try:
            self.df_test = pd.read_excel(TEST_CASE_FILE, engine='openpyxl').iloc[:, 1:]
        except Exception as e:
            raise RuntimeError(f"Failed to load test case file: {e}")

        test_cases = []
        for unit_test in self.df_test.values:
            test_case = TestCase(
                test_num=str(int(unit_test[0])).zfill(3),
                funcs='' if pd.isna(unit_test[4]) else unit_test[4],
                pre_condition=unit_test[6],
                inputs='' if pd.isna(unit_test[7]) else unit_test[7],
                expect=unit_test[8],
                note='' if pd.isna(unit_test[-1]) else unit_test[-1],
                cycle=int(unit_test[5]),
                c_file=unit_test[3]
            )
            test_cases.append(test_case)

        return test_cases

    def _get_definitions(self, note: str) -> List[str]:
        """정의 목록 생성"""
        custom_definitions = [n for n in note.split('\n') if n] if note else []
        return custom_definitions + DEFAULT_DEFINITIONS

    def _apply_definitions(self, code_str: Optional[str], definitions: List[str]) -> str:
        """정의 적용"""
        if not code_str:
            return ""

        result = code_str
        for definition in definitions:
            if ':' in definition:
                key, value = map(str.strip, definition.split(':', 1))
                result = result.replace(key, value)

        return result

    def _parse_preconditions(self, pre_condition: Optional[str],
                             dict_test: Dict[str, str], c_file: str) -> List[str]:
        """사전 조건 파싱"""
        if not pre_condition or pd.isna(pre_condition):
            return []

        lst_pre = []
        for pre_cond in pre_condition.split('\n'):
            pre_cond = pre_cond.strip()
            if not pre_cond:
                continue

            if 'Test' in pre_cond:
                num = pre_cond.replace('Test_', '').replace('()', '').zfill(3)
                lst_pre.append(dict_test.get(num, ""))
            elif 'reset' in pre_cond:
                lst_pre.extend(self.dict_var.get(c_file, []))
            else:
                lst_pre.append(f"    {pre_cond};")

        return lst_pre

    def _parse_inputs(self, inputs: str) -> List[str]:
        """입력 파싱"""
        if not inputs or pd.isna(inputs):
            return []

        lst_input = []
        for inp in inputs.split('\n'):
            inp = inp.strip()
            if not inp:
                continue

            if '~' in inp and ')' in inp:
                paren_idx = inp.find(')')
                range_part = inp[:paren_idx].strip().split('~')
                val_part = inp[paren_idx + 1:].strip()

                start_range = int(range_part[0])
                end_range = int(range_part[-1])

                for r_index in range(start_range, end_range + 1):
                    lst_input.append(f"    {r_index}) {val_part};")
            else:
                lst_input.append(f"    {inp};")

        return lst_input

    def _parse_expected_results(self, expect: str) -> Tuple[List[str], Dict[int, List[Tuple[str, str]]]]:
        """예상 결과 파싱"""
        lst_var = []
        result = defaultdict(list)

        if ')' in expect:
            # 사이클별 결과
            for match in EXPECT_PATTERN.finditer(expect):
                key = int(match.group(1))
                var = match.group(2)
                val = match.group(3)
                result[key].append((var, val))
                if var not in lst_var:
                    lst_var.append(var)
        else:
            # 단일 결과
            for match in VAR_VAL_PATTERN.finditer(expect):
                var = match.group(1)
                val = match.group(2)
                result[DEFAULT_CYCLE_NUMBER].append((var, val))
                if var not in lst_var:
                    lst_var.append(var)

        return lst_var, dict(result)

    def _generate_condition_code(self, test_case: TestCase, lst_input: List[str],
                                 func: str, lst_var: List[str]) -> Tuple[List[str], List[str]]:
        """조건 코드 생성"""
        lst_cond = []
        lst_cond_for_pre = []
        sub_symbol = ','.join(['%d'] * len(lst_var))

        if ')' in test_case.inputs:
            # 사이클별 입력 처리
            for i in range(test_case.cycle):
                in_cycle = [f"    {in_code.replace(f'{i + 1})', '').strip()};"
                            for in_code in lst_input if in_code.startswith(f"    {i + 1})")]
                in_cycle.append(func)
                lst_cond_for_pre.extend(in_cycle)

                in_cycle.append(f"    fprintf(fptr, \"{sub_symbol}\\n\", {', '.join(lst_var)});")
                lst_cond.extend(in_cycle)
        else:
            # 단일 입력 처리
            lst_cond.extend(lst_input)
            lst_cond_for_pre.extend(lst_input)

            for _ in range(test_case.cycle):
                lst_cond_for_pre.append(func)
                lst_cond.append(func)
                lst_cond.append(f"    fprintf(fptr, \"{sub_symbol}\\n\", {', '.join(lst_var)});")

        return lst_cond, lst_cond_for_pre

    def _generate_function_code(self, test_case: TestCase, lst_var: List[str],
                                pre_code: str, condition: str) -> str:
        """함수 코드 생성"""
        out_col = (f"    FILE *fptr;\n"
                   f"    fptr = fopen(\"../result/{self.time}/test_{test_case.test_num}.csv\", \"w\");\n"
                   f"    fprintf(fptr, \"{','.join(lst_var)}\\n\");")

        return f"""
Void Test_{test_case.test_num}()
{{
{out_col}
{pre_code}
{condition}
    fclose(fptr);
}}"""

    def _generate_test_code(self) -> str:
        """테스트 코드 생성"""
        lst_code = ['#include <stdio.h>'] + [f'#include "{inc}"' for inc in self.include]
        main_test = []
        dict_test = {}

        test_cases = self._load_test_data()

        for test_case in test_cases:
            # 함수 코드 포맷팅
            func = '\n'.join([f"    {f.strip()};" for f in test_case.funcs.split('\n') if f.strip()])

            # 정의 적용
            definitions = self._get_definitions(test_case.note)

            # 사전 조건 처리
            lst_pre = self._parse_preconditions(test_case.pre_condition, dict_test, test_case.c_file)
            pre_code = remove_leading_newlines(lst_pre)
            pre_code = self._apply_definitions(pre_code, definitions)

            # 입력 및 예상 결과 처리
            inputs = self._apply_definitions(test_case.inputs, definitions)
            expect = self._apply_definitions(test_case.expect, definitions)

            lst_var, result = self._parse_expected_results(expect)
            self.exp_result.append(result)

            # 입력 처리
            lst_input = self._parse_inputs(inputs)

            # 조건 코드 생성
            lst_cond, lst_cond_for_pre = self._generate_condition_code(
                test_case, lst_input, func, lst_var)

            condition = '\n'.join(lst_cond)

            # 함수 코드 생성
            func_code_for_pre = '\n'.join(lst_cond_for_pre)
            if pre_code:
                func_code_for_pre = f"{pre_code}\n{func_code_for_pre}"

            func_code = self._generate_function_code(test_case, lst_var, pre_code, condition)

            lst_code.append(func_code)
            main_test.append(f"    Test_{test_case.test_num}();")
            dict_test[test_case.test_num] = func_code_for_pre

        # 메인 함수 생성
        main_code = f"""
int main(void)
{{
{chr(10).join(main_test)}
    return 0;
}}"""

        lst_code.append(main_code)
        return '\n'.join(lst_code)

    def _create_driver_file(self, code: str) -> None:
        """드라이버 파일 생성"""
        main_c = Path(STUB_PATH) / DRIVER_CODE
        try:
            with open(main_c, 'w', encoding='utf-8') as f:
                f.write(code)
        except IOError as e:
            raise RuntimeError(f"Failed to create driver file: {e}")

    # Deprecated methods for backward compatibility
    def run_driver(self, gcc_option: str) -> bool:
        """Deprecated: Use _run_driver instead"""
        return self._run_driver(gcc_option)

    def get_code(self) -> str:
        """Deprecated: Use _generate_test_code instead"""
        return self._generate_test_code()

    def create_file(self, code: str) -> None:
        """Deprecated: Use _create_driver_file instead"""
        self._create_driver_file(code)
