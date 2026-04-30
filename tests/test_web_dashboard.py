"""
PR-018: Web Dashboard 测试
验证前端构建和基本功能
"""

import os
import subprocess
import pytest

WEB_DIR = os.path.join(os.path.dirname(__file__), '..', 'web')


class TestWebBuild:
    """测试 Web 构建"""

    def test_web_directory_exists(self):
        """web 目录存在"""
        assert os.path.isdir(WEB_DIR)

    def test_package_json_exists(self):
        """package.json 存在"""
        assert os.path.isfile(os.path.join(WEB_DIR, 'package.json'))

    def test_vite_config_exists(self):
        """vite.config.ts 存在"""
        assert os.path.isfile(os.path.join(WEB_DIR, 'vite.config.ts'))

    def test_app_tsx_exists(self):
        """App.tsx 存在"""
        assert os.path.isfile(os.path.join(WEB_DIR, 'src', 'App.tsx'))

    def test_main_tsx_exists(self):
        """main.tsx 存在"""
        assert os.path.isfile(os.path.join(WEB_DIR, 'src', 'main.tsx'))

    def test_index_css_exists(self):
        """index.css 存在"""
        assert os.path.isfile(os.path.join(WEB_DIR, 'src', 'index.css'))

    def test_pages_directory_exists(self):
        """pages 目录存在"""
        assert os.path.isdir(os.path.join(WEB_DIR, 'src', 'pages'))

    def test_login_page_exists(self):
        """Login 页面存在"""
        assert os.path.isfile(os.path.join(WEB_DIR, 'src', 'pages', 'Login.tsx'))

    def test_notes_page_exists(self):
        """Notes 页面存在"""
        assert os.path.isfile(os.path.join(WEB_DIR, 'src', 'pages', 'Notes.tsx'))

    def test_note_editor_page_exists(self):
        """NoteEditor 页面存在"""
        assert os.path.isfile(os.path.join(WEB_DIR, 'src', 'pages', 'NoteEditor.tsx'))

    def test_tags_page_exists(self):
        """Tags 页面存在"""
        assert os.path.isfile(os.path.join(WEB_DIR, 'src', 'pages', 'Tags.tsx'))

    def test_activity_page_exists(self):
        """Activity 页面存在"""
        assert os.path.isfile(os.path.join(WEB_DIR, 'src', 'pages', 'Activity.tsx'))

    def test_settings_page_exists(self):
        """Settings 页面存在"""
        assert os.path.isfile(os.path.join(WEB_DIR, 'src', 'pages', 'Settings.tsx'))

    def test_dashboard_page_exists(self):
        """Dashboard 页面存在"""
        assert os.path.isfile(os.path.join(WEB_DIR, 'src', 'pages', 'Dashboard.tsx'))

    def test_api_lib_exists(self):
        """API 客户端存在"""
        assert os.path.isfile(os.path.join(WEB_DIR, 'src', 'lib', 'api.ts'))

    def test_dist_directory_exists(self):
        """dist 目录存在（构建产物）"""
        dist = os.path.join(WEB_DIR, 'dist')
        if os.path.isdir(dist):
            assert os.path.isfile(os.path.join(dist, 'index.html'))

    def test_vite_proxy_config(self):
        """Vite 代理配置正确"""
        config_path = os.path.join(WEB_DIR, 'vite.config.ts')
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert '/api' in content
        assert 'localhost:8000' in content


class TestWebDependencies:
    """测试 Web 依赖"""

    def test_react_installed(self):
        """React 已安装"""
        pkg_path = os.path.join(WEB_DIR, 'package.json')
        with open(pkg_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'react' in content

    def test_react_router_installed(self):
        """React Router 已安装"""
        pkg_path = os.path.join(WEB_DIR, 'package.json')
        with open(pkg_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'react-router-dom' in content

    def test_tailwind_installed(self):
        """Tailwind CSS 已安装"""
        pkg_path = os.path.join(WEB_DIR, 'package.json')
        with open(pkg_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert 'tailwindcss' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
