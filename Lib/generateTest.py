import os
import time
import pandas as pd
from Lib.stubFile import StubFile
from Lib.commons import RESULT_PATH, STUB_PATH, TEST_CASE_FILE

DRIVER_CODE = 'test_driver.c'  # test driver 코드
DEFINITIONS = ['OFF : 0', 'ON : 1', 'FALSE : 0', 'TRUE : 1', 'NULL_16 : 65535']


class GenSWTest(StubFile):
    output_column = r"""    FILE *fptr;
    fptr = fopen("../result/{time}/test_{num}.csv", "w");
    fprintf(fptr, "{col}\n");"""
    output_val = r"""    fprintf(fptr, "{sym}\n", {var});"""
    func_code = r"""{out_col}
{pre_cond}

{cond}
{out_close}"""
    function_sample = r"""
Void Test_{num}( )
/*
{func}
*/"""

    main_sample = r"""
int main(void)
/*
{test}
    return 0;
*/"""

    def __init__(self, gcc_option: str, pjt: str, compil_option: str, source: list, header: list):
        StubFile.__init__(self, pjt=pjt, c_option=compil_option, source=source, header=header)
        self.file = TEST_CASE_FILE
        self.include = [f.replace('.c', '.h') for f in os.listdir(STUB_PATH) if '.c' in f]
        self.time = time.strftime('%Y%m%d_%H%M%S', time.localtime(time.time()))
        self.df_test = pd.DataFrame()
        self.exp_val, self.var = [], []
        self.create_file(self.get_code())
        self.status = self.run_driver(gcc_option=gcc_option)

    def run_driver(self, gcc_option: str):
        build_status = False
        if not os.path.exists(RESULT_PATH):
            os.makedirs(RESULT_PATH)  # result 폴더 없으면 생성
        os.makedirs(os.path.join(RESULT_PATH, self.time))  # 날짜 폴더 생성
        current_dir = os.getcwd()  # default folder
        os.chdir(os.path.join(current_dir, "data", "stub"))  # stub 폴더 CLI 이동
        os.system(f"gcc {gcc_option}")
        test_exe = [gcc_cmd for gcc_cmd in gcc_option.split() if '.exe' in gcc_cmd][0]
        if os.path.isfile(test_exe):
            os.system(test_exe)  # test.exe 실행
            build_status = True
        os.chdir(current_dir)  # default folder 복귀
        return build_status

    def get_code(self) -> str:
        lst_code = ['#include <stdio.h>'] + [f'#include "{inc}"' for inc in self.include]
        self.df_test = pd.read_excel(self.file, engine='openpyxl').iloc[:, 1:]
        main_test, out_var, exp_val, dict_test = [], [], [], {}
        for unit_test in self.df_test.values:
            funcs, pre_condition, inputs, expect, note = unit_test[3], unit_test[5], unit_test[6], unit_test[7], unit_test[-1]
            test_num = str(unit_test[0]).zfill(3)
            func = '\n'.join([f"    {f.strip()};" for f in funcs.split('\n')])  # Function이 여러개일 경우 고려
            if pd.isna(inputs):
                inputs = ''  # input이 없을 경우
            lst_pre_condition = [] if pd.isna(pre_condition) or pre_condition == '' else pre_condition.split('\n')
            lst_pre = []
            for pre_cond in lst_pre_condition:
                if 'Test' in pre_cond:
                    num = pre_cond.replace('Test_', '').replace('()', '').zfill(3)
                    lst_pre.append(dict_test[num])
                elif 'reset' in pre_cond:
                    lst_pre.extend(self.dict_var[unit_test[2]])
                else:
                    lst_pre.append(f"    {pre_cond};")
            pre_code = '\n'.join(lst_pre)
            define = [] if pd.isna(note) or note == '' else [n for n in note.split('\n') if n != '']
            define += DEFINITIONS
            for d in define:
                def_val = d.split(':')
                pre_code = pre_code.replace(def_val[0].strip(), def_val[1].strip())
                inputs = inputs.replace(def_val[0].strip(), def_val[1].strip())
                expect = expect.replace(def_val[0].strip(), def_val[1].strip())

            lst_var, lst_exp_val = [], []
            for exp in expect.split('\n'):
                if exp != '':
                    lst_temp = exp.split()
                    lst_var.append(lst_temp[0])
                    lst_exp_val.append(lst_temp[-1])
            exp_val.append(lst_exp_val)
            out_var.append(lst_var)
            sub_symbol = ','.join(['%d' for _ in range(len(lst_var))])

            cycle = int(unit_test[4])
            lst_cond, lst_cond_for_pre, lst_input = [], [], []
            for inp in inputs.split('\n'):
                if inp != "":
                    if '~' in inp and ')' in inp:
                        r_in = inp[:inp.find(')')].strip().split('~')
                        val_in = inp[inp.find(')') + 1:].strip()
                        for r_index in range(int(r_in[0]), int(r_in[-1]) + 1):
                            lst_input.append(f"    {r_index}) {val_in};")
                    else:
                        lst_input.append(f"    {inp.strip()};")

            if ')' in inputs:
                for i in range(cycle):
                    in_cycle = [f"    {in_code.replace(f'{i+1})', '').strip()};" for in_code in lst_input if f'{i+1})' == in_code[:in_code.find(')')].strip()]
                    in_cycle.append(func)
                    lst_cond_for_pre += in_cycle

                    in_cycle.append(self.output_val.format(sym=sub_symbol, var=', '.join(lst_var)))
                    lst_cond += in_cycle
            else:
                lst_cond.extend(lst_input)
                lst_cond_for_pre.extend(lst_input)
                for i in range(cycle):
                    lst_cond_for_pre.append(func)
                    lst_cond.append(func)
                    lst_cond.append(self.output_val.format(sym=sub_symbol, var=', '.join(lst_var)))
            condition = '\n'.join(lst_cond)
            func_code_for_pre = self.func_code.format(out_col="", pre_cond=pre_code, cond='\n'.join(lst_cond_for_pre), out_close="")
            func_code = self.function_sample.format(num=test_num, func=self.func_code.format(out_col=self.output_column.format(num=test_num, time=self.time, col=','.join(lst_var)), pre_cond=pre_code, cond=condition, out_close="    fclose(fptr);"))
            lst_code.append(func_code.replace('/*', '{').replace('*/', '}'))
            main_test.append(f"    Test_{test_num}();")
            dict_test[test_num] = func_code_for_pre

        self.exp_val = exp_val
        self.var = out_var
        main_code = self.main_sample.format(test='\n'.join(main_test))
        lst_code.append(main_code.replace('/*', '{').replace('*/', '}'))
        return '\n'.join(lst_code)

    def create_file(self, code: str):
        main_c = os.path.join(STUB_PATH, DRIVER_CODE)
        with open(main_c, 'w') as f:
            f.write(code)
