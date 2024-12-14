import os.path
import pandas as pd
import openpyxl
import streamlit as st
import plotly.express as px
from Lib.commons import colorize, add_col_data, get_2d_list, UPLOAD_PATH, TEST_CASE_FILE
from Lib.generateTest import GenSWTest
from Lib.loadRes import LoadRes


st.set_page_config(layout="wide")

st.sidebar.title("SW Test")

if st.session_state["upload_test"] is True:
    col1, col2 = st.columns([1, 1])
    col1.title("테스트 실행 및 결과")
    col2.info("업로드된 테스트 파일 적용중")
    pjt_path = UPLOAD_PATH
else:
    st.title("테스트 실행 및 결과")
    pjt_path = st.session_state['project_path']

with st.spinner('테스트 실행중입니다......'):
    swTest = GenSWTest(gcc_option=st.session_state["gcc_option"],
                       pjt=pjt_path,
                       compil_option=st.session_state["gcc_option"],
                       source=st.session_state["source_file"],
                       header=st.session_state["header_file"])

    if swTest.status is True:
        resUT = LoadRes(time=swTest.time)

        meas_out = ['\n'.join([f"{var} = {res}" for var, res in zip(lst_var, lst_res)]) for lst_var, lst_res in zip(swTest.var, resUT.meas_res)]
        result = ['Pass' if lst_val == lst_res else 'Fail' for lst_val, lst_res in zip(swTest.exp_val, resUT.meas_res)]
        fail_index = [str(i+1) for i, res in enumerate(result) if res == 'Fail']
        
        col1, col2 = st.columns([1, 1])
        fig = px.pie(
            pd.DataFrame({'result': ['Pass', 'Fail'], 'number': [len(result) - len(fail_index), len(fail_index)]}),
            names='result',
            values='number',
            title='결과 현황',
            hole=.3,
            color_discrete_sequence=["#00ff00", "#ff0000"])  # hole을 주면 donut 차트
        fig.update_traces(textposition='inside', textinfo='percent+label+value')
        fig.update_layout(margin=dict(b=10, l=0, r=0), font=dict(size=12))
        col1.plotly_chart(fig)
        if len(fail_index) != 0:
            st.error(f"테스트 {', '.join(fail_index)}에서 에러가 있습니다.")
        else:
            st.success("모든 테스트가 에러 없이 통과했습니다.")

        st.info(f"테스트 케이스 총 {len(result)}개, 성공: {len(result) - len(fail_index)}개, 실패: {len(fail_index)}개")

        # Xlsx 스타일 유지 및 결과 데이터 추가
        wb = openpyxl.load_workbook(TEST_CASE_FILE)
        ws = wb.active
        add_col_data(ws, 9, 'Measured(산출값)', meas_out)
        add_col_data(ws, 10, 'Result(결과)', result, True)

        result_file = f"{resUT.res_path}_SW_TestCase.xlsx"
        wb.save(result_file)
        wb.close()

        #  Data Frame 변환
        swTest.df_test.insert(7, 'Measured(산출값)', meas_out, True)
        swTest.df_test.insert(1, 'Result(결과)', result, True)
        df_style = swTest.df_test.style.map(colorize, subset=["Result(결과)"])
        st.dataframe(df_style, height=(len(swTest.df_test) + 1) * 35 + 10, hide_index=True)

        with open(result_file, mode="rb") as file:
            btn = st.download_button(
                type="primary",
                label="📊📈 Download Result (테스트 결과 다운로드)",
                data=file,
                file_name=os.path.basename(result_file),
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
        
        result_files = get_2d_list(divider=3, path=resUT.res_path)
        for res in result_files:
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1.expander(os.path.basename(res[0])):
                df_res1 = pd.read_csv(f"{resUT.res_path}/{res[0]}", dtype=object, encoding='cp1252')
                st.dataframe(df_res1, hide_index=True)
            
            if 'nan' not in res[1]:
                with col2.expander(os.path.basename(res[1])):
                    df_res2 = pd.read_csv(f"{resUT.res_path}/{res[1]}", dtype=object, encoding='cp1252')
                    st.dataframe(df_res2, hide_index=True)

            if 'nan' not in res[2]:
                with col3.expander(os.path.basename(res[2])):
                    df_res3 = pd.read_csv(f"{resUT.res_path}/{res[2]}", dtype=object, encoding='cp1252')
                    st.dataframe(df_res3, hide_index=True)
    else:
        st.error("컴파일러를 통한 빌드가 정상적으로 진행되지 않았습니다. 에러로그를 통해 소스코드를 다시 확인해주세요")
        with open(f"{UPLOAD_PATH}/error.log", "r", encoding='utf-8') as f:
            st.text(''.join(f.readlines()))
