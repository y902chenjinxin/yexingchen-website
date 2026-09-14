"""资讯后台自动同步服务（feed_sync.sync_all_sources_once）单元测试。

不触碰真实 RSS 网络与数据库，全部 mock：
- SessionLocal → 假会话（返回若干源，记录 commit）
- _fetch_source_articles / _upsert_articles → 打桩
"""
from unittest import mock

from app.services import feed_sync


def test_sync_all_sources_once_ok_and_fail_per_source():
    s1 = mock.MagicMock()
    s1.last_status = 0
    s1.last_error = ""
    s1.last_check_at = None
    s2 = mock.MagicMock()
    s2.last_status = 0
    s2.last_error = ""
    s2.last_check_at = None

    db = mock.MagicMock()
    (db.query.return_value.filter.return_value.all.return_value) = [s1, s2]

    session_maker = mock.MagicMock()
    session_maker.return_value.__enter__.return_value = db

    with (
        mock.patch.object(feed_sync, "SessionLocal", session_maker),
        mock.patch.object(
            feed_sync,
            "_fetch_source_articles",
            side_effect=[["art1", "art2"], RuntimeError("网络失败")],
        ),
        mock.patch.object(feed_sync, "_upsert_articles", return_value=3),
    ):
        result = feed_sync.sync_all_sources_once()

    # s1 成功：3 篇新增，last_status=1
    assert result == {"total": 2, "added": 3, "failed": 1}
    assert s1.last_status == 1
    assert s1.last_error == ""
    assert s1.last_check_at is not None
    # s2 失败：last_status=2，记录错误
    assert s2.last_status == 2
    assert s2.last_error == "网络失败"
    assert s2.last_check_at is not None
    db.commit.assert_called_once()


def test_sync_all_sources_once_empty_sources():
    db = mock.MagicMock()
    (db.query.return_value.filter.return_value.all.return_value) = []
    session_maker = mock.MagicMock()
    session_maker.return_value.__enter__.return_value = db

    with mock.patch.object(feed_sync, "SessionLocal", session_maker):
        result = feed_sync.sync_all_sources_once()

    assert result == {"total": 0, "added": 0, "failed": 0}
    db.commit.assert_called_once()
    feed_sync._fetch_source_articles  # noqa  # 未调用亦可，无需额外断言