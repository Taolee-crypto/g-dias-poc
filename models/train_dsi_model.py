# train_dsi_model.py - G-DIAS PoC: Basic DSI model training
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, r2_score
import xgboost as xgb
import joblib
import matplotlib.pyplot as plt

# 1. Create synthetic training data (replace with real dataset)
np.random.seed(42)
n_samples = 1000

data = pd.DataFrame({
    'gdp_growth': np.random.normal(3, 2, n_samples),
    'corruption_index': np.random.uniform(20, 90, n_samples),
    'press_freedom_score': np.random.uniform(30, 95, n_samples),
    'electoral_turnout': np.random.uniform(40, 85, n_samples),
    'judicial_independence': np.random.uniform(25, 90, n_samples),
    'civil_liberty_violations': np.random.poisson(5, n_samples),
    'media_censorship_events': np.random.poisson(2, n_samples)
})

# Synthetic target: DSI score (higher = more democratic stability)
# Simple rule-based target for demonstration
data['dsi_score'] = (
    0.25 * data['gdp_growth'] +
    0.20 * (100 - data['corruption_index']) +
    0.20 * data['press_freedom_score'] +
    0.15 * data['electoral_turnout'] +
    0.10 * data['judicial_independence'] -
    0.05 * data['civil_liberty_violations'] -
    0.05 * data['media_censorship_events']
)

# Clip to 0–100 range and add some noise
data['dsi_score'] = np.clip(data['dsi_score'] + np.random.normal(0, 3, n_samples), 0, 100)

# Features and target
features = [
    'gdp_growth', 'corruption_index', 'press_freedom_score',
    'electoral_turnout', 'judicial_independence',
    'civil_liberty_violations', 'media_censorship_events'
]
X = data[features]
y = data['dsi_score']

# 2. Preprocessing
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42
)

# 3. Train XGBoost regressor
model = xgb.XGBRegressor(
    objective='reg:squarederror',
    n_estimators=200,
    learning_rate=0.05,
    max_depth=5,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)

model.fit(X_train, y_train)

# 4. Evaluate
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"MAE: {mae:.2f}")
print(f"R²: {r2:.3f}")

# 5. Save model and scaler
joblib.dump(model, 'models/dsi_model.pkl')
joblib.dump(scaler, 'models/scaler.pkl')

print("Model and scaler saved to 'models/' folder")

# Optional: Feature importance plot
xgb.plot_importance(model)
plt.savefig('docs/feature_importance.png')
plt.close()
