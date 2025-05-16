import os
import time
from typing import List, Dict, Optional
import pandas as pd
from Lib.stubFile import StubFile
from Lib.commons import RESULT_PATH, STUB_PATH, TEST_CASE_FILE

DRIVER_CODE = 'test_driver.c'  # test driver 코드
DEFINITIONS = ['OFF : 0', 'ON : 1', 'FALSE : 0', 'TRUE : 1', 'NULL_16 : 65535']


class GenSWTest(StubFile):
    def __init__(self, gcc_option: str, pjt: str, compil_option: str, source: List[str], header: List[str]):
        StubFile.__init__(self, pjt=pjt, c_option=compil_option, source=source, header=header)
        self.file: str = TEST_CASE_FILE
        self.include: List[str] = [f.replace('.c', '.h') for f in os.listdir(STUB_PATH) if f.endswith('.c')]
        self.time: str = time.strftime('%Y%m%d_%H%M%S', time.localtime())
        self.df_test: pd.DataFrame = pd.DataFrame()
        self.exp_val: List[List[str]] = []
        self.var: List[List[str]] = []
        self.create_file(self.get_code())
        self.status: bool = self.run_driver(gcc_option=gcc_option)

    def run_driver(self, gcc_option: str) -> bool:
        """테스트 드라이버 실행"""
        if not os.path.exists(RESULT_PATH):
            os.makedirs(RESULT_PATH)  # result 폴더 없으면 생성

        result_time_path = os.path.join(RESULT_PATH, self.time)
        os.makedirs(result_time_path)  # 날짜 폴더 생성

        current_dir = os.getcwd()  # default folder
        stub_dir = os.path.join(current_dir, "data", "stub")
        os.chdir(stub_dir)  # stub 폴더 CLI 이동

        os.system(f"gcc {gcc_option}")

        # exe 파일 확인 및 실행
        test_exe = next((gcc_cmd for gcc_cmd in gcc_option.split() if gcc_cmd.endswith('.exe')), None)
        build_status = False

        if test_exe and os.path.isfile(test_exe):
            os.system(test_exe)  # test.exe 실행
            build_status = True

        os.chdir(current_dir)  # default folder 복귀
        return build_status

    def _format_output_column(self, test_num: str) -> str:
        """출력 컬럼 포맷 생성"""
        return f"    FILE *fptr;\n    fptr = fopen(\"../result/{self.time}/test_{test_num}.csv\", \"w\");\n    fprintf(fptr, \"{{col}}\\n\");"

    def _format_output_val(self, sub_symbol: str, var_list: List[str]) -> str:
        """출력 값 포맷 생성"""
        return f"    fprintf(fptr, \"{sub_symbol}\\n\", {', '.join(var_list)});"

    def _format_function(self, out_col: str, pre_cond: str, cond: str, out_close: str = "") -> str:
        """함수 코드 포맷 생성"""
        return f"{out_col}\n{pre_cond}\n{cond}\n{out_close}"

    def _parse_preconditions(self, pre_condition: Optional[str], dict_test: Dict[str, str], c_file: str) -> List[str]:
        """사전 조건 파싱"""
        if not pre_condition or pd.isna(pre_condition):
            return []

        lst_pre = []
        for pre_cond in pre_condition.split('\n'):
            if 'Test' in pre_cond:
                num = pre_cond.replace('Test_', '').replace('()', '').zfill(3)
                lst_pre.append(dict_test.get(num, ""))
            elif 'reset' in pre_cond:
                lst_pre.extend(self.dict_var.get(c_file, []))
            else:
                lst_pre.append(f"    {pre_cond};")

        return lst_pre

    def _apply_definitions(self, code_str: Optional[str], definitions: List[str]) -> str:
        """정의 적용"""
        if not code_str:
            return ""

        for definition in definitions:
            if ':' in definition:
                key, value = definition.split(':', 1)
                code_str = code_str.replace(key.strip(), value.strip())

        return code_str

    def _parse_inputs(self, inputs: str, cycle: int) -> List[str]:
        """입력 파싱"""
        if not inputs or pd.isna(inputs):
            return []

        lst_input = []
        for inp in inputs.split('\n'):
            if not inp:
                continue

            if '~' in inp and ')' in inp:
                range_part = inp[:inp.find(')')].strip().split('~')
                val_part = inp[inp.find(')') + 1:].strip()

                for r_index in range(int(range_part[0]), int(range_part[-1]) + 1):
                    lst_input.append(f"    {r_index}) {val_part};")
            else:
                lst_input.append(f"    {inp.strip()};")

        return lst_input

    def get_code(self) -> str:
        """테스트 코드 생성"""
        lst_code: List[str] = ['#include <stdio.h>'] + [f'#include "{inc}"' for inc in self.include]
        self.df_test = pd.read_excel(self.file, engine='openpyxl').iloc[:, 1:]
        main_test: List[str] = []
        dict_test: Dict[str, str] = {}

        for unit_test in self.df_test.values:
            test_num: str = str(int(unit_test[0])).zfill(3)
            funcs: str = unit_test[3]
            pre_condition: Optional[str] = unit_test[5]
            inputs: str = '' if pd.isna(unit_test[6]) else unit_test[6]
            expect: str = unit_test[7]
            note: str = '' if pd.isna(unit_test[-1]) else unit_test[-1]
            cycle: int = int(unit_test[4])
            c_file: str = unit_test[2]

            # 함수 코드 포맷팅
            func: str = '\n'.join([f"    {f.strip()};" for f in funcs.split('\n') if f.strip()])

            # 사전 조건 처리
            lst_pre: List[str] = self._parse_preconditions(pre_condition, dict_test, c_file)
            pre_code: str = '\n'.join(lst_pre)

            # 정의 적용
            definitions: List[str] = [n for n in note.split('\n') if n] + DEFINITIONS if note else DEFINITIONS
            pre_code = self._apply_definitions(pre_code, definitions)
            inputs = self._apply_definitions(inputs, definitions)
            expect = self._apply_definitions(expect, definitions)

            # 예상 값 처리
            lst_var: List[str] = []
            lst_exp_val: List[str] = []
            for exp in expect.split('\n'):
                if exp:
                    lst_temp = exp.split()
                    lst_var.append(lst_temp[0])
                    lst_exp_val.append(lst_temp[-1])

            self.exp_val.append(lst_exp_val)
            self.var.append(lst_var)
            sub_symbol: str = ','.join(['%d' for _ in range(len(lst_var))])

            # 입력 처리
            lst_input: List[str] = self._parse_inputs(inputs, cycle)

            # 조건 처리
            lst_cond: List[str] = []
            lst_cond_for_pre: List[str] = []

            if ')' in inputs:
                for i in range(cycle):
                    in_cycle: List[str] = [f"    {in_code.replace(f'{i + 1})', '').strip()};"
                                           for in_code in lst_input if in_code.startswith(f"    {i + 1})")]
                    in_cycle.append(func)
                    lst_cond_for_pre += in_cycle

                    in_cycle.append(self._format_output_val(sub_symbol, lst_var))
                    lst_cond += in_cycle
            else:
                lst_cond.extend(lst_input)
                lst_cond_for_pre.extend(lst_input)
                for i in range(cycle):
                    lst_cond_for_pre.append(func)
                    lst_cond.append(func)
                    lst_cond.append(self._format_output_val(sub_symbol, lst_var))

            condition: str = '\n'.join(lst_cond)

            # 함수 코드 생성
            out_col: str = self._format_output_column(test_num).format(col=','.join(lst_var))
            func_code_for_pre: str = self._format_function("", pre_code, '\n'.join(lst_cond_for_pre))

            func_code: str = f"""
Void Test_{test_num}()
{{
{self._format_function(out_col, pre_code, condition, "    fclose(fptr);")}
}}"""

            lst_code.append(func_code)
            main_test.append(f"    Test_{test_num}();")
            dict_test[test_num] = func_code_for_pre

        # 메인 함수 생성
        main_code: str = f"""
int main(void)
{{
{chr(10).join(main_test)}
    return 0;
}}"""

        lst_code.append(main_code)
        return '\n'.join(lst_code)

    def create_file(self, code: str) -> None:
        """파일 생성"""
        main_c = os.path.join(STUB_PATH, DRIVER_CODE)
        with open(main_c, 'w') as f:
            f.write(code)
