import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from Lib.commons import STUB_PATH


@dataclass
class CompileOptions:
    """컴파일 옵션을 담는 데이터 클래스"""
    delete: List[str]
    insert: List[str]
    define: List[str]


class StubFile:
    """C/C++ 프로젝트 파일을 스텁 형태로 변환하는 클래스"""

    # 상수 정의
    C_EXTENSION = '.c'
    H_EXTENSION = '.h'
    COMMON_HEADER = 'common.h'
    SKIP_KEYWORDS = {'const', 'inline', 'volatile'}
    DECLARATION_ENDINGS = {'};', ');'}

    def __init__(self, pjt: str, c_option: str, source: List[str], header: List[str]):
        self.pjt_path = Path(pjt)
        self.lst_source = source.copy()
        self.lst_header = header.copy()
        self.options = self._parse_options(c_option)
        self.dict_var: Dict[str, List[str]] = {}

        # 메인 처리 실행
        self._process_stub_files()

    def _process_stub_files(self) -> None:
        """스텁 파일 처리의 메인 워크플로우"""
        self._prepare_stub_environment()
        self._process_source_files()
        self._process_header_files()

    def _prepare_stub_environment(self) -> None:
        """스텁 환경 준비 및 파일 복사"""
        stub_path = Path(STUB_PATH)

        # 스텁 디렉토리 초기화
        if stub_path.exists():
            shutil.rmtree(stub_path)
        stub_path.mkdir(parents=True, exist_ok=True)

        # 필요한 파일들 복사
        for file_path in self._collect_required_files():
            shutil.copy2(file_path, stub_path)

    def _collect_required_files(self) -> List[Path]:
        """프로젝트에서 필요한 파일들 수집"""
        required_files = []
        source_names = set(self.lst_source)

        for file_path in self.pjt_path.rglob('*'):
            if not file_path.is_file():
                continue

            if (file_path.suffix == self.C_EXTENSION and
                    file_path.name in source_names):
                required_files.append(file_path)
            elif file_path.suffix == self.H_EXTENSION:
                required_files.append(file_path)

        return required_files

    def _process_source_files(self) -> None:
        """소스 파일들 처리"""
        self.dict_var.clear()
        stub_path = Path(STUB_PATH)

        for c_file in self.lst_source:
            source_path = stub_path / c_file
            header_path = source_path.with_suffix(self.H_EXTENSION)

            if not source_path.exists():
                continue

            # 소스 파일 처리
            processed_lines = self._apply_delete_options(source_path)
            front_code, rear_code = self._separate_code(processed_lines)

            declaration_result = self._process_declarations(front_code)
            implementation_lines = self._process_implementation(rear_code)

            # 결과 저장
            self.dict_var[source_path.name] = declaration_result.variables

            # 파일 업데이트
            self._write_file(source_path,
                             declaration_result.filtered_code + implementation_lines)

            if declaration_result.extern_declarations:
                self._append_to_file(header_path, declaration_result.extern_declarations)

    def _process_header_files(self) -> None:
        """헤더 파일들 처리"""
        stub_path = Path(STUB_PATH)

        for header_file in self.lst_header:
            header_path = stub_path / header_file

            if not header_path.exists():
                continue

            processed_lines = self._apply_delete_options(header_path)

            # common.h에 define 옵션 추가
            if (self.options.define and
                    header_file == self.COMMON_HEADER):
                processed_lines.extend(
                    f"#define {define_op}\n" for define_op in self.options.define
                )

            self._write_file(header_path, processed_lines)

    @dataclass
    class DeclarationResult:
        """선언부 처리 결과를 담는 데이터 클래스"""
        filtered_code: List[str]
        variables: List[str]
        extern_declarations: List[str]

    def _process_declarations(self, code_lines: List[str]) -> 'DeclarationResult':
        """선언부 처리 및 필터링"""
        filtered_code = []
        variables = []
        extern_declarations = []

        for line in code_lines:
            # #define 문은 그대로 유지
            if '#define' in line:
                filtered_code.append(line)
                continue

            # 세미콜론이 없거나 특정 키워드가 있는 라인은 그대로 유지
            if (';' not in line or
                    any(keyword in line for keyword in self.SKIP_KEYWORDS)):
                filtered_code.append(line)
                continue

            # static 변수 처리
            if 'static' in line:
                line_without_static = line.replace('static', '', 1).strip()
                extern_declarations.append(f"extern {line_without_static}")
                filtered_code.append(line_without_static + '\n')
                line = line_without_static
            else:
                filtered_code.append(line)

            # 변수 초기화 코드 생성
            variable_init = self._generate_variable_initialization(line)
            if variable_init:
                variables.append(variable_init)

        return self.DeclarationResult(filtered_code, variables, extern_declarations)

    def _generate_variable_initialization(self, line: str) -> Optional[str]:
        """변수 초기화 코드 생성"""
        # 함수나 구조체 선언은 제외
        if any(ending in line for ending in self.DECLARATION_ENDINGS):
            return None

        tokens = line.strip().split()
        if len(tokens) < 2:
            return None

        var_name = tokens[1].replace(';', '')

        if '[' in var_name and ']' in var_name:
            # 배열 초기화
            array_name = var_name.split('[')[0]
            return f"    {array_name} = {{0}};"
        else:
            # 일반 변수 초기화
            return f"    {var_name} = 0;"

    def _process_implementation(self, code_lines: List[str]) -> List[str]:
        """구현부 필터링 및 처리"""
        ref_func_prefixes = {source.split('_')[0] for source in self.lst_source}
        ref_func_prefixes.update(self.options.insert)

        processed_lines = []

        for line in code_lines:
            # static 제거 (inline 제외)
            if 'static' in line and 'inline' not in line:
                line = line.replace('static', '', 1)

            # 관련 없는 함수 선언 제외
            if (('(' in line and ');' in line) and
                    not any(prefix in line for prefix in ref_func_prefixes)):
                continue

            processed_lines.append(line)

        return processed_lines

    def _apply_delete_options(self, file_path: Path) -> List[str]:
        """파일에서 삭제 옵션 적용"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [
                    line for line in f
                    if not any(delete_op in line for delete_op in self.options.delete)
                ]
        except (IOError, UnicodeDecodeError) as e:
            print(f"파일 읽기 오류 {file_path}: {e}")
            return []

    @staticmethod
    def _separate_code(lines: List[str]) -> Tuple[List[str], List[str]]:
        """코드를 선언부와 구현부로 분리"""
        for i, line in enumerate(lines):
            if (';' not in line and '(' in line and ')' in line and
                    i + 1 < len(lines) and '{' in lines[i + 1]):
                return lines[:i], lines[i:]

        return lines, []

    @staticmethod
    def _write_file(file_path: Path, content: List[str]) -> None:
        """파일에 내용 쓰기"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(content)
        except IOError as e:
            print(f"파일 쓰기 오류 {file_path}: {e}")

    @staticmethod
    def _append_to_file(file_path: Path, lines: List[str]) -> None:
        """파일에 내용 추가"""
        if not lines:
            return

        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write('\n' + '\n'.join(lines))
        except IOError as e:
            print(f"파일 추가 오류 {file_path}: {e}")

    @staticmethod
    def _parse_options(options: str) -> CompileOptions:
        """컴파일 옵션 파싱"""
        delete_options = []
        insert_options = []
        define_options = []

        for option_group in options.split('-'):
            if not option_group.strip():
                continue

            parts = option_group.split()
            if not parts:
                continue

            flag = parts[0]
            values = parts[1:]

            if flag.startswith('D'):
                delete_options.extend(values)
            elif flag.startswith('I'):
                insert_options.extend(values)
            elif flag.startswith('A'):
                define_options.append(' '.join(values))

        return CompileOptions(delete_options, insert_options, define_options)