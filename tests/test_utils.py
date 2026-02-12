"""Tests for utility functions."""

from mcp_server_tuya.utils import (
    validate_brightness,
    validate_color_temperature,
    validate_hsv,
    format_success_response,
    format_error_response,
    hsv_to_tuya_format,
)


class TestValidateBrightness:
    def test_valid_min(self):
        valid, msg = validate_brightness(0)
        assert valid is True
        assert msg == ""

    def test_valid_max(self):
        valid, msg = validate_brightness(1000)
        assert valid is True

    def test_valid_mid(self):
        valid, msg = validate_brightness(500)
        assert valid is True

    def test_invalid_negative(self):
        valid, msg = validate_brightness(-1)
        assert valid is False
        assert "-1" in msg

    def test_invalid_over_max(self):
        valid, msg = validate_brightness(1001)
        assert valid is False


class TestValidateColorTemperature:
    def test_valid_range(self):
        assert validate_color_temperature(0)[0] is True
        assert validate_color_temperature(500)[0] is True
        assert validate_color_temperature(1000)[0] is True

    def test_invalid_range(self):
        assert validate_color_temperature(-1)[0] is False
        assert validate_color_temperature(1001)[0] is False


class TestValidateHSV:
    def test_valid(self):
        valid, msg = validate_hsv(180, 128, 128)
        assert valid is True

    def test_valid_boundaries(self):
        assert validate_hsv(0, 0, 0)[0] is True
        assert validate_hsv(360, 255, 255)[0] is True

    def test_invalid_hue(self):
        assert validate_hsv(361, 128, 128)[0] is False
        assert validate_hsv(-1, 128, 128)[0] is False

    def test_invalid_saturation(self):
        assert validate_hsv(180, 256, 128)[0] is False
        assert validate_hsv(180, -1, 128)[0] is False

    def test_invalid_value(self):
        assert validate_hsv(180, 128, 256)[0] is False
        assert validate_hsv(180, 128, -1)[0] is False


class TestFormatResponses:
    def test_success_basic(self):
        resp = format_success_response("OK")
        assert resp["success"] is True
        assert resp["message"] == "OK"
        assert "device_id" not in resp

    def test_success_with_device(self):
        resp = format_success_response("OK", device_id="abc123")
        assert resp["device_id"] == "abc123"

    def test_success_with_data(self):
        resp = format_success_response("OK", data={"key": "val"})
        assert resp["data"] == {"key": "val"}

    def test_error_basic(self):
        resp = format_error_response("NotFound", "Device missing")
        assert resp["success"] is False
        assert resp["error"] == "NotFound"

    def test_error_with_suggestion(self):
        resp = format_error_response("Err", "Msg", suggestion="Try X")
        assert resp["suggestion"] == "Try X"


class TestHSVToTuya:
    def test_zero(self):
        result = hsv_to_tuya_format(0, 0, 0)
        assert result == "000000000000"

    def test_max(self):
        result = hsv_to_tuya_format(360, 255, 255)
        assert result == "036010001000"

    def test_mid(self):
        result = hsv_to_tuya_format(180, 128, 128)
        # 128/255*1000 ≈ 501
        assert result.startswith("0180")
