import os
import shutil
from typing import List, Dict, Tuple
from Lib.commons import STUB_PATH


class StubFile:
    def __init__(self, pjt: str, c_option: str, source: List[str], header: List[str]):
        self.dict_var: Dict[str, List[str]] = {}
        self.pjt_path: str = pjt
        self.lst_source: List[str] = source.copy()  # 원본 리스트 보존을 위해 copy 사용
        self.lst_header: List[str] = header.copy()
        self.del_op: List[str]
        self.insert_op: List[str]
        self.del_op, self.insert_op = self.get_options(options=c_option)
        self.prepare_stub_environment()
        self.stub_source()
        self.stub_header()

    def prepare_stub_environment(self) -> None:
        """스텁 환경 준비 및 파일 복사"""
        # 소스 파일과 헤더 파일 경로 수집
        source_paths, header_paths = self.collect_file_paths()

        # 스텁 디렉토리 초기화
        if os.path.exists(STUB_PATH):
            shutil.rmtree(STUB_PATH)  # 지정된 폴더와 하위 폴더 파일 모두 삭제
        os.makedirs(STUB_PATH)

        # 파일 복사
        for file_path in source_paths + header_paths:
            shutil.copy2(file_path, STUB_PATH)

    def collect_file_paths(self) -> Tuple[List[str], List[str]]:
        """프로젝트에서 필요한 소스 및 헤더 파일 경로 수집"""
        source_paths: List[str] = []
        header_paths: List[str] = []

        for root, _, files in os.walk(self.pjt_path):
            for file in files:
                file_path = os.path.join(root, file)

                if file.endswith('.c') and file in self.lst_source:
                    source_paths.append(file_path)
                elif file.endswith('.h'):
                    header_paths.append(file_path)

        return source_paths, header_paths

    def stub_source(self) -> None:
        """소스 파일 스텁 처리"""
        self.dict_var.clear()  # 초기화

        for c_file in self.lst_source:
            stub_file_path = os.path.join(STUB_PATH, c_file)
            h_file_path = stub_file_path.replace('.c', '.h')

            # 소스 파일 처리
            revised_code = self.apply_option(file_path=stub_file_path)
            front_code, rear_code = self.separate_code(revised_code)
            lst_front, variables, extern = self.filter_declaration(code=front_code)
            lst_rear = self.filter_description(code=rear_code)

            # 변수 목록 저장
            self.dict_var[os.path.basename(stub_file_path)] = variables

            # 소스 파일 업데이트
            self.write_file(stub_file_path, ''.join(lst_front + lst_rear))

            # 헤더 파일 업데이트 (extern 선언 추가)
            self.append_to_file(h_file_path, extern)

    def stub_header(self):
        """헤더 파일 스텁 처리"""
        for file in self.lst_header:
            header_path = os.path.join(STUB_PATH, file)
            revised_code = self.apply_option(file_path=header_path)
            self.write_file(header_path, ''.join(revised_code))

    @staticmethod
    def write_file(file_path: str, content: str) -> None:
        """파일 쓰기"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    @staticmethod
    def append_to_file(file_path: str, lines: List[str]) -> None:
        """파일에 내용 추가"""
        if not lines:
            return

        with open(file_path, 'r+', encoding='utf-8') as f:
            h_code = f.readlines()  # 기존 내용 읽기
            f.seek(0)  # 파일 처음으로 이동
            f.write('\n'.join(h_code + lines))  # 새 내용 쓰기
            f.truncate()  # 기존 내용이 길 경우 잘라줌

    @staticmethod
    def get_options(options: str) -> Tuple[List[str], List[str]]:
        """컴파일 옵션 파싱"""
        delete_option: List[str] = []
        insert_option: List[str] = []

        for option in [op.split() for op in options.split('-') if op]:
            if option and option[0].startswith('D'):
                delete_option = option[1:]
            elif option and option[0].startswith('I'):
                insert_option = option[1:]

        return delete_option, insert_option

    def apply_option(self, file_path: str) -> List[str]:
        """파일에 옵션 적용"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line for line in f.readlines()
                    if not any(op in line for op in self.del_op)]

    @staticmethod
    def separate_code(lst_str: List[str]) -> Tuple[List[str], List[str]]:
        """코드를 선언부와 구현부로 분리"""
        for i, line in enumerate(lst_str):
            if ';' not in line and '(' in line and ')' in line:
                if i + 1 < len(lst_str) and '{' in lst_str[i + 1]:
                    return lst_str[:i], lst_str[i:]

        return lst_str, []  # 구현부가 없는 경우

    @staticmethod
    def filter_declaration(code: List[str]) -> Tuple[List[str], List[str], List[str]]:
        """선언부 필터링"""
        rev_code: List[str] = []
        variables: List[str] = []
        extern: List[str] = []
        defines: List[List[str]] = []

        for line in code:
            if '#define' in line:
                tokens = line.split()
                if len(tokens) > 1:
                    defines.append(tokens[1:])
                rev_code.append(line)
                continue

            if ';' not in line or any(x in line for x in ('const', 'inline', 'volatile')):
                rev_code.append(line)
                continue

            # 내부전역 변수를 외부전역 변수로 변환
            if 'static' in line:
                line_without_static = line.replace('static', '')
                extern.append(f"extern {line_without_static}")
                rev_code.append(line_without_static)
            else:
                rev_code.append(line)

            # 변수 초기화 코드 생성 (함수/구조체 선언 제외)
            if not any(x in line for x in ('};', ');')):
                tokens = line.split()
                if len(tokens) > 1:
                    var_name = tokens[1].replace(';', '')

                    if '[' in var_name and ']' in var_name:
                        # 배열 초기화
                        variables.append(f"    {var_name.split('[')[0]} = {{0}};")
                    else:
                        # 일반 변수 초기화
                        variables.append(f"    {var_name} = 0;")

        return rev_code, variables, extern

    def filter_description(self, code: List[str]) -> List[str]:
        """구현부 필터링"""
        ref_func_prefixes: List[str] = [source.split('_')[0] for source in self.lst_source]

        result: List[str] = []
        for line in code:
            # 내부 전역함수를 외부 전역함수로 변경
            if 'static' in line and 'inline' not in line:
                line = line.replace('static', '')

            # 함수 선언부 중 관련 없는 것 제외
            if not ('(' in line and ');' in line) or any(ref in line for ref in ref_func_prefixes):
                result.append(line)

        return result
