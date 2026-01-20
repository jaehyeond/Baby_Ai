"""A2A 에이전트 클라이언트 래퍼"""

import httpx
from uuid import uuid4
from typing import Optional, AsyncIterator

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    Message,
    MessageSendParams,
    Part,
    SendStreamingMessageRequest,
    TextPart,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    JSONRPCErrorResponse,
)


class AgentClient:
    """단일 A2A 에이전트와 통신하는 클라이언트"""

    def __init__(self, agent_url: str, httpx_client: httpx.AsyncClient):
        self.agent_url = agent_url
        self.httpx_client = httpx_client
        self.agent_card: Optional[AgentCard] = None
        self.client: Optional[A2AClient] = None

    async def connect(self) -> AgentCard:
        """에이전트에 연결하고 Agent Card를 가져옴"""
        resolver = A2ACardResolver(self.httpx_client, self.agent_url)
        self.agent_card = await resolver.get_agent_card()
        self.client = A2AClient(self.httpx_client, agent_card=self.agent_card)
        return self.agent_card

    async def send_message(self, content: str, context_id: Optional[str] = None) -> str:
        """
        메시지를 보내고 결과를 받음

        Args:
            content: 보낼 메시지 내용
            context_id: 컨텍스트 ID (없으면 새로 생성)

        Returns:
            에이전트 응답 텍스트
        """
        if not self.client:
            await self.connect()

        ctx_id = context_id or uuid4().hex

        message = Message(
            role="user",
            parts=[Part(root=TextPart(text=content))],
            message_id=str(uuid4()),
            context_id=ctx_id,
        )

        request = SendStreamingMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(message=message),
        )

        result_text = ""

        async for result in self.client.send_message_streaming(request):
            if isinstance(result.root, JSONRPCErrorResponse):
                raise Exception(f"Agent error: {result.root.error}")

            event = result.root.result

            if isinstance(event, TaskArtifactUpdateEvent):
                if event.artifact and event.artifact.parts:
                    for part in event.artifact.parts:
                        if hasattr(part, "root") and hasattr(part.root, "text"):
                            result_text = part.root.text

        return result_text

    @property
    def name(self) -> str:
        """에이전트 이름"""
        return self.agent_card.name if self.agent_card else "Unknown"


class AgentPool:
    """여러 에이전트를 관리하는 풀"""

    def __init__(self):
        self.agents: dict[str, AgentClient] = {}
        self.httpx_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.httpx_client = httpx.AsyncClient(timeout=120)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.httpx_client:
            await self.httpx_client.aclose()

    async def register(self, agent_id: str, agent_url: str) -> AgentCard:
        """
        에이전트를 풀에 등록

        Args:
            agent_id: 에이전트 식별자 (예: "coder", "tester")
            agent_url: 에이전트 URL

        Returns:
            Agent Card
        """
        client = AgentClient(agent_url, self.httpx_client)
        card = await client.connect()
        self.agents[agent_id] = client
        return card

    def get(self, agent_id: str) -> AgentClient:
        """에이전트 클라이언트 가져오기"""
        if agent_id not in self.agents:
            raise KeyError(f"Agent '{agent_id}' not found in pool")
        return self.agents[agent_id]

    async def call(self, agent_id: str, content: str) -> str:
        """
        에이전트 호출

        Args:
            agent_id: 에이전트 식별자
            content: 보낼 메시지

        Returns:
            에이전트 응답
        """
        return await self.get(agent_id).send_message(content)
