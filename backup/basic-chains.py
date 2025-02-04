import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from queue import Queue, Empty
import threading
import requests
import logging
from datetime import datetime

class DeepSeekAgentApp:
    def __init__(self, master):
        self.master = master
        master.title("DeepSeek Agent Orchestrator")
        master.geometry("1000x800")

        # Initialize queue first
        self.queue = Queue()

        # Setup logging
        self.setup_logging()
        self.logger = logging.getLogger("AgentSystem")

        # Initialize Ollama connection
        self.ollama_url = "http://localhost:11434/api"
        self.available_models = self.get_ollama_models()

        # Agent configuration
        self.agents = {}
        self.current_process = None

        # Create UI components
        self.create_widgets()

        # Thread management
        self.running = False

        # Start queue checker
        self.master.after(100, self.process_queue)

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='agent_system.log',
            filemode='a'
        )
        # Add UI log handler
        self.ui_log_handler = UIHandler(self.queue)
        self.ui_log_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.ui_log_handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.ui_log_handler)

    def get_ollama_models(self):
        try:
            response = requests.get(f"{self.ollama_url}/tags")
            response.raise_for_status()
            return [model["name"] for model in response.json()["models"]]
        except Exception as e:
            self.logger.error(f"Model fetch failed: {str(e)}")
            return []

    def create_widgets(self):
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Configuration Panel
        config_frame = ttk.LabelFrame(main_frame, text="Agent Configuration")
        config_frame.pack(fill=tk.X, pady=5)

        # Model Selection
        ttk.Label(config_frame, text="Model:").grid(row=0, column=0, sticky=tk.W)
        self.model_selector = ttk.Combobox(config_frame, values=self.available_models)
        self.model_selector.grid(row=0, column=1, sticky=tk.EW, pady=5)
        if self.available_models:
            self.model_selector.current(0)

        # Agent Count with validation
        ttk.Label(config_frame, text="Number of Agents:").grid(row=1, column=0, sticky=tk.W)
        vcmd = (self.master.register(self.validate_spinbox), '%P')
        self.agent_count = ttk.Spinbox(
            config_frame,
            from_=1,
            to=5,
            validate='key',
            validatecommand=vcmd
        )
        self.agent_count.set(1)
        self.agent_count.grid(row=1, column=1, sticky=tk.EW, pady=5)
        self.agent_count.configure(command=self.update_agent_config)

        # Agent Configuration Notebook
        self.agent_notebook = ttk.Notebook(config_frame)
        self.agent_notebook.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=5)

        # Process Control
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)
        self.start_btn = ttk.Button(control_frame, text="Start Processing", command=self.start_processing)
        self.start_btn.pack(side=tk.LEFT)
        self.chain_output = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Chain Outputs", variable=self.chain_output).pack(side=tk.LEFT, padx=10)

        # Output Display
        output_frame = ttk.LabelFrame(main_frame, text="System Output")
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.output_area = scrolledtext.ScrolledText(output_frame, state=tk.DISABLED)
        self.output_area.pack(fill=tk.BOTH, expand=True)

        # Initial agent setup
        self.update_agent_config()

    def validate_spinbox(self, new_value):
        """Validate spinbox input to only accept numbers 1-5"""
        if new_value == '' or (new_value.isdigit() and 1 <= int(new_value) <= 5):
            return True
        return False

    def update_agent_config(self):
        num_agents = int(self.agent_count.get())
        current_tabs = self.agent_notebook.tabs()

        # Remove extra tabs
        while len(current_tabs) > num_agents:
            self.agent_notebook.forget(current_tabs[-1])
            current_tabs = self.agent_notebook.tabs()

        # Add missing tabs
        for i in range(1, num_agents + 1):
            tab_text = f"Agent {i}"
            existing_tab_texts = [self.agent_notebook.tab(tab, "text") for tab in current_tabs]
            if tab_text not in existing_tab_texts:
                agent_frame = ttk.Frame(self.agent_notebook)
                self.agent_notebook.add(agent_frame, text=tab_text)

                prompt_label = ttk.Label(agent_frame, text=f"Agent {i} Prompt:")
                prompt_label.pack(anchor=tk.W)

                prompt_input = scrolledtext.ScrolledText(agent_frame, height=4)
                prompt_input.pack(fill=tk.X, expand=True)

                # Store reference
                self.agents[i] = {
                    "prompt_input": prompt_input,
                    "response": None
                }
                current_tabs = self.agent_notebook.tabs()

        # Update tab order
        for i, tab in enumerate(self.agent_notebook.tabs()):
            self.agent_notebook.tab(tab, text=f"Agent {i+1}")

    def start_processing(self):
        if not self.running and self.available_models:
            self.running = True
            self.start_btn.config(state=tk.DISABLED)
            threading.Thread(target=self.process_agents, daemon=True).start()

    def process_agents(self):
        try:
            num_agents = int(self.agent_count.get())
            selected_model = self.model_selector.get()
            chain_outputs = self.chain_output.get()

            self.queue.put(("clear", ""))
            self.logger.info(f"Starting process with {num_agents} agents (Chain: {chain_outputs})")

            current_context = ""
            for agent_num in range(1, num_agents+1):
                agent_prompt = self.agents[agent_num]["prompt_input"].get("1.0", tk.END).strip()

                if chain_outputs and current_context:
                    full_prompt = f"{agent_prompt}\n\nContext from previous steps:\n{current_context}"
                else:
                    full_prompt = agent_prompt

                self.logger.info(f"Agent {agent_num} processing with prompt: {agent_prompt[:50]}...")

                response = self.generate_response(full_prompt, selected_model, agent_num)
                current_context += f"\n\nAgent {agent_num} Output:\n{response}"

                self.agents[agent_num]["response"] = response
                self.queue.put(("output", f"\nAgent {agent_num} Output:\n{'='*40}\n{response}\n\n"))
                self.logger.info(f"Agent {agent_num} completed processing")

            self.logger.info("Process completed successfully")
        except Exception as e:
            self.logger.error(f"Process failed: {str(e)}")
        finally:
            self.queue.put(("complete", ""))

    def generate_response(self, prompt, model_name, agent_num):
        try:
            self.logger.debug(f"Agent {agent_num} generating response...")
            response = requests.post(
                f"{self.ollama_url}/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            self.logger.error(f"Agent {agent_num} error: {str(e)}")
            return f"Error generating response: {str(e)}"

    def process_queue(self):
        try:
            while True:
                msg_type, content = self.queue.get_nowait()

                if msg_type == "output":
                    self.output_area.config(state=tk.NORMAL)
                    self.output_area.insert(tk.END, content)
                    self.output_area.see(tk.END)
                    self.output_area.config(state=tk.DISABLED)

                elif msg_type == "clear":
                    self.output_area.config(state=tk.NORMAL)
                    self.output_area.delete(1.0, tk.END)
                    self.output_area.config(state=tk.DISABLED)

                elif msg_type == "complete":
                    self.running = False
                    self.start_btn.config(state=tk.NORMAL)

        except Empty:
            pass

        self.master.after(100, self.process_queue)

class UIHandler(logging.Handler):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        msg = self.format(record)
        self.queue.put(("output", f"[LOG] {msg}\n"))

if __name__ == "__main__":
    root = tk.Tk()
    app = DeepSeekAgentApp(root)
    root.mainloop()