"""API 路由单元测试"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import app


@pytest.fixture
def client():
    """FastAPI 测试客户端"""
    return TestClient(app)


class TestHealthCheck:
    """健康检查接口测试"""

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "AvatarAgent"


class TestConfigRoutes:
    """配置管理路由测试"""

    def test_get_api_keys(self, client):
        response = client.get("/api/config/apikeys")
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data

    def test_add_and_delete_api_key(self, client):
        test_key = "test_api_key_unit_test"

        # 添加
        response = client.post(
            "/api/config/apikeys",
            json={"key": test_key},
        )
        assert response.status_code == 200

        # 验证存在
        response = client.get("/api/config/apikeys")
        assert test_key in response.json()["keys"]

        # 删除 - FastAPI DELETE with body需使用 request 方法
        response = client.request(
            "DELETE",
            "/api/config/apikeys",
            json={"key": test_key},
        )
        assert response.status_code == 200

        # 验证已删除
        response = client.get("/api/config/apikeys")
        assert test_key not in response.json()["keys"]

    def test_check_services(self, client):
        response = client.get("/api/config/services")
        assert response.status_code == 200
        data = response.json()
        assert "cosyvoice" in data
        assert "heygem" in data
        assert "tuilionnx" in data


class TestAudioRoutes:
    """音频处理路由测试"""

    def test_list_voices(self, client):
        response = client.get("/api/audio/voices")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_tts_service_status(self, client):
        response = client.get("/api/audio/service/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestVideoRoutes:
    """视频后期路由测试"""

    def test_list_fonts(self, client):
        response = client.get("/api/video/fonts")
        assert response.status_code == 200
        data = response.json()
        assert "fonts" in data
        assert len(data["fonts"]) > 0

    def test_list_bgm(self, client):
        response = client.get("/api/video/bgm")
        assert response.status_code == 200
        data = response.json()
        assert "bgm_list" in data


class TestAvatarRoutes:
    """数字人路由测试"""

    def test_heygem_status(self, client):
        response = client.get("/api/avatar/service/heygem/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_tuilionnx_status(self, client):
        response = client.get("/api/avatar/service/tuilionnx/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
