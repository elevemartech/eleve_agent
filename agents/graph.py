"""
StateGraph LangGraph — orquestração de todos os agentes.

Fluxo:
  router → [greeting|financial|faq|secretary|enrollment|protocol|announcement|human|closing]
         → END
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.router import router_node, route_to_agent
from agents.greeting import greeting_node
from agents.financial import financial_node
from agents.faq import faq_node
from agents.secretary import secretary_node
from agents.enrollment import enrollment_node
from agents.protocol import protocol_node
from agents.announcement import announcement_node
from agents.human import human_node
from agents.closing import closing_node


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Nós
    graph.add_node("router",       router_node)
    graph.add_node("greeting",     greeting_node)
    graph.add_node("financial",    financial_node)
    graph.add_node("faq",          faq_node)
    graph.add_node("secretary",    secretary_node)
    graph.add_node("enrollment",   enrollment_node)
    graph.add_node("protocol",     protocol_node)
    graph.add_node("announcement", announcement_node)
    graph.add_node("human",        human_node)
    graph.add_node("closing",      closing_node)

    # Entrada
    graph.set_entry_point("router")

    # Roteamento condicional após o router
    graph.add_conditional_edges(
        "router",
        route_to_agent,
        {
            "greeting":     "greeting",
            "financial":    "financial",
            "faq":          "faq",
            "secretary":    "secretary",
            "enrollment":   "enrollment",
            "protocol":     "protocol",
            "announcement": "announcement",
            "human":        "human",
            "closing":      "closing",
        },
    )

    # Todos os agentes terminam em END
    for node in ["greeting", "financial", "faq", "secretary",
                 "enrollment", "protocol", "announcement", "human", "closing"]:
        graph.add_edge(node, END)

    return graph.compile()


# Singleton compilado
agent_graph = build_graph()
