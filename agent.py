from datetime import datetime
from typing import List, Literal

from langchain_core.messages import SystemMessage, merge_message_runs
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.store.base import BaseStore

from memory import MemoryManager
from models import Ingredients, Preferences, UpdateMemory
from prompts import (
    INGREDIENTS_INSTRUCTION,
    MODEL_SYSTEM_MESSAGE,
    PREFERENCES_INSTRUCTION,
)


class IngredientTrackerAgent:
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.model = self._initialize_model()
        self.preferences_llm = self.model.with_structured_output(Preferences)
        self.ingredients_llm = self.model.with_structured_output(Ingredients)
        self.graph = self._build_graph()

    def _initialize_model(self):
        """Initialize the LLM"""
        return ChatOpenAI(
            model="qwen3:14b",
            temperature=0,
            base_url="http://localhost:11434/v1",
            api_key="not-needed",
        )

    def _build_graph(self):
        """Builds and returns the LangGraph"""
        builder = StateGraph(MessagesState)

        builder.add_node("update_preferences", self._update_preferences)
        builder.add_node("update_ingredients", self._update_ingredients)
        builder.add_node("chat", self._chat)

        builder.add_edge(START, "chat")
        builder.add_conditional_edges("chat", self._route_message)
        builder.add_edge("update_preferences", "chat")
        builder.add_edge("update_ingredients", "chat")

        return builder.compile(
            checkpointer=self.memory_manager.checkpointer,
            store=self.memory_manager.store,
        )

    def _chat(self, state: MessagesState, config: RunnableConfig, store: BaseStore):
        """Main chat node that processes user input and generates responses"""
        user_id = config["configurable"]["user_id"]

        user_preferences = self.memory_manager.get_preferences(user_id)
        ingredients = self.memory_manager.get_ingredients(user_id)

        system_msg = MODEL_SYSTEM_MESSAGE.format(
            user_preferences=user_preferences, ingredients=ingredients
        )

        response = self.model.bind_tools(
            [UpdateMemory], parallel_tool_calls=True
        ).invoke([SystemMessage(content=system_msg)] + state["messages"])

        return {"messages": [response]}

    def _update_preferences(
        self, state: MessagesState, config: RunnableConfig, store: BaseStore
    ):
        """Update user preferences based on conversation"""
        user_id = config["configurable"]["user_id"]
        existing_preferences = self.memory_manager.get_preferences(user_id)

        instruction = PREFERENCES_INSTRUCTION.format(
            current_preferences=existing_preferences, time=datetime.now().isoformat()
        )

        updated_messages = list(
            merge_message_runs(
                [SystemMessage(content=instruction)] + state["messages"][:-1]
            )
        )

        result = self.preferences_llm.invoke(updated_messages)
        self.memory_manager.update_preferences(user_id, result.model_dump_json())

        tool_calls = state["messages"][-1].tool_calls
        return {
            "messages": [
                {
                    "role": "tool",
                    "content": "preferences have been updated",
                    "tool_call_id": tool_calls[0]["id"],
                }
            ]
        }

    def _update_ingredients(
        self, state: MessagesState, config: RunnableConfig, store: BaseStore
    ):
        """Update user ingredients based on conversation"""
        user_id = config["configurable"]["user_id"]
        existing_ingredients = self.memory_manager.get_ingredients(user_id)

        instruction = INGREDIENTS_INSTRUCTION.format(
            current_ingredients=existing_ingredients, time=datetime.now().isoformat()
        )

        updated_messages = list(
            merge_message_runs(
                [SystemMessage(content=instruction)] + state["messages"][:-1]
            )
        )

        result = self.ingredients_llm.invoke(updated_messages)
        self.memory_manager.update_ingredients(user_id, result.model_dump_json())

        tool_calls = state["messages"][-1].tool_calls
        return {
            "messages": [
                {
                    "role": "tool",
                    "content": "ingredients have been updated",
                    "tool_call_id": tool_calls[0]["id"],
                }
            ]
        }

    def _route_message(
        self, state: MessagesState, config: RunnableConfig, store: BaseStore
    ) -> List[Literal["update_preferences", "update_ingredients", END]]:
        """Route to appropriate nodes based on tool calls"""
        message = state["messages"][-1]
        routes = []

        if not hasattr(message, "tool_calls") or not message.tool_calls:
            return [END]

        for tool_call in message.tool_calls:
            if tool_call["args"]["update_type"] == "preferences":
                routes.append("update_preferences")
            elif tool_call["args"]["update_type"] == "ingredients":
                routes.append("update_ingredients")

        if not routes:
            routes.append(END)

        return routes

    def invoke(self, messages, config):
        """Invoke the graph with the given messages and config"""
        return self.graph.invoke({"messages": messages}, config=config)
