"""A2A CLI 클라이언트"""

import asyncio
import sys
from uuid import uuid4

import click
import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    Part,
    SendMessageRequest,
    SendStreamingMessageRequest,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
)


async def run_client(agent_url: str):
    """A2A 클라이언트 실행"""
    print(f"\n{'='*50}")
    print(f"A2A CLI Client")
    print(f"{'='*50}\n")

    async with httpx.AsyncClient(timeout=120) as httpx_client:
        try:
            # Agent Card 가져오기
            print(f"[연결 중] {agent_url}")
            resolver = A2ACardResolver(httpx_client, agent_url)
            card = await resolver.get_agent_card()

            print(f"[연결 완료] {card.name}")
            print(f"[설명] {card.description}")
            if card.skills:
                print(f"[스킬] {', '.join(s.name for s in card.skills)}")
            print()

        except Exception as e:
            print(f"[오류] Agent 연결 실패: {e}")
            return

        # A2A 클라이언트 생성
        client = A2AClient(httpx_client, agent_card=card)
        context_id = uuid4().hex
        streaming = card.capabilities and card.capabilities.streaming

        # 대화 루프
        while True:
            try:
                # 사용자 입력 받기
                user_input = input("\n입력> ").strip()

                if not user_input:
                    continue

                if user_input.lower() in [":q", "quit", "exit"]:
                    print("\n종료합니다.")
                    break

                # 메시지 생성
                message = Message(
                    role="user",
                    parts=[Part(root=TextPart(text=user_input))],
                    message_id=str(uuid4()),
                    context_id=context_id,
                )

                params = MessageSendParams(message=message)

                if streaming:
                    # 스트리밍 요청
                    await handle_streaming_response(client, params, context_id)
                else:
                    # 일반 요청
                    await handle_normal_response(client, params)

            except KeyboardInterrupt:
                print("\n\n중단됨.")
                break
            except Exception as e:
                print(f"\n[오류] {e}")


async def handle_streaming_response(
    client: A2AClient,
    params: MessageSendParams,
    context_id: str,
):
    """스트리밍 응답 처리"""
    request = SendStreamingMessageRequest(
        id=str(uuid4()),
        params=params,
    )

    print()  # 줄바꿈

    async for result in client.send_message_streaming(request):
        # 에러 체크
        if isinstance(result.root, JSONRPCErrorResponse):
            print(f"[오류] {result.root.error}")
            return

        event = result.root.result

        if isinstance(event, Task):
            # 태스크 생성됨
            pass

        elif isinstance(event, TaskStatusUpdateEvent):
            # 상태 업데이트
            state = event.status.state
            if state == TaskState.working:
                if event.status.message and event.status.message.parts:
                    msg = event.status.message.parts[0]
                    if hasattr(msg, "root") and hasattr(msg.root, "text"):
                        print(f"[작업 중] {msg.root.text}")

            elif state == TaskState.completed:
                print("[완료]")

            elif state == TaskState.input_required:
                if event.status.message and event.status.message.parts:
                    msg = event.status.message.parts[0]
                    if hasattr(msg, "root") and hasattr(msg.root, "text"):
                        print(f"[추가 입력 필요] {msg.root.text}")

        elif isinstance(event, TaskArtifactUpdateEvent):
            # 결과물 수신
            artifact = event.artifact
            if artifact and artifact.parts:
                for part in artifact.parts:
                    if hasattr(part, "root") and hasattr(part.root, "text"):
                        print(f"\n{part.root.text}")

        elif isinstance(event, Message):
            # 직접 메시지
            if event.parts:
                for part in event.parts:
                    if hasattr(part, "root") and hasattr(part.root, "text"):
                        print(part.root.text)


async def handle_normal_response(client: A2AClient, params: MessageSendParams):
    """일반(non-streaming) 응답 처리"""
    request = SendMessageRequest(
        id=str(uuid4()),
        params=params,
    )

    response = await client.send_message(request)

    if isinstance(response.root, JSONRPCErrorResponse):
        print(f"[오류] {response.root.error}")
        return

    result = response.root.result

    if isinstance(result, Task):
        # 태스크 결과
        if result.artifacts:
            for artifact in result.artifacts:
                if artifact.parts:
                    for part in artifact.parts:
                        if hasattr(part, "root") and hasattr(part.root, "text"):
                            print(f"\n{part.root.text}")
        elif result.status and result.status.message:
            for part in result.status.message.parts:
                if hasattr(part, "root") and hasattr(part.root, "text"):
                    print(part.root.text)

    elif isinstance(result, Message):
        # 메시지 결과
        for part in result.parts:
            if hasattr(part, "root") and hasattr(part.root, "text"):
                print(part.root.text)


@click.command()
@click.option(
    "--agent",
    default="http://localhost:9999",
    help="A2A Agent URL",
)
def main(agent: str):
    """A2A CLI 클라이언트를 시작합니다."""
    try:
        asyncio.run(run_client(agent))
    except Exception as e:
        print(f"실행 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
