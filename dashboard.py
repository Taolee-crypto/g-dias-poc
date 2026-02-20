# dashboard.py - G-DIAS PoC 대시보드 (더미 데이터 사용)
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="G-DIAS PoC Dashboard", layout="wide")
st.title("G-DIAS Proof of Concept Dashboard")
st.markdown("실시간 민주주의 리스크 분석 데모 (더미 데이터)")

# 더미 데이터 생성 (실제로는 Kafka에서 읽어옴)
countries = ['South Korea', 'United States', 'Brazil', 'India', 'Germany']
dsi_scores = np.random.uniform(40, 90, 5).round(1)
adp_risks = np.random.uniform(10, 60, 5).round(1)

df = pd.DataFrame({
    'Country': countries,
    'DSI Score (0-100)': dsi_scores,
    'ADP Risk %': adp_risks
})

st.subheader("국가별 민주주의 안정성 지수 (DSI) & 권위주의화 위험 (ADP)")
st.dataframe(df.style.format({"DSI Score (0-100)": "{:.1f}", "ADP Risk %": "{:.1f}"}), use_container_width=True)

st.subheader("DSI 점수 추이 (더미 차트)")
chart_data = pd.DataFrame(
    np.random.randn(20, 5) * 10 + 70,  # 70~90 범위 시뮬레이션
    columns=countries
)
st.line_chart(chart_data)

st.markdown("---")
st.info("이것은 PoC 데모입니다. 실제로는 Kafka 스트림에서 실시간 데이터가 들어옵니다.")