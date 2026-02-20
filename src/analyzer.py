# analyzer.py - G-DIAS PoC 기본 분석기
import json
import pandas as pd
from kafka import KafkaConsumer
import xgboost as xgb
import joblib  # 모델 로드용
from sklearn.preprocessing import MinMaxScaler

# 설정
KAFKA_BOOTSTRAP = 'localhost:9092'
TOPIC = 'worldbank_gdp'  # 예시 토픽
MODEL_PATH = 'models/dsi_model.pkl'  # 학습된 모델 파일

# 모델 로드 (실제로는 미리 학습된 모델 사용)
# In analyzer.py
model = joblib.load('models/dsi_model.pkl')
scaler = joblib.load('models/scaler.pkl')

# ...
scaled_features = scaler.transform(features)
dsi_score = model.predict(scaled_features)[0]
def process_message(message):
    try:
        data = json.loads(message.value.decode('utf-8'))
        # 예시: World Bank 데이터에서 필요한 피처 추출
        df = pd.DataFrame([data])
        features = df[['gdp_growth', 'corruption_index', 'press_freedom', 'electoral_turnout']].fillna(0)
        
        # 정규화 (학습 시와 동일하게)
        scaled_features = scaler.fit_transform(features)  # PoC용, 실제로는 scaler 저장·로드
        
        # DSI 예측
        dsi_score = model.predict(scaled_features)[0]
        dsi_score = round(min(max(dsi_score, 0), 100), 2)  # 0~100 범위
        
        print(f"Country: {data.get('country', 'Unknown')}")
        print(f"DSI Score: {dsi_score}")
        print("---")
        
        # 실제로는 여기서 결과 저장 또는 API로 전송
        return dsi_score
    except Exception as e:
        print(f"Error processing message: {e}")
        return None

# Kafka Consumer 실행
consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP,
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='gdias-poc-group',
    value_deserializer=lambda x: x  # json.loads는 내부에서
)

print("G-DIAS PoC Analyzer started. Listening to Kafka topic...")
for message in consumer:
    process_message(message)
