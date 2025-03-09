"""
AIAgent - An AI-powered conversational agent with state machine architecture.

This module implements a configurable AI agent that uses LLM (Large Language Model) capabilities
through OpenRouter API. The agent operates on a state machine pattern where transitions
between states are determined by LLM responses.

Features:
- State machine based conversation flow
- Integration with OpenRouter API (via OpenAI client)
- Configurable via TOML files
- Custom action registration
- Comprehensive logging
- Debug/development mode
"""

import os, json, datetime
from typing import Dict, Any, Callable

# Choose the appropriate TOML library based on Python version
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Python 3.10 and below, requires 'pip install tomli'

from openai import OpenAI

class AIAgent:
    """
    A conversational AI agent that operates as a state machine.
    
    The agent processes user inputs, makes API calls to language models,
    and can transition between predefined states to handle different
    conversation stages. It also supports custom action registration for
    extending functionality.
    """
    
    def __init__(self, config_path: str, api_key: str = None, dev_mode: bool = False):
        """
        Initialize the AI agent with a configuration file.
        
        Args:
            config_path: Path to the TOML configuration file
            api_key: OpenRouter API key (defaults to OPENAI_API_KEY environment variable)
            dev_mode: When True, prints detailed debugging information
        """
        # Validate and set API key
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Provide it as a parameter or set OPENAI_API_KEY environment variable.")
        
        # Initialize dev mode flag
        self.dev_mode = dev_mode
        
        # Initialize OpenAI client with OpenRouter configuration
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )
        
        # Load configuration from TOML file
        self.config = self._load_config(config_path)
        
        # Initialize state and history tracking
        self.current_state = self.config.get("initial_state", "start")
        self.conversation_history = []
        
        # Separate search history for search-related actions
        self.search_history = []
        
        # Dictionary to store registered custom actions
        self.available_actions = {}
        
        # Initialize logging with timestamp for unique file names
        self.log_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self.log_file = f"agent_log_{self.log_timestamp}.txt"
        
        # Log initialization information
        self._log_info(f"Agent initialized with config from {config_path}")
        self._log_info(f"Initial state: {self.current_state}")
        self._log_info(f"Dev mode: {self.dev_mode}")
        
        # Print additional info in dev mode
        if self.dev_mode:
            print(f"[DEV] Agent initialized in dev mode with config from {config_path}")
            print(f"[DEV] Initial state: {self.current_state}")
            print(f"[DEV] Logging to file: {self.log_file}")
    
    def _log_info(self, message: str):
        """
        Write a simple information message to the log file.
        
        Args:
            message: The message to log
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def _log_json(self, title: str, data: Any):
        """
        Format and write JSON data to the log file with a title.
        
        Args:
            title: Title describing the JSON data
            data: The data to log (will be JSON serialized if possible)
        """
        self._log_info(f"===== {title} =====")
        if isinstance(data, (dict, list)):
            try:
                formatted_json = json.dumps(data, ensure_ascii=False, indent=2)
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"{formatted_json}\n")
            except:
                self._log_info(f"Unable to serialize to JSON: {str(data)}")
        else:
            self._log_info(str(data))
        self._log_info("=" * (len(title) + 12))  # 12 is the length of "===== " and " ====="
    
    def _load_config(self, config_path: str) -> Dict:
        """
        Load and parse the TOML configuration file.
        
        Args:
            config_path: Path to the TOML configuration file
            
        Returns:
            Dict containing the parsed configuration
        """
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    
    def register_action(self, action_name: str, action_func: Callable):
        """
        Register an external function that the agent can call during execution.
        
        This allows extending the agent with custom functionality.
        
        Args:
            action_name: Name of the action to register
            action_func: The function to call when this action is triggered
        """
        self.available_actions[action_name] = action_func
        self._log_info(f"Registered action: {action_name}")
        if self.dev_mode:
            print(f"[DEV] Registered action: {action_name}")
    
    def _call_llm(self, prompt: str, temperature: float, model: str) -> Dict:
        """
        Call the LLM API and return the response as a parsed JSON.
        
        This method constructs the prompt with system context, handles API communication,
        and processes the response.
        
        Args:
            prompt: The specific prompt for the current state
            temperature: Temperature setting for LLM response randomness
            model: Model identifier to use for the API call
            
        Returns:
            Dict containing the parsed JSON response from the LLM
        """
        try:
            # Get the general description from the config
            description = self.config.get("description", {})
            role = description.get("role", "")
            state_machine_logic = description.get("state_machine_logic", "")
            work_principles = description.get("work_principles", "")
            
            # Format search history as a separate block if it exists
            search_history_block = ""
            if self.search_history:
                search_history_block = "\n\nSEARCH HISTORY:\n"
                for idx, search_result in enumerate(self.search_history):
                    search_history_block += f"Search #{idx+1}: {search_result}\n\n"
                print("[DEV] SEARCH HISTORY:")
                for i, search_result in enumerate(self.search_history):
                    print(f"[DEV] Search Result #{i+1}:")
                    print(search_result)
                    print("-"*40) 
            
            # Construct a complete system prompt that includes the general description and search history
            complete_system_prompt = f"""
            {role}

            {state_machine_logic}

            {work_principles}

            CURRENT STATE: {self.current_state}
            {search_history_block}
            {prompt}
            """
            
            # Format the system prompt and user conversation history
            messages = [{"role": "system", "content": complete_system_prompt}]
            
            # Add conversation history
            for msg in self.conversation_history:
                messages.append(msg)
            
            # Log LLM call details
            self._log_info(f"CALLING LLM - Model: {model}, Temperature: {temperature}")
            self._log_info(f"Current state: {self.current_state}")
            self._log_json("System prompt", {"role": "system", "content": complete_system_prompt})
            
            for i, msg in enumerate(messages):
                if i > 0:  # Skip system prompt as it's already logged separately
                    self._log_json(f"Message {i} ({msg['role']})", msg)
            
            if self.search_history:
                for i, search_result in enumerate(self.search_history):
                    self._log_info(f"Search Result #{i+1}:")
                    self._log_info(search_result)

          
            # Output debug information if in dev mode
            if self.dev_mode:
                print("\n" + "="*80)
                if self.search_history:
                    print("[DEV] SEARCH HISTORY:")
                    for i, search_result in enumerate(self.search_history):
                        print(f"[DEV] Search Result #{i+1}:")
                        print(search_result)
                        print("-"*40)  

                print("[DEV] CALLING LLM")
                print(f"[DEV] Model: {model}")
                print(f"[DEV] Temperature: {temperature}")
                print("[DEV] Prompt and Messages:")
                for i, msg in enumerate(messages):
                    print(f"[DEV] Message {i} ({msg['role']}):")
                    print(f"{msg['content']}")
                    print("-"*40)  # Separator between messages for better readability
                
                print("="*80 + "\n")
            
            # Make the actual API call
            completion = self.client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=messages,
                max_tokens=5000,
                response_format={"type": "json_object"}
            )
            
            response_text = completion.choices[0].message.content
            
            # Log the raw LLM response
            self._log_json("LLM RAW RESPONSE", response_text)
            
            if self.dev_mode:
                print("\n" + "="*80)
                print("[DEV] LLM RAW RESPONSE:")
                print(response_text)
                print("="*80 + "\n")
            
            # Parse JSON response, handle errors gracefully
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                error_msg = f"Error: LLM response is not valid JSON: {response_text}"
                self._log_info(error_msg)
                if self.dev_mode:
                    print(f"[DEV] {error_msg}")
                return {
                    "action": "error",
                    "message": "I apologize, but I encountered an error processing your request.",
                    "next_state": "error",
                    "require_input": "1"  # Default to requiring input after an error
                }
        except Exception as e:
            # Handle any other exceptions during API call
            error_msg = f"Error calling LLM API: {e}"
            self._log_info(error_msg)
            if self.dev_mode:
                print(f"[DEV] {error_msg}")
            return {
                "action": "error",
                "message": f"Error occurred: {str(e)}",
                "next_state": "error",
                "require_input": "1"  # Default to requiring input after an error
            }
    
    def run(self, user_input: str = None):
        """
        Run the agent's main loop, processing user input and transitioning between states.
        
        This is the main method to start the agent's execution. It will continue running
        until it reaches a terminal state or encounters an error.
        
        Args:
            user_input: Initial user input to start the conversation (optional)
        """
        # Process initial user input if provided
        if user_input:
            self.conversation_history.append({"role": "user", "content": user_input})
            self._log_json("Initial user input", {"role": "user", "content": user_input})
            if self.dev_mode:
                print(f"[DEV] Initial user input: {user_input}")
        
        # Main execution loop counter
        loop_count = 0
        
        # Main agent execution loop
        while True:
            loop_count += 1
            self._log_info(f"===== LOOP #{loop_count} =====")
            
            # Get current state configuration from the config file
            state_config = self.config["states"].get(self.current_state)
            if not state_config:
                error_msg = f"Error: State '{self.current_state}' not found in configuration"
                self._log_info(error_msg)
                if self.dev_mode:
                    print(f"[DEV] {error_msg}")
                print(error_msg)
                break
            
            # Log current state information
            self._log_info(f"Current state: {self.current_state}")
            self._log_info(f"Allowed transitions: {state_config.get('transitions', [])}")
            
            if self.dev_mode:
                print(f"[DEV] Current state: {self.current_state}")
                print(f"[DEV] Allowed transitions: {state_config.get('transitions', [])}")
            
            # Extract configuration for the current state
            prompt = state_config["prompt"]
            temperature = state_config.get("temperature", 0.7)
            model = state_config.get("model", "llama3-70b-8192")
            
            # Call LLM with the configured prompt and settings
            response = self._call_llm(prompt, temperature, model)
            
            # Extract response components for processing
            action = response.get("action", "")
            message = response.get("message", "")
            next_state = response.get("next_state", "")
            require_input = response.get("require_input", "1")  # Default to requiring input if not specified
            
            # Log LLM decision information
            self._log_info(f"LLM decided action: {action}")
            self._log_info(f"LLM next state: {next_state}")
            self._log_info(f"LLM require_input: {require_input}")
            
            if self.dev_mode:
                print(f"[DEV] LLM decided action: {action}")
                print(f"[DEV] LLM next state: {next_state}")
                print(f"[DEV] LLM require_input: {require_input}")
            
            # Add assistant's message to conversation history
            self.conversation_history.append({"role": "assistant", "content": message})
            
            # Log assistant's reply
            self._log_json("Assistant reply", {"role": "assistant", "content": message})
            
            # Display the message to the user
            print(f"Agent: {message}")            
                
            # Execute registered action if specified in the response
            if action and action in self.available_actions:
                # Extract any action parameters from the response
                action_params = response.get("action_params", {})
                self._log_json(f"Executing action: {action}", action_params)
                if self.dev_mode:
                    print(f"[DEV] Executing action: {action}")
                    print(f"[DEV] Action parameters: {action_params}")
                
                # Call the registered action function with parameters
                action_result = self.available_actions[action](action_params)
                self._log_info(f"Action result: {action_result}")
                
                # Handle different types of action results
                if action_result:
                    if action == "search":
                        # Add search results to separate search history
                        self.search_history.append(action_result)
                        self._log_info(f"Search result added to search history")
                        if self.dev_mode:
                            print(f"[DEV] Search result added to search history")
                    else:
                        # For other actions, add result to conversation history
                        self.conversation_history.append({
                            "role": "system", 
                            "content": f"Action result: {action_result}"
                        })
                        self._log_json("Action result added to conversation", {
                            "role": "system", 
                            "content": f"Action result: {action_result}"
                        })
                    
                    if self.dev_mode:
                        print(f"[DEV] Action result: {action_result}")
            
            # Validate and process state transition
            allowed_transitions = state_config.get("transitions", [])
            if next_state in self.config["states"] and (not allowed_transitions or next_state in allowed_transitions):
                self._log_info(f"Transitioning from '{self.current_state}' to '{next_state}'")
                if self.dev_mode:
                    print(f"[DEV] Transitioning from '{self.current_state}' to '{next_state}'")
                self.current_state = next_state
            else:
                # Handle invalid state transition
                error_msg = f"Error: Invalid transition from '{self.current_state}' to '{next_state}'"
                self._log_info(error_msg)
                if self.dev_mode:
                    print(f"[DEV] {error_msg}")
                print(error_msg)
                self.current_state = "error"
            
            # Check if this is a terminal state to exit the loop
            if next_state == "exit" or next_state == "":
                self._log_info("Reached terminal state, exiting.")
                if self.dev_mode:
                    print("[DEV] Reached terminal state, exiting.")
                break            

            # Handle user input requirements for the next loop iteration
            if require_input == "1":
                # Get user input for the next iteration
                user_input = input("You: ")
                self.conversation_history.append({"role": "user", "content": user_input})
                self._log_json("User input", {"role": "user", "content": user_input})
                if self.dev_mode:
                    print(f"[DEV] User input: {user_input}")
            else:
                # Continue to next state without user input
                self._log_info("No user input required, proceeding to next state automatically")
                if self.dev_mode:
                    print("[DEV] No user input required, proceeding to next state automatically")