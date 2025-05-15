# ingrai - 🍳 Ingredient Tracker Chatbot

A Streamlit-based chatbot with persistent memory that uses tools to keep track
of your ingredients and preferences.

- Food preferences and dietary restrictions
- Ingredients you have available at home

The application uses a PostgreSQL database to remember chat history,
preferences, and ingredients.

## Technology Stack

- **Frontend**: Streamlit
- **AI Framework**: LangChain and LangGraph
- **Language Model**: Qwen3 14B (running locally)
- **Database**: PostgreSQL for persistent storage
- **Architecture**: Agent-based system with memory management

## Project Structure

- `app.py`: Streamlit application and user interface
- `agent.py`: Implementation of the conversational agent with LangGraph
- `memory.py`: Memory management and database persistence layer
- `models.py`: Pydantic models for data structures
- `prompts.py`: System messages and instructions for the language model

## Setup and Installation

### Prerequisites

- Python 3.9+
- PostgreSQL
- Ollama (for running the Qwen model locally)

### Installation Steps

1.Clone the repository:

```bash
git clone git@github.com:ccrvos/ingrai.git
cd ingrai
```

2.Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3.Set up PostgreSQL:

```bash
# Make sure PostgreSQL is running on port 5442
# Example using Docker:
docker run --name postgres-ingrai -e POSTGRES_PASSWORD=postgres -p 5442:5432 -d postgres
```

4.Install Ollama:
Follow [Ollama installation instructions](https://github.com/ollama/ollama)

5.Run the Ollama server:

```bash
ollama serve
```

6.Open new terminal and run the Ollama model:

```bash
ollama run qwen3:14b
```

7.Run the application:

```bash
streamlit run app.py
```
