import os
import shutil
from Lib.commons import STUB_PATH


class StubFile:
    def __init__(self, pjt: str, c_option: str, source: list, header: list):
        self.pjt_path = pjt
        self.lst_app, self.lst_common = self.classify_source(sources=source[:])
        self.lst_header = header[:]
        self.del_op, self.insert_op = self.get_options(options=c_option)
        self.get_all_code()
        self.dict_var = self.stub_app()
        self.stub_rest()

    def stub_app(self):
        dict_vars = {}
        for c_file in self.lst_app:
            c_file = f"{STUB_PATH}/{c_file}"
            front_code, rear_code = self.separate_code(self.apply_option(file_path=c_file))
            lst_front, variables, extern = self.filter_front(code=front_code)
            lst_rear = self.filter_rear(code=rear_code)
            dict_vars[os.path.basename(c_file)] = variables

            with open(c_file, 'w', encoding='utf-8') as f:
                f.write(''.join(lst_front + lst_rear))

            h_file = c_file.replace('.c', '.h')
            with open(h_file, 'r', encoding='utf-8') as f:
                h_code = f.readlines()

            with open(h_file, 'w', encoding='utf-8') as f:
                f.write(''.join(h_code + extern))
        return dict_vars

    def stub_rest(self):
        for file in self.lst_common + self.lst_header:
            rev_code = self.apply_option(file_path=f"{STUB_PATH}/{file}")
            with open(f"{STUB_PATH}/{file}", 'w', encoding='utf-8') as f:
                f.write(''.join(rev_code))

    @staticmethod
    def get_options(options: str):
        ops = [op.split() for op in options.split('-') if op != '']
        delete_option, insert_option = [], []
        for option in ops:
            if 'D' in option[0]:
                delete_option = option[1:]
            elif 'I' in option[0]:
                insert_option = option[1:]
        return delete_option, insert_option

    def apply_option(self, file_path: str):
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.readlines()
            rev_lst = [line for line in code if not any(ele in line for ele in self.del_op)]
        return rev_lst

    @staticmethod
    def separate_code(lst_str: list):
        ind_code = len(lst_str)
        for i, s in enumerate(lst_str):
            if ';' not in s and '(' in s and ')' in s:
                if '{' in lst_str[i+1]:
                    ind_code = i
                    break
        return lst_str[:ind_code], lst_str[ind_code:]

    @staticmethod
    def filter_front(code: list):
        rev_code, variables, extern, defines = [], [], [], []
        for c_line in code:
            if ';' in c_line and 'const' not in c_line:
                if 'static' in c_line:
                    c_line = c_line.replace('static', '')

                if '[' in c_line and ']' in c_line:
                    define = c_line[c_line.find('[') + 1:c_line.find(']')]
                    for d in defines:
                        if define == d[0]:
                            c_line = c_line.replace(define, d[1])

                if ');' not in c_line:
                    variables.append(f"    {c_line.split()[1].replace(';', ' = 0;')}")

                extern.append(f"extern {c_line}")

            elif '#define' in c_line:
                defines.append(c_line.split()[1:])

            if ');' not in c_line:
                rev_code.append(c_line)
        return rev_code, variables, extern

    def filter_rear(self, code: list):
        ref_func = ['App_'] + [com.replace('.c', '') for com in self.lst_common]
        rev_code = []
        for c_line in code:
            if 'static' in c_line:
                c_line = c_line.replace('static', '')

            if ';' in c_line and '(' in c_line and ')' in c_line:
                if any(ele in c_line for ele in ref_func):
                    rev_code.append(c_line)
            else:
                rev_code.append(c_line)
        return rev_code

    @staticmethod
    def classify_source(sources: list):
        app, com = [], []
        for source in sources:
            if 'App_' in source:
                app.append(source)
            else:
                com.append(source)
        return app, com

    def get_all_code(self):
        root_c, root_h = [], []
        self.lst_common += [h.replace('.h', '.c') for h in self.lst_header if not h.replace('.h', '.c') in self.lst_common]
        for (root, directories, files) in os.walk(self.pjt_path):
            for file in files:
                if '.c' in file[-2:]:
                    for c_name in self.lst_app + self.lst_common:
                        if c_name == file:
                            root_c.append(os.path.join(root, file))
                elif '.h' in file[-2:]:
                    root_h.append(os.path.join(root, file))

        if os.path.exists(STUB_PATH):
            shutil.rmtree(STUB_PATH)  # 지정된 폴더와 하위 폴더 파일 모두 삭제
        os.makedirs(STUB_PATH)

        for file in root_c + root_h:
            shutil.copy2(str(file), str(STUB_PATH))

        self.lst_common = [os.path.basename(c) for c in root_c if 'App_' not in os.path.basename(c)]
