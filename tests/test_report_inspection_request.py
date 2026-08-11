import pytest
from systems.backend.app.report.report_generator import generate_report
from systems.backend.app.report.report_constants import INSPECTION_REQUEST_LIMITATIONS


class TestInspectionRequestReport:
    """
    systems/backend/app/report/generator.py 직접 참조 점검 요청 보고서 전용 테스트
    """

    def test_inspection_request_schema(self):
        """단일 설비 점검 요청 보고서의 필수 스키마 구조 및 고정값 검증"""
        report = generate_report(
            "predictive_inspection_request",
            asset_id="CMP-S03-L03-01",
            observed_at="2026-08-29T23:00:00+09:00"
        )

        required_keys = [
            "schema_version", "report_type", "report_id", "generated_at",
            "generation_method", "view_scope", "subject", "status",
            "manager_view", "engineer_view", "evidence_references",
            "limitations", "provenance"
        ]
        for key in required_keys:
            assert key in report, f"필수 키 {key}가 누락되었습니다."

        assert report["schema_version"] == "report-output-v0.1"
        assert report["report_type"] == "predictive_inspection_request"
        assert report["generation_method"] == "deterministic"
        assert report["view_scope"] == "report_view_only"
        assert report["status"]["confirmation_status"] == "predicted_not_confirmed"
        assert report["report_id"] == "REPORT#CMP-S03-L03-01#2026-08-29T23:00:00+09:00"

        assert report["subject"]["location_label"] == "03구역 / 03라인"
        assert report["subject"]["asset_type_label"] == "공기압축기"
        assert report["limitations"] == INSPECTION_REQUEST_LIMITATIONS

    def test_inspection_request_direction_filtering(self):
        """top_factors 중 direction == 'risk_up'만 inspection_targets 후보에 포함되는지 검증"""
        custom_factors = [
            {"feature": "rotation_raw_6h_mean", "raw_contribution": 1.2, "direction": "risk_up"},
            {"feature": "vibration_raw_6h_mean", "raw_contribution": -0.8, "direction": "risk_down"},
            {"feature": "pressure_raw_6h_abs_mean", "raw_contribution": 0.5, "direction": "risk_up"}
        ]

        report = generate_report("predictive_inspection_request", top_factors=custom_factors)
        targets = report["engineer_view"]["inspection_targets"]

        assert len(targets) == 2
        assert targets[0]["feature"] == "rotation_raw_6h_mean"
        assert targets[0]["rank"] == 1
        assert targets[1]["feature"] == "pressure_raw_6h_abs_mean"
        assert targets[1]["rank"] == 2

    def test_inspection_request_mock_fields_are_null(self):
        """mock/선택 필드가 임의 값 없이 None/null 인지 검증"""
        report = generate_report("predictive_inspection_request")
        
        mock_fields = ["production_impact", "estimated_downtime_minutes", "work_order_id", "line_id"]
        for field in mock_fields:
            assert report.get(field) is None, f"mock 필드 {field}는 None이어야 합니다."
