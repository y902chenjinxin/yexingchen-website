"""统一错误码与路由注册回归测试。"""

import pytest
from fastapi import HTTPException, status

from app.main import app
from app.schemas.errors import ErrCode, get_http_status, raise_error


@pytest.mark.parametrize(
    ("code", "expected_status"),
    [
        (ErrCode.INVALID_PARAM, status.HTTP_400_BAD_REQUEST),
        (ErrCode.INTERNAL_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR),
        (ErrCode.AUTH_INVALID_TOKEN, status.HTTP_401_UNAUTHORIZED),
        (ErrCode.AUTH_USER_NOT_EXIST, status.HTTP_404_NOT_FOUND),
        (ErrCode.AUTH_USER_STATUS_INVALID, status.HTTP_401_UNAUTHORIZED),
        (ErrCode.AUTH_INVALID_CREDENTIALS, status.HTTP_401_UNAUTHORIZED),
        (ErrCode.AUTH_RATE_LIMITED, status.HTTP_429_TOO_MANY_REQUESTS),
        (ErrCode.AUTH_PERMISSION_DENIED, status.HTTP_403_FORBIDDEN),
        (ErrCode.REG_EMAIL_EXISTS, status.HTTP_400_BAD_REQUEST),
        (ErrCode.USER_PASSWORD_WEAK, status.HTTP_400_BAD_REQUEST),
        (ErrCode.MUSIC_NOT_FOUND, status.HTTP_404_NOT_FOUND),
        (ErrCode.NOVEL_NOT_FOUND, status.HTTP_404_NOT_FOUND),
        (ErrCode.VIDEO_NOT_FOUND, status.HTTP_404_NOT_FOUND),
        (ErrCode.TOOL_NOT_FOUND, status.HTTP_404_NOT_FOUND),
        (ErrCode.SYS_FILE_NOT_FOUND, status.HTTP_404_NOT_FOUND),
        (ErrCode.SYS_DATABASE_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR),
    ],
)
def test_get_http_status(code, expected_status):
    assert get_http_status(code[0]) == expected_status


def test_unknown_error_code_is_server_error():
    assert get_http_status(987654) == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_raise_error_preserves_code_and_custom_message():
    with pytest.raises(HTTPException) as exc_info:
        raise_error(ErrCode.MUSIC_NOT_FOUND, "指定音乐不存在")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc_info.value.detail == {
        "code": ErrCode.MUSIC_NOT_FOUND[0],
        "msg": "指定音乐不存在",
    }


def test_workbench_router_is_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/workbench/summary" in paths
