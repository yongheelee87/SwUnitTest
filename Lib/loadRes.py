import os
from Lib.commons import load_csv_list, RESULT_PATH


class LoadRes:
    def __init__(self, time: str):
        self.temp = None
        self.res_path = f"{RESULT_PATH}/{time}"
        self.meas_res = self.load_res()

    def load_res(self) -> list:
        csv_files = [file for file in os.listdir(self.res_path) if 'csv' in file]
        return [load_csv_list(f"{self.res_path}/{csv_file}")[-1] for csv_file in csv_files]
