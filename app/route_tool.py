from app.utils.tool_utils import route_tool


@route_tool
def cambia_agente(  # Name must match the one in the route_tool_schema.py file
    current_agent: str,
    target_agent: str,
    summary: str = "",
    reason: str = "",
) -> str:
    # Implement any logic needed here. The agents won't see the output of this function but
    # it can be used to log or process the change.
    return f"Agente cambiado de {current_agent} a {target_agent}."


schema_params = {
    "DESCRIPTION": "Herramienta para cambiar el agente actual a otro agente.",
    "FIELDS": {
        "current_agent": "Nombre del agente actual.",
        "target_agent": "Nombre del agente al que se cambiará.",
        "summary": "Resumen de la conversación hasta el momento.",
        "reason": "Razón para cambiar de agente.",
    },
    "CURRENT_AGENT_FIELD": "current_agent",
    "TARGET_AGENT_FIELD": "target_agent",
    "REQUIRED_FIELDS": [
        "current_agent",
        "target_agent",
        "summary",
    ],  # Or None if all are required
}
