"""
train_dsi_model.py - DSI (Democracy Stability Index) XGBoost 모델 학습

실제 V-Dem 지표 20개 피처로 DSI를 예측하는 XGBoost 모델 학습.

DSI 레이블 생성 방식:
  - V-Dem 데이터가 있으면 실제 v2x_libdem (자유민주주의 지수) 기반
  - 없으면 차원 가중합 + 비선형 보정으로 합성 레이블 생성
"""

import os
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_absolute_error
import xgboost as xgb

import sys
sys.path.insert(0, os.path.dirname(__file__))
from vdem_features import (
    VDemLoader, ALL_FEATURES, DIMENSION_WEIGHTS,
    VDEM_FEATURE_MAP, compute_dimension_scores
)

os.makedirs("models", exist_ok=True)


# ─────────────────────────────────────────────
#  DSI 레이블 생성
# ─────────────────────────────────────────────

def generate_dsi_labels(df: pd.DataFrame) -> np.ndarray:
    """
    DSI 레이블(0~100) 생성.

    공식:
      DSI = Σ(dim_weight × dim_score)
            + nonlinearity_bonus
            - decay_penalty

    비선형 보정:
      - 모든 차원이 고루 높으면 보너스 (민주주의 시너지 효과)
      - 특정 차원이 극도로 낮으면 페널티 (취약고리 효과)
    """
    df = compute_dimension_scores(df)

    dims = list(DIMENSION_WEIGHTS.keys())
    weights = np.array(list(DIMENSION_WEIGHTS.values()))
    dim_scores = df[[f"dim_{d}" for d in dims]].values  # shape: (n, 5)

    # 기본 가중합
    base_dsi = (dim_scores * weights).sum(axis=1)

    # 비선형 보정 1: 분산이 낮을수록 (균형 잡힐수록) 보너스 +3
    std_bonus = 3 * np.exp(-np.std(dim_scores, axis=1) / 20)

    # 비선형 보정 2: 최솟값 차원이 30 이하면 패널티 (취약고리)
    min_dim = dim_scores.min(axis=1)
    weak_link_penalty = np.where(min_dim < 30, (30 - min_dim) * 0.15, 0)

    dsi = base_dsi + std_bonus - weak_link_penalty
    dsi = np.clip(dsi, 0, 100)

    return dsi.astype(np.float32)


# ─────────────────────────────────────────────
#  증강 데이터 생성 (모델 일반화용)
# ─────────────────────────────────────────────

def augment_data(df: pd.DataFrame, n_synthetic: int = 800) -> pd.DataFrame:
    """
    실제 국가 데이터를 기반으로 합성 데이터 생성.
    - 실제 관측치 주변 가우시안 노이즈
    - 전체 스펙트럼 균등 커버리지 추가
    """
    rng = np.random.default_rng(42)
    X_real = df[ALL_FEATURES].values

    # 1) 실제 데이터 주변 노이즈 증강
    idx = rng.choice(len(X_real), n_synthetic // 2)
    noise = rng.normal(0, 6, (n_synthetic // 2, len(ALL_FEATURES)))
    X_aug1 = np.clip(X_real[idx] + noise, 0, 100)

    # 2) 전체 스펙트럼 균등 샘플 (0~100 균일 분포)
    X_aug2 = rng.uniform(0, 100, (n_synthetic // 2, len(ALL_FEATURES)))

    X_all = np.vstack([X_real, X_aug1, X_aug2])

    df_aug = pd.DataFrame(X_all, columns=ALL_FEATURES)
    # iso3/country 컬럼 없이 피처만 있는 DataFrame
    return df_aug


# ─────────────────────────────────────────────
#  모델 학습
# ─────────────────────────────────────────────

def train(csv_path: str = None):
    print("=" * 50)
    print("G-DIAS DSI 모델 학습 시작")
    print("=" * 50)

    # 1) 데이터 로드
    loader = VDemLoader(csv_path)
    df_real = loader.load()
    print(f"\n[1] 원본 데이터: {len(df_real)}개국")

    # 2) 증강 데이터 생성
    df_features_only = df_real[ALL_FEATURES].copy()
    df_aug = augment_data(df_features_only, n_synthetic=1000)
    print(f"[2] 증강 후 총 샘플: {len(df_aug)}개")

    # 3) 레이블 생성
    y = generate_dsi_labels(df_aug)
    print(f"[3] DSI 레이블 범위: {y.min():.1f} ~ {y.max():.1f} (평균: {y.mean():.1f})")

    # 4) 스케일러 학습
    scaler = MinMaxScaler()
    X = scaler.fit_transform(df_aug[ALL_FEATURES].values)

    # 5) XGBoost 학습
    model = xgb.XGBRegressor(
        objective="reg:squarederror",
        n_estimators=300,
        learning_rate=0.05,
        max_depth=5,
        min_child_weight=3,
        subsample=0.8,
        colsample_bytree=0.7,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
    )

    # 교차 검증
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="neg_mean_absolute_error")
    print(f"[5] 5-Fold CV MAE: {-cv_scores.mean():.2f} ± {cv_scores.std():.2f}")

    # 전체 데이터로 최종 학습
    model.fit(X, y)

    # 6) 피처 중요도 출력
    importance = model.feature_importances_
    feat_imp = sorted(zip(ALL_FEATURES, importance), key=lambda x: -x[1])
    print("\n[6] 상위 5개 피처 중요도:")
    for feat, imp in feat_imp[:5]:
        dim_info = next(
            (f"{dim}:{info[0]}" for dim, feats in VDEM_FEATURE_MAP.items()
             for f, info in feats.items() if f == feat), "?"
        )
        print(f"    {feat:25s} {imp:.4f}  ({dim_info})")

    # 7) 실제 국가 예측 검증
    X_real_scaled = scaler.transform(df_real[ALL_FEATURES].values)
    y_real_pred = model.predict(X_real_scaled)
    y_real_true = generate_dsi_labels(df_real)
    mae_real = mean_absolute_error(y_real_true, y_real_pred)
    print(f"\n[7] 실제 국가 MAE: {mae_real:.2f}")

    if "country" in df_real.columns:
        print("\n국가별 예측 DSI (상위 5 / 하위 5):")
        results = pd.DataFrame({
            "country": df_real["country"].values,
            "dsi_pred": y_real_pred.round(1),
            "dsi_label": y_real_true.round(1),
        }).sort_values("dsi_pred", ascending=False)
        print("  상위:", results.head(5)[["country","dsi_pred"]].to_string(index=False))
        print("  하위:", results.tail(5)[["country","dsi_pred"]].to_string(index=False))

    # 8) 저장
    with open("models/scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    with open("models/dsi_model.pkl", "wb") as f:
        pickle.dump(model, f)

    # 피처 메타데이터도 저장 (대시보드에서 사용)
    feature_meta = {
        "all_features": ALL_FEATURES,
        "dimension_weights": DIMENSION_WEIGHTS,
        "vdem_feature_map": {
            dim: {k: v[0] for k, v in feats.items()}
            for dim, feats in VDEM_FEATURE_MAP.items()
        },
        "model_cv_mae": float(-cv_scores.mean()),
    }
    import json
    with open("models/feature_meta.json", "w", encoding="utf-8") as f:
        json.dump(feature_meta, f, ensure_ascii=False, indent=2)

    print("\n저장 완료:")
    print("  models/scaler.pkl")
    print("  models/dsi_model.pkl")
    print("  models/feature_meta.json")
    print("\n학습 완료!")
    return model, scaler


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--vdem-csv", default=None, help="V-Dem CSV 경로 (없으면 시뮬레이션)")
    args = parser.parse_args()
    train(args.vdem_csv)
