# ===================================================================
# tools/get_guardian_by_phone.py
#
# CORREÇÃO: endpoint atualizado de
#   /api/v1/contacts/students/guardians/   ← não existe
# para
#   /api/v1/people/lookup-whatsapp/        ← endpoint real da API
#
# O endpoint lookup-whatsapp recebe ?phone=<numero> e retorna:
# {
#   "found": true,
#   "guardian": { "id": "uuid", "name": "...", "phone": "..." },
#   "students": [
#     { "id": "uuid", "name": "...", "enrollment_number": "...",
#       "current_class": "...", "siga_student_id": "...", "relationship": "..." }
#   ]
# }
# ===================================================================

import json
from langchain_core.tools import tool
from core.api_client import DjangoAPIClient


@tool
async def get_guardian_by_phone(phone: str, sa_token: str, **kwargs) -> str:
    """
    Identifica o responsável pelo número de WhatsApp e retorna dados dos filhos matriculados.
    Retorna JSON com found, guardian_id, guardian_name e lista de alunos.
    Use sempre no início do atendimento para personalizar a conversa.
    """
    client = DjangoAPIClient(token=sa_token)

    # Normaliza: mantém apenas dígitos
    phone_digits = "".join(filter(str.isdigit, phone))

    try:
        result = await client.get(
            "/api/v1/people/lookup-whatsapp/",
            params={"phone": phone_digits},
        )

        # Resposta: {"found": bool, "guardian": {...}, "students": [...]}
        if not result.get("found"):
            return json.dumps({
                "found": False,
                "message": "Responsável não encontrado no sistema.",
            }, ensure_ascii=False)

        guardian = result.get("guardian", {})
        students = []
        for s in result.get("students", []):
            students.append({
                "id": str(s.get("id", "")),
                "name": s.get("name", ""),
                "grade": s.get("current_class", ""),
                "enrollment": s.get("enrollment_number", ""),
                "relationship": s.get("relationship", ""),
            })

        ctx = {
            "found": True,
            "guardian_id": str(guardian.get("id", "")),
            "guardian_name": guardian.get("name", ""),
            "students": students,
        }
        return json.dumps(ctx, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "found": False,
            "message": f"Erro ao consultar: {e}",
        }, ensure_ascii=False)