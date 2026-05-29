"""
统一错误码体系
格式: 5位数字 XYnnn
X = 模块(1=认证, 2=用户, 3=音乐, 4=小说, 5=视频, 6=工具, 7=系统)
Y = 错误类型(0=参数, 1=权限, 2=资源, 3=内部)
nnn = 序号
"""

from fastapi import HTTPException, status


class ErrCode:
    # 通用
    SUCCESS = (0, "操作成功")
    INVALID_PARAM = (10001, "参数错误")
    UNAUTHORIZED = (10101, "未授权")
    FORBIDDEN = (10103, "禁止访问")
    NOT_FOUND = (10203, "资源不存在")
    INTERNAL_ERROR = (10300, "内部错误")

    # 认证模块 (11xxx)
    AUTH_INVALID_TOKEN = (11101, "无效的token或token已过期")
    AUTH_USER_NOT_EXIST = (11102, "用户不存在")
    AUTH_USER_STATUS_INVALID = (11103, "账号状态异常")
    AUTH_INVALID_CREDENTIALS = (11104, "邮箱或密码错误")
    AUTH_RATE_LIMITED = (11105, "登录过于频繁，请稍后重试")
    AUTH_PERMISSION_DENIED = (11106, "需要管理员权限")

    # 注册模块 (11xxx)
    REG_EMAIL_EXISTS = (11201, "该邮箱已注册")
    REG_CODE_EXPIRED = (11202, "验证码已过期，请重新获取")
    REG_CODE_INVALID = (11203, "验证码错误")
    REG_CODE_EXCEED_ATTEMPTS = (11204, "尝试次数过多，请稍后重试")
    REG_CODE_NOT_REQUESTED = (11205, "请先获取验证码")
    REG_PENDING = (11206, "注册申请已提交，请等待管理员审批")

    # 用户模块 (12xxx)
    USER_UPDATE_FAILED = (12101, "用户信息更新失败")
    USER_AVATAR_UPDATE_FAILED = (12102, "头像更新失败")
    USER_PASSWORD_WEAK = (12103, "密码至少8位，需包含大小写字母和数字")

    # 音乐模块 (13xxx)
    MUSIC_NOT_FOUND = (13201, "音乐不存在")
    MUSIC_UPLOAD_FAILED = (13301, "音乐上传失败")
    MUSIC_DELETE_FAILED = (13302, "音乐删除失败")

    # 小说模块 (14xxx)
    NOVEL_NOT_FOUND = (14201, "小说不存在")
    NOVEL_UPLOAD_FAILED = (14301, "小说上传失败")
    NOVEL_DELETE_FAILED = (14302, "小说删除失败")

    # 视频模块 (15xxx)
    VIDEO_NOT_FOUND = (15201, "视频不存在")
    VIDEO_UPLOAD_FAILED = (15301, "视频上传失败")
    VIDEO_DELETE_FAILED = (15302, "视频删除失败")

    # 工具模块 (16xxx)
    TOOL_NOT_FOUND = (16201, "工具不存在")
    TOOL_CREATE_FAILED = (16301, "工具创建失败")
    TOOL_UPDATE_FAILED = (16302, "工具更新失败")
    TOOL_DELETE_FAILED = (16303, "工具删除失败")

    # 系统模块 (99xxx)
    SYS_DATABASE_ERROR = (99301, "数据库错误")
    SYS_FILE_NOT_FOUND = (99302, "文件不存在")
    SYS_UPLOAD_FAILED = (99303, "文件上传失败")


def get_http_status(code: int) -> int:
    """根据错误码返回HTTP状态"""
    if 10101 <= code <= 10199:
        return status.HTTP_401_UNAUTHORIZED
    if code == 10103:
        return status.HTTP_403_FORBIDDEN
    if code == 10203:
        return status.HTTP_404_NOT_FOUND
    if code == 10001:
        return status.HTTP_400_BAD_REQUEST
    if code >= 99300:
        return status.HTTP_500_INTERNAL_SERVER_ERROR
    return status.HTTP_400_BAD_REQUEST


def raise_error(code: tuple, detail: str = None):
    """抛出统一错误"""
    code_num, default_msg = code
    message = detail or default_msg
    raise HTTPException(
        status_code=get_http_status(code_num),
        detail={"code": code_num, "msg": message}
    )


def error_response(code: tuple, detail: str = None) -> dict:
    """返回统一错误格式"""
    code_num, default_msg = code
    return {"code": code_num, "msg": detail or default_msg}