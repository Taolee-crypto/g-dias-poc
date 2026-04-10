"""
alert_engine.py - G-DIAS 경보 시스템

경보 로직:
  - 30일 이동평균 기반 DSI 급락 감지
  - 차원별 임계값 위반 감지
  - 복합 지표 동시 하락 감지 (취약 신호)
  - 심각도: CRITICAL / WARNING / WATCH / INFO
"""

import json
import pickle
import numpy as np
import pandas as pd
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from vdem_features import (
    VDemLoader, ALL_FEATURES, DIMENSION_WEIGHTS,
    compute_dimension_scores
)


# ─────────────────────────────────────────────
#  경보 데이터 클래스
# ─────────────────────────────────────────────

@dataclass
class Alert:
    iso3: str
    country: str
    severity: str           # CRITICAL / WARNING / WATCH / INFO
    alert_type: str         # 경보 유형 코드
    title: str              # 짧은 제목
    message: str            # 상세 메시지
    dsi_current: float
    dsi_previous: float     # 30일 전 값 (또는 기준점)
    dsi_delta: float        # 변화량
    triggered_dims: list    # 문제가 감지된 차원들
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self):
        return asdict(self)


# ─────────────────────────────────────────────
#  임계값 정의
# ─────────────────────────────────────────────

THRESHOLDS = {
    # DSI 절대값 임계
    "dsi_critical":  30,    # CRITICAL: 민주주의 심각 위기
    "dsi_warning":   45,    # WARNING: 위험 구간
    "dsi_watch":     60,    # WATCH: 주의 필요

    # DSI 변화량 임계 (30일 기준)
    "delta_critical": -8.0,  # CRITICAL: 급락
    "delta_warning":  -5.0,  # WARNING: 빠른 하락
    "delta_watch":    -3.0,  # WATCH: 하락 추세

    # 차원별 임계
    "dim_critical":   25,    # 특정 차원이 이 이하
    "dim_warning":    40,

    # 복합 지표: N개 차원 동시 하락
    "multi_dim_warning":  3,   # 3개 이상 차원 동시 하락이면 WARNING
    "multi_dim_watch":    2,
}


# ─────────────────────────────────────────────
#  DSI 히스토리 시뮬레이터 (Kafka 대체)
# ─────────────────────────────────────────────

class DSIHistoryStore:
    """
    국가별 DSI 시계열 저장소.
    실제 환경에서는 Redis/TimescaleDB로 교체.
    현재는 인메모리 + JSON 파일 영속성.
    """

    def __init__(self, path: str = "data/dsi_history.json"):
        self.path = path
        self.store: dict = {}  # {iso3: [(timestamp, dsi, dims_dict), ...]}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                self.store = json.load(f)

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.store, f, indent=2)

    def push(self, iso3: str, dsi: float, dims: dict, ts: str = None):
        if iso3 not in self.store:
            self.store[iso3] = []
        ts = ts or datetime.now(timezone.utc).isoformat()
        self.store[iso3].append({"ts": ts, "dsi": dsi, "dims": dims})
        # 최근 90일치만 유지 (일별 기준 90개)
        if len(self.store[iso3]) > 90:
            self.store[iso3] = self.store[iso3][-90:]

    def get_recent(self, iso3: str, n: int = 30) -> list:
        return self.store.get(iso3, [])[-n:]

    def get_30d_ago(self, iso3: str) -> Optional[dict]:
        history = self.store.get(iso3, [])
        if len(history) < 2:
            return None
        return history[max(0, len(history) - 30)]

    def seed_history(self, df: pd.DataFrame, dsi_scores: np.ndarray, dim_scores_df: pd.DataFrame):
        """초기 히스토리 시드: 12개월치 시뮬레이션"""
        rng = np.random.default_rng(42)
        for i, row in df.iterrows():
            iso3 = row.get("iso3", f"C{i:03d}")
            base_dsi = float(dsi_scores[i])
            # 각 국가에 맞는 월별 트렌드 (기울기)
            trend = rng.normal(0, 0.4)

            for day_offset in range(365, -1, -30):  # 12개월 전부터
                ts = (datetime.now(timezone.utc) - timedelta(days=day_offset)).isoformat()
                t = (365 - day_offset) / 365
                dsi = base_dsi - trend * (365 - day_offset) / 30
                dsi += rng.normal(0, 1.5)
                dsi = float(np.clip(dsi, 0, 100))

                dims = {}
                for dim in DIMENSION_WEIGHTS:
                    col = f"dim_{dim}"
                    if col in dim_scores_df.columns:
                        base_d = float(dim_scores_df.iloc[i][col])
                        dims[dim] = float(np.clip(base_d - trend * (365 - day_offset) / 30
                                                   + rng.normal(0, 2), 0, 100))
                self.push(iso3, dsi, dims, ts)

        self.save()
        print(f"[HistoryStore] {len(df)}개국 히스토리 시드 완료")


# ─────────────────────────────────────────────
#  경보 엔진
# ─────────────────────────────────────────────

class AlertEngine:
    """
    DSI 점수와 히스토리를 받아 경보를 생성.
    """

    def __init__(self, history_store: DSIHistoryStore):
        self.history = history_store
        self.alerts: list[Alert] = []

    def evaluate(self, iso3: str, country: str, dsi: float, dims: dict) -> list[Alert]:
        """단일 국가 평가 → 발생한 경보 리스트 반환"""
        new_alerts = []

        prev = self.history.get_30d_ago(iso3)
        dsi_prev = prev["dsi"] if prev else dsi
        delta = dsi - dsi_prev

        # ── 규칙 1: DSI 절대값 임계 위반
        if dsi < THRESHOLDS["dsi_critical"]:
            new_alerts.append(Alert(
                iso3=iso3, country=country,
                severity="CRITICAL",
                alert_type="ABS_CRITICAL",
                title=f"민주주의 위기 수준",
                message=f"DSI {dsi:.1f} — 심각한 민주주의 후퇴 구간 (기준: {THRESHOLDS['dsi_critical']})",
                dsi_current=dsi, dsi_previous=dsi_prev, dsi_delta=delta,
                triggered_dims=[d for d, v in dims.items() if v < THRESHOLDS["dim_critical"]],
            ))
        elif dsi < THRESHOLDS["dsi_warning"]:
            new_alerts.append(Alert(
                iso3=iso3, country=country,
                severity="WARNING",
                alert_type="ABS_WARNING",
                title="민주주의 위험 구간 진입",
                message=f"DSI {dsi:.1f} — 위험 구간 (기준: {THRESHOLDS['dsi_warning']})",
                dsi_current=dsi, dsi_previous=dsi_prev, dsi_delta=delta,
                triggered_dims=[],
            ))

        # ── 규칙 2: 30일 변화량 기반
        if delta <= THRESHOLDS["delta_critical"]:
            new_alerts.append(Alert(
                iso3=iso3, country=country,
                severity="CRITICAL",
                alert_type="DELTA_CRITICAL",
                title="DSI 급격한 하락",
                message=f"30일간 {delta:.1f}pt 하락 (임계: {THRESHOLDS['delta_critical']}pt)",
                dsi_current=dsi, dsi_previous=dsi_prev, dsi_delta=delta,
                triggered_dims=[],
            ))
        elif delta <= THRESHOLDS["delta_warning"]:
            new_alerts.append(Alert(
                iso3=iso3, country=country,
                severity="WARNING",
                alert_type="DELTA_WARNING",
                title="DSI 빠른 하락 추세",
                message=f"30일간 {delta:.1f}pt 하락 감지",
                dsi_current=dsi, dsi_previous=dsi_prev, dsi_delta=delta,
                triggered_dims=[],
            ))
        elif delta <= THRESHOLDS["delta_watch"]:
            new_alerts.append(Alert(
                iso3=iso3, country=country,
                severity="WATCH",
                alert_type="DELTA_WATCH",
                title="DSI 하락 추세 감지",
                message=f"30일간 {delta:.1f}pt 하락 — 지속 모니터링 필요",
                dsi_current=dsi, dsi_previous=dsi_prev, dsi_delta=delta,
                triggered_dims=[],
            ))

        # ── 규칙 3: 특정 차원 임계 위반
        for dim, score in dims.items():
            if score < THRESHOLDS["dim_critical"]:
                dim_label = {
                    "electoral": "선거 무결성",
                    "judicial":  "사법 독립성",
                    "media":     "언론 자유",
                    "civil":     "시민사회",
                    "exec_constraints": "행정부 견제"
                }.get(dim, dim)
                new_alerts.append(Alert(
                    iso3=iso3, country=country,
                    severity="CRITICAL",
                    alert_type=f"DIM_CRITICAL_{dim.upper()}",
                    title=f"{dim_label} 지수 위기",
                    message=f"{dim_label} 점수 {score:.1f} — 심각 임계치({THRESHOLDS['dim_critical']}) 이하",
                    dsi_current=dsi, dsi_previous=dsi_prev, dsi_delta=delta,
                    triggered_dims=[dim],
                ))

        # ── 규칙 4: 복합 하락 (여러 차원 동시 하락)
        if prev and prev.get("dims"):
            dims_prev = prev["dims"]
            declining_dims = [
                d for d in dims
                if d in dims_prev and dims[d] - dims_prev.get(d, dims[d]) < -3.0
            ]
            if len(declining_dims) >= THRESHOLDS["multi_dim_warning"]:
                new_alerts.append(Alert(
                    iso3=iso3, country=country,
                    severity="WARNING",
                    alert_type="MULTI_DIM_DECLINE",
                    title="복합 민주주의 지표 동시 하락",
                    message=(f"{len(declining_dims)}개 차원 동시 하락: "
                             f"{', '.join(declining_dims)}"),
                    dsi_current=dsi, dsi_previous=dsi_prev, dsi_delta=delta,
                    triggered_dims=declining_dims,
                ))

        # 중복 제거: 같은 iso3+type은 하나만
        seen = set()
        deduped = []
        for a in new_alerts:
            key = (a.iso3, a.alert_type)
            if key not in seen:
                seen.add(key)
                deduped.append(a)

        self.alerts.extend(deduped)
        return deduped

    def evaluate_all(self, df: pd.DataFrame, dsi_scores: np.ndarray,
                     dim_scores_df: pd.DataFrame) -> list[Alert]:
        """전체 국가 일괄 평가"""
        self.alerts = []
        for i, row in df.iterrows():
            iso3 = row.get("iso3", f"C{i:03d}")
            country = row.get("country", iso3)
            dsi = float(dsi_scores[i])
            dims = {
                dim: float(dim_scores_df.iloc[i][f"dim_{dim}"])
                for dim in DIMENSION_WEIGHTS
                if f"dim_{dim}" in dim_scores_df.columns
            }
            self.history.push(iso3, dsi, dims)
            self.evaluate(iso3, country, dsi, dims)

        return self.alerts

    def get_summary(self) -> dict:
        sev_count = {"CRITICAL": 0, "WARNING": 0, "WATCH": 0, "INFO": 0}
        for a in self.alerts:
            sev_count[a.severity] = sev_count.get(a.severity, 0) + 1
        return {
            "total_alerts": len(self.alerts),
            "by_severity": sev_count,
            "countries_alerted": len({a.iso3 for a in self.alerts}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def to_dataframe(self) -> pd.DataFrame:
        if not self.alerts:
            return pd.DataFrame()
        return pd.DataFrame([a.to_dict() for a in self.alerts]).sort_values(
            ["severity", "dsi_delta"],
            key=lambda s: s.map({"CRITICAL": 0, "WARNING": 1, "WATCH": 2, "INFO": 3})
            if s.name == "severity" else s
        )


# ─────────────────────────────────────────────
#  통합 실행
# ─────────────────────────────────────────────

def run_full_pipeline(vdem_csv: str = None, history_path: str = "data/dsi_history.json"):
    """
    V-Dem 로드 → 피처 추출 → DSI 예측 → 경보 평가 → 결과 출력
    """
    print("=" * 55)
    print("G-DIAS 전체 파이프라인 실행")
    print("=" * 55)

    # 1) 모델 로드
    model_path = "models/dsi_model.pkl"
    scaler_path = "models/scaler.pkl"
    if not os.path.exists(model_path):
        print("[ERROR] 모델 없음. 먼저 train_dsi_model.py 실행하세요.")
        return None, None

    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(scaler_path, "rb") as f:
        scaler = pickle.load(f)

    # 2) 데이터 로드 및 피처 계산
    loader = VDemLoader(vdem_csv)
    df = loader.load()
    df = compute_dimension_scores(df)

    # 3) DSI 예측
    X = scaler.transform(df[ALL_FEATURES].values)
    dsi_scores = model.predict(X)
    df["dsi"] = dsi_scores.round(1)

    # 4) 히스토리 초기화
    history = DSIHistoryStore(history_path)
    if not history.store:
        print("[HistoryStore] 초기 히스토리 생성 중...")
        history.seed_history(df, dsi_scores, df)

    # 5) 경보 평가
    engine = AlertEngine(history)
    alerts = engine.evaluate_all(df, dsi_scores, df)
    history.save()

    # 6) 결과 출력
    summary = engine.get_summary()
    print(f"\n경보 요약:")
    print(f"  총 경보: {summary['total_alerts']}건")
    print(f"  CRITICAL: {summary['by_severity']['CRITICAL']}")
    print(f"  WARNING:  {summary['by_severity']['WARNING']}")
    print(f"  WATCH:    {summary['by_severity']['WATCH']}")
    print(f"  대상 국가: {summary['countries_alerted']}개국")

    if alerts:
        print("\n주요 경보 (상위 5개):")
        df_alerts = engine.to_dataframe()
        for _, row in df_alerts.head(5).iterrows():
            print(f"  [{row['severity']:8s}] {row['country']:20s} DSI={row['dsi_current']:.1f} "
                  f"Δ{row['dsi_delta']:+.1f}  {row['title']}")

    # JSON 저장
    alerts_out = [a.to_dict() for a in alerts]
    os.makedirs("data", exist_ok=True)
    with open("data/latest_alerts.json", "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "alerts": alerts_out}, f, ensure_ascii=False, indent=2)
    print("\n경보 결과 저장: data/latest_alerts.json")

    return df, alerts


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--vdem-csv", default=None)
    parser.add_argument("--history", default="data/dsi_history.json")
    args = parser.parse_args()
    run_full_pipeline(args.vdem_csv, args.history)
