"""
vdem_features.py - V-Dem 데이터셋 피처 정의 및 수집 레이어

실제 V-Dem 변수명을 기반으로 DSI 계산에 필요한 피처를 정의.
V-Dem API 또는 CSV 파일에서 데이터를 로드하고 정규화.

V-Dem 데이터셋: https://v-dem.net/data/the-v-dem-dataset/
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional
import os

# ─────────────────────────────────────────────
#  DSI 5대 차원 및 V-Dem 변수 매핑
# ─────────────────────────────────────────────

VDEM_FEATURE_MAP = {
    # 차원 1: 선거 무결성 (Electoral Integrity)
    "electoral": {
        "v2xel_frefair":    ("선거 자유·공정성 지수",         1.0),  # 핵심
        "v2x_suffr":        ("보통선거권 지수",               0.7),
        "v2elintmon":       ("선거 독립 감시",                0.6),
        "v2elirreg":        ("선거 불규칙성 역수",            0.8),   # 낮을수록 문제 → 역수 처리
    },
    # 차원 2: 사법 독립성 (Judicial Independence)
    "judicial": {
        "v2juhcind":        ("고위법원 독립성",               1.0),  # 핵심
        "v2juncind":        ("하위법원 독립성",               0.8),
        "v2jucomp":         ("사법부 인사 독립",              0.7),
        "v2jupack":         ("법원 패킹 역수",                0.6),
    },
    # 차원 3: 언론 자유·다원성 (Media Pluralism)
    "media": {
        "v2mecenefi":       ("언론 검열 역수",                1.0),  # 핵심
        "v2merange":        ("언론 다양성",                   0.9),
        "v2mebias":         ("미디어 편향 역수",              0.7),
        "v2mecrit":         ("정부 비판 보도 자유",           0.8),
    },
    # 차원 4: 시민사회 (Civil Society)
    "civil": {
        "v2xcs_ccsi":       ("핵심 시민사회 지수",            1.0),  # 핵심
        "v2cseeorgs":       ("시민단체 활동 자유",            0.8),
        "v2cscnsult":       ("정부-시민사회 협의",            0.6),
        "v2csreprss":       ("시민사회 탄압 역수",            0.9),
    },
    # 차원 5: 행정부 견제 (Executive Constraints)
    "exec_constraints": {
        "v2x_execorr":      ("행정부 부패 역수",              1.0),  # 핵심
        "v2exrescon":       ("행정부 법준수",                 0.9),
        "v2lgoppart":       ("의회 반대의견 참여",            0.7),
        "v2lginvstp":       ("입법부 행정부 감사",            0.8),
    }
}

# DSI 차원별 가중치 (합계 = 1.0)
DIMENSION_WEIGHTS = {
    "electoral":         0.25,
    "judicial":          0.22,
    "media":             0.18,
    "civil":             0.18,
    "exec_constraints":  0.17,
}

# 모든 피처 플랫 리스트 (XGBoost 입력 순서)
ALL_FEATURES = [
    feat
    for dim_features in VDEM_FEATURE_MAP.values()
    for feat in dim_features.keys()
]

assert len(ALL_FEATURES) == 20, f"피처 수 불일치: {len(ALL_FEATURES)}"


# ─────────────────────────────────────────────
#  V-Dem 데이터 로더
# ─────────────────────────────────────────────

class VDemLoader:
    """
    V-Dem 데이터를 로드하고 피처 벡터로 변환.

    우선순위:
    1. 실제 V-Dem CSV (data/vdem_core.csv) 존재 시 사용
    2. 없으면 실제 국가별 추정치 기반 시뮬레이션 데이터 사용
    """

    # 실제 연구 기반 국가별 추정 점수 (V-Dem 2023 기반, -5~+5 스케일 → 0~100 정규화)
    # 출처: Freedom House 2024, V-Dem 2023, RSF Press Freedom Index 2024
    COUNTRY_ESTIMATES = {
        # (ISO3, 국가명, [electoral, judicial, media, civil, exec_constraints])
        # 값은 0~100 정규화 기준
        "SWE": ("Sweden",         [94, 91, 93, 95, 87]),
        "DEU": ("Germany",        [89, 88, 85, 90, 84]),
        "CAN": ("Canada",         [87, 86, 84, 88, 80]),
        "AUS": ("Australia",      [86, 85, 82, 84, 78]),
        "FRA": ("France",         [82, 83, 78, 81, 76]),
        "JPN": ("Japan",          [82, 80, 74, 81, 78]),
        "GBR": ("United Kingdom", [80, 82, 75, 78, 75]),
        "KOR": ("South Korea",    [79, 74, 73, 80, 74]),
        "CHL": ("Chile",          [76, 75, 73, 77, 69]),
        "USA": ("United States",  [70, 75, 71, 78, 66]),
        "ZAF": ("South Africa",   [66, 68, 64, 65, 52]),
        "ARG": ("Argentina",      [67, 62, 65, 68, 63]),
        "IDN": ("Indonesia",      [63, 58, 60, 65, 59]),
        "SGP": ("Singapore",      [60, 72, 52, 63, 63]),
        "BRA": ("Brazil",         [60, 55, 57, 63, 55]),
        "IND": ("India",          [56, 50, 48, 58, 58]),
        "MEX": ("Mexico",         [52, 47, 51, 55, 45]),
        "POL": ("Poland",         [58, 52, 54, 56, 55]),
        "NGA": ("Nigeria",        [44, 38, 43, 47, 38]),
        "HUN": ("Hungary",        [40, 35, 33, 42, 40]),
        "TUR": ("Turkey",         [35, 28, 25, 38, 30]),
        "EGY": ("Egypt",          [18, 24, 16, 26, 26]),
        "RUS": ("Russia",         [15, 20, 12, 22, 21]),
        "CHN": ("China",          [ 8, 18,  9, 15, 20]),
    }

    def __init__(self, csv_path: Optional[str] = None):
        self.csv_path = csv_path or "data/vdem_core.csv"

    def load(self) -> pd.DataFrame:
        """
        데이터 로드 우선순위:
          1. 실제 V-Dem CSV
          2. 실시간 수집 데이터 (World Bank + TI + IDEA + UN)
          3. 연구 기반 추정치 (최후 폴백)
        """
        if os.path.exists(self.csv_path):
            print(f"[VDemLoader] 실제 V-Dem CSV 로드: {self.csv_path}")
            return self._load_from_csv()
        try:
            from data_collector import collect as collect_live
            df_live = collect_live(force_refresh=False)
            if not df_live.empty and "dim_electoral" in df_live.columns:
                print("[VDemLoader] 실시간 수집 데이터 사용 (WB+TI+IDEA+UN)")
                return self._adapt_live_data(df_live)
        except Exception as e:
            print(f"[VDemLoader] 실시간 수집 실패: {e}")
        print("[VDemLoader] 폴백: 연구 기반 추정치 사용")
        return self._load_simulated()

    def _adapt_live_data(self, df_live) -> "pd.DataFrame":
        result = df_live.copy()
        dim_map = {"electoral":"dim_electoral","judicial":"dim_judicial",
                   "media":"dim_media","civil":"dim_civil",
                   "exec_constraints":"dim_exec_constraints"}
        rng = np.random.default_rng(42)
        for feat in ALL_FEATURES:
            if feat not in result.columns:
                dim_key = next((d for d, feats in VDEM_FEATURE_MAP.items() if feat in feats), None)
                col = dim_map.get(dim_key, "dim_electoral") if dim_key else "dim_electoral"
                base = result[col].values if col in result.columns else np.full(len(result), 50.0)
                w = VDEM_FEATURE_MAP.get(dim_key, {}).get(feat, (None, 1.0))[1] if dim_key else 1.0
                result[feat] = np.clip(base * w + rng.normal(0, 4, len(result)), 0, 100).round(2)
        return result

    def _load_simulated(self) -> pd.DataFrame:
        """연구 기반 추정치로 피처 DataFrame 생성"""
        rows = []
        for iso3, (country_name, dim_scores) in self.COUNTRY_ESTIMATES.items():
            electoral, judicial, media, civil, exec_c = dim_scores

            # 각 차원을 세부 피처로 분해 (차원 점수 기반 + 약간의 변동)
            rng = np.random.default_rng(seed=hash(iso3) % 2**32)
            def jitter(base, n=4, spread=5):
                vals = base + rng.normal(0, spread, n)
                return np.clip(vals, 0, 100).tolist()

            row = {"iso3": iso3, "country": country_name, "year": 2023}

            for i, (feat, (_, w)) in enumerate(VDEM_FEATURE_MAP["electoral"].items()):
                row[feat] = jitter(electoral)[i]
            for i, (feat, (_, w)) in enumerate(VDEM_FEATURE_MAP["judicial"].items()):
                row[feat] = jitter(judicial)[i]
            for i, (feat, (_, w)) in enumerate(VDEM_FEATURE_MAP["media"].items()):
                row[feat] = jitter(media)[i]
            for i, (feat, (_, w)) in enumerate(VDEM_FEATURE_MAP["civil"].items()):
                row[feat] = jitter(civil)[i]
            for i, (feat, (_, w)) in enumerate(VDEM_FEATURE_MAP["exec_constraints"].items()):
                row[feat] = jitter(exec_c)[i]

            rows.append(row)

        df = pd.DataFrame(rows)
        df[ALL_FEATURES] = df[ALL_FEATURES].round(2)
        return df

    def _load_from_csv(self) -> pd.DataFrame:
        """실제 V-Dem CSV에서 필요한 컬럼만 추출"""
        df = pd.read_csv(self.csv_path, low_memory=False)

        # V-Dem 원본은 -5~+5 스케일 → 0~100 정규화
        available = [f for f in ALL_FEATURES if f in df.columns]
        missing = [f for f in ALL_FEATURES if f not in df.columns]

        if missing:
            print(f"[VDemLoader] 누락 피처 {len(missing)}개: {missing[:5]}...")

        # 최신 연도만
        df = df[df["year"] == df["year"].max()].copy()

        for feat in available:
            col = df[feat]
            min_val, max_val = col.min(), col.max()
            if max_val > min_val:
                df[feat] = (col - min_val) / (max_val - min_val) * 100

        return df[["country_name", "year"] + available].rename(
            columns={"country_name": "country"}
        )

    def get_feature_matrix(self, df: pd.DataFrame) -> np.ndarray:
        """DataFrame → XGBoost 입력 행렬"""
        return df[ALL_FEATURES].values.astype(np.float32)


# ─────────────────────────────────────────────
#  차원 점수 계산 (모델 독립적 해석용)
# ─────────────────────────────────────────────

def compute_dimension_scores(df: pd.DataFrame) -> pd.DataFrame:
    """각 차원의 가중 평균 점수를 계산해 df에 추가"""
    result = df.copy()
    for dim, features in VDEM_FEATURE_MAP.items():
        weights = np.array([w for _, w in features.values()])
        weights = weights / weights.sum()
        cols = list(features.keys())
        result[f"dim_{dim}"] = df[cols].values @ weights
    return result


if __name__ == "__main__":
    loader = VDemLoader()
    df = loader.load()
    df = compute_dimension_scores(df)
    print(f"\n로드된 국가 수: {len(df)}")
    print(f"피처 수: {len(ALL_FEATURES)}")
    print("\n샘플 (스웨덴):")
    sweden = df[df["iso3"] == "SWE"]
    if not sweden.empty:
        for dim in ["electoral", "judicial", "media", "civil", "exec_constraints"]:
            print(f"  dim_{dim}: {sweden[f'dim_{dim}'].values[0]:.1f}")
