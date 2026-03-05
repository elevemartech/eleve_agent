"""Tool: Últimas solicitações dos alunos vinculados ao responsável."""
import json
from langchain_core.tools import tool
from core.api_client import DjangoAPIClient


STATUS_PT = {
    "pending":           "Pendente",
    "in_review":         "Em análise",
    "awaiting_approval": "Aguardando aprovação",
    "approved":          "Aprovado",
    "in_progress":       "Em andamento",
    "completed":         "Concluído ✅",
    "rejected":          "Não aprovado",
    "cancelled":         "Cancelado",
}


@tool
async def get_requests_by_guardian(
    guardian_context: str,
    sa_token: str,
    **kwargs,
) -> str:
    """
    Retorna as últimas solicitações dos alunos vinculados ao responsável.
    Recebe guardian_context como JSON string (saída de get_guardian_by_phone).
    """
    # CORREÇÃO: o parâmetro anterior era `guardian_id` (UUID do responsável),
    # mas o campo `siga_user_id` no model Request representa o aluno, não o
    # responsável. A busca correta é por cada siga_student_id dos filhos.
    client = DjangoAPIClient(token=sa_token)

    try:
        ctx = json.loads(guardian_context) if isinstance(guardian_context, str) else guardian_context
    except (json.JSONDecodeError, TypeError):
        return "Erro: guardian_context inválido."

    students = ctx.get("students", [])

    if not students:
        return "Nenhum aluno vinculado ao responsável para consultar solicitações."

    all_items = []

    for student in students:
        siga_student_id = student.get("siga_student_id", "")
        student_name = student.get("name", "?")

        if not siga_student_id:
            continue

        try:
            result = await client.get(
                "/api/v1/requests/by_siga_user/",
                params={
                    "siga_user_id": siga_student_id,
                    "ordering": "-created_at",
                    "page_size": 3,
                },
            )
            items = result.get("results", result) if isinstance(result, dict) else result

            for item in items:
                all_items.append({**item, "_student_name": student_name})

        except Exception as e:
            all_items.append({
                "_student_name": student_name,
                "_error": str(e),
            })

    if not all_items:
        return "Nenhuma solicitação encontrada para os alunos deste responsável."

    lines = []
    for item in all_items:
        if item.get("_error"):
            lines.append(f"• Aluno: {item['_student_name']} | Erro ao consultar: {item['_error']}")
            continue

        status_label = STATUS_PT.get(item.get("status", ""), item.get("status", ""))
        lines.append(
            f"• Protocolo: {item.get('protocol', '?')} | "
            f"Tipo: {item.get('request_type_display', item.get('request_type', '?'))} | "
            f"Status: {status_label} | "
            f"Aluno: {item.get('siga_user_name', item['_student_name'])}"
        )

    return "Solicitações encontradas:\n" + "\n".join(lines)