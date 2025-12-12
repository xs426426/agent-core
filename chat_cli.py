"""
Agent 对话命令行工具
直接在终端和 Agent 进行自然语言对话
"""
import httpx
import sys

AGENT_URL = "http://localhost:8000/api/agent/chat"
SESSION_ID = "cli-user"

def chat(message: str) -> str:
    """发送消息给 Agent"""
    try:
        response = httpx.post(
            AGENT_URL,
            json={"message": message, "session_id": SESSION_ID},
            timeout=120.0
        )
        data = response.json()
        if data.get("success"):
            return data.get("response", "无响应")
        else:
            return f"错误: {data.get('error', '未知错误')}"
    except httpx.ConnectError:
        return "错误: 无法连接到 Agent 服务，请确保服务已启动 (端口 8000)"
    except Exception as e:
        return f"错误: {str(e)}"

def main():
    print("=" * 50)
    print("  Agent 对话终端")
    print("  输入自然语言和无人机 Agent 对话")
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

            print("Agent 思考中...")
            response = chat(user_input)
            print(f"\nAgent: {response}\n")
            print("-" * 50)

        except KeyboardInterrupt:
            print("\n再见!")
            break
        except EOFError:
            break

if __name__ == "__main__":
    main()
