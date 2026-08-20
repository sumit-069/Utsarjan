# 🚀 Utsarjan — AI Agent Builder

> Build, validate, deploy, and integrate AI agents from natural-language requirements.

Utsarjan is a production-oriented **AI Agent Builder** that converts a user's natural-language description into a task-specific AI agent.

It uses **LLMs for requirement analysis and code generation**, **LangGraph for multi-step orchestration**, and **FastAPI for exposing generated agents as APIs**.

---

## ✨ Features

- 🤖 **Natural-language Agent Generation**
  - Describe what you want your agent to do.
  - Utsarjan analyzes the requirements and generates the agent.

- 🧠 **AI-Powered Planning**
  - Requirement analysis
  - Tool selection
  - Architecture design
  - Agent code generation

- 🔀 **LangGraph Orchestration**
  - Multi-step agent-building workflow
  - Maintains intermediate state between stages.

- 🛠️ **Dynamic Tool Selection**
  - Selects tools according to the agent's requirements.
  - Supports different agent categories such as:
    - Simple
    - Coding
    - Research
    - PDF
    - Custom

- ⚡ **Automatic FastAPI Deployment**
  - Every generated agent gets its own FastAPI wrapper.
  - Automatic Uvicorn server startup.
  - Swagger/OpenAPI documentation available at `/docs`.

- 🔌 **Dynamic API Parameters**
  - API inputs are generated according to the actual agent requirements.
  - No unnecessary `pdf_path`, `context_file`, or generic parameters.

- 🔐 **API Key Authentication**
  - Each agent can have its own API key.
  - External applications can authenticate using:
    ```text
    X-API-Key: your_api_key
    ```

- 🌐 **Website Integration**
  - Generated agents can be integrated into external websites and applications through REST APIs.

- 🔢 **Automatic Port Allocation**
  - Each generated agent receives an available port automatically.
  - Prevents port conflicts between agents.

- ❤️ **Health Monitoring**
  - Health endpoint:
    ```text
    /health
    ```

- 🧪 **Generated Code Validation**
  - Syntax validation
  - Import validation
  - LLM/API validation
  - Tool validation
  - Entry-point validation

- 🛡️ **Error Handling**
  - Generated agents are validated before deployment.
  - Server logs are captured when an agent fails to start.

---

# 🏗️ Architecture

```text
                    ┌──────────────────────┐
                    │      User Prompt     │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │ Requirement Analysis │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │    Tool Selection    │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │ Architecture Design  │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │   Code Generation    │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │     Validation       │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │   FastAPI Wrapper    │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │  Port + API Key      │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │   Running AI Agent   │
                    └──────────────────────┘