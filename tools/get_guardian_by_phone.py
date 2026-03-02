"""Tool: Identifica responsável pelo número de telefone via SIGA."""
import json
from langchain_core.tools import tool
from core.api_client import DjangoAPIClient


@tool
async def get_guardian_by_phone(phone: str, sa_token: str, **kwargs) -> str:
    """
    Identifica o responsável pelo telefone e retorna dados dos filhos.
    Retorna JSON com found, guardian_id, guardian_name e lista de alunos.
    """
    client = DjangoAPIClient(token=sa_token)

    # Remove caracteres não numéricos
    phone_digits = "".join(filter(str.isdigit, phone))

    try:
        result = await client.get(
            "/api/v1/contacts/students/guardians/",
            params={"search": phone_digits},
        )
        guardians = result if isinstance(result, list) else result.get("results", [])

        if not guardians:
            return json.dumps({
                "found": False,
                "message": "Responsável não encontrado no sistema.",
            }, ensure_ascii=False)

        guardian = guardians[0]
        students = []
        for filho in guardian.get("filhos", []):
            students.append({
                "id": str(filho.get("id", "")),
                "name": filho.get("nome", ""),
                "grade": filho.get("serie", ""),
                "enrollment": filho.get("matricula", ""),
            })

        ctx = {
            "found": True,
            "guardian_id": str(guardian.get("id", "")),
            "guardian_name": guardian.get("nome", guardian.get("name", "")),
            "students": students,
        }
        return json.dumps(ctx, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "found": False,
            "message": f"Erro ao consultar: {e}",
        }, ensure_ascii=False)
