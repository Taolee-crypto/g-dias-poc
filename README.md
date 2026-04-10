# G-DIAS PoC v2 (Global Democratic Integrity Automated System)

**Real-time, bias-free global democratic risk analysis system**

목적: 민주주의 후퇴 조기 경보를 위한 완전 자동 분석 시스템

핵심 특징:
- 100% quantitative data (설문·전문가 판단 배제)
- Human-Free (인간 개입 완전 제거)
- Real-time 스트리밍 처리 (Kafka 연동)
- Open-source & 투명성 (코드·로그 공개)

---

## v2 주요 변경사항

### 피처 설계 (vdem_features.py)
- **20개 V-Dem 실제 변수** 사용 (v2xel_frefair, v2juhcind 등)
- 5대 차원: Electoral / Judicial / Media / Civil Society / Executive Constraints
- 차원별 가중치: Electoral 25%, Judicial 22%, Media 18%, Civil 18%, Exec 17%
- V-Dem CSV 있으면 자동 로드, 없으면 연구 기반 추정치 사용

### 모델 (train_dsi_model.py)
- XGBoost (300 estimators, 5-fold CV MAE ≈ 1.87)
- 비선형 DSI 레이블: 가중합 + 균형 보너스 + 취약고리 패널티
- 1,024개 샘플 (24개 실제 + 1,000개 증강)
- 상위 피처: 고위법원독립성, 선거자유공정성, 선거불규칙성

### 경보 엔진 (alert_engine.py)
4가지 경보 규칙:
1. **절대값 임계**: DSI < 30 → CRITICAL, < 45 → WARNING
2. **30일 변화량**: Δ < -8pt → CRITICAL, < -5pt → WARNING, < -3pt → WATCH
3. **차원별 임계**: 특정 차원 < 25 → CRITICAL
4. **복합 하락**: 3개 이상 차원 동시 하락 → WARNING

---

## 실행 방법

```bash
# 1. 의존성
pip install -r requirements.txt

# 2. 모델 학습 (V-Dem CSV 없으면 시뮬레이션)
python src/train_dsi_model.py

# 3. 경보 파이프라인 테스트
python src/alert_engine.py

# 4. 대시보드 실행
streamlit run dashboard.py
```

### 실제 V-Dem 데이터 사용 시:
```bash
# V-Dem 데이터셋 다운로드: https://v-dem.net/data/the-v-dem-dataset/
python src/train_dsi_model.py --vdem-csv data/V-Dem-CY-Core-v13.csv
streamlit run dashboard.py
```

---

## 파일 구조

```
g-dias/
├── dashboard.py              # Streamlit 대시보드 (Plotly 차트, 세계지도)
├── requirements.txt
├── src/
│   ├── vdem_features.py      # V-Dem 피처 정의 및 데이터 로더
│   ├── train_dsi_model.py    # XGBoost 학습 (20 features)
│   └── alert_engine.py       # 경보 엔진 (4가지 규칙)
├── models/
│   ├── dsi_model.pkl
│   ├── scaler.pkl
│   └── feature_meta.json
└── data/
    ├── dsi_history.json      # 국가별 DSI 시계열
    └── latest_alerts.json    # 최신 경보 결과
```

---

## 다음 단계 (v3)

- [ ] 실제 V-Dem API 연동 (자동 업데이트)
- [ ] Kafka 실시간 스트림 완성
- [ ] 국가별 뉴스 피드 연동 (보조 신호)
- [ ] 알림 발송 (이메일/Slack)
- [ ] Docker 단일 명령 배포

이 PoC는 Mozilla Democracy x AI Cohort 2026 제출용 프로토타입입니다.
피드백 환영합니다!
