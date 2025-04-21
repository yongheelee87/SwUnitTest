import os
import time
import pandas as pd
from typing import List, Dict, Tuple, Any, Optional
from pathlib import Path
from Lib.stubFile import StubFile
from Lib.commons import RESULT_PATH, STUB_PATH, TEST_CASE_FILE

DRIVER_CODE = 'test_driver.c'  # test driver code
DEFINITIONS = ['OFF : 0', 'ON : 1', 'FALSE : 0', 'TRUE : 1', 'NULL_16 : 65535']


class GenSWTest(StubFile):
    """
    Class to generate and run software tests
    """
    # Template strings for code generation
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

    def __init__(self, gcc_option: str, pjt: str, compil_option: str,
                 source: List[str], header: List[str]):
        """
        Initialize the test generator and runner

        Args:
            gcc_option: GCC compilation options
            pjt: Project path
            compil_option: Compilation options
            source: List of source files
            header: List of header files
        """
        # Initialize parent class
        super().__init__(pjt=pjt, c_option=compil_option, source=source, header=header)

        self.file = TEST_CASE_FILE
        self.include = [f.replace('.c', '.h') for f in os.listdir(STUB_PATH)
                        if f.endswith('.c')]
        self.time = time.strftime('%Y%m%d_%H%M%S', time.localtime())
        self.df_test = pd.DataFrame()
        self.exp_val: List[List[str]] = []
        self.var: List[List[str]] = []

        # Generate and execute test
        self.create_file(self.get_code())
        self.status = self.run_driver(gcc_option=gcc_option)

    def run_driver(self, gcc_option: str) -> bool:
        """
        Compile and run the test driver

        Args:
            gcc_option: GCC compilation options string

        Returns:
            Boolean indicating success or failure
        """
        build_status = False

        # Create results directory if it doesn't exist
        result_path = Path(RESULT_PATH)
        if not result_path.exists():
            result_path.mkdir(parents=True)

        # Create timestamped directory for current test run
        time_path = result_path / self.time
        time_path.mkdir(exist_ok=True)

        # Save current directory, change to stub directory
        current_dir = os.getcwd()
        stub_path = Path(current_dir) / "data" / "stub"
        os.chdir(stub_path)

        try:
            # Compile test driver
            os.system(f"gcc {gcc_option}")

            # Find executable in gcc options
            test_exe = None
            for gcc_cmd in gcc_option.split():
                if gcc_cmd.endswith('.exe'):
                    test_exe = gcc_cmd
                    break

            # Run the executable if compilation succeeded
            if test_exe and os.path.isfile(test_exe):
                os.system(test_exe)  # Run test.exe
                build_status = True
        except Exception as e:
            print(f"Error compiling/running test: {str(e)}")
        finally:
            # Return to original directory
            os.chdir(current_dir)

        return build_status

    def get_code(self) -> str:
        """
        Generate test driver code

        Returns:
            String containing complete test driver code
        """
        # Start with includes
        lst_code = ['#include <stdio.h>']
        lst_code += [f'#include "{inc}"' for inc in self.include]

        # Read test case file
        try:
            self.df_test = pd.read_excel(self.file, engine='openpyxl').iloc[:, 1:]
        except Exception as e:
            print(f"Error reading test case file: {str(e)}")
            return "\n".join(lst_code + ["// Error reading test case file"])

        main_test, out_var, exp_val = [], [], []
        dict_test = {}  # Dictionary to store test code for pre-conditions

        # Process each test case
        for unit_test in self.df_test.values:
            try:
                # Extract test case data
                test_num = str(unit_test[0]).zfill(3)
                funcs = unit_test[3]
                pre_condition = unit_test[5]
                inputs = unit_test[6] if not pd.isna(unit_test[6]) else ''
                expect = unit_test[7]
                note = unit_test[-1]

                # Format function calls
                func = '\n'.join([f"    {f.strip()};" for f in funcs.split('\n')])

                # Process pre-conditions
                lst_pre_condition = []
                if not pd.isna(pre_condition) and pre_condition != '':
                    lst_pre_condition = pre_condition.split('\n')

                lst_pre = []
                for pre_cond in lst_pre_condition:
                    if 'Test' in pre_cond:
                        num = pre_cond.replace('Test_', '').replace('()', '').zfill(3)
                        if num in dict_test:
                            lst_pre.append(dict_test[num])
                    elif 'reset' in pre_cond:
                        lst_pre.extend(self.dict_var.get(unit_test[2], []))
                    else:
                        lst_pre.append(f"    {pre_cond};")

                pre_code = '\n'.join(lst_pre)

                # Process definitions/constants
                define = []
                if not pd.isna(note) and note != '':
                    define = [n for n in note.split('\n') if n]

                define += DEFINITIONS

                # Apply definitions to code
                for d in define:
                    if ':' in d:
                        def_parts = d.split(':')
                        if len(def_parts) >= 2:
                            key, value = def_parts[0].strip(), def_parts[1].strip()
                            pre_code = pre_code.replace(key, value)
                            inputs = inputs.replace(key, value)
                            expect = expect.replace(key, value)

                # Process expected values
                lst_var, lst_exp_val = [], []
                for exp in expect.split('\n'):
                    if exp.strip():
                        lst_temp = exp.split()
                        if len(lst_temp) > 1:
                            lst_var.append(lst_temp[0])
                            lst_exp_val.append(lst_temp[-1])

                exp_val.append(lst_exp_val)
                out_var.append(lst_var)

                # Create format string for output
                sub_symbol = ','.join(['%d' for _ in range(len(lst_var))])

                # Process test inputs
                cycle = int(unit_test[4])
                lst_cond, lst_cond_for_pre, lst_input = [], [], []

                for inp in inputs.split('\n'):
                    inp = inp.strip()
                    if not inp:
                        continue

                    if '~' in inp and ')' in inp:
                        # Range of inputs
                        r_in = inp[:inp.find(')')].strip().split('~')
                        val_in = inp[inp.find(')') + 1:].strip()

                        try:
                            start = int(r_in[0])
                            end = int(r_in[-1])
                            for r_index in range(start, end + 1):
                                lst_input.append(f"    {r_index}) {val_in};")
                        except (ValueError, IndexError):
                            lst_input.append(f"    {inp};")
                    else:
                        lst_input.append(f"    {inp};")

                # Generate test code
                if ')' in inputs:
                    for i in range(cycle):
                        # Find inputs for this cycle
                        cycle_prefix = f'{i + 1})'
                        in_cycle = []

                        for in_code in lst_input:
                            in_prefix = in_code[:in_code.find(')')].strip()
                            if in_prefix == cycle_prefix:
                                in_cycle.append(f"    {in_code.replace(cycle_prefix, '').strip()};")

                        in_cycle.append(func)
                        lst_cond_for_pre += in_cycle

                        in_cycle.append(self.output_val.format(
                            sym=sub_symbol, var=', '.join(lst_var)))
                        lst_cond += in_cycle
                else:
                    # Simple inputs (no cycles)
                    lst_cond.extend(lst_input)
                    lst_cond_for_pre.extend(lst_input)

                    for i in range(cycle):
                        lst_cond_for_pre.append(func)
                        lst_cond.append(func)
                        lst_cond.append(self.output_val.format(
                            sym=sub_symbol, var=', '.join(lst_var)))

                # Create final code
                condition = '\n'.join(lst_cond)
                func_code_for_pre = self.func_code.format(
                    out_col="",
                    pre_cond=pre_code,
                    cond='\n'.join(lst_cond_for_pre),
                    out_close=""
                )

                func_code = self.function_sample.format(
                    num=test_num,
                    func=self.func_code.format(
                        out_col=self.output_column.format(
                            num=test_num, time=self.time, col=','.join(lst_var)
                        ),
                        pre_cond=pre_code,
                        cond=condition,
                        out_close="    fclose(fptr);"
                    )
                )

                # Add function to code list
                lst_code.append(func_code.replace('/*', '{').replace('*/', '}'))
                main_test.append(f"    Test_{test_num}();")
                dict_test[test_num] = func_code_for_pre

            except Exception as e:
                print(f"Error processing test case {unit_test[0]}: {str(e)}")

        # Store results for later use
        self.exp_val = exp_val
        self.var = out_var

        # Add main function
        main_code = self.main_sample.format(test='\n'.join(main_test))
        lst_code.append(main_code.replace('/*', '{').replace('*/', '}'))

        # Return complete code
        return '\n'.join(lst_code)

    def create_file(self, code: str) -> None:
        """
        Write test driver code to file

        Args:
            code: String containing complete test driver code
        """
        main_c = Path(STUB_PATH) / DRIVER_CODE

        try:
            with open(main_c, 'w', encoding='utf-8') as f:
                f.write(code)
        except Exception as e:
            print(f"Error writing test driver file: {str(e)}")