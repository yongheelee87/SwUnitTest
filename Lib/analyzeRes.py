import os
import openpyxl
from Lib.commons import load_csv_list, add_col_data, RESULT_PATH, TEST_CASE_FILE


class AnalyzeRes:
    def __init__(self, time: str, var: list, exp_val: list):
        self.temp = None
        self.res_path = f"{RESULT_PATH}/{time}"
        self.meas_out, self.result, self.fail_index = self.analyze_res(var, exp_val)
        self.make_res_xlsx()

    def load_res(self) -> list:
        csv_files = [file for file in os.listdir(self.res_path) if 'csv' in file]
        return [load_csv_list(f"{self.res_path}/{csv_file}")[-1] for csv_file in csv_files]

    def analyze_res(self, var: list, exp_val: list):
        meas_res = self.load_res()
        meas_out = ['\n'.join([f"{var} = {res}" for var, res in zip(lst_var, lst_res)]) for lst_var, lst_res in zip(var, meas_res)]
        result = ['Pass' if lst_val == lst_res else 'Fail' for lst_val, lst_res in zip(exp_val, meas_res)]
        fail_index = [str(i+1) for i, res in enumerate(result) if res == 'Fail']
        return meas_out, result, fail_index

    def make_res_xlsx(self):
        # Xlsx 스타일 유지 및 결과 데이터 추가
        wb = openpyxl.load_workbook(TEST_CASE_FILE)
        ws = wb.active
        add_col_data(ws, 10, 'Measured(산출값)', self.meas_out)
        add_col_data(ws, 11, 'Result(결과)', self.result, True)

        wb.save(f"{self.res_path}_SW_TestCase.xlsx")
        wb.close()
