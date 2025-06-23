import os
import gradio as gr
import requests
import inspect
import pandas as pd
import sys
import time
from dotenv import load_dotenv
from smolagents import DuckDuckGoSearchTool, OpenAIServerModel, CodeAgent, Tool
from blablador import Models

# (Keep Constants as is)
# --- Constants ---
DEFAULT_API_URL = "https://agents-course-unit4-scoring.hf.space"

# --- Basic Agent Definition ---
# ----- THIS IS WERE YOU CAN BUILD WHAT YOU WANT ------
load_dotenv()


class BasicAgent:

    def __init__(self, model_provider: str = "Blablador"):
        self.model_provider = model_provider

        if model_provider == "Blablador":

            models = Models(
                api_key=os.getenv("Blablador_API_KEY")).get_model_ids()
            model_id_blablador = 5
            model_name = " ".join(
                models[model_id_blablador].split(" - ")[1].split()[:2])
            print("The agent uses the following model:", model_name)

            answer_llm = OpenAIServerModel(
                model_id=models[model_id_blablador],
                api_base="https://helmholtz-blablador.fz-juelich.de:8000/v1",
                api_key=os.getenv("Blablador_API_KEY"),
                flatten_messages_as_text=True,
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

        self.agent = CodeAgent(
            tools=[DuckDuckGoSearchTool()],
            model=answer_llm,
            planning_interval=3,
            max_steps=10,
            # verbosity_level=LogLevel.ERROR,
        )

    def __call__(self,
                 question: str,
                 file_url: str = "",
                 file_ext: str = "") -> str:
        print(f"Agent received question (first 50 chars): {question[:50]}...")

        SYSTEM_PROMPT = """You are a general AI assistant. I will ask you a question. 
        Report your thoughts, and finish your answer with the following template: FINAL ANSWER: [YOUR FINAL ANSWER]. 
        YOUR FINAL ANSWER should be a number OR as few words as possible OR a comma separated list of numbers and/or strings. 
        If you are asked for a number, don't use comma to write your number 
        neither use units such as $ or percent sign unless specified otherwise. 
        If you are asked for a string, don't use articles, neither ABBREVIATIONS, (e.g. for cities), 
        and write the digits in plain text unless specified otherwise. 
        If you are asked for a comma separated list, 
        apply the above rules depending of whether the element to be put in the list is a number or a string.
        """

        # Prepare additional_args for file handling
        additional_args = {}

        # Handle file if provided
        if file_url:
            # print(f"Downloading file from: {file_url}")
            # file_content = self._download_file(file_url, file_ext)

            # if file_content is not None:
            #     # Give the file a clear name based on its extension
            #     if file_ext.lower() == 'csv':
            #         # For CSV files, try to load as DataFrame
            #         try:
            #             import io
            #             if isinstance(file_content, str):
            #                 df = pd.read_csv(io.StringIO(file_content))
            #             else:
            #                 df = pd.read_csv(io.BytesIO(file_content))
            #             additional_args['dataframe'] = df
            #             additional_args['csv_file'] = file_content
            #             print(f"Loaded CSV file with shape: {df.shape}")
            #         except Exception as e:
            #             print(f"Could not parse CSV file: {e}")
            #             additional_args['file_content'] = file_content

            #     elif file_ext.lower() in ['json']:
            #         try:
            #             import json
            #             if isinstance(file_content, bytes):
            #                 file_content = file_content.decode('utf-8')
            #             json_data = json.loads(file_content)
            #             additional_args['json_data'] = json_data
            #             additional_args['file_content'] = file_content
            #             print(f"Loaded JSON file")
            #         except Exception as e:
            #             print(f"Could not parse JSON file: {e}")
            #             additional_args['file_content'] = file_content

            #     else:
            #         # For other file types, just pass the content
            #         additional_args['file_content'] = file_content
            #         if file_ext:
            #             additional_args['file_extension'] = file_ext
            #         print(f"Loaded {file_ext} file")

            # Update the prompt to mention the file
            # full_prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {question}\n\nNote: A {file_ext} file has been provided and is available for your analysis."
            additional_args = f"{file_url}_{file_ext}"
            full_prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {question}\n\nNote: A {file_ext} file has been provided and is available for your analysis."

            # else:
            # full_prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {question}\n\nNote: Could not retrieve the file from {file_url}."
        else:
            full_prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {question}"

        # # Combine system prompt with the user question
        # full_prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {question}"

        try:
            answer = self.agent.run(full_prompt)
            # answer = self.agent.run(
            #     task=full_prompt,
            #     additional_args=additional_args if additional_args else None)
            print(f"Agent returning answer: {answer}")
            if self.model_provider == "Gemini":
                time.sleep(10)
            return answer
        except Exception as e:
            print(f"Error running agent: {e}")
            return f"Error: {e}"

    def _download_file(self, file_url: str, file_ext: str = "") -> str:
        """Download file content from URL and return as text or bytes"""
        try:
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
            print(f"Error downloading file from {file_url}: {e}")
            return None


def run_and_submit_all(profile: gr.OAuthProfile | None):
    """
    Fetches all questions, runs the BasicAgent on them, submits all answers,
    and displays the results.
    """
    # --- Determine HF Space Runtime URL and Repo URL ---
    space_id = os.getenv(
        "SPACE_ID")  # Get the SPACE_ID for sending link to the code

    if profile:
        username = f"{profile.username}"
        print(f"User logged in: {username}")
    else:
        print("User not logged in.")
        return "Please Login to Hugging Face with the button.", None

    api_url = DEFAULT_API_URL
    questions_url = f"{api_url}/questions"
    submit_url = f"{api_url}/submit"

    # 1. Instantiate Agent ( modify this part to create your agent)
    try:
        agent = BasicAgent("Blablador")
    except Exception as e:
        print(f"Error instantiating agent: {e}")
        return f"Error initializing agent: {e}", None
    # In the case of an app running as a hugging Face space, this link points toward your codebase ( usefull for others so please keep it public)
    agent_code = f"https://huggingface.co/spaces/{space_id}/tree/main"
    print(agent_code)

    # 2. Fetch Questions
    print(f"Fetching questions from: {questions_url}")
    try:
        response = requests.get(questions_url, timeout=15)
        response.raise_for_status()
        questions_data = response.json()
        if not questions_data:
            print("Fetched questions list is empty.")
            return "Fetched questions list is empty or invalid format.", None
        print(f"Fetched {len(questions_data)} questions.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching questions: {e}")
        return f"Error fetching questions: {e}", None
    except requests.exceptions.JSONDecodeError as e:
        print(f"Error decoding JSON response from questions endpoint: {e}")
        print(f"Response text: {response.text[:500]}")
        return f"Error decoding server response for questions: {e}", None
    except Exception as e:
        print(f"An unexpected error occurred fetching questions: {e}")
        return f"An unexpected error occurred fetching questions: {e}", None

    # 3. Run your Agent
    results_log = []
    answers_payload = []
    print(f"Running agent on {len(questions_data)} questions...")
    for item in questions_data:
        task_id = item.get("task_id")
        question_text = item.get("question")
        if not task_id or question_text is None:
            print(f"Skipping item with missing task_id or question: {item}")
            continue

        file_name = item.get("file_name")
        file_ext = None
        file_url = None

        if file_name:
            file_ext = file_name.split('.')[-1].lower()
            file_url = f"{api_url}/files/{task_id}"

        try:
            submitted_answer = agent(question_text)
            # submitted_answer = agent(question_text, file_url, file_ext)
            answers_payload.append({
                "task_id": task_id,
                "submitted_answer": submitted_answer
            })
            results_log.append({
                "Task ID": task_id,
                "Question": question_text,
                "Submitted Answer": submitted_answer
            })
        except Exception as e:
            print(f"Error running agent on task {task_id}: {e}")
            results_log.append({
                "Task ID": task_id,
                "Question": question_text,
                "Submitted Answer": f"AGENT ERROR: {e}"
            })

    if not answers_payload:
        print("Agent did not produce any answers to submit.")
        return "Agent did not produce any answers to submit.", pd.DataFrame(
            results_log)

    # 4. Prepare Submission
    submission_data = {
        "username": username.strip(),
        "agent_code": agent_code,
        "answers": answers_payload
    }
    status_update = f"Agent finished. Submitting {len(answers_payload)} answers for user '{username}'..."
    print(status_update)

    # 5. Submit
    print(f"Submitting {len(answers_payload)} answers to: {submit_url}")
    try:
        response = requests.post(submit_url, json=submission_data, timeout=60)
        response.raise_for_status()
        result_data = response.json()
        final_status = (
            f"Submission Successful!\n"
            f"User: {result_data.get('username')}\n"
            f"Overall Score: {result_data.get('score', 'N/A')}% "
            f"({result_data.get('correct_count', '?')}/{result_data.get('total_attempted', '?')} correct)\n"
            f"Message: {result_data.get('message', 'No message received.')}")
        print("Submission successful.")
        results_df = pd.DataFrame(results_log)
        return final_status, results_df
    except requests.exceptions.HTTPError as e:
        error_detail = f"Server responded with status {e.response.status_code}."
        try:
            error_json = e.response.json()
            error_detail += f" Detail: {error_json.get('detail', e.response.text)}"
        except requests.exceptions.JSONDecodeError:
            error_detail += f" Response: {e.response.text[:500]}"
        status_message = f"Submission Failed: {error_detail}"
        print(status_message)
        results_df = pd.DataFrame(results_log)
        return status_message, results_df
    except requests.exceptions.Timeout:
        status_message = "Submission Failed: The request timed out."
        print(status_message)
        results_df = pd.DataFrame(results_log)
        return status_message, results_df
    except requests.exceptions.RequestException as e:
        status_message = f"Submission Failed: Network error - {e}"
        print(status_message)
        results_df = pd.DataFrame(results_log)
        return status_message, results_df
    except Exception as e:
        status_message = f"An unexpected error occurred during submission: {e}"
        print(status_message)
        results_df = pd.DataFrame(results_log)
        return status_message, results_df


# --- Build Gradio Interface using Blocks ---
with gr.Blocks() as demo:
    gr.Markdown("# Basic Agent Evaluation Runner")
    gr.Markdown("""
        **Instructions:**

        1.  Please clone this space, then modify the code to define your agent's logic, the tools, the necessary packages, etc ...
        2.  Log in to your Hugging Face account using the button below. This uses your HF username for submission.
        3.  Click 'Run Evaluation & Submit All Answers' to fetch questions, run your agent, submit answers, and see the score.

        ---
        **Disclaimers:**
        Once clicking on the "submit button, it can take quite some time ( this is the time for the agent to go through all the questions).
        This space provides a basic setup and is intentionally sub-optimal to encourage you to develop your own, more robust solution. For instance for the delay process of the submit button, a solution could be to cache the answers and submit in a seperate action or even to answer the questions in async.
        """)

    gr.LoginButton()

    run_button = gr.Button("Run Evaluation & Submit All Answers")

    status_output = gr.Textbox(label="Run Status / Submission Result",
                               lines=5,
                               interactive=False)
    # Removed max_rows=10 from DataFrame constructor
    results_table = gr.DataFrame(label="Questions and Agent Answers",
                                 wrap=True)

    run_button.click(fn=run_and_submit_all,
                     outputs=[status_output, results_table])

if __name__ == "__main__":
    print("\n" + "-" * 30 + " App Starting " + "-" * 30)
    # Check for SPACE_HOST and SPACE_ID at startup for information
    space_host_startup = os.getenv("SPACE_HOST")
    space_id_startup = os.getenv("SPACE_ID")  # Get SPACE_ID at startup

    if space_host_startup:
        print(f"✅ SPACE_HOST found: {space_host_startup}")
        print(
            f"   Runtime URL should be: https://{space_host_startup}.hf.space")
    else:
        print(
            "ℹ️  SPACE_HOST environment variable not found (running locally?)."
        )

    if space_id_startup:  # Print repo URLs if SPACE_ID is found
        print(f"✅ SPACE_ID found: {space_id_startup}")
        print(f"   Repo URL: https://huggingface.co/spaces/{space_id_startup}")
        print(
            f"   Repo Tree URL: https://huggingface.co/spaces/{space_id_startup}/tree/main"
        )
    else:
        print(
            "ℹ️  SPACE_ID environment variable not found (running locally?). Repo URL cannot be determined."
        )

    print("-" * (60 + len(" App Starting ")) + "\n")

    print("Launching Gradio Interface for Basic Agent Evaluation...")
    demo.launch(debug=True, share=False)
