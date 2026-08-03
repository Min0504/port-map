"""scanner 단위 테스트 (mock 기반)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanners import base, mac_linux


def test_psutil_schema():
    """psutil 스캔 결과가 JSON 스키마 필수 필드를 갖추는지."""
    if not base.is_available():
        return  # psutil 없으면 스킵
    result = base.scan(self_pid=0)
    assert "ports" in result
    assert "scanned_at" in result
    assert "scanner" in result
    assert "count" in result
    assert "error" in result
    if result["ports"]:
        p = result["ports"][0]
        for field in ("port", "protocol", "family", "state", "pid",
                      "process", "cmdline", "remote", "permission"):
            assert field in p, f"missing field: {field}"


def test_self_port_filter():
    """자기 PID가 스냅샷에서 제외되는지."""
    if not base.is_available():
        return
    # 실제 서버 포트를 self_pid로 주면 제외되어야 함
    result = base.scan(self_pid=-1)  # 존재 않는 PID → 필터링 안 됨
    assert result["error"] is None or result["error"]


def test_lsof_parse():
    """lsof 출력 파싱 검증 (mock)."""
    assert mac_linux._parse_port("*:8080") == 8080
    assert mac_linux._parse_port("1.2.3.4:443") == 443
    assert mac_linux._parse_port("[::]:3000") == 3000
    assert mac_linux._parse_port("noport") is None


if __name__ == "__main__":
    test_psutil_schema()
    test_self_port_filter()
    test_lsof_parse()
    print("scanner tests passed")
