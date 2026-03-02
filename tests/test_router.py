"""Testes do router — classificação de intenção."""
import pytest
from unittest.mock import AsyncMock, patch
from agents.state import AgentState


def make_state(**kwargs) -> AgentState:
    return {
        "input": "olá",
        "phone": "5521999999999",
        "contact_name": "Maria",
        "school_id": "1",
        "school_name": "Escola Teste",
        "sa_token": "sa_live_test",
        "session_id": "abc-123",
        "instance_token": "tok",
        "history": [],
        "response": "",
        "current_agent": "",
        "current_step": 0,
        "keep_flow": False,
        "collected_data": {},
        "guardian_context": None,
        **kwargs,
    }


@pytest.mark.asyncio
async def test_router_greeting():
    """Sessão nova com saudação deve rotear para greeting."""
    with patch("agents.router.ChatOpenAI") as MockLLM:
        mock_instance = AsyncMock()
        mock_instance.ainvoke = AsyncMock(
            return_value=type("R", (), {"content": '{"agent": "greeting", "keep_flow": false, "confidence": 0.97}'})()
        )
        MockLLM.return_value = mock_instance

        from agents.router import router_node
        state = make_state(input="Boa tarde!")
        result = await router_node(state)

        assert result["current_agent"] == "greeting"
        assert result["keep_flow"] is False


@pytest.mark.asyncio
async def test_router_keep_flow():
    """Resposta curta com agente ativo deve manter keep_flow=true."""
    with patch("agents.router.ChatOpenAI") as MockLLM:
        mock_instance = AsyncMock()
        mock_instance.ainvoke = AsyncMock(
            return_value=type("R", (), {"content": '{"agent": "secretary", "keep_flow": true, "confidence": 0.92}'})()
        )
        MockLLM.return_value = mock_instance

        from agents.router import router_node
        state = make_state(
            input="Pedro Silva",
            current_agent="secretary",
            current_step=1,
        )
        result = await router_node(state)

        assert result["current_agent"] == "secretary"
        assert result["keep_flow"] is True


@pytest.mark.asyncio
async def test_router_financial():
    """Mensagem sobre boleto deve rotear para financial."""
    with patch("agents.router.ChatOpenAI") as MockLLM:
        mock_instance = AsyncMock()
        mock_instance.ainvoke = AsyncMock(
            return_value=type("R", (), {"content": '{"agent": "financial", "keep_flow": false, "confidence": 0.95}'})()
        )
        MockLLM.return_value = mock_instance

        from agents.router import router_node
        state = make_state(input="Preciso do boleto de novembro")
        result = await router_node(state)

        assert result["current_agent"] == "financial"


@pytest.mark.asyncio
async def test_router_fallback_on_error():
    """Erro no LLM deve retornar faq como fallback."""
    with patch("agents.router.ChatOpenAI") as MockLLM:
        mock_instance = AsyncMock()
        mock_instance.ainvoke = AsyncMock(side_effect=Exception("LLM error"))
        MockLLM.return_value = mock_instance

        from agents.router import router_node
        state = make_state(input="qualquer coisa")
        result = await router_node(state)

        assert result["current_agent"] == "faq"
        assert result["keep_flow"] is False
