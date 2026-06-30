"""
LangGraph workflow builder and runner implementation.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import AIMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph
from langgraph.types import Command, interrupt

from src.agents.analyst import analyst_node
from src.agents.recommender import create_recommender_node
from src.agents.researcher import researcher_node
from src.agents.state import InvestmentAgentState
from src.config import AppConfig, get_config, get_api_keys
from src.logger import get_logger

logger = get_logger(__name__)


def human_approval_node(state: InvestmentAgentState) -> dict[str, Any]:
    """Halts execution to await human approval/modification of the portfolio recommendation.

    Args:
        state: Shared LangGraph state.

    Returns:
        State updates with the user's decision.
    """
    logger.info("Human approval gate activated, pausing execution...")
    
    # Pack up the proposed recommendation for the UI/Interrupt response
    payload = {
        "portfolio_recommendation": state.get("portfolio_recommendation"),
        "watchlist": state.get("tickers"),
    }
    
    # This halts graph execution and yields control back to the caller
    decision = interrupt(payload)
    
    logger.info("Human approval decision received", decision=decision)
    return {"human_approval": decision}


def route_after_approval(state: InvestmentAgentState) -> Literal["continue", "end"]:
    """Determines transition logic based on user gate decision.

    Args:
        state: Shared state.
    """
    approval = state.get("human_approval")
    if approval == "approve":
        return "continue"
    return "end"


def build_investment_graph(config: AppConfig, api_keys: Any) -> Any:
    """Builds and compiles the sequential multi-agent LangGraph workflow.

    Args:
        config: Loaded AppConfig.
        api_keys: Loaded APIKeys.

    Returns:
        Compiled LangGraph compiled graph.
    """
    logger.info("Building investment graph workflow...")

    # 1. Initialize LLM
    llm_conf = config.llm
    if llm_conf.provider == "openai" and api_keys.openai_api_key:
        logger.info("Initializing OpenAI client", model=llm_conf.model)
        llm = ChatOpenAI(
            model=llm_conf.model,
            temperature=llm_conf.temperature,
            api_key=api_keys.openai_api_key,
        )
    else:
        logger.info("Initializing local Ollama client", model=llm_conf.model)
        llm = ChatOllama(
            model=llm_conf.model,
            temperature=llm_conf.temperature,
        )

    # 2. Set up nodes
    recommender = create_recommender_node(llm)

    # 3. Assemble Graph
    builder = StateGraph(InvestmentAgentState)

    builder.add_node("researcher", researcher_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("recommender", recommender)
    builder.add_node("human_approval", human_approval_node)

    # 4. Wire edges sequentially
    builder.add_edge(START, "researcher")
    builder.add_edge("researcher", "analyst")
    builder.add_edge("analyst", "recommender")
    builder.add_edge("recommender", "human_approval")
    
    # Conditional edge after approval gate
    builder.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {
            "continue": END,
            "end": END,
        }
    )

    # Compile with memory persistence
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    logger.info("Graph compilation successful")
    return graph


def run_investment_analysis(graph: Any, tickers: list[str], thread_id: str) -> dict[str, Any]:
    """Runs the investment analysis graph until it interrupts at the human approval gate.

    Args:
        graph: Compiled LangGraph object.
        tickers: Watchlist tickers.
        thread_id: Unique execution identifier.

    Returns:
        Graph output (usually showing proposed recommendations before approval).
    """
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "tickers": tickers,
        "audit_log": [f"Pipeline started for {', '.join(tickers)}."],
        "error_log": [],
    }
    
    logger.info("Starting graph execution run", thread_id=thread_id)
    return graph.invoke(initial_state, config=config)


def resume_with_approval(graph: Any, thread_id: str, decision: str) -> dict[str, Any]:
    """Resumes a paused graph after the approval gate.

    Args:
        graph: Compiled LangGraph object.
        thread_id: Execution identifier.
        decision: One of 'approve', 'reject'.

    Returns:
        Final graph execution state.
    """
    config = {"configurable": {"thread_id": thread_id}}
    logger.info("Resuming graph execution run", thread_id=thread_id, decision=decision)
    # Resume by sending the user's decision payload via Command
    return graph.invoke(Command(resume=decision), config=config)
