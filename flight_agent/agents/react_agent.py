from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_core.messages import AIMessage, ToolMessage

def build_react_graph(
    model: Any,
    tool_executor: Callable[[List[Dict[str, Any]]], List[ToolMessage]],
    should_halt: Optional[Callable[[], bool]] = None,
):
    """
    Constructs a LangGraph ReAct agent loop:
    START -> agent -> (should_continue?) -> tools -> agent ... -> END
    Respects external harness termination signals (human stop, loop, stall, budget).
    """
    def agent_node(state: MessagesState) -> Dict[str, Any]:
        response = model.invoke(state["messages"])
        return {"messages": [response]}

    def tools_node(state: MessagesState) -> Dict[str, Any]:
        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return {"messages": []}
        tool_messages = tool_executor(last_message.tool_calls)
        return {"messages": tool_messages}

    def should_continue(state: MessagesState) -> str:
        if should_halt and should_halt():
            return END
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)

    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()
