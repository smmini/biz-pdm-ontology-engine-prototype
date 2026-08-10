# 원본/결과물 파일 위치

이 문서는 `biz-pdm-ontology-engine-prototype`이 실제로 읽고 쓰는 파일 위치를 정리한다. 기능 검증 목적의 프로토타입이므로, 구조적 정합성보다 "지금 이 경로에 뭐가 있는지"를 정확히 아는 것이 우선이다.

---

## 1. 원본(raw) 입력

| 경로 | 내용 | 상태 |
|---|---|---|
| `data/` | Azure PdM 데이터셋 계열 CSV 파일 5개<br>- `PdM_errors.csv` (129,077 bytes)<br>- `PdM_failures.csv` (24,336 bytes)<br>- `PdM_machines.csv` (1,582 bytes)<br>- `PdM_maint.csv` (104,903 bytes)<br>- `PdM_telemetry.csv` (80,142,329 bytes) | 사용 중 |

---

## 2. 중간 산출물

| 경로 | 내용 | 상태 |
|---|---|---|
| `data_preprocessed/raw_extracted/` | extraction 단계 중간 산출물 CSV 파일 5개<br>- `PdM_errors.csv` (121,233 bytes)<br>- `PdM_failures.csv` (22,808 bytes)<br>- `PdM_machines.csv` (1,376 bytes)<br>- `PdM_maint.csv` (98,325 bytes)<br>- `PdM_telemetry.csv` (80,142,317 bytes) | 사용 중 |
| `data_preprocessed/features/` | feature 생성 산출물 4개<br>- `PdM_telemetry_X.npy` (56,069,952 bytes, 파생 feature 행렬)<br>- `PdM_telemetry_columns.json` (216 bytes, feature 컬럼명 목록)<br>- `PdM_telemetry_datetime.npy` (7,008,856 bytes, 관측시각 배열)<br>- `PdM_telemetry_machineID.npy` (7,008,856 bytes, 자산 ID 배열) | 사용 중 |

---

## 3. 최종 산출물 (모델)

| 경로 | 내용 | 상태 |
|---|---|---|
| `models_store/lightgbm/model.joblib` | LightGBM 학습 모델 파일 (346,797 bytes) | 사용 중 |
| `models_store/random_forest/model.joblib` | Random Forest 학습 모델 파일 (674,541,602 bytes) | 사용 중 |
| `models_store/xgboost/model.joblib` | XGBoost 학습 모델 파일 (447,029 bytes) | 사용 중 |
| `models_store/registry.json` | 모델 레지스트리 정보 (729 bytes)<br>- `trained_at`: "2026-08-04T08:12:41.875914"<br>- `feature_cols`: 8개 컬럼 항목<br>- `models`: `lightgbm`, `xgboost`, `random_forest` 3종 경로 및 `train_positive_rate` | 사용 중 |

---

## 4. `config.py`에 정의만 되어있고 현재 미사용인 경로

| 경로 | 정의값 | 실제 사용 여부 | 비고 |
|---|---|---|---|
| `CANONICAL_V3_1_DIR` | `C:\kosa\project\final\predictive_maintenance_canonical_v3.1\canonical\dataset` | 미사용 (코드 전수 검색 결과 import/참조 0건) | 향후 canonical v3.1 연동 시 사용 예정으로 추정. 실제 로컬 디렉터리 및 원천 CSV 7개는 존재함. |
| `GEN_DATA_OUTPUT_DIR` | `C:\kosa\project\final\gen_data\output` | 미사용 (코드 전수 검색 결과 import/참조 0건) | 향후 gen_data 연동 시 사용 예정으로 추정. 실제 로컬 디렉터리는 존재함 (`raw/`, `sensor/`). |
| `PROCESSED_SENSOR_DIR` | `C:\kosa\project\final\ontology_dashboard\data\sensor` | 미사용 (코드 전수 검색 결과 import/참조 0건) | **경로 자체가 로컬에 존재하지 않음** (`ontology_dashboard/data` 없음). |
| `PROCESSED_RESULT_DIR` | `C:\kosa\project\final\ontology_dashboard\data\result` | 미사용 (코드 전수 검색 결과 import/참조 0건) | **경로 자체가 로컬에 존재하지 않음** (`ontology_dashboard/data` 없음). |
