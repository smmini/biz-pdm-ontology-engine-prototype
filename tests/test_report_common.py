import pytest
from systems.backend.app.report.generator import generate_report


class TestReportCommon:
    """
    systems/backend/app/report/generator.py 직접 참조 및 공통 결정론성 테스트
    """

    def test_invalid_report_type_raises_value_error(self):
        """지원하지 않는 report_type 입력 시 ValueError가 발생하는지 검증"""
        with pytest.raises(ValueError, match="지원하지 않는 report_type"):
            generate_report("invalid_report_type_name")

    def test_deterministic_output(self):
        """동일한 입력으로 2회 실행 시 100% 동일한 출력을 반환하는지(결정론성) 검증"""
        out1_inspection = generate_report("predictive_inspection_request")
        out2_inspection = generate_report("predictive_inspection_request")
        assert out1_inspection == out2_inspection

        out1_summary = generate_report("predictive_maintenance_status_summary")
        out2_summary = generate_report("predictive_maintenance_status_summary")
        assert out1_summary == out2_summary
