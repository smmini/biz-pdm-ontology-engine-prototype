ASSET_TYPE_LABELS = {
    "compressor": "공기압축기",
    "cnc": "CNC 설비"
}

STATUS_GRADE_LABELS = {
    "critical": "위험",
    "warning": "경고",
    "attention": "주의",
    "data_quality_hold": "데이터 확인",
    "normal": "정상"
}

STATUS_SENTENCES = {
    "critical": "즉시 점검이 필요한 위험 신호",
    "warning": "우선순위 점검이 필요한 경고 신호",
    "attention": "추가 관찰이 필요한 주의 신호",
    "data_quality_hold": "센서 데이터 확인이 필요한 상태",
    "normal": "특이 위험 신호가 없는 정상 상태"
}

FEATURE_DISPLAY_LABELS = {
    "rotation_raw_6h_mean": "회전 상태 평균값",
    "rotation_raw_6h_abs_mean": "회전 변동 크기",
    "rotation_raw_6h_std": "회전 불안정성",
    "pressure_raw_6h_mean": "압력 평균값",
    "pressure_raw_6h_abs_mean": "압력 변동 크기",
    "pressure_raw_current": "현재 압력",
    "vibration_raw_6h_mean": "진동 평균값",
    "vibration_raw_6h_std": "진동 불안정성",
    "vibration_raw_current": "현재 진동",
    "voltage_raw_6h_mean": "전압 평균값",
    "voltage_raw_current": "현재 전압",
    "rotation_raw": "회전 상태",
    "pressure_raw": "압력",
    "vibration_raw": "진동",
    "voltage_raw": "전압",
    "air_temperature_k": "공기 온도",
    "process_temperature_k": "공정 온도",
    "rotational_speed_rpm": "회전 속도",
    "torque_nm": "토크",
    "tool_wear_min": "공구 마모"
}

SENSOR_DISPLAY_LABELS = {
    "rotation_raw": "회전 상태",
    "pressure_raw": "압력",
    "vibration_raw": "진동",
    "voltage_raw": "전압",
    "air_temperature_k": "공기 온도",
    "process_temperature_k": "공정 온도",
    "rotational_speed_rpm": "회전 속도",
    "torque_nm": "토크",
    "tool_wear_min": "공구 마모"
}

INSPECTION_CHECK_LABELS = {
    "rotation_raw_6h_mean": "회전부 속도 저하 여부 확인",
    "rotation_raw_6h_abs_mean": "회전 변화가 갑자기 커졌는지 확인",
    "rotation_raw_6h_std": "이상음·진동 동반 여부 확인",
    "pressure_raw_6h_mean": "압력 저하/변동 여부 확인",
    "vibration_raw_6h_std": "진동 상태 흔들림 확인",
    "voltage_raw_6h_mean": "전압 안정성 확인",
    "tool_wear_min": "공구 마모 누적 시간 확인",
}

INSPECTION_PLAIN_REASONS = {
    "rotation_raw_6h_mean": "최근 회전 상태가 평소 기준보다 낮게 나타났습니다. 벨트, 축, 모터 부하와 이물 걸림을 우선 확인합니다.",
    "rotation_raw_6h_abs_mean": "회전값이 일정하게 유지되지 않고 변동 폭이 커졌습니다. 부하 변화, 압력 변화, 운전 조건 변경 여부를 함께 봅니다.",
    "rotation_raw_6h_std": "회전값 흔들림이 위험 근거로 잡혔습니다. 현장에서 소음, 떨림, 체결 상태를 확인합니다.",
    "pressure_raw_6h_mean": "압력 관측 수치가 평소 기준 범위에서 벗어났습니다. 배관 leak 및 밸브 상태를 점검합니다.",
    "vibration_raw_6h_std": "진동 불안정성이 증가했습니다. 베어링 및 체결 상태 점검이 필요합니다.",
    "tool_wear_min": "공구 마모 누적 시간이 경고 기준에 도달했습니다. 공구 교체 주기를 확인합니다.",
}

INSPECTION_REQUEST_LIMITATIONS = [
    "모델 예측 기반 점검 요청이며 고장 확정이 아닙니다.",
    "자동 설비 정지 또는 자동 작업 지시를 의미하지 않습니다."
]

STATUS_SUMMARY_LIMITATIONS = [
    "상태 요약 보고서는 고장 확정 보고서가 아닙니다.",
    "자동 설비 정지 또는 자동 작업 지시를 의미하지 않습니다.",
    "데이터 확인 상태는 고장 위험이 아니라 데이터 품질 확인 대상으로 분리합니다."
]
