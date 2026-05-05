#!/usr/bin/env python3
"""
NovelOps 内测版功能测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

def test_config():
    """测试配置加载"""
    print("测试配置加载...")
    from novelops.config import load_app_config, load_invites, validate_invite_code, get_session_secret

    cfg = load_app_config()
    print(f"  ✓ 配置加载成功")

    invites = load_invites()
    print(f"  ✓ 邀请码配置: {len(invites)} 个")

    # 测试邀请码验证
    test_code = list(invites.keys())[0] if invites else None
    if test_code:
        result = validate_invite_code(test_code)
        print(f"  ✓ 邀请码验证: {test_code} -> {result}")

    try:
        secret = get_session_secret()
        print(f"  ✓ Session 密钥已配置")
    except Exception as e:
        print(f"  ⚠ Session 密钥: {e}")

def test_session():
    """测试 session 管理"""
    print("\n测试 session 管理...")
    from novelops.session import get_serializer, get_session, set_session, clear_session
    from fastapi import Request, Response
    from fastapi.testclient import TestClient

    serializer = get_serializer()
    print(f"  ✓ Session 序列化器创建成功")

    # 测试序列化
    data = {"project_id": "test_project", "user": "test"}
    token = serializer.dumps(data)
    decoded = serializer.loads(token)
    assert decoded == data
    print(f"  ✓ Session 序列化/反序列化正常")

def test_web_app():
    """测试 Web 应用"""
    print("\n测试 Web 应用...")
    from novelops.web import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    client = TestClient(app)

    # 测试邀请码页面
    response = client.get("/invite")
    assert response.status_code == 200
    print(f"  ✓ 邀请码页面访问正常")

    # 测试未登录访问首页（应该重定向到邀请码页）
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/invite"
    print(f"  ✓ 未登录重定向正常")

    # 测试无效邀请码
    response = client.post("/invite", data={"code": "INVALID"})
    assert response.status_code == 200
    assert "邀请码无效" in response.text
    print(f"  ✓ 无效邀请码处理正常")

    # 测试有效邀请码
    from novelops.config import load_invites
    invites = load_invites()
    if invites:
        valid_code = list(invites.keys())[0]
        response = client.post("/invite", data={"code": valid_code}, follow_redirects=False)
        assert response.status_code == 303
        # 新版本重定向到项目列表
        assert response.headers["location"] == "/projects"
        print(f"  ✓ 有效邀请码登录正常")

        # 测试登录后访问项目列表
        cookies = response.cookies
        response = client.get("/projects", cookies=cookies)
        assert response.status_code == 200
        print(f"  ✓ 登录后访问项目列表正常")


def test_multi_project():
    """测试多项目功能"""
    print("\n测试多项目功能...")
    from novelops.user import add_user_project, get_user_projects, check_project_access
    from novelops.indexer import connect

    # 创建测试用户和项目关联
    with connect() as conn:
        # 清理测试数据
        conn.execute("DELETE FROM user_projects WHERE user_id LIKE 'test_%'")
        conn.commit()

        # 添加测试关联
        add_user_project("test_user1", "life_balance", is_default=True)
        print(f"  ✓ 添加用户项目关联")

        # 测试权限检查
        assert check_project_access("test_user1", "life_balance")
        assert not check_project_access("test_user2", "life_balance")
        print(f"  ✓ 权限检查正常")

        # 测试获取用户项目
        projects = get_user_projects("test_user1")
        assert len(projects) > 0
        print(f"  ✓ 获取用户项目列表正常")

        # 清理测试数据
        conn.execute("DELETE FROM user_projects WHERE user_id LIKE 'test_%'")
        conn.commit()

def test_templates():
    """测试模板文件"""
    print("\n测试模板文件...")
    from pathlib import Path

    templates_dir = Path(__file__).parent / "novelops" / "templates"
    required_templates = ["invite.html", "workspace.html", "base.html"]

    for template in required_templates:
        path = templates_dir / template
        assert path.exists(), f"模板文件不存在: {template}"
        print(f"  ✓ {template} 存在")

def test_deploy_files():
    """测试部署文件"""
    print("\n测试部署文件...")
    from pathlib import Path

    deploy_dir = Path(__file__).parent / "deploy"
    required_files = [
        "nginx.conf",
        "novelops.service",
        "backup.sh",
        "DEPLOYMENT.md"
    ]

    for file in required_files:
        path = deploy_dir / file
        assert path.exists(), f"部署文件不存在: {file}"
        print(f"  ✓ {file} 存在")

def main():
    print("=" * 60)
    print("NovelOps 内测版功能测试")
    print("=" * 60)

    try:
        test_config()
        test_session()
        test_templates()
        test_deploy_files()
        test_multi_project()
        test_web_app()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
