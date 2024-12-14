import os
import shutil
import yaml
import streamlit as st
from Lib.commons import DEFAULT_DIR, RESULT_PATH, SETTING_YAML

if "first_time_connection" not in st.session_state:
    st.session_state["first_time_connection"] = True  # 처음 접속 플래그 삽입
    st.session_state["upload_test"] = False  # 테스트파일 업로드 상태

    with open(SETTING_YAML, encoding='utf-8-sig') as f:
        setting = yaml.load(f, Loader=yaml.SafeLoader)
        f.close()

    st.session_state["project_path"] = setting['project_path']
    st.session_state["git_branch"] = setting['git_branch']
    st.session_state["gcc_option"] = setting['gcc_option']
    st.session_state["compilation_option"] = setting['compilation_option']
    st.session_state["source_file"] = setting['source_file']
    st.session_state["header_file"] = setting['header_file']


st.set_page_config(layout="wide")

# Customize the sidebar
markdown = """
결과 파일 20개 초과로 오래된 파일 삭제 완료
"""

st.sidebar.title("SW Test based on Scenario")

result_files = [f for f in os.listdir(RESULT_PATH) if 'xlsx' in f]
if len(result_files) > 20:
    for res in result_files[:-20]:
        os.remove(f"{RESULT_PATH}/{res}")
        shutil.rmtree(f"{RESULT_PATH}/{res.replace('_SW_TestCase.xlsx', '')}")
        st.sidebar.info(markdown)

st.title("SW TEST based on Scenario")

st.markdown(
    """
    해당 SW 테스트는 시나리오 기반 유닛테스트로써 편집 및 관리에 용이한 xlsx 또는 csv 포멧을 활용하여 시나리오에 따른 테스트 결과를 산출할 수 있다. 
    """
)

st.header("Instructions", divider=True)

markdown = """
- Test_Setting(테스트설정) Tab을 통해 테스트를 위한 세부설정을 한다.
"""
st.markdown(markdown)
st.page_link(f"{DEFAULT_DIR}/pages/1_⚙️_Test_Setting.py", label="테스트 설정", icon="⚙️")

markdown = """
- 테스트설정이 올바르게 되어 있다면 테스트케이스를 업로드한다.
"""
st.markdown(markdown)
st.page_link(f"{DEFAULT_DIR}/pages/2_🧾_Test_Case.py", label="테스트 케이스", icon="🧾")

markdown = """
- 테스트를 진행하고 Result에서 진행된 최근 결과를 확인 및 다운로드한다
"""
st.markdown(markdown)
st.page_link(f"{DEFAULT_DIR}/pages/3_▶️_Run_Test.py", label="테스트 실행 및 결과", icon="▶️")

markdown = """
- 테스트를 통해 이전의 저장된 데이터들을 확인할 수 있다.
"""
st.markdown(markdown)
st.page_link(f"{DEFAULT_DIR}/pages/4_🗂️_Data_Storage.py", label="데이터 저장소", icon="🗂️")
