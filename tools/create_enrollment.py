"""Tool: Registra solicitação de matrícula com protocolo no funil da API."""
from langchain_core.tools import tool
from core.api_client import DjangoAPIClient


@tool
async def create_enrollment(
    candidate_name: str,
    responsible_name: str,
    phone: str,
    candidate_dob: str = "",
    responsible_email: str = "",
    desired_grade: str = "",
    desired_shift: str = "",
    request_type: str = "nova",
    sa_token: str = "",
    session_id: str = "",
    **kwargs,
) -> str:
    """
    Registra interesse de matrícula na API.
    request_type: nova | rematricula | transferencia
    desired_shift: M (manhã) | T (tarde) | I (integral)
    """
    client = DjangoAPIClient(token=sa_token)
    try:
        payload = {
            "candidate_name": candidate_name,
            "request_type": request_type,
            "responsible_name": responsible_name,
            "responsible_phone": phone,
            "responsible_email": responsible_email,
            "desired_grade_name": desired_grade,
            "desired_shift": desired_shift[:1].upper() if desired_shift else "",
            "candidate_dob": candidate_dob,
            "channel": "whatsapp",
            "notes": f"Captação via WhatsApp. Session: {session_id}" if session_id else "Captação via WhatsApp",
        }
        result = await client.post("/api/v1/secretary/enrollments/", json=payload)
        protocol = result.get("protocol", result.get("id", ""))
        return (
            f"Solicitação de matrícula registrada!\n"
            f"Protocolo: {protocol}\n"
            f"Aluno: {candidate_name}\n"
            f"Nossa equipe entrará em contato em breve."
        )
    except Exception as e:
        return f"Não foi possível registrar: {e}"
