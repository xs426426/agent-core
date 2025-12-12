"""
无人机 Agent 命令行交互界面
"""
import requests
import sys

API_URL = "http://localhost:8000/api/agent/chat"
SESSION_ID = "cli-session"

def chat(message: str) -> str:
    """发送消息给 Agent"""
    try:
        resp = requests.post(API_URL, json={
            "message": message,
            "session_id": SESSION_ID
        }, timeout=60)
        data = resp.json()
        if data.get("success"):
            return data.get("response", "无响应")
        else:
            return f"错误: {data.get('error', '未知错误')}"
    except requests.exceptions.ConnectionError:
        return "错误: 无法连接到服务器，请确保服务已启动 (python -m uvicorn app.main:app)"
    except Exception as e:
        return f"错误: {str(e)}"

def main():
    print("=" * 50)
    print("  无人机智能控制助手")
    print("  输入自然语言指令与无人机交互")
    print("  输入 'quit' 或 'exit' 退出")
    print("=" * 50)
    print()

    while True:
        try:
            user_input = input("你: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["quit", "exit", "q"]:
                print("再见!")
                break

            print("思考中...")
            response = chat(user_input)
            print(f"\n助手: {response}\n")

        except KeyboardInterrupt:
            print("\n再见!")
            break

if __name__ == "__main__":
    main()
