import os
import shutil
import streamlit as st
import yaml
from Lib.commons import git_checkout, DEFAULT_DIR, SETTING_YAML, LAST_SETTING_YAML, UPLOAD_PATH


def get_list_text_area(text_file):
    lst_file = []
    for f_line in text_file.split('\n'):
        if '- ' in f_line[:3]:
            lst_file.append(f_line.replace('- ', '').strip())
        elif '' != f_line:
            lst_file.append(f_line.strip())
    return lst_file


st.set_page_config(layout="wide")

st.sidebar.title("SW Test")

st.title("테스트 설정")


_, _, _, col4 = st.columns(4)
col4.page_link(f"{DEFAULT_DIR}/pages/3_▶️_Run_Test.py", label="테스트 실행 및 결과", icon="▶️")

new_files = st.file_uploader(" 테스트 파일 업로드", accept_multiple_files=True, type={"c", "h"})
if new_files:
    st.session_state["upload_test"] = True

    if os.path.exists(UPLOAD_PATH):
        shutil.rmtree(UPLOAD_PATH)
    os.mkdir(UPLOAD_PATH)
    sources, headers = [], []
    for upload_file in new_files:
        file_name = upload_file.name
        with open(f"{UPLOAD_PATH}/{file_name}", "wb") as f:
            f.write(upload_file.getbuffer())
        if '.c' in file_name:
            if file_name not in sources:
                sources.append(file_name)
        else:
            if file_name not in headers:
                headers.append(file_name)
    st.session_state["source_file"] = sources
    st.session_state["header_file"] = headers

    col1, col2 = st.columns(2)
    if col1.button("⭕ 코드 컴파일 적합성 확인", type="primary", use_container_width=True):
        main = """int main(void)
{
    return 0;
}"""
        with open(f"{UPLOAD_PATH}/main.c", "w") as f:
            f.write(main)

        os.chdir(UPLOAD_PATH)  # upload 폴더 CLI 이동
        os.system(f"gcc -g **.c -o test.exe 2> error.log")
        os.chdir(DEFAULT_DIR)  # default 폴더 복귀
        if os.path.exists(f"{UPLOAD_PATH}/test.exe"):
            st.success("성공적으로 프로젝트 빌드 가능합니다")
        else:
            st.error("컴파일러를 통한 빌드가 정상적으로 진행되지 않았습니다. 에러로그를 통해 소스코드를 다시 확인해주세요")
            with open(f"{UPLOAD_PATH}/error.log", "r", encoding='utf-8') as f:
                st.text(''.join(f.readlines()))
    st.write('📖 업로드 파일 리스트')
    st.write({'source_file': sources, 'header_file': headers})

    gcc_option = st.text_input("GCC Options", value=st.session_state['gcc_option'])
    compile_option = st.text_input("Compilation Options", value=st.session_state['compilation_option'])

    st.session_state["gcc_option"] = gcc_option
    st.session_state["compilation_option"] = compile_option
else:
    st.session_state["upload_test"] = False

    git_dir = st.text_input("Git Directory", value=st.session_state['project_path'])
    git_branch = st.text_input("Git Branch", value=st.session_state['git_branch'])
    gcc_option = st.text_input("GCC Options", value=st.session_state['gcc_option'])
    compile_option = st.text_input("Compilation Options", value=st.session_state['compilation_option'])

    sources = st.text_area("Source Files", value='\n'.join(st.session_state['source_file']))
    headers = st.text_area("Header Files", height=150, value='\n'.join(st.session_state['header_file']))

    git_checkout(git_dir, git_branch)

    col1, col2 = st.columns(2)

    if col1.button('❕ 현재 기입된 설정으로 변경', type="primary", use_container_width=True):
        st.session_state['project_path'] = git_dir
        st.session_state['git_branch'] = git_branch
        st.session_state['gcc_option'] = gcc_option
        st.session_state['compilation_option'] = compile_option
        st.session_state['source_file'] = get_list_text_area(sources)
        st.session_state['header_file'] = get_list_text_area(headers)

        git_checkout(git_dir, git_branch)

    if col2.button('💾 기입된 설정을 파일에 저장', use_container_width=True):
        st.session_state['project_path'] = git_dir
        st.session_state['git_branch'] = git_branch
        st.session_state['gcc_option'] = gcc_option
        st.session_state['compilation_option'] = compile_option
        st.session_state['source_file'] = get_list_text_area(sources)
        st.session_state['header_file'] = get_list_text_area(headers)

        set_yaml = {'project_path': git_dir,
                    'git_branch': git_branch,
                    'gcc_option': gcc_option,
                    'compilation_option': compile_option,
                    'source_file': st.session_state['source_file'],
                    'header_file': st.session_state['header_file']}

        shutil.copyfile(SETTING_YAML, LAST_SETTING_YAML)
        with open(SETTING_YAML, 'w') as file:
            file.write("# To disable the code, add a semicolon at the beginning\n\n")
            yaml.dump(set_yaml, file, default_flow_style=False, sort_keys=False)

        st.rerun()

    st.markdown(f"""
    📝 현재 프로젝트 경로 및 빌드 설정
    - ""project path**: {st.session_state['project_path']}
    - ""git branch**: {st.session_state['git_branch']}
    - ""gcc option**: {st.session_state['gcc_option']}
    - ""compilation option**: {st.session_state['compilation_option']}""")

    st.markdown(f"""
    📝 현재 프로젝트 경로 및 빌드 설정
    - ""source files**: {st.session_state['source_file']}
    - ""header files**: {st.session_state['header_file']}""")


