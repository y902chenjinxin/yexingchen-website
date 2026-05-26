import os
from qcloud_cos import CosConfig
from qcloud_cos import CosServiceError
from app.config import settings


def get_cos_client():
    """获取腾讯COS客户端"""
    config = CosConfig(
        Region=settings.COS_REGION,
        SecretId=settings.COS_SECRET_ID,
        SecretKey=settings.COS_SECRET_KEY,
    )
    return config


def upload_to_cos(local_file_path: str, cos_path: str) -> str:
    """上传文件到腾讯COS，返回COS URL"""
    from qcloud_cos import CosS3Client

    config = get_cos_client()
    client = CosS3Client(config)

    # 上传
    with open(local_file_path, 'rb') as f:
        client.put_object(
            Bucket=settings.COS_BUCKET,
            Body=f,
            Key=cos_path,
            StorageClass='STANDARD'
        )

    # 生成URL
    url = f"https://{settings.COS_BUCKET}.cos.{settings.COS_REGION}.myqcloud.com/{cos_path}"
    return url


def delete_from_cos(cos_path: str):
    """从腾讯COS删除文件"""
    from qcloud_cos import CosS3Client

    config = get_cos_client()
    client = CosS3Client(config)

    try:
        client.delete_object(
            Bucket=settings.COS_BUCKET,
            Key=cos_path
        )
    except CosServiceError as e:
        pass  # 忽略删除错误