"""
dashboard.py - G-DIAS PoC 대시보드 v3
- AI 국가별 분석 보고서 (Claude API)
- 깔끔한 레이아웃, 겹침 없음
- 명확한 그래프
"""

import sys, os, json, pickle
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from vdem_features import VDemLoader, ALL_FEATURES, DIMENSION_WEIGHTS, compute_dimension_scores
from alert_engine import AlertEngine, DSIHistoryStore, run_full_pipeline
from ai_report import generate_country_report, generate_global_summary

# ── 페이지 설정
st.set_page_config(
    page_title="G-DIAS Dashboard",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
div[data-testid="metric-container"] {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 16px 20px;
}
div[data-testid="metric-container"] label { font-size: 13px !important; color: #64748b !important; }
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    font-size: 28px !important; font-weight: 600 !important;
}
.alert-box { border-radius: 8px; padding: 10px 14px; margin: 6px 0; line-height: 1.5; }
.alert-critical { background: #fef2f2; border-left: 4px solid #ef4444; }
.alert-warning  { background: #fff7ed; border-left: 4px solid #f97316; }
.alert-watch    { background: #fefce8; border-left: 4px solid #eab308; }
.report-box {
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 18px 22px; margin-top: 8px; line-height: 1.8;
}
.finding-item {
    background: #eff6ff; border-radius: 6px; padding: 8px 12px;
    margin: 4px 0; font-size: 14px; border-left: 3px solid #3b82f6;
}
.rec-item {
    background: #f0fdf4; border-radius: 6px; padding: 8px 12px;
    margin: 4px 0; font-size: 14px; border-left: 3px solid #22c55e;
}
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] { padding: 8px 20px; border-radius: 8px 8px 0 0; }
section[data-testid="stSidebar"] { min-width: 260px; max-width: 300px; }
</style>
""", unsafe_allow_html=True)

def dsi_color(v):
    if v >= 75: return "#16a34a"
    if v >= 55: return "#d97706"
    if v >= 40: return "#ea580c"
    return "#dc2626"

# ── 데이터 로드
@st.cache_resource
def load_model():
    with open("models/dsi_model.pkl", "rb") as f:
        model = pickle.load(f)
    with open("models/scaler.pkl", "rb") as f:
        scaler = pickle.load(f)
    with open("models/feature_meta.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    return model, scaler, meta

@st.cache_data(ttl=600)
def load_data():
    df, alerts = run_full_pipeline()
    return df, alerts

# ── 사이드바
with st.sidebar:
    st.markdown("## 🌐 G-DIAS")
    st.caption("Global Democratic Integrity Automated System")
    st.divider()
    try:
        model, scaler, meta = load_model()
        st.success(f"✅ 모델 로드 완료\nCV MAE: {meta.get('model_cv_mae', 0):.2f}")
    except FileNotFoundError:
        st.error("모델 없음\npython src/train_dsi_model.py 실행 필요")
        st.stop()
    st.divider()
    st.markdown("#### 필터")
    min_dsi, max_dsi = st.slider("DSI 범위", 0, 100, (0, 100))
    show_alerts_only = st.checkbox("경보 국가만 표시", value=False)
    st.divider()
    st.markdown("#### DSI 기준표")
    st.markdown("🟢 **안정** 75점 이상\n\n🟡 **주의** 55~74점\n\n🟠 **위험** 40~54점\n\n🔴 **위기** 0~39점")
    st.divider()
    st.caption(f"업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ── 데이터 준비
with st.spinner("데이터 로드 중..."):
    try:
        df, alerts = load_data()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        st.stop()

alert_dict = {}
for a in (alerts or []):
    iso = a.iso3 if hasattr(a, 'iso3') else a.get('iso3', '')
    if iso not in alert_dict:
        alert_dict[iso] = []
    alert_dict[iso].append(a.__dict__ if hasattr(a, '__dict__') else a)

df_display = df[(df["dsi"] >= min_dsi) & (df["dsi"] <= max_dsi)].copy()
if show_alerts_only:
    df_display = df_display[df_display["iso3"].isin(alert_dict.keys())]

global_avg = float(df["dsi"].mean())

# ── 헤더
st.markdown("# 🌐 G-DIAS · 민주주의 리스크 실시간 분석")
st.caption("Global Democratic Integrity Automated System — 100% Quantitative · Human-Free · Open-Source")

sev_count = {}
for a in (alerts or []):
    s = a.severity if hasattr(a, 'severity') else a.get('severity', '')
    sev_count[s] = sev_count.get(s, 0) + 1

m1, m2, m3, m4, m5 = st.columns(5)
with m1: st.metric("🌍 모니터링 국가", f"{len(df)}개국")
with m2: st.metric("📊 글로벌 평균 DSI", f"{global_avg:.1f}")
with m3: st.metric("🔴 CRITICAL", sev_count.get("CRITICAL", 0))
with m4: st.metric("🟠 WARNING", sev_count.get("WARNING", 0))
with m5: st.metric("⚠️ 고위험 국가", f"{(df['dsi'] < 45).sum()}개국")

st.markdown("---")

# ── 탭
tab_map, tab_rank, tab_alerts, tab_report, tab_global, tab_sources, tab_regime, tab_conflict = st.tabs([
    "🗺️  세계 지도",
    "📊  국가 순위",
    "🚨  경보 로그",
    "🔬  국가 분석 보고서",
    "🌐  글로벌 요약",
    "📡  데이터 소스",
    "🏛️  레짐 분석",
    "⚔️  분쟁 모니터",
])

# ── TAB 1: 세계 지도
with tab_map:
    st.subheader("국가별 DSI 분포")
    st.caption("지도 위에 마우스를 올리면 상세 점수를 확인할 수 있습니다.")
    fig_map = px.choropleth(
        df, locations="iso3", color="dsi", hover_name="country",
        hover_data={"dsi": ":.1f", "iso3": False},
        color_continuous_scale=[
            [0.00, "#dc2626"], [0.30, "#ea580c"],
            [0.45, "#d97706"], [0.60, "#65a30d"],
            [0.75, "#16a34a"], [1.00, "#064e3b"],
        ],
        range_color=(0, 100), labels={"dsi": "DSI 점수"},
    )
    fig_map.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=10, b=0),
        coloraxis_colorbar=dict(
            title="DSI 점수",
            tickvals=[0, 30, 45, 55, 75, 100],
            ticktext=["0\n위기", "30", "45\n위험", "55\n주의", "75\n안정", "100"],
            len=0.75, thickness=15,
        ),
        geo=dict(showframe=False, showcoastlines=True,
                 coastlinecolor="#cbd5e1", landcolor="#f1f5f9",
                 oceancolor="#dbeafe", showocean=True),
    )
    st.plotly_chart(fig_map, use_container_width=True)

    lc1, lc2, lc3, lc4 = st.columns(4)
    with lc1: st.markdown("🟢 **안정** (DSI 75+)")
    with lc2: st.markdown("🟡 **주의** (DSI 55~74)")
    with lc3: st.markdown("🟠 **위험** (DSI 40~54)")
    with lc4: st.markdown("🔴 **위기** (DSI 0~39)")

# ── TAB 2: 국가 순위
with tab_rank:
    st.subheader("국가별 DSI 종합 순위")
    df_sorted = df_display.sort_values("dsi", ascending=False).reset_index(drop=True)

    bar_colors = [dsi_color(v) for v in df_sorted["dsi"]]
    fig_bar = go.Figure(go.Bar(
        x=df_sorted["dsi"].round(1),
        y=df_sorted["country"],
        orientation="h",
        marker_color=bar_colors,
        text=[f"{v:.1f}" for v in df_sorted["dsi"]],
        textposition="outside",
        textfont=dict(size=12),
        hovertemplate="<b>%{y}</b><br>DSI: %{x:.1f}<extra></extra>",
    ))
    fig_bar.add_vline(
        x=global_avg, line_dash="dash", line_color="#6366f1", line_width=1.5,
        annotation_text=f" 글로벌 평균 {global_avg:.1f}",
        annotation_position="top", annotation_font=dict(color="#6366f1", size=12),
    )
    fig_bar.update_layout(
        height=max(520, len(df_sorted) * 32 + 100),
        xaxis=dict(range=[0, 112], title="DSI 점수 (0~100)",
                   showgrid=True, gridcolor="#f1f5f9", zeroline=False),
        yaxis=dict(autorange="reversed", tickfont=dict(size=12)),
        margin=dict(l=20, r=70, t=30, b=50),
        plot_bgcolor="white", showlegend=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    st.subheader("5대 차원 레이더 비교")
    st.caption("최대 5개국까지 선택해 비교할 수 있습니다.")

    all_cn = df_sorted["country"].tolist()
    defaults = [c for c in ["Sweden", "United States", "Turkey", "India"] if c in all_cn]
    sel_compare = st.multiselect("비교 국가", all_cn, default=defaults[:4], max_selections=5)

    if sel_compare:
        dim_cols = ["dim_electoral","dim_judicial","dim_media","dim_civil","dim_exec_constraints"]
        dim_labels_r = ["선거 무결성","사법 독립성","언론 자유","시민사회","행정부 견제"]
        pal = ["#3b82f6","#ef4444","#f59e0b","#10b981","#8b5cf6"]

        fig_radar = go.Figure()
        for i, cn in enumerate(sel_compare):
            row = df[df["country"] == cn]
            if row.empty: continue
            vals = [float(row[c].iloc[0]) if c in row.columns else 50 for c in dim_cols]
            fig_radar.add_trace(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=dim_labels_r + [dim_labels_r[0]],
                fill="toself", name=cn,
                line=dict(color=pal[i % len(pal)], width=2), opacity=0.55,
            ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100],
                                tickfont=dict(size=11), gridcolor="#e2e8f0"),
                angularaxis=dict(tickfont=dict(size=12)),
            ),
            legend=dict(orientation="h", yanchor="bottom", y=-0.18,
                        xanchor="center", x=0.5, font=dict(size=12)),
            height=500, margin=dict(l=60, r=60, t=40, b=100),
        )
        st.plotly_chart(fig_radar, use_container_width=True)

# ── TAB 3: 경보 로그
with tab_alerts:
    st.subheader("활성 경보 로그")

    if not alerts:
        st.info("현재 활성 경보가 없습니다.")
    else:
        sev_filter = st.radio(
            "심각도 필터", ["전체", "CRITICAL", "WARNING", "WATCH"],
            horizontal=True,
        )
        sev_icon = {"CRITICAL":"🔴","WARNING":"🟠","WATCH":"🟡","INFO":"🔵"}
        sev_cls  = {"CRITICAL":"alert-critical","WARNING":"alert-warning",
                    "WATCH":"alert-watch","INFO":"alert-watch"}

        filtered = alerts if sev_filter == "전체" else [
            a for a in alerts
            if (a.severity if hasattr(a, 'severity') else a.get('severity','')) == sev_filter
        ]
        st.caption(f"표시 중: {len(filtered)}건 / 전체 {len(alerts)}건")
        st.markdown("")

        for a in sorted(filtered, key=lambda x:
                {"CRITICAL":0,"WARNING":1,"WATCH":2,"INFO":3}[
                    x.severity if hasattr(x,'severity') else x.get('severity','INFO')]):
            sev     = a.severity if hasattr(a,'severity') else a.get('severity','')
            country = a.country  if hasattr(a,'country')  else a.get('country','')
            title   = a.title    if hasattr(a,'title')    else a.get('title','')
            msg     = a.message  if hasattr(a,'message')  else a.get('message','')
            dsi_c   = a.dsi_current if hasattr(a,'dsi_current') else a.get('dsi_current',0)
            dsi_d   = a.dsi_delta   if hasattr(a,'dsi_delta')   else a.get('dsi_delta',0)
            icon    = sev_icon.get(sev, "⚪")
            cls     = sev_cls.get(sev, "alert-watch")
            delta_color = "#dc2626" if dsi_d < 0 else "#16a34a"
            st.markdown(f"""
<div class="alert-box {cls}">
  <strong>{icon} [{sev}] &nbsp; {country}</strong>
  &nbsp;|&nbsp; DSI {dsi_c:.1f}
  &nbsp;<span style="color:{delta_color};font-weight:600">Δ{dsi_d:+.1f}</span><br>
  <span style="font-weight:600">{title}</span><br>
  <span style="font-size:13px;color:#475569">{msg}</span>
</div>""", unsafe_allow_html=True)

# ── TAB 4: 국가 분석 보고서
with tab_report:
    st.subheader("🤖 AI 국가별 민주주의 분석 보고서")
    st.caption("Claude AI가 V-Dem 지표 데이터를 바탕으로 생성한 전문 분석 보고서입니다.")
    st.markdown("")

    country_list = df.sort_values("dsi", ascending=False)["country"].tolist()
    sel_col, btn_col = st.columns([4, 1])
    with sel_col:
        selected_country = st.selectbox("분석 국가 선택", country_list)
    with btn_col:
        st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
        gen_btn = st.button("📝 보고서 생성", type="primary", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    if selected_country:
        row = df[df["country"] == selected_country].iloc[0]
        iso3    = row.get("iso3", "")
        dsi_val = float(row["dsi"])
        dim_map = {"electoral":"dim_electoral","judicial":"dim_judicial",
                   "media":"dim_media","civil":"dim_civil","exec_constraints":"dim_exec_constraints"}
        dims_val = {k: float(row[v]) if v in row.index else 50.0 for k, v in dim_map.items()}
        c_alerts = alert_dict.get(iso3, [])

        # 기본 현황 메트릭
        mc1, mc2, mc3, mc4 = st.columns(4)
        df_rank = df.sort_values("dsi", ascending=False).reset_index(drop=True)
        rank_num = df_rank[df_rank["country"] == selected_country].index[0] + 1
        with mc1: st.metric("DSI 점수", f"{dsi_val:.1f} / 100")
        with mc2: st.metric("글로벌 평균 대비", f"{dsi_val - global_avg:+.1f}pt")
        with mc3: st.metric("글로벌 순위", f"{rank_num}위 / {len(df)}개국")
        with mc4: st.metric("활성 경보", f"{len(c_alerts)}건")

        st.markdown("")

        # 차원 점수 차트
        st.markdown("#### 5대 차원 점수")
        dim_label_ko = {"electoral":"선거 무결성","judicial":"사법 독립성",
                        "media":"언론 자유","civil":"시민사회","exec_constraints":"행정부 견제"}
        dim_df = pd.DataFrame({
            "차원": [dim_label_ko[k] for k in dims_val],
            "점수": [round(v, 1) for v in dims_val.values()],
        })
        fig_dim = px.bar(
            dim_df, x="점수", y="차원", orientation="h",
            range_x=[0, 100], text="점수",
            color="점수",
            color_continuous_scale=["#dc2626","#ea580c","#d97706","#65a30d","#16a34a"],
            range_color=[0, 100],
        )
        fig_dim.update_traces(
            texttemplate="%{text:.1f}", textposition="outside", textfont=dict(size=13))
        fig_dim.update_layout(
            height=280, coloraxis_showscale=False, plot_bgcolor="white",
            xaxis=dict(title="점수", range=[0,112], showgrid=True, gridcolor="#f1f5f9"),
            yaxis=dict(title="", tickfont=dict(size=13)),
            margin=dict(l=10, r=70, t=10, b=30),
        )
        st.plotly_chart(fig_dim, use_container_width=True)

        # 트렌드 차트
        history_store = DSIHistoryStore()
        history = history_store.get_recent(iso3, 13)
        if history:
            hist_df = pd.DataFrame(history)
            hist_df["date"] = pd.to_datetime(
                hist_df["ts"], format="ISO8601", utc=True
            ).dt.strftime("%m월")
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=hist_df["date"], y=hist_df["dsi"].round(1),
                mode="lines+markers",
                line=dict(color=dsi_color(dsi_val), width=2.5),
                marker=dict(size=7),
                fill="tozeroy", fillcolor="rgba(22,163,74,0.13)",
                hovertemplate="%{x}: DSI %{y:.1f}<extra></extra>",
            ))
            fig_trend.add_hline(
                y=global_avg, line_dash="dot", line_color="#6366f1",
                annotation_text=f" 글로벌 평균 {global_avg:.1f}",
                annotation_font=dict(color="#6366f1", size=11),
            )
            fig_trend.update_layout(
                title=dict(text=f"{selected_country} — 12개월 DSI 추이", font=dict(size=14)),
                height=270, plot_bgcolor="white",
                yaxis=dict(range=[0,100], title="DSI", showgrid=True, gridcolor="#f1f5f9"),
                xaxis=dict(title="", showgrid=False),
                margin=dict(l=20, r=20, t=45, b=30),
                showlegend=False,
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        # AI 보고서
        st.markdown("#### 🤖 AI 분석 보고서")
        report_key = f"report_{iso3}"

        if gen_btn or report_key in st.session_state:
            if report_key not in st.session_state or gen_btn:
                with st.spinner(f"'{selected_country}' 분석 보고서 생성 중..."):
                    report = generate_country_report(
                        country=selected_country, iso3=iso3,
                        dsi=dsi_val, dims=dims_val,
                        alerts=c_alerts, global_avg=global_avg,
                    )
                    st.session_state[report_key] = report

            report = st.session_state[report_key]
            risk_ko = {"STABLE":"🟢 안정","CAUTION":"🟡 주의",
                       "WARNING":"🟠 위험","CRITICAL":"🔴 위기"}
            st.markdown(f"**위험 수준:** {risk_ko.get(report.risk_level, report.risk_level)}")
            st.markdown(f'<div class="report-box">{report.report_ko}</div>',
                        unsafe_allow_html=True)

            st.markdown("")
            fc, rc = st.columns(2)
            with fc:
                st.markdown("**🔍 핵심 발견사항**")
                for item in report.key_findings:
                    st.markdown(f'<div class="finding-item">• {item}</div>',
                                unsafe_allow_html=True)
            with rc:
                st.markdown("**💡 정책 권고사항**")
                for item in report.recommendations:
                    st.markdown(f'<div class="rec-item">• {item}</div>',
                                unsafe_allow_html=True)
        else:
            st.info("위 **보고서 생성** 버튼을 클릭하면 AI가 상세 분석 보고서를 작성합니다.")

# ── TAB 5: 글로벌 요약
with tab_global:
    st.subheader("🌐 글로벌 민주주의 현황")

    if st.button("🌐 AI 글로벌 요약 생성", type="primary"):
        with st.spinner("글로벌 현황 분석 중..."):
            summary_text = generate_global_summary(df, alerts or [], global_avg)
            st.session_state["global_summary"] = summary_text

    if "global_summary" in st.session_state:
        st.markdown(f'<div class="report-box">{st.session_state["global_summary"]}</div>',
                    unsafe_allow_html=True)
        st.markdown("")
    else:
        st.info("버튼을 클릭하면 AI가 현재 글로벌 민주주의 동향을 분석합니다.")

    st.markdown("---")
    st.subheader("DSI 점수 분포")
    fig_hist = px.histogram(
        df, x="dsi", nbins=20,
        labels={"dsi":"DSI 점수","count":"국가 수"},
        color_discrete_sequence=["#6366f1"],
    )
    fig_hist.add_vline(x=global_avg, line_dash="dash", line_color="#ef4444",
                       annotation_text=f" 평균 {global_avg:.1f}",
                       annotation_font=dict(color="#ef4444", size=12))
    fig_hist.update_layout(
        height=300, plot_bgcolor="white", bargap=0.1,
        xaxis=dict(range=[0,100], title="DSI 점수", showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(title="국가 수", showgrid=True, gridcolor="#f1f5f9"),
        margin=dict(l=20, r=20, t=20, b=40),
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("---")
    st.subheader("상위 5 vs 하위 5개국")
    top5 = df.nlargest(5,"dsi")[["country","dsi"]].reset_index(drop=True)
    bot5 = df.nsmallest(5,"dsi")[["country","dsi"]].reset_index(drop=True)

    tc, bc = st.columns(2)
    with tc:
        st.markdown("##### 🟢 민주주의 상위 5개국")
        for _, r in top5.iterrows():
            st.markdown(f"**{r['country']}** &nbsp; DSI {r['dsi']:.1f}")
    with bc:
        st.markdown("##### 🔴 민주주의 하위 5개국")
        for _, r in bot5.iterrows():
            st.markdown(f"**{r['country']}** &nbsp; DSI {r['dsi']:.1f}")


# ── TAB 6: 데이터 소스 투명성
with tab_sources:
    st.subheader("📡 수집 데이터 출처 및 방법론")
    st.caption("G-DIAS는 아래 1차 공개 데이터만 사용합니다. 언론 보도·전문가 설문·편집된 지수는 사용하지 않습니다.")
    st.markdown("")

    src_data = [
        {"소스": "World Bank WGI", "지표": "언론자유, 법치주의, 부패통제, 정부효과성, 정치안정, 규제품질",
         "갱신": "연 1회", "스케일": "-2.5~+2.5 → 0~100",
         "원본 URL": "https://databank.worldbank.org/source/worldwide-governance-indicators",
         "사용 차원": "electoral, judicial, media, civil, exec_constraints 전체"},
        {"소스": "Transparency International CPI", "지표": "부패인식지수 (2023)",
         "갱신": "연 1회", "스케일": "0~100",
         "원본 URL": "https://www.transparency.org/en/cpi/2023",
         "사용 차원": "judicial, exec_constraints, media"},
        {"소스": "International IDEA", "지표": "최근 국회의원/대통령 선거 투표율 (%)",
         "갱신": "선거 시", "스케일": "0~100%",
         "원본 URL": "https://www.idea.int/data-tools/data/voter-turnout",
         "사용 차원": "electoral"},
        {"소스": "UN E-Government Index", "지표": "전자정부 발전 지수 (2022)",
         "갱신": "격년", "스케일": "0~1 → 0~100",
         "원본 URL": "https://publicadministration.un.org/egovkb/",
         "사용 차원": "civil"},
        {"소스": "V-Dem Institute (선택적)", "지표": "20개 민주주의 세부 변수 (CSV 제공 시)",
         "갱신": "연 1회", "스케일": "자체 스케일 → 0~100",
         "원본 URL": "https://v-dem.net/data/the-v-dem-dataset/",
         "사용 차원": "전체 (CSV 있을 때 우선 사용)"},
    ]
    st.dataframe(
        pd.DataFrame(src_data).set_index("소스"),
        use_container_width=True, height=230,
    )

    st.markdown("---")
    st.subheader("📐 DSI 차원 계산 공식")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.markdown("""
**Electoral Integrity (선거 무결성)**

**Judicial Independence (사법 독립성)**

**Media Pluralism (언론 자유)**

        """)
    with col_f2:
        st.markdown("""
**Civil Society (시민사회)**

**Executive Constraints (행정부 견제)**

**DSI 종합 점수**

        """)

    st.markdown("---")
    st.subheader("⚠️ 데이터 한계 및 주의사항")
    st.warning("""
- **러시아 투표율**: 공식 발표치 사용 (독립 검증 불가). 높은 투표율이 선거 자유도를 의미하지 않음.
- **중국**: 전인대 직접선거 없음 → 투표율 항목 제외, 나머지 지표로 계산.
- **WGI 갱신 지연**: World Bank WGI는 1~2년 지연 발표. 현재 2022년 데이터 사용.
- **CPI 한계**: TI CPI는 인식 기반 설문 포함 — 완전한 1차 데이터가 아님을 명시.
- 이 시스템은 **조기 경보 도구**이며 국가에 대한 최종 판단이 아님.
    """)

    # 캐시 상태 표시
    import os, json
    cache_path = "data/live_data_cache.json"
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            cache_meta = json.load(f)
        st.info(f"마지막 데이터 수집: {cache_meta.get('fetched_at', '알 수 없음')[:19]} UTC")
        if st.button("🔄 데이터 강제 갱신"):
            from data_collector import collect
            with st.spinner("실시간 데이터 수집 중..."):
                collect(force=True)
            st.success("갱신 완료! 페이지를 새로고침하세요.")
    else:
        st.info("캐시 없음 — 다음 실행 시 자동 수집됩니다.")

st.markdown("---")
st.caption("G-DIAS PoC v3 · Mozilla Democracy × AI Cohort 2026 · V-Dem 기반 시뮬레이션 · XGBoost 20 features · 보고서: Claude AI")


# ── TAB 7: 레짐 분석 ─────────────────────────
with tab_regime:
    st.subheader("🏛️ 레짐 유형 분석 — 민주주의 파사드 탐지")
    st.caption("국가명·공식 명칭과 실제 통치 구조의 괴리를 정량화합니다.")

    from regime_classifier import get_all_regimes, REGIME_COLORS, REGIME_TYPE_LABELS
    regimes = get_all_regimes()

    type_counts = {}
    for r in regimes:
        type_counts[r.regime_label_ko] = type_counts.get(r.regime_label_ko, 0) + 1
    fig_types = px.pie(
        names=list(type_counts.keys()),
        values=list(type_counts.values()),
        title="레짐 유형 분포",
        color_discrete_sequence=px.colors.qualitative.Set2,
        hole=0.35,
    )
    fig_types.update_layout(height=300, margin=dict(l=10,r=10,t=40,b=10))

    rp_data = []
    for r in regimes:
        dsi_row = df[df["iso3"] == r.iso3]
        dsi_v2 = float(dsi_row["dsi"].iloc[0]) if not dsi_row.empty else 50.0
        rp_data.append({
            "국가": r.country, "iso3": r.iso3,
            "DSI": dsi_v2, "RPI": r.rpi_total,
            "파사드": r.facade_score,
            "레짐": r.regime_label_ko,
            "이름괴리": r.name_reality_gap,
        })
    rdf = pd.DataFrame(rp_data)

    col_pie, col_scatter = st.columns([1, 2])
    with col_pie:
        st.plotly_chart(fig_types, use_container_width=True)
    with col_scatter:
        fig_sc = px.scatter(
            rdf, x="DSI", y="RPI",
            color="레짐", size="파사드",
            hover_name="국가",
            hover_data={"DSI":":.1f","RPI":":.1f","파사드":":.0f","이름괴리":":.0f"},
            title="DSI vs RPI — 버블 크기: 파사드(허울) 점수",
            size_max=38,
            labels={"DSI":"민주주의 지수 (DSI)","RPI":"공화주의 원칙지수 (RPI)"},
        )
        fig_sc.add_shape(type="line",x0=0,y0=0,x1=100,y1=100,
                         line=dict(dash="dot",color="#94a3b8",width=1))
        fig_sc.add_annotation(x=80,y=87,text="DSI=RPI 균형선",
                              font=dict(size=10,color="#94a3b8"),showarrow=False)
        fig_sc.update_layout(height=340, plot_bgcolor="white",
                             margin=dict(l=20,r=20,t=40,b=30))
        st.plotly_chart(fig_sc, use_container_width=True)

    st.markdown("---")
    st.subheader("명칭-실체 괴리 TOP 국가")
    st.caption("국가명에 '민주주의'·'인민'·'공화국'을 쓰면서 실제로는 반민주적인 국가")
    gap_df = rdf[rdf["이름괴리"] > 15].sort_values("이름괴리", ascending=False)
    if not gap_df.empty:
        fig_gap = px.bar(
            gap_df, x="이름괴리", y="국가", orientation="h",
            color="이름괴리",
            color_continuous_scale=["#fbbf24","#f97316","#ef4444","#7f1d1d"],
            range_color=[15,100], text="이름괴리",
            title="명칭-실체 괴리 지수",
            labels={"이름괴리":"괴리 점수","국가":""},
        )
        fig_gap.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        fig_gap.update_layout(
            height=max(280, len(gap_df)*32+80),
            coloraxis_showscale=False, plot_bgcolor="white",
            xaxis=dict(range=[0,115], showgrid=True, gridcolor="#f1f5f9"),
            margin=dict(l=20,r=60,t=40,b=30),
        )
        st.plotly_chart(fig_gap, use_container_width=True)

    st.markdown("---")
    st.subheader("국가별 RPI 상세")
    sel_reg = st.selectbox("국가 선택 ", [r.country for r in sorted(regimes, key=lambda x: -x.rpi_total)], key="reg_sel")
    r = next((x for x in regimes if x.country == sel_reg), None)
    if r:
        mc1,mc2,mc3,mc4 = st.columns(4)
        with mc1: st.metric("RPI 종합", f"{r.rpi_total:.1f}")
        with mc2: st.metric("레짐 유형", r.regime_label_ko)
        with mc3: st.metric("파사드 점수", f"{r.facade_score:.0f}")
        with mc4: st.metric("이름-실체 괴리", f"{r.name_reality_gap:.0f}")

        rpi_d = {"권력분립":r.rpi_separation_of_powers,"임기제한":r.rpi_term_limits,
                 "헌법우위":r.rpi_constitutional_supremacy,"분권화":r.rpi_decentralization,
                 "정치경쟁":r.rpi_political_competition}
        fig_rpi = px.bar(
            x=list(rpi_d.values()), y=list(rpi_d.keys()), orientation="h",
            range_x=[0,100], text=[f"{v:.0f}" for v in rpi_d.values()],
            color=list(rpi_d.values()),
            color_continuous_scale=["#dc2626","#d97706","#16a34a"],
            range_color=[0,100], title=f"{sel_reg} — 공화주의 5대 원칙",
        )
        fig_rpi.update_traces(textposition="outside")
        fig_rpi.update_layout(height=260, coloraxis_showscale=False, plot_bgcolor="white",
                              xaxis=dict(range=[0,112],showgrid=True,gridcolor="#f1f5f9"),
                              margin=dict(l=10,r=60,t=40,b=30))
        st.plotly_chart(fig_rpi, use_container_width=True)

        if r.facade_evidence:
            st.markdown("**🚩 파사드 근거**")
            for ev in r.facade_evidence:
                st.markdown(f"- {ev}")
        if r.analyst_notes:
            st.info(r.analyst_notes)

# ── TAB 8: 분쟁 모니터 ──────────────────────
with tab_conflict:
    st.subheader("⚔️ 분쟁 모니터 — 민주주의 지표 왜곡 분석")
    st.caption("전쟁·분쟁은 민주주의 지표를 왜곡합니다. 맥락 없는 점수 비교는 분석 오류입니다.")
    st.caption("출처: ACLED 2024, UCDP 2024, OCHA, UNHCR, Human Rights Watch, ICG")

    from conflict_monitor import CONFLICT_DB, get_active_conflicts

    active_c = get_active_conflicts()
    st.markdown(f"**현재 모니터링: {len(CONFLICT_DB)}개 분쟁 | 활성: {len(active_c)}건**")
    st.markdown("")

    conf_rows = [{"국가":c.country,"iso3":c.iso3,"강도":c.intensity,
                  "지표왜곡":c.distortion_factor,"유형":", ".join(c.conflict_type[:2]),
                  "상태":c.status} for c in CONFLICT_DB.values()]
    conf_df2 = pd.DataFrame(conf_rows).sort_values("강도", ascending=False)

    fig_conf = px.bar(
        conf_df2, x="강도", y="국가", orientation="h",
        color="강도",
        color_continuous_scale=["#fef9c3","#f97316","#ef4444","#7f1d1d"],
        range_color=[0,100], text="강도",
        title="분쟁 강도 지수 (0=평화, 100=전면전)",
        labels={"강도":"분쟁 강도","국가":""},
    )
    fig_conf.update_traces(texttemplate="%{text:.0f}", textposition="outside")
    fig_conf.update_layout(
        height=max(320, len(conf_df2)*30+80),
        coloraxis_showscale=False, plot_bgcolor="white",
        xaxis=dict(range=[0,115],showgrid=True,gridcolor="#f1f5f9"),
        margin=dict(l=20,r=60,t=50,b=30),
    )
    st.plotly_chart(fig_conf, use_container_width=True)

    st.markdown("---")
    st.subheader("분쟁별 상세 현황 및 민주주의 지표 왜곡")
    dim_ko = {"electoral":"선거무결성","judicial":"사법독립","media":"언론자유",
              "civil":"시민사회","exec_constraints":"행정견제"}

    for c in sorted(CONFLICT_DB.values(), key=lambda x: -x.intensity):
        icon = "🔴" if c.intensity>70 else "🟠" if c.intensity>40 else "🟡"
        with st.expander(
            f"{icon} **{c.country}** — 강도 {c.intensity:.0f} | 왜곡 {c.distortion_factor:.0f}% | {c.status}"
        ):
            d1, d2 = st.columns(2)
            with d1:
                st.markdown(f"**분쟁 유형:** {', '.join(c.conflict_type)}")
                st.markdown(f"**시작 연도:** {c.start_year}년")
                st.markdown(f"**주요 당사자:** {', '.join(c.parties[:4])}")
                if c.international_involvement:
                    st.markdown(f"**외부 개입:** {', '.join(c.international_involvement[:3])}")
            with d2:
                st.markdown(f"**민간인 피해:** {c.civilian_impact[:120]}...")
                if c.displacement:
                    st.markdown(f"**실향·난민:** {c.displacement}")

            if c.affected_dimensions:
                warp_items = [f"{dim_ko.get(d,d)} {v:+.0f}pt" for d,v in c.affected_dimensions.items()]
                st.warning(f"⚠️ 지표 왜곡: {' | '.join(warp_items)}")
            if getattr(c, 'conflict_notes', None):
                st.info(getattr(c, 'conflict_notes', ''))
            st.caption(f"출처: {', '.join(c.sources[:2])}")

    st.markdown("---")
    st.markdown("""
**보정 원칙:**
- 🟦 **피침략국** (우크라이나): 전시 민주주의 제한은 침략의 결과 → 상향 보정
- 🟥 **침략 수행국** (러시아): 전쟁 개시 책임 → 추가 하향 보정
- 🟧 **내전·테러국**: 분쟁 강도 비례 왜곡 계수, 맥락 명시
- ⬛ **점령지** (팔레스타인): 민주주의 지표 적용 자체가 부적절 — 별도 표기
    """)
