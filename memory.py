import json
from typing import Optional

import psycopg_pool
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from psycopg.rows import dict_row


class MemoryManager:
    def __init__(self, store: Optional[BaseStore] = None, checkpointer=None):
        self.store = store or InMemoryStore()
        self.DB_URI = (
            "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
        )

        self.pool = psycopg_pool.ConnectionPool(
            self.DB_URI,
            min_size=1,
            max_size=5,
            kwargs={"autocommit": True, "row_factory": dict_row},
        )
        with self.pool.connection() as conn:
            self.checkpointer = PostgresSaver(conn=conn)
            self.checkpointer.setup()  # only run on new DB

        self._init_tables()

    def _init_tables(self):
        """Create tables for streamlit_messages, user_preferences, and user_ingredients"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS streamlit_messages (
                        thread_id TEXT PRIMARY KEY,
                        messages JSONB NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                    
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        user_id TEXT PRIMARY KEY,
                        preferences JSONB NOT NULL
                    );
                    
                    CREATE TABLE IF NOT EXISTS user_ingredients (
                        user_id TEXT PRIMARY KEY,
                        ingredients JSONB NOT NULL
                    );
                """)

    def save_streamlit_messages(self, thread_id, messages):
        """Save Streamlit messages to DB"""
        serialized = []
        for msg in messages:
            if hasattr(msg, "type") and hasattr(msg, "content"):
                serialized.append({"role": msg.type, "content": msg.content})

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO streamlit_messages (thread_id, messages)
                    VALUES (%s, %s::jsonb)
                    ON CONFLICT (thread_id) 
                    DO UPDATE SET messages = %s::jsonb
                    """,
                    (thread_id, json.dumps(serialized), json.dumps(serialized)),
                )

    def load_streamlit_messages(self, thread_id):
        """Load Streamlit messages from DB"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT messages FROM streamlit_messages
                    WHERE thread_id = %s
                    """,
                    (thread_id,),
                )

                result = cur.fetchone()
                if not result:
                    return []

                from langchain_core.messages import AIMessage, HumanMessage

                messages = []
                for msg in result["messages"]:
                    if msg["role"] == "human":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "ai":
                        messages.append(AIMessage(content=msg["content"]))

                return messages

    def save_preferences(self, user_id, preferences_json):
        """Save user preferences to DB"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_preferences (user_id, preferences)
                    VALUES (%s, %s::jsonb)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET preferences = %s::jsonb
                    """,
                    (user_id, preferences_json, preferences_json),
                )

    def load_preferences(self, user_id):
        """Load user preferences from DB"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT preferences FROM user_preferences
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )

                result = cur.fetchone()
                if not result:
                    return None

                return json.dumps(result["preferences"])

    def save_ingredients(self, user_id, ingredients_json):
        """Save user ingredients to DB"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_ingredients (user_id, ingredients)
                    VALUES (%s, %s::jsonb)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET ingredients = %s::jsonb
                    """,
                    (user_id, ingredients_json, ingredients_json),
                )

    def load_ingredients(self, user_id):
        """Load user ingredients from DB"""
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ingredients FROM user_ingredients
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )

                result = cur.fetchone()
                if not result:
                    return None

                return json.dumps(result["ingredients"])

    def get_preferences(self, user_id):
        """Retrieve user preferences from store or database"""
        namespace = ("preferences", user_id)
        memories = self.store.search(namespace)
        # First, try store seach for memories
        if memories:
            return memories[0].value

        # Second, return DB result
        return self.load_preferences(user_id)

    def get_ingredients(self, user_id):
        """Retrieve user ingredients from store or database"""
        namespace = ("ingredients", user_id)
        memories = self.store.search(namespace)
        if memories:
            return memories[0].value

        return self.load_ingredients(user_id)

    def update_preferences(self, user_id, value):
        """Update user preferences in store and database"""
        namespace = ("preferences", user_id)
        self.store.put(namespace=namespace, key=user_id, value=value)
        self.save_preferences(user_id, value)

    def update_ingredients(self, user_id, value):
        """Update user ingredients in store and database"""
        namespace = ("ingredients", user_id)
        self.store.put(namespace=namespace, key=user_id, value=value)
        self.save_ingredients(user_id, value)
