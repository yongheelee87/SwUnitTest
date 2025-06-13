import os
import yaml
import pandas as pd
import streamlit as st
from zipfile import ZipFile
from streamlit_tree_select import tree_select
from Lib.commons import colorize, get_2d_list, SETTING_YAML, LAST_SETTING_YAML, TEST_CASE_FILE, LAST_TEST_CASE_FILE, RESULT_PATH, DOWNLOAD_ZIP


st.set_page_config(layout="wide")

st.sidebar.title("SW Test")

st.title("테스트 데이터")
select_set = st.selectbox('테스트 설정 파일', ['setting.yaml', 'last_setting.yaml'])

yaml_file = LAST_SETTING_YAML if 'last' in select_set else SETTING_YAML
with open(yaml_file, encoding='utf-8-sig') as f:
    setting = yaml.load(f, Loader=yaml.SafeLoader)

st.write('📝 현재 프로젝트 경로 및 빌드 설정')
st.markdown('\n'.join([f"- **{key}**: {val}" for key, val in setting.items()]))

col1, _ = st.columns(2)

with open(yaml_file, mode="rb") as file:
    col1.download_button(
        use_container_width=True,
        label="📥 Download yaml (테스트 설정 파일 다운로드)",
        data=file,
        file_name=os.path.basename(yaml_file),
        mime="text/yaml",
    )

result_files = [f for f in os.listdir(RESULT_PATH) if 'xlsx' in f]
result_files.reverse()

select_result = st.selectbox('테스트 결과 파일', result_files)
df_test = pd.read_excel(f"{RESULT_PATH}/{select_result}", engine='openpyxl').iloc[:, 1:]
df_style = df_test.style.map(colorize, subset=["Result(결과)"])
st.dataframe(df_style, height=(len(df_test) + 1) * 35 + 10, hide_index=True)

col1, _ = st.columns(2)

with open(f"{RESULT_PATH}/{select_result}", mode="rb") as file:
    col1.download_button(
        use_container_width=True,
        tpye="primary",
        label="📊📈 Download Result (테스트 결과 다운로드)",
        data=file,
        file_name=select_result,
        mime="application/vnd.ms-excel",
    )

st.markdown("""
<style>
[data-testid="stExpander"] {
    background-color: #eeeeee;
    color: black;
}
[data-testid="stExpanderToggleIcon"] {
    visibility: show;
}
</style>
""", unsafe_allow_html=True)

csv_path = f"{RESULT_PATH}/{select_result.replace('_testcase.xlsx', '')}"
result_files = get_2d_list(divider=3, path=csv_path)
for res in result_files:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1.expander(os.path.basename(res[0])):
        df_res1 = pd.read_csv(f"{csv_path}/{res[0]}", dtype=object, encoding='cp1252')
        st.dataframe(df_res1, hide_index=True)

    if 'nan' not in res[1]:
        with col2.expander(os.path.basename(res[1])):
            df_res2 = pd.read_csv(f"{csv_path}/{res[1]}", dtype=object, encoding='cp1252')
            st.dataframe(df_res2, hide_index=True)

    if 'nan' not in res[2]:
        with col3.expander(os.path.basename(res[2])):
            df_res3 = pd.read_csv(f"{csv_path}/{res[2]}", dtype=object, encoding='cp1252')
            st.dataframe(df_res3, hide_index=True)

st.subheader("프로젝트내 파일 Zip 다운로드")

files = [{"label": f, "value": f"{RESULT_PATH}/{f}"} for f in os.listdir(RESULT_PATH) if '.xlsx' in f]
# Create node to display
nodes = [
    {
        "label": "Setting",
        "value": "setting",
        "children": [
            {"label": "setting.yaml", "value": SETTING_YAML},
            {"label": "last_setting.yaml", "value": LAST_SETTING_YAML},
        ]
    },
    {
        "label": "Test_Case",
        "value": "test_case",
        "children": [
            {"label": "testcase.xlsx", "value": TEST_CASE_FILE},
            {"label": "last_testcase.xlsx", "value": LAST_TEST_CASE_FILE},
        ]
    },
    {
        "label": "Result",
        "value": "result",
        "children": files,
    },
]

return_select = tree_select(nodes, expanded=["setting", "test_case", "result"])

with ZipFile(DOWNLOAD_ZIP, 'w') as myzip:
    for file in return_select['checked']:
        if 'xlsx' in file or '.yaml' in file:
            myzip.write(file)

col1, _ = st.columns(2)
with open(DOWNLOAD_ZIP, mode="rb") as file:
    col1.download_button(
        use_container_width=True,
        label="🧷 Download Zip (파일 Zip 다운로드)",
        data=file,
        file_name="SW_Test.zip",
        mime="application/zip",
    )
