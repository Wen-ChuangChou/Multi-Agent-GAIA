import json
import os
import pandas as pd
import requests
import sys
import time
import yaml
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Any
from smolagents import (DuckDuckGoSearchTool, OpenAIServerModel, CodeAgent,
                        ToolCallingAgent, ActionStep, TaskStep, LogLevel, tool)
from utils.blablador_helper import BlabladorChatModel
from utils.agent_tools import visit_webpage, analyze_image

load_dotenv()
RESULT_DIR = "results"


class BasicAgent:

    def __init__(self,
                 model_provider: str = "Blablador",
                 memory_file: str = None):
        self.model_provider = model_provider

        if memory_file is None:
            os.makedirs(RESULT_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%m%d_%H%M")
            self.memory_file = os.path.join(RESULT_DIR,
                                            f"agent_memory_{timestamp}.json")
        else:
            self.memory_file = memory_file

        if model_provider == "Blablador":

            # Initialize LLM via Blablador
            API_KEY = os.getenv("Blablador_API_KEY")
            LLM_helper = BlabladorChatModel(api_key=API_KEY)

            model_name = "Qwen3.5-122B"  # Options: Qwen3.5-122B, MiniMax-M2.7
            model_fullname = LLM_helper.get_model_fullname(model_name)
            print(f"The agent uses the following model: {model_fullname}\n")

            vlm_model_name = "Qwen3.5-122B"
            vlm_model_fullname = LLM_helper.get_model_fullname(vlm_model_name)
            print(
                f"The image agent uses the following model: {vlm_model_fullname}\n"
            )

            answer_llm = OpenAIServerModel(
                model_id=model_fullname,
                api_base="https://api.helmholtz-blablador.fz-juelich.de/v1",
                api_key=API_KEY,
                timeout=300,
                max_tokens=16384,
                temperature=1)

            vlm_llm = OpenAIServerModel(
                model_id=vlm_model_fullname,
                api_base="https://api.helmholtz-blablador.fz-juelich.de/v1",
                api_key=API_KEY,
                timeout=300,
                max_tokens=1024,
                temperature=0.2)

        elif model_provider == "Gemini":

            # model_name = "gemini-2.5-flash-preview-05-20"
            model_name = "gemini-2.0-flash"
            print("The agent uses the following model:", model_name)

            answer_llm = OpenAIServerModel(
                model_id=model_name,
                api_base=
                "https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=os.getenv("Gemini_API_KEY2"),
                temperature=0.2)
        else:
            print(
                f"Error: Unsupported model provider '{model_provider}'. Only 'Blablador' and 'Gemini' are supported."
            )
            sys.exit(1)

        self.search_agent = ToolCallingAgent(
            tools=[DuckDuckGoSearchTool(), visit_webpage],
            model=answer_llm,
            max_steps=5,
            name="search_agent",
            description=
            "An agent that can search the web and read web pages. Give it a clear search query or URL, and it will return the information you need. IMPORTANT: Do NOT attempt to read or visit Wikipedia URLs (https://en.wikipedia.org/wiki) as they block requests and return 403 Forbidden errors. Always prefer alternative sources.",
            verbosity_level=LogLevel.ERROR,
        )

        @tool
        def ask_image_agent(question: str, image_path: str) -> str:
            """
            An agent that can analyze images. Give it an image path and a question.
            
            Args:
                question: The question to ask about the image.
                image_path: The absolute path to the image file.
            """
            from PIL import Image
            try:
                image = Image.open(image_path).convert('RGB')
                vision_agent = CodeAgent(tools=[],
                                         model=vlm_llm,
                                         add_base_tools=False,
                                         verbosity_level=LogLevel.ERROR)
                return str(vision_agent.run(question, images=[image]))
            except Exception as e:
                return f"Error analyzing image: {e}"

        self.image_agent = ask_image_agent

        self.manager_agent = CodeAgent(
            tools=[self.image_agent],
            model=answer_llm,
            planning_interval=3,
            max_steps=5,
            additional_authorized_imports=["time", "numpy", "pandas"],
            managed_agents=[self.search_agent],
            verbosity_level=LogLevel.ERROR,
            max_print_outputs_length=2000,
        )

    def __call__(self,
                 question: str,
                 task_id: str = "",
                 file_url: str = "",
                 file_ext: str = "") -> str:
        print(f"Agent received question (first 50 chars): {question[:50]}...")

        prompt_file_path = os.path.join(os.path.dirname(__file__), "prompt",
                                        "system_prompt.yaml")
        try:
            with open(prompt_file_path, "r", encoding="utf-8") as f:
                prompt_data = yaml.safe_load(f)
                SYSTEM_PROMPT = prompt_data.get("prompt", "")
        except Exception as e:
            print(f"Failed to load system prompt from yaml: {e}")
            SYSTEM_PROMPT = ""

        # Prepare additional_args for file handling
        additional_args = {}

        # Handle file if provided
        if file_url:
            print(f"Downloading file from: {file_url}")
            file_content = self._download_file(file_url, file_ext)

            if file_content is not None:
                # Give the file a clear name based on its extension
                if file_ext.lower() == 'csv':
                    # For CSV files, try to load as DataFrame
                    try:
                        import io
                        if isinstance(file_content, str):
                            df = pd.read_csv(io.StringIO(file_content))
                        else:
                            df = pd.read_csv(io.BytesIO(file_content))
                        additional_args['dataframe'] = df
                        additional_args['csv_file'] = file_content
                        print(f"Loaded CSV file with shape: {df.shape}")
                    except Exception as e:
                        print(f"Could not parse CSV file: {e}")
                        additional_args['file_content'] = file_content

                elif file_ext.lower() in ['json']:
                    try:
                        import json
                        if isinstance(file_content, bytes):
                            file_content = file_content.decode('utf-8')
                        json_data = json.loads(file_content)
                        additional_args['json_data'] = json_data
                        additional_args['file_content'] = file_content
                        print(f"Loaded JSON file")
                    except Exception as e:
                        print(f"Could not parse JSON file: {e}")
                        additional_args['file_content'] = file_content

                elif file_ext.lower() in ['xlsx', 'xls']:
                    try:
                        import io
                        import pandas as pd
                        if isinstance(file_content, bytes):
                            df = pd.read_excel(io.BytesIO(file_content))
                        else:
                            df = pd.read_excel(io.StringIO(file_content))
                        additional_args['dataframe'] = df
                        additional_args['file_path'] = file_url
                        print(f"Loaded Excel file with shape: {df.shape}")
                    except Exception as e:
                        print(f"Could not parse Excel file: {e}")
                        additional_args['file_path'] = file_url

                elif file_ext.lower() in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                    additional_args['image_path'] = file_url
                    print(f"Loaded {file_ext} file path: {file_url}")
                else:
                    if isinstance(file_content, bytes):
                        additional_args['file_path'] = file_url
                        print(
                            f"Passed {file_ext} file path instead of binary content: {file_url}"
                        )
                    else:
                        additional_args['file_content'] = file_content
                        print(f"Loaded {file_ext} file content")
                    if file_ext:
                        additional_args['file_extension'] = file_ext

            # Update the prompt to mention the file
            full_prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {question}\n\nNote: A {file_ext} file has been provided and is available for your analysis."
            # if file_ext.lower() in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            # full_prompt += f"\nIMPORTANT: You MUST use the image_agent to analyze the image. The image path is: {file_url}"

        else:
            full_prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {question}\n\nNote: Could not retrieve the file from {file_url}."
        # else:
        #     full_prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {question}"

        # # Combine system prompt with the user question
        # full_prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {question}"

        try:
            # answer = self.manager_agent.run(full_prompt)
            answer = self.manager_agent.run(
                task=full_prompt,
                additional_args=additional_args if additional_args else None)

            # Force the output to only contain the content after FINAL ANSWER:
            if isinstance(answer, str) and "FINAL ANSWER:" in answer:
                answer = answer.split("FINAL ANSWER:")[-1].strip()

            # If the answer is a float, format it to 2 decimal places to ensure precision (common in GAIA)
            if isinstance(answer, float):
                answer = f"{answer:.2f}"

            print(f"Agent returning answer: {answer}")

            # Export memory after execution
            self.export_memory_to_json(task_id=task_id,
                                       question=question,
                                       answer=answer)

            # Sleep for 10 seconds if using Gemini to avoid rate limiting
            if self.model_provider == "Gemini":
                time.sleep(10)
            return answer
        except Exception as e:
            print(f"Error running agent: {e}")
            return f"Error: {e}"

    def export_memory_to_json(self,
                              task_id: str = "",
                              question: str = "",
                              answer: str = "",
                              error: str = ""):
        """Export agent's memory to JSON file for each question"""
        memory_data = self.extract_memory_data()

        # Load existing memory file if it exists
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = {"questions": [], "batch_info": {}}

        # Create question data
        question_data = {
            "question_id": task_id or len(existing_data["questions"]) + 1,
            "timestamp": datetime.now().isoformat(),
            "model_provider": self.model_provider,
            "task": question,
            "result": answer,
            "error": error,
            "memory": memory_data,
            "memory_stats": self.get_memory_stats()
        }

        # Add or update question
        if task_id:
            # Check if question_id already exists and update it
            question_exists = False
            for i, existing_question in enumerate(existing_data["questions"]):
                if existing_question["question_id"] == task_id:
                    existing_data["questions"][i] = question_data
                    question_exists = True
                    break

            if not question_exists:
                existing_data["questions"].append(question_data)
        else:
            existing_data["questions"].append(question_data)

        # Update batch info
        existing_data["batch_info"] = {
            "total_questions": len(existing_data["questions"]),
            "last_updated": datetime.now().isoformat(),
            "model_provider": self.model_provider
        }

        # Save to file
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data,
                      f,
                      indent=2,
                      ensure_ascii=False,
                      default=str)

        print(f"Memory for question {task_id} exported to {self.memory_file}")

    def extract_memory_data(self) -> Dict[str, Any]:
        """Extract memory data from agent"""
        memory_data = {"system_prompt": None, "steps": [], "full_steps": []}

        # Get system prompt
        if hasattr(
                self.manager_agent.memory,
                'system_prompt') and self.manager_agent.memory.system_prompt:
            memory_data["system_prompt"] = {
                "content":
                str(self.manager_agent.memory.system_prompt.system_prompt),
                "type":
                "system_prompt"
            }

        # Get all memory steps
        for i, step in enumerate(self.manager_agent.memory.steps):
            step_data = {
                "step_index": i,
                "step_type": type(step).__name__,
                "timestamp": datetime.now().isoformat()
            }

            if isinstance(step, TaskStep):
                step_data.update({
                    "task":
                    step.task,
                    "task_images":
                    len(step.task_images) if step.task_images else 0
                })

            elif isinstance(step, ActionStep):
                step_data.update({
                    "step_number":
                    step.step_number,
                    "llm_output":
                    getattr(step, 'action', None),
                    "observations":
                    step.observations,
                    "error":
                    str(step.error) if step.error else None,
                    "has_images":
                    len(step.observations_images) > 0
                    if step.observations_images else False
                })

            memory_data["steps"].append(step_data)

        # Get full steps as dictionaries (as mentioned in docs)
        try:
            full_steps = self.manager_agent.memory.get_full_steps()
            memory_data["full_steps"] = full_steps
        except Exception as e:
            print(f"Could not get full steps: {e}")
            memory_data["full_steps"] = []

        return memory_data

    def get_memory_stats(self) -> Dict[str, int]:
        """Get statistics about the agent's memory"""
        stats = {
            "total_steps": len(self.manager_agent.memory.steps),
            "task_steps": 0,
            "action_steps": 0,
            "error_steps": 0,
            "successful_steps": 0
        }

        for step in self.manager_agent.memory.steps:
            if isinstance(step, TaskStep):
                stats["task_steps"] += 1
            elif isinstance(step, ActionStep):
                stats["action_steps"] += 1
                if step.error:
                    stats["error_steps"] += 1
                else:
                    stats["successful_steps"] += 1

        return stats

    def _download_file(self, file_url: str, file_ext: str = "") -> str:
        """Download file content from URL or read from local path.

        Supports both HTTP URLs and local file paths (for GAIA dataset
        fallback when the /files/{task_id} endpoint is broken).
        """
        try:
            # Handle local file paths (from GAIA dataset)
            if os.path.isfile(file_url):
                print(f"Reading local file: {file_url}")
                text_exts = [
                    'txt', 'csv', 'json', 'md', 'py', 'js', 'html', 'xml'
                ]
                if file_ext.lower() in text_exts:
                    with open(file_url, 'r', encoding='utf-8') as f:
                        return f.read()
                else:
                    with open(file_url, 'rb') as f:
                        return f.read()

            # Handle HTTP URLs
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()

            # For text files, return as string
            if file_ext.lower() in [
                    'txt', 'csv', 'json', 'md', 'py', 'js', 'html', 'xml'
            ]:
                return response.text
            else:
                # For binary files, return the content as bytes
                return response.content

        except Exception as e:
            print(f"Error loading file from {file_url}: {e}")
            return None
