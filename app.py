import uuid

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

from agent import IngredientTrackerAgent
from memory import MemoryManager
from models import Ingredients, Preferences

load_dotenv()

st.set_page_config(page_title="Ingredient Tracker Chatbot", layout="wide")
st.title("🍳 Ingredient Tracker Chatbot")

if "memory_manager" not in st.session_state:
    st.session_state.memory_manager = MemoryManager()
if "user_id" not in st.session_state:
    st.session_state.user_id = "test_user"  # str(uuid.uuid4())
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = (
        st.session_state.memory_manager.load_streamlit_messages(
            st.session_state.user_id
        )
        or []
    )
if "agent" not in st.session_state:
    st.session_state.agent = IngredientTrackerAgent(st.session_state.memory_manager)
if "placeholder" not in st.session_state:
    st.session_state.placeholder = None


def get_preferences():
    return st.session_state.memory_manager.get_preferences(st.session_state.user_id)


def get_ingredients():
    return st.session_state.memory_manager.get_ingredients(st.session_state.user_id)


with st.sidebar:
    st.subheader("📋 Your Preferences")
    preferences_data = get_preferences()
    if preferences_data:
        try:
            prefs = Preferences.model_validate_json(preferences_data)

            if prefs.likes:
                st.write("**Likes:**")
                for item in prefs.likes:
                    st.write(f"- {item}")

            if prefs.dislikes:
                st.write("**Dislikes:**")
                for item in prefs.dislikes:
                    st.write(f"- {item}")

            if prefs.dietary_restrictions:
                st.write("**Dietary Restrictions:**")
                for item in prefs.dietary_restrictions:
                    st.write(f"- {item}")

            if prefs.cooking_goals:
                st.write("**Cooking Goals:**")
                for item in prefs.cooking_goals:
                    st.write(f"- {item}")
        except Exception as e:
            st.error(f"Error displaying preferences: {e}")
    else:
        st.write(
            "No preferences saved yet. Tell the chatbot about your food preferences!"
        )

    st.subheader("🥕 Your Ingredients")
    ingredients_data = get_ingredients()
    if ingredients_data:
        try:
            ingredients = Ingredients.model_validate_json(ingredients_data)
            for ingredient in ingredients.names:
                st.write(f"- {ingredient}")
        except Exception as e:
            st.error(f"Error displaying ingredients: {e}")
    else:
        st.write(
            "No ingredients saved yet. Tell the chatbot what ingredients you have!"
        )

for message in st.session_state.chat_messages:
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            if "<think>" in message.content and "</think>" in message.content:
                thinking_part = (
                    message.content.split("</think>")[0].replace("<think>", "").strip()
                )
                response_part = message.content.split("</think>")[1].strip()

                with st.expander("View thinking process"):
                    st.markdown(
                        f'<div style="white-space: pre-wrap;">{thinking_part}</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown(response_part)
            else:
                st.markdown(message.content)

if prompt := st.chat_input("What ingredients do you have?"):
    user_message = HumanMessage(content=prompt)

    with st.chat_message("user"):
        st.markdown(prompt)
        st.session_state.chat_messages.append(HumanMessage(content=prompt))

    with st.chat_message("assistant"):
        config = {
            "configurable": {
                "user_id": st.session_state.user_id,
                "thread_id": st.session_state.user_id,
            }
        }

        result = st.session_state.agent.invoke([user_message], config=config)
        content = result["messages"][-1].content

        st.session_state.placeholder = AIMessage(content=content)
        st.session_state.chat_messages.append(st.session_state.placeholder)
        st.session_state.memory_manager.save_streamlit_messages(
            st.session_state.user_id, st.session_state.chat_messages
        )

        with st.sidebar:
            st.rerun()
