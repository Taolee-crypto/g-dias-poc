# train_and_save_dummy_model.py
import os
import pickle
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import xgboost as xgb

os.makedirs('models', exist_ok=True)

# 더미 데이터로 scaler 학습
X_dummy = np.random.rand(200, 7)
scaler = MinMaxScaler()
scaler.fit(X_dummy)

with open('models/scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)
print("scaler.pkl 저장 완료")

# 더미 XGBoost 모델
model = xgb.XGBRegressor(
    objective='reg:squarederror',
    n_estimators=100,
    learning_rate=0.1,
    max_depth=4,
    random_state=42
)

y_dummy = np.random.rand(200) * 100
model.fit(X_dummy, y_dummy)

with open('models/dsi_model.pkl', 'wb') as f:
    pickle.dump(model, f)
print("dsi_model.pkl 저장 완료")

print("완료! models 폴더에 두 파일이 생성되었습니다.")