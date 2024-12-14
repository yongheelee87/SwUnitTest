import os
import shutil
import pandas as pd
import openpyxl
import streamlit as st
from Lib.commons import DEFAULT_DIR, TEST_CASE_FILE, LAST_TEST_CASE_FILE


st.set_page_config(layout="wide")

st.sidebar.title("SW Test")

if "upload_test" in st.session_state and st.session_state["upload_test"] is True:
    col1, col2 = st.columns([1, 1])
    col1.title("테스트 케이스")
    col2.info("업로드된 테스트 파일 적용중")
else:
    st.title("테스트 케이스")

with st.spinner('작업중입니다......'):
    _, _, _, col4 = st.columns(4)
    col4.page_link(f"{DEFAULT_DIR}/pages/3_▶️_Run_Test.py", label="테스트 실행 및 결과", icon="▶️")
    
    df_utest = pd.read_excel(TEST_CASE_FILE, engine='openpyxl').iloc[:, 1:]
    new_utest = st.file_uploader('SW Test Case 파일 업로드', type={'xlsx', 'csv'})
    if new_utest:
        df_new_utest = pd.read_excel(new_utest, engine='openpyxl').iloc[:, 1:]
        if df_utest.equals(df_new_utest):
            st.info('현재 저장되어 있는 테스트 케이스와의 변경이 없습니다.')
        else:
            df_utest = df_new_utest
            shutil.copyfile(TEST_CASE_FILE, LAST_TEST_CASE_FILE)
            with open(TEST_CASE_FILE, mode='wb') as f:
                f.write(new_utest.getvalue())
            st.success('성공적으로 변경 및 저장되었습니다')
    edited_df = st.data_editor(df_utest, height=(len(df_utest)+1)*35+10, hide_index=True)

col1, col2 = st.columns([1, 1])
if col1.button("⭕ 현재 설정으로 저장", type="primary", use_container_width=True):
    shutil.copyfile(TEST_CASE_FILE, LAST_TEST_CASE_FILE)

    wb = openpyxl.load_workbook(TEST_CASE_FILE)
    ws = wb.active
    for row, row_vals in enumerate(edited_df.to_numpy()):
        for col, val in enumerate(row_vals):
            ws.cell(row=row+2, column=col+2).value = val

    wb.save(TEST_CASE_FILE)
    wb.close()
    st.rerun()

with open(TEST_CASE_FILE, mode="rb") as file:
    col2.download_button(
        use_container_width=True,
        label="📥 Download Test Case (현재 테스트 다운로드)",
        data=file,
        file_name=os.path.basename(TEST_CASE_FILE),
        mime="application/vnd.ms-excel",
    )

if os.path.exists(LAST_TEST_CASE_FILE):
    st.write("저장된 직전 테스트 파일")
    df_utest = pd.read_excel(LAST_TEST_CASE_FILE, engine='openpyxl').iloc[:, 1:]
    st.dataframe(df_utest, height=(len(df_utest) + 1) * 35 + 10, hide_index=True)

    _, col2 = st.columns([1, 1])

    with open(LAST_TEST_CASE_FILE, mode='rb') as file:
        col2.download_button(
            use_container_width=True,
            label="📥 Download Backup (이전 테스트 다운로드)",
            data=file,
            file_name=os.path.basename(LAST_TEST_CASE_FILE),
            mime="application/vnd.ms-excel",
        )
