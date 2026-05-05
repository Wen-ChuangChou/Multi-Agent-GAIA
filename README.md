# **AI Multi-Agent Orchestration: Tool-Augmented Reasoning on the GAIA Benchmark**

## **Project Description**

This project implements an advanced autonomous agent system designed to tackle the **GAIA (General AI Assistants)** benchmark. Unlike traditional chatbots, this agent utilizes a multi-agent orchestration framework to solve complex, multi-modal tasks that require real-world reasoning, tool usage, and information synthesis.

The system is built on the [smolagents](https://github.com/huggingface/smolagents) framework, featuring a hierarchical agent structure. A **Manager Agent** (CodeAgent) plans and delegates tasks to specialized sub-agents for web searching and vision-based analysis. This approach allows the agent to navigate the web, analyze images, process diverse file formats (CSV, JSON, Excel), and perform multi-step reasoning to reach accurate conclusions for difficult real-world questions.

![AI Multi-Agent Orchestration](pics/multi_agent.png)

### **Key Capabilities**

| Capability | Description |
|---|---|
| **Multi-Agent Orchestration** | A hierarchical design where a Manager Agent plans and coordinates specialized search and vision agents. |
| **Autonomous Web Search** | Integrated `DuckDuckGoSearchTool` and webpage visitation to retrieve real-time information from the internet. |
| **Multi-Modal Analysis** | Native support for analyzing images and structured data files (CSV, XLSX, JSON) using Python-based logic. |
| **Robust File Handling** | A specialized GAIA file resolver to manage local and remote resources, ensuring high reliability during evaluation. |
| **Telemetry & Tracing** | Full integration with **Langfuse** via OpenTelemetry for granular monitoring of agent steps and performance. |

## **Installation**

### **Prerequisites**

- Python **3.12+**
- A [Gemini API key](https://aistudio.google.com/app/apikey) or [Blablador API key](https://helmholtz-blablador.fz-juelich.de/)
- Git

### **Steps**

1. **Clone the repository**
   ```bash
   git clone https://github.com/Thomas-Chou/Agent_Gaia.git
   cd Agent_Gaia
   ```

2. **Create and activate a virtual environment** *(recommended)*
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root and add your keys:
   ```env
   GEMINI_API_KEY=your_gemini_key
   Blablador_API_KEY=your_blablador_key
   LANGFUSE_PUBLIC_KEY=your_public_key
   LANGFUSE_SECRET_KEY=your_secret_key
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```

---

## **Usage**

### **1. Run the Gradio App — `app.py`**

The project includes a Gradio-based web interface for running and monitoring evaluations.

```bash
python app.py
```

**Features:**
- **Standard Evaluation**: Runs the agent against the GAIA benchmark questions.
- **Test Mode**: Runs a limited set of questions (first 5) for quick validation.
- **Specific Question**: Target a single question index to debug specific failures.
- **Auto-Submission**: Automatically submits results to the scoring endpoint.

### **2. Agent Core — `agent.py`**

The `BasicAgent` class encapsulates the multi-agent logic. It can be used programmatically in other scripts:

```python
from agent import BasicAgent

agent = BasicAgent(model_provider="Gemini")
answer = agent("What is the current population of Paris according to the latest official census?")
print(answer)
```

---

## **Project Structure**

```
Agent_Gaia/
│
├── app.py                  # Gradio UI & Evaluation runner
├── agent.py                # Core BasicAgent implementation (Multi-agent logic)
├── requirements.txt        # Python dependencies
│
├── prompt/                 # System prompt templates
│   └── system_prompt.yaml  # Main system prompt for the agent
│
├── utils/                  # Helper modules
│   ├── agent_tools.py      # Custom tools (visit_webpage, etc.)
│   ├── gaia_files.py       # GAIA dataset file path resolver
│   └── blablador_helper.py # Blablador API wrapper
│
└── pics/                   # Visual documentation and debug screenshots
```

## **Technical Highlights: Multi-Agent Efficiency & Problem Solving**

### **1. Why a Search Agent is Essential**
If the Manager Agent attempts to search and process documents directly, it often faces an overwhelming amount of raw data, much of which is irrelevant. This "data noise" can cause the agent to lose focus or exceed token limits. 

By using a specialized **Search Agent**, we delegate the task of data retrieval and synthesis. The Search Agent explores the web, filters the noise, and returns a condensed, well-organized report to the Manager. 

*   **Efficiency Gain**: In one instance, **12,956 tokens** of raw search data were condensed into a highly relevant **1,116-token** report.

![Search Agent Process](pics/serach_agent.png)
![Search Agent Outcome](pics/search_agent_outcome.png)

### **2. Overcoming Wikipedia's 403 Forbidden Error**
Through **Langfuse** telemetry, we identified that the agent was frequently blocked when trying to read Wikipedia articles using standard scraping methods, resulting in `403 Forbidden` errors.

![Wikipedia Error](pics/error_accessing_wiki.png)

**The Fix**: We implemented a custom `visit_webpage` tool that detects Wikipedia links and redirects the request to **Wikipedia's REST API**. This provides clean, structured JSON content, completely bypassing the need for scraping and resolving the access issue.

![Wikipedia Fix](pics/fix_accessing_wiki.png)

---

## **Results & Performance**

The system was evaluated against the **GAIA Benchmark**, which tests an AI’s ability to execute multi-step, multi-modal tasks that humans find intuitive but models often struggle with. 

*   **Benchmark Performance**: The agent currently achieves a **60% accuracy rate** on the GAIA evaluation set, demonstrating strong foundational reasoning and tool usage.
*   **Dynamic Reasoning**: By leveraging a `CodeAgent` for orchestration, the system autonomously writes and executes Python logic to manipulate complex datasets and verify external findings.
*   **Complete Observability**: Integration with **Langfuse** provides a deep-dive view into every thought, tool call, and state change. Traces are available in the [Langfuse Dashboard](https://cloud.langfuse.com/traces) and persisted locally in `results/agent_memory.json` for offline analysis.

## **Future Roadmap**

1.  **Extended Modality Support**: Integration of specialized tools for audio transcription (e.g., OpenAI Whisper) and high-fidelity document parsing (e.g., Docling) to handle unstructured data more effectively.
2.  **Adaptive Planning**: Enhancing the Manager Agent's ability to perform **real-time plan revision**—enabling it to pivot or backtrack when a specific search path or tool call yields unsatisfactory results.
3.  **Automated Prompt Engineering**: Implementing Reinforcement Learning (RL) loops to dynamically optimize system prompts and tool descriptions based on historical success rates.
4.  **Verification & Self-Correction**: Introducing a dedicated 'Critic' agent to audit final responses against retrieved evidence, reducing hallucinations and improving overall reliability.

## **Reference:**

1. [GAIA: A Benchmark for General AI Assistants](https://huggingface.co/datasets/gaia-benchmark/GAIA).
2. [Smolagents Documentation](https://huggingface.co/docs/smolagents/index).
3. [Blablador Helmholtz API](https://helmholtz-blablador.fz-juelich.de/).
