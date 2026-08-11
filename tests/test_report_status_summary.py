import pytest
from systems.backend.app.report.report_generator import generate_report
from systems.backend.app.report.report_constants import STATUS_SUMMARY_LIMITATIONS


class TestStatusSummaryReport:
    """
    systems/backend/app/report/generator.py 직접 참조 다중 설비 상태 요약 보고서 전용 테스트
    """

    def test_status_summary_schema(self):
        """다중 설비 상태 요약 보고서의 필수 스키마 구조 및 고정값 검증"""
        report = generate_report("predictive_maintenance_status_summary")

        required_keys = [
            "report_type", "generation_method", "generated_at",
            "prediction_horizon_hours", "summary", "line_summaries",
            "priority_assets", "limitations", "provenance"
        ]
        for key in required_keys:
            assert key in report, f"필수 키 {key}가 누락되었습니다."

        assert report["report_type"] == "predictive_maintenance_status_summary"
        assert report["generation_method"] == "deterministic"
        assert report["prediction_horizon_hours"] == 24
        assert report["limitations"] == STATUS_SUMMARY_LIMITATIONS

    def test_status_summary_custom_assets_aggregation(self):
        """사용자 지정 설비 목록 전달 시 5분류 상태 카운트 집계 및 priority_assets 정렬 검증"""
        custom_assets = [
            {"asset_id": "CMP-S01-L01-01", "status_grade": "critical", "probability": 0.85},
            {"asset_id": "CNC-S01-L01-02", "status_grade": "warning", "probability": 0.65},
            {"asset_id": "CNC-S01-L01-03", "status_grade": "normal", "probability": 0.10},
            {"asset_id": "CNC-S01-L01-04", "status_grade": "attention", "probability": 0.40},
            {"asset_id": "CMP-S01-L01-05", "status_grade": "data_quality_hold", "probability": 0.05}
        ]

        report = generate_report(
            "predictive_maintenance_status_summary",
            assets=custom_assets,
            total_assets=5
        )

        counts = report["summary"]["status_counts"]
        assert counts["critical"] == 1
        assert counts["warning"] == 1
        assert counts["attention"] == 1
        assert counts["data_quality_hold"] == 1
        assert counts["normal"] == 1

        priorities = report["priority_assets"]
        assert len(priorities) == 3
        assert priorities[0]["asset_id"] == "CMP-S01-L01-01"
        assert priorities[1]["asset_id"] == "CNC-S01-L01-02"
        assert priorities[2]["asset_id"] == "CNC-S01-L01-04"
