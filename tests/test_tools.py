"""Testes das tools — integração com a API (mockada)."""
import pytest
import respx
import httpx
import json


@pytest.mark.asyncio
async def test_get_guardian_by_phone_found():
    from tools.get_guardian_by_phone import get_guardian_by_phone

    mock_response = [
        {
            "id": 1234,
            "nome": "Maria Silva",
            "filhos": [
                {"id": 2070, "nome": "Pedro Silva", "serie": "5TH", "matricula": "20241234"}
            ],
        }
    ]

    with respx.mock:
        respx.get(
            "http://localhost:8000/api/v1/contacts/students/guardians/",
        ).mock(return_value=httpx.Response(200, json=mock_response))

        result = await get_guardian_by_phone.ainvoke({
            "phone": "5521999999999",
            "sa_token": "sa_live_test",
        })

    parsed = json.loads(result)
    assert parsed["found"] is True
    assert parsed["guardian_name"] == "Maria Silva"
    assert len(parsed["students"]) == 1
    assert parsed["students"][0]["name"] == "Pedro Silva"


@pytest.mark.asyncio
async def test_get_guardian_by_phone_not_found():
    from tools.get_guardian_by_phone import get_guardian_by_phone

    with respx.mock:
        respx.get(
            "http://localhost:8000/api/v1/contacts/students/guardians/",
        ).mock(return_value=httpx.Response(200, json=[]))

        result = await get_guardian_by_phone.ainvoke({
            "phone": "5521000000000",
            "sa_token": "sa_live_test",
        })

    parsed = json.loads(result)
    assert parsed["found"] is False


@pytest.mark.asyncio
async def test_create_evaluation_success():
    from tools.create_evaluation import create_evaluation

    with respx.mock:
        respx.post(
            "http://localhost:8000/api/v1/evaluations/",
        ).mock(return_value=httpx.Response(201, json={"id": "abc", "rating": 9}))

        result = await create_evaluation.ainvoke({
            "name": "Maria Silva",
            "phone": "5521999999999",
            "rating": 9,
            "channel": "whatsapp",
            "sa_token": "sa_live_test",
        })

    assert "9/10" in result


@pytest.mark.asyncio
async def test_search_faq_found():
    from tools.search_faq import search_faq

    mock_response = {
        "results": [
            {"question": "Qual o horário?", "answer": "Das 7h às 17h."},
        ]
    }

    with respx.mock:
        respx.get(
            "http://localhost:8000/api/v1/faqs/",
        ).mock(return_value=httpx.Response(200, json=mock_response))

        result = await search_faq.ainvoke({
            "query": "horário",
            "sa_token": "sa_live_test",
        })

    assert "7h" in result
