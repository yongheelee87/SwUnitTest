import os
import shutil
from typing import List, Dict, Tuple, Any
from pathlib import Path
from Lib.commons import STUB_PATH


class StubFile:
    """
    Class to manage stub file generation for testing
    """

    def __init__(self, pjt: str, c_option: str, source: List[str], header: List[str]):
        """
        Initialize the stub file generator

        Args:
            pjt: Project path
            c_option: Compilation options
            source: List of source files
            header: List of header files
        """
        self.pjt_path = pjt
        self.lst_app, self.lst_common = self.classify_source(sources=source.copy())
        self.lst_header = header.copy()
        self.del_op, self.insert_op = self.get_options(options=c_option)
        self.get_all_code()
        self.dict_var = self.stub_app()
        self.stub_rest()

    def stub_app(self) -> Dict[str, List[str]]:
        """
        Generate stub files for application code

        Returns:
            Dictionary of variable initialization statements by file
        """
        dict_vars = {}
        for c_file in self.lst_app:
            full_path = Path(STUB_PATH) / c_file
            front_code, rear_code = self.separate_code(self.apply_option(file_path=str(full_path)))
            lst_front, variables, extern = self.filter_front(code=front_code)
            lst_rear = self.filter_rear(code=rear_code)
            dict_vars[os.path.basename(str(full_path))] = variables

            # Write modified C file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(''.join(lst_front + lst_rear))

            # Update corresponding header file
            h_file = str(full_path).replace('.c', '.h')
            try:
                with open(h_file, 'r', encoding='utf-8') as f:
                    h_code = f.readlines()

                with open(h_file, 'w', encoding='utf-8') as f:
                    f.write(''.join(h_code + extern))
            except Exception as e:
                print(f"Error updating header file {h_file}: {str(e)}")

        return dict_vars

    def stub_rest(self) -> None:
        """
        Process remaining common and header files
        """
        for file in self.lst_common + self.lst_header:
            file_path = Path(STUB_PATH) / file
            try:
                rev_code = self.apply_option(file_path=str(file_path))
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(''.join(rev_code))
            except Exception as e:
                print(f"Error processing file {file}: {str(e)}")

    @staticmethod
    def get_options(options: str) -> Tuple[List[str], List[str]]:
        """
        Parse compilation options

        Args:
            options: Compilation option string

        Returns:
            Tuple of (delete_options, insert_options)
        """
        delete_option, insert_option = [], []

        if not options:
            return delete_option, insert_option

        ops = [op.split() for op in options.split('-') if op.strip()]

        for option in ops:
            if option and 'D' in option[0]:
                delete_option = option[1:]
            elif option and 'I' in option[0]:
                insert_option = option[1:]

        return delete_option, insert_option

    def apply_option(self, file_path: str) -> List[str]:
        """
        Apply compilation options to file contents

        Args:
            file_path: Path to the file

        Returns:
            List of strings containing filtered file content
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.readlines()

            # Remove lines containing any of the delete options
            if self.del_op:
                return [line for line in code if not any(ele in line for ele in self.del_op)]
            else:
                return code
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='cp949') as f:
                    code = f.readlines()

                if self.del_op:
                    return [line for line in code if not any(ele in line for ele in self.del_op)]
                else:
                    return code
            except Exception as e:
                print(f"Error reading file {file_path}: {str(e)}")
                return []

    @staticmethod
    def separate_code(lst_str: List[str]) -> Tuple[List[str], List[str]]:
        """
        Separate code into declarations and function implementations

        Args:
            lst_str: List of strings containing code

        Returns:
            Tuple of (front_code, rear_code)
        """
        ind_code = len(lst_str)

        for i, s in enumerate(lst_str):
            if ';' not in s and '(' in s and ')' in s:
                if i + 1 < len(lst_str) and '{' in lst_str[i + 1]:
                    ind_code = i
                    break

        return lst_str[:ind_code], lst_str[ind_code:]

    @staticmethod
    def filter_front(code: List[str]) -> Tuple[List[str], List[str], List[str]]:
        """
        Filter and process declarations in front part of code

        Args:
            code: List of code lines

        Returns:
            Tuple of (processed_code, variable_init_statements, extern_declarations)
        """
        rev_code, variables, extern, defines = [], [], [], []

        for c_line in code:
            if ';' in c_line and 'const' not in c_line:
                if 'static' in c_line:
                    c_line = c_line.replace('static', '')

                # Process array dimensions defined by macros
                if '[' in c_line and ']' in c_line:
                    define = c_line[c_line.find('[') + 1:c_line.find(']')]
                    for d in defines:
                        if define == d[0]:
                            c_line = c_line.replace(define, d[1])

                # Create variable initialization statement
                if ');' not in c_line:
                    var_parts = c_line.split()
                    if len(var_parts) > 1:
                        variables.append(f"    {var_parts[1].replace(';', ' = 0;')}")

                extern.append(f"extern {c_line}")

            elif '#define' in c_line:
                parts = c_line.split()
                if len(parts) > 2:
                    defines.append(parts[1:])

            if ');' not in c_line:
                rev_code.append(c_line)

        return rev_code, variables, extern

    def filter_rear(self, code: List[str]) -> List[str]:
        """
        Filter and process function implementations in rear part of code

        Args:
            code: List of code lines

        Returns:
            List of processed code lines
        """
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
    def classify_source(sources: List[str]) -> Tuple[List[str], List[str]]:
        """
        Classify source files into application and common files

        Args:
            sources: List of source files

        Returns:
            Tuple of (app_files, common_files)
        """
        app, com = [], []

        for source in sources:
            if 'App_' in source:
                app.append(source)
            else:
                com.append(source)

        return app, com

    def get_all_code(self) -> None:
        """
        Copy all necessary files from project to stub directory
        """
        # Add corresponding C files for all header files
        self.lst_common += [h.replace('.h', '.c') for h in self.lst_header
                            if h.replace('.h', '.c') not in self.lst_common]

        root_c, root_h = [], []
        pjt_path = Path(self.pjt_path)

        # Find all matching files in project directory
        for root, _, files in os.walk(pjt_path):
            root_path = Path(root)
            for file in files:
                if file.endswith('.c'):
                    if file in (self.lst_app + self.lst_common):
                        root_c.append(str(root_path / file))
                elif file.endswith('.h'):
                    root_h.append(str(root_path / file))

        # Recreate stub directory
        stub_path = Path(STUB_PATH)
        if stub_path.exists():
            shutil.rmtree(stub_path)
        stub_path.mkdir(parents=True)

        # Copy files to stub directory
        for file in root_c + root_h:
            try:
                shutil.copy2(file, str(stub_path))
            except Exception as e:
                print(f"Error copying file {file}: {str(e)}")

        # Update common file list with actual filenames
        self.lst_common = [os.path.basename(c) for c in root_c
                           if 'App_' not in os.path.basename(c)]