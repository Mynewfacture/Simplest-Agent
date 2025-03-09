#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Configuration Editor GUI

This module provides a graphical user interface for editing and visualizing
agent configuration files in TOML format. It allows users to modify state machine
configurations including state transitions, prompts, temperatures, and models.

Features:
- Edit configuration parameters through an intuitive interface
- Visualize the state machine as a directed graph
- Add, edit, and delete states
- Configure transitions between states
- Save and reload configurations
"""

import os, sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import networkx as nx

# Choose the appropriate TOML library based on Python version
try:
    import tomllib  # Python 3.11+
    import tomli_w as tomli_write  # For writing TOML
except ImportError:
    import tomli as tomllib  # Python 3.10 and below
    import tomli_w as tomli_write  # For writing TOML

class ConfigEditorApp:
    """
    Main application class for the Agent Configuration Editor GUI.
    
    This class handles the creation of the UI, loading/saving of configuration files,
    and all user interactions for editing the agent configuration.
    
    Attributes:
        root (tk.Tk): The main Tkinter window
        config_path (str): Path to the TOML configuration file
        config_data (dict): Loaded configuration data
        notebook (ttk.Notebook): Main tab container
    """
    def __init__(self, root, config_path):
        """
        Initialize the ConfigEditorApp with the specified root window and config path.
        
        Args:
            root (tk.Tk): The main Tkinter window
            config_path (str): Path to the TOML configuration file
        """
        self.root = root
        self.root.title("Agent Config Editor")
        self.root.geometry("1200x800")
        self.config_path = config_path
        self.config_data = None
        
        # Create main frame with notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create editor tab
        self.editor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.editor_frame, text="Editor")
        
        # Create visualization tab
        self.graph_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.graph_frame, text="State Visualization")
        
        # Setup the editor interface
        self.setup_editor_interface()
        
        # Setup the graph visualization interface
        self.setup_graph_interface()
        
        # Load initial configuration
        self.load_config()
        
    def setup_editor_interface(self):
        """
        Initialize the editor interface with tree navigation and editing panels.
        
        This method creates the left navigation panel with a treeview and the
        right panel for editing configuration properties.
        """
        # Create main frame
        self.main_frame = ttk.Frame(self.editor_frame)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create left panel for navigation
        self.left_panel = ttk.Frame(self.main_frame, width=300)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Create right panel for editing
        self.right_panel = ttk.Frame(self.main_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Create treeview for navigation
        self.tree = ttk.Treeview(self.left_panel)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # Create frame for buttons
        self.btn_frame = ttk.Frame(self.left_panel)
        self.btn_frame.pack(fill=tk.X, pady=10)
        
        # Create buttons
        self.save_btn = ttk.Button(self.btn_frame, text="Save", command=self.save_config)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        self.reload_btn = ttk.Button(self.btn_frame, text="Reload", command=self.load_config)
        self.reload_btn.pack(side=tk.LEFT, padx=5)
        
        self.add_state_btn = ttk.Button(self.btn_frame, text="Add State", command=self.add_state)
        self.add_state_btn.pack(side=tk.LEFT, padx=5)
    
    def setup_graph_interface(self):
        """
        Initialize the graph visualization interface.
        
        This method creates the controls for the graph visualization and 
        the container for the NetworkX graph rendering.
        """
        # Create controls frame at the top
        self.graph_controls = ttk.Frame(self.graph_frame)
        self.graph_controls.pack(fill=tk.X, padx=10, pady=10)
        
        # Add refresh button
        self.refresh_graph_btn = ttk.Button(self.graph_controls, text="Refresh Graph", command=self.update_graph)
        self.refresh_graph_btn.pack(side=tk.LEFT, padx=5)
        
        # Add layout options
        ttk.Label(self.graph_controls, text="Layout:").pack(side=tk.LEFT, padx=(20, 5))
        self.layout_var = tk.StringVar(value="spring")
        layouts = ["spring", "circular", "kamada_kawai", "planar", "random", "shell", "spectral"]
        self.layout_combo = ttk.Combobox(self.graph_controls, textvariable=self.layout_var, values=layouts)
        self.layout_combo.pack(side=tk.LEFT, padx=5)
        self.layout_combo.bind("<<ComboboxSelected>>", lambda e: self.update_graph())
        
        # Create frame for the graph
        self.graph_container = ttk.Frame(self.graph_frame)
        self.graph_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Canvas for the graph will be created when needed
        self.canvas = None
        
    def load_config(self):
        """
        Load the TOML configuration file from disk.
        
        This method reads the configuration file, parses it as TOML,
        populates the navigation tree, and updates the graph visualization.
        
        Displays success or error messages to the user.
        """
        try:
            with open(self.config_path, "rb") as f:
                self.config_data = tomllib.load(f)
            self.populate_tree()
            self.update_graph()
            messagebox.showinfo("Success", "Configuration loaded successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")
    
    def populate_tree(self):
        """
        Populate the navigation tree with configuration data.
        
        This method clears the existing tree and rebuilds it based on the
        current configuration data, including root items, description fields,
        states, and their properties.
        """
        # Clear existing tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add root items
        root_id = self.tree.insert("", "end", text="Configuration Root", values=["root"])
        
        # Add basic configuration
        if "initial_state" in self.config_data:
            self.tree.insert(root_id, "end", text=f"Initial State: {self.config_data['initial_state']}", 
                            values=["initial_state"])
        
        # Add description
        if "description" in self.config_data:
            desc_id = self.tree.insert(root_id, "end", text="Description", values=["description"])
            for key in self.config_data["description"]:
                self.tree.insert(desc_id, "end", text=key, values=["description", key])
        
        # Add states
        if "states" in self.config_data:
            states_id = self.tree.insert(root_id, "end", text="States", values=["states"])
            for state_name in self.config_data["states"]:
                state_id = self.tree.insert(states_id, "end", text=state_name, values=["states", state_name])
                for key in self.config_data["states"][state_name]:
                    self.tree.insert(state_id, "end", text=key, values=["states", state_name, key])
        
        # Expand all
        self.tree.item(root_id, open=True)
    
    def update_graph(self):
        """
        Update the state machine visualization graph.
        
        This method creates or refreshes the NetworkX directed graph based on
        the current configuration data, applying the selected layout algorithm.
        The graph shows states as nodes and transitions as edges, with special
        highlighting for the initial state.
        """
        if not self.config_data or 'states' not in self.config_data:
            return
        
        # Clear the existing graph container
        for widget in self.graph_container.winfo_children():
            widget.destroy()
        
        # Create a new figure
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create a directed graph
        G = nx.DiGraph()
        
        # Add nodes (states)
        for state_name in self.config_data['states']:
            # Add color highlight for initial state
            if self.config_data.get('initial_state') == state_name:
                G.add_node(state_name, initial=True)
            else:
                G.add_node(state_name, initial=False)
        
        # Add edges (transitions)
        for state_name, state_data in self.config_data['states'].items():
            if 'transitions' in state_data:
                for target in state_data['transitions']:
                    if target in self.config_data['states']:
                        G.add_edge(state_name, target)
        
        # Get the layout algorithm
        layout_name = self.layout_var.get()
        if layout_name == "spring":
            pos = nx.spring_layout(G, seed=42)
        elif layout_name == "circular":
            pos = nx.circular_layout(G)
        elif layout_name == "kamada_kawai":
            pos = nx.kamada_kawai_layout(G)
        elif layout_name == "planar":
            try:
                pos = nx.planar_layout(G)
            except:
                pos = nx.spring_layout(G, seed=42)  # Fallback if graph is not planar
        elif layout_name == "random":
            pos = nx.random_layout(G, seed=42)
        elif layout_name == "shell":
            pos = nx.shell_layout(G)
        elif layout_name == "spectral":
            pos = nx.spectral_layout(G)
        else:
            pos = nx.spring_layout(G, seed=42)
        
        # Create node lists by type for coloring
        initial_nodes = [n for n, attr in G.nodes(data=True) if attr.get('initial', False)]
        regular_nodes = [n for n, attr in G.nodes(data=True) if not attr.get('initial', False)]
        
        # Draw the nodes
        nx.draw_networkx_nodes(G, pos, nodelist=initial_nodes, node_color='lightgreen', node_size=700, ax=ax)
        nx.draw_networkx_nodes(G, pos, nodelist=regular_nodes, node_color='skyblue', node_size=500, ax=ax)
        
        # Draw the edges
        nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.7, arrowsize=20, ax=ax)
        
        # Draw the labels
        nx.draw_networkx_labels(G, pos, font_size=10, font_family='sans-serif', ax=ax)
        
        # Remove the axis
        ax.set_axis_off()
        
        # Add title
        plt.title("State Machine Visualization", fontsize=16)
        
        # Add legend
        import matplotlib.patches as mpatches
        initial_patch = mpatches.Patch(color='lightgreen', label='Initial State')
        regular_patch = mpatches.Patch(color='skyblue', label='Regular State')
        plt.legend(handles=[initial_patch, regular_patch], loc='upper right')
        
        # Create canvas
        canvas = FigureCanvasTkAgg(fig, master=self.graph_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Store reference to canvas
        self.canvas = canvas
    
    def on_tree_select(self, event):
        """
        Handle tree item selection events.
        
        This method clears the right panel and shows the appropriate editor
        based on the selected tree item.
        
        Args:
            event: The Tkinter event object (can be None when called programmatically)
        """
        # Clear right panel
        for widget in self.right_panel.winfo_children():
            widget.destroy()
        
        # Get selected item
        selected_item = self.tree.selection()[0]
        values = self.tree.item(selected_item, "values")
        
        if not values:
            return
        
        # Show appropriate editor based on selection
        if values[0] == "root":
            self.show_root_editor()
        elif values[0] == "initial_state":
            self.show_initial_state_editor()
        elif values[0] == "description":
            if len(values) > 1:
                self.show_description_field_editor(values[1])
            else:
                self.show_description_editor()
        elif values[0] == "states":
            if len(values) == 1:
                self.show_states_editor()
            elif len(values) == 2:
                self.show_state_editor(values[1])
            elif len(values) == 3:
                self.show_state_field_editor(values[1], values[2])
    
    def show_root_editor(self):
        """
        Display the root configuration overview editor.
        
        This method shows a summary of the configuration file, including
        the path, initial state, and a list of available states.
        """
        frame = ttk.LabelFrame(self.right_panel, text="Configuration Overview")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Show configuration summary
        info_text = f"""
        Configuration File: {self.config_path}
        Initial State: {self.config_data.get('initial_state', 'Not set')}
        Number of States: {len(self.config_data.get('states', {}))}
        
        States:
        {', '.join(list(self.config_data.get('states', {}).keys()))}
        """
        
        info_label = ttk.Label(frame, text=info_text, justify=tk.LEFT, padding=10)
        info_label.pack(fill=tk.BOTH, expand=True)
    
    def show_initial_state_editor(self):
        """
        Display the initial state editor.
        
        This method creates a dropdown for selecting the initial state
        from the available states in the configuration.
        """
        frame = ttk.LabelFrame(self.right_panel, text="Initial State")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create dropdown for initial state
        state_label = ttk.Label(frame, text="Initial State:")
        state_label.pack(pady=(10, 5))
        
        state_var = tk.StringVar(value=self.config_data.get('initial_state', ''))
        state_dropdown = ttk.Combobox(frame, textvariable=state_var)
        state_dropdown['values'] = list(self.config_data.get('states', {}).keys())
        state_dropdown.pack(pady=(0, 10))
        
        # Save button
        save_btn = ttk.Button(frame, text="Update", 
                             command=lambda: self.update_initial_state(state_var.get()))
        save_btn.pack(pady=10)
    
    def update_initial_state(self, new_state):
        """
        Update the initial state in the configuration.
        
        Args:
            new_state (str): The name of the new initial state
            
        Validates that the state exists before updating and shows
        appropriate success or error messages.
        """
        if not new_state or new_state not in self.config_data.get('states', {}):
            messagebox.showerror("Error", f"Invalid state: {new_state}")
            return
        
        self.config_data['initial_state'] = new_state
        self.populate_tree()
        self.update_graph()  # Update the graph to show new initial state
        messagebox.showinfo("Success", f"Initial state updated to {new_state}")
    
    def show_description_editor(self):
        """
        Display the description editor.
        
        This method creates text widgets for each description field
        in the configuration, allowing the user to edit them.
        """
        frame = ttk.LabelFrame(self.right_panel, text="Description")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a scrolled text widget for each description field
        for key in self.config_data.get('description', {}):
            field_frame = ttk.LabelFrame(frame, text=key)
            field_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            text_widget = scrolledtext.ScrolledText(field_frame, wrap=tk.WORD, height=10)
            text_widget.insert(tk.END, self.config_data['description'][key])
            text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            update_btn = ttk.Button(field_frame, text="Update", 
                                   command=lambda k=key, t=text_widget: self.update_description_field(k, t.get("1.0", tk.END)))
            update_btn.pack(pady=5)
    
    def show_description_field_editor(self, field):
        """
        Display the editor for a specific description field.
        
        Args:
            field (str): The name of the description field to edit
            
        Creates a text widget for editing the specified description field.
        """
        frame = ttk.LabelFrame(self.right_panel, text=f"Description - {field}")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a scrolled text widget for the description field
        text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD)
        text_widget.insert(tk.END, self.config_data['description'].get(field, ''))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Save button
        save_btn = ttk.Button(frame, text="Update", 
                             command=lambda: self.update_description_field(field, text_widget.get("1.0", tk.END)))
        save_btn.pack(pady=10)
    
    def update_description_field(self, field, new_text):
        """
        Update a description field in the configuration.
        
        Args:
            field (str): The name of the description field to update
            new_text (str): The new content for the description field
            
        Creates the description section if it doesn't exist.
        """
        if 'description' not in self.config_data:
            self.config_data['description'] = {}
        
        self.config_data['description'][field] = new_text.strip()
        messagebox.showinfo("Success", f"Description field '{field}' updated")
    
    def show_states_editor(self):
        """
        Display the states list editor.
        
        This method creates a listbox showing all available states
        with buttons for adding, deleting, and editing states.
        """
        frame = ttk.LabelFrame(self.right_panel, text="States")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a listbox of states
        listbox_frame = ttk.Frame(frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        states_list = list(self.config_data.get('states', {}).keys())
        listbox = tk.Listbox(listbox_frame)
        for state in states_list:
            listbox.insert(tk.END, state)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons for state management
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        add_btn = ttk.Button(btn_frame, text="Add State", command=self.add_state)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        del_btn = ttk.Button(btn_frame, text="Delete State", 
                            command=lambda: self.delete_state(listbox.get(listbox.curselection()) if listbox.curselection() else None))
        del_btn.pack(side=tk.LEFT, padx=5)
        
        edit_btn = ttk.Button(btn_frame, text="Edit State", 
                             command=lambda: self.edit_state(listbox.get(listbox.curselection()) if listbox.curselection() else None))
        edit_btn.pack(side=tk.LEFT, padx=5)
    
    def show_state_editor(self, state_name):
        """
        Display the editor for a specific state.
        
        Args:
            state_name (str): The name of the state to edit
            
        Creates a tabbed interface with editors for each state property
        (prompt, temperature, model, transitions).
        """
        frame = ttk.LabelFrame(self.right_panel, text=f"State: {state_name}")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs for each field
        state_data = self.config_data['states'][state_name]
        
        # Prompt tab
        prompt_tab = ttk.Frame(notebook)
        notebook.add(prompt_tab, text="Prompt")
        
        prompt_text = scrolledtext.ScrolledText(prompt_tab, wrap=tk.WORD)
        prompt_text.insert(tk.END, state_data.get('prompt', ''))
        prompt_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        prompt_btn = ttk.Button(prompt_tab, text="Update Prompt", 
                               command=lambda: self.update_state_field(state_name, 'prompt', prompt_text.get("1.0", tk.END)))
        prompt_btn.pack(pady=10)
        
        # Temperature tab
        temp_tab = ttk.Frame(notebook)
        notebook.add(temp_tab, text="Temperature")
        
        temp_label = ttk.Label(temp_tab, text="Temperature (0.0 - 1.0):")
        temp_label.pack(pady=(10, 5))
        
        temp_var = tk.DoubleVar(value=state_data.get('temperature', 0.7))
        temp_slider = ttk.Scale(temp_tab, from_=0.0, to=1.0, variable=temp_var, orient=tk.HORIZONTAL)
        temp_slider.pack(fill=tk.X, padx=20, pady=5)
        
        temp_value = ttk.Label(temp_tab, textvariable=temp_var)
        temp_value.pack(pady=5)
        
        temp_btn = ttk.Button(temp_tab, text="Update Temperature", 
                             command=lambda: self.update_state_field(state_name, 'temperature', temp_var.get()))
        temp_btn.pack(pady=10)
        
        # Model tab
        model_tab = ttk.Frame(notebook)
        notebook.add(model_tab, text="Model")
        
        model_label = ttk.Label(model_tab, text="Model:")
        model_label.pack(pady=(10, 5))
        
        model_var = tk.StringVar(value=state_data.get('model', ''))
        model_entry = ttk.Entry(model_tab, textvariable=model_var, width=40)
        model_entry.pack(pady=5)
        
        model_options = ["llama3-70b-8192", "qwen/qwen-2.5-72b-instruct", "gpt-4o", "claude-3-opus-20240229"]
        model_dropdown = ttk.Combobox(model_tab, textvariable=model_var, values=model_options)
        model_dropdown.pack(pady=5)
        
        model_btn = ttk.Button(model_tab, text="Update Model", 
                              command=lambda: self.update_state_field(state_name, 'model', model_var.get()))
        model_btn.pack(pady=10)
        
        # Transitions tab
        trans_tab = ttk.Frame(notebook)
        notebook.add(trans_tab, text="Transitions")
        
        trans_label = ttk.Label(trans_tab, text="Allowed Transitions (comma-separated):")
        trans_label.pack(pady=(10, 5))
        
        trans_var = tk.StringVar(value=", ".join(state_data.get('transitions', [])))
        trans_entry = ttk.Entry(trans_tab, textvariable=trans_var, width=40)
        trans_entry.pack(pady=5)
        
        # Add all states as checkbuttons
        trans_frame = ttk.Frame(trans_tab)
        trans_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        trans_vars = {}
        all_states = list(self.config_data['states'].keys())
        current_transitions = state_data.get('transitions', [])
        
        for i, state in enumerate(all_states):
            var = tk.BooleanVar(value=state in current_transitions)
            trans_vars[state] = var
            check = ttk.Checkbutton(trans_frame, text=state, variable=var)
            check.grid(row=i//2, column=i%2, sticky=tk.W, padx=10, pady=5)
        
        trans_btn = ttk.Button(trans_tab, text="Update Transitions", 
                              command=lambda: self.update_transitions(state_name, trans_vars))
        trans_btn.pack(pady=10)
    
    def show_state_field_editor(self, state_name, field_name):
        """
        Display the editor for a specific state field.
        
        Args:
            state_name (str): The name of the state
            field_name (str): The name of the field to edit
            
        Creates an appropriate editor widget based on the field type.
        """
        frame = ttk.LabelFrame(self.right_panel, text=f"State: {state_name} - {field_name}")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        state_data = self.config_data['states'][state_name]
        field_value = state_data.get(field_name, '')
        
        if field_name == 'prompt':
            # Text area for prompt
            text_widget = scrolledtext.ScrolledText(frame, wrap=tk.WORD)
            text_widget.insert(tk.END, field_value)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            save_btn = ttk.Button(frame, text="Update", 
                                 command=lambda: self.update_state_field(state_name, field_name, text_widget.get("1.0", tk.END)))
            save_btn.pack(pady=10)
        
        elif field_name == 'temperature':
            # Slider for temperature
            temp_label = ttk.Label(frame, text="Temperature (0.0 - 1.0):")
            temp_label.pack(pady=(20, 10))
            
            temp_var = tk.DoubleVar(value=field_value)
            temp_slider = ttk.Scale(frame, from_=0.0, to=1.0, variable=temp_var, orient=tk.HORIZONTAL, length=300)
            temp_slider.pack(pady=10)
            
            temp_value = ttk.Label(frame, textvariable=temp_var)
            temp_value.pack(pady=10)
            
            save_btn = ttk.Button(frame, text="Update", 
                                 command=lambda: self.update_state_field(state_name, field_name, temp_var.get()))
            save_btn.pack(pady=20)
        
        elif field_name == 'model':
            # Entry for model name
            model_label = ttk.Label(frame, text="Model:")
            model_label.pack(pady=(20, 10))
            
            model_var = tk.StringVar(value=field_value)
            model_entry = ttk.Entry(frame, textvariable=model_var, width=40)
            model_entry.pack(pady=10)
            
            # Add common model options
            model_options = ["llama3-70b-8192", "qwen/qwen-2.5-72b-instruct", "gpt-4o", "claude-3-opus-20240229"]
            model_label = ttk.Label(frame, text="Common Models:")
            model_label.pack(pady=(20, 10))
            
            model_listbox = tk.Listbox(frame, height=5)
            for model in model_options:
                model_listbox.insert(tk.END, model)
            model_listbox.pack(pady=10)
            
            # Double click to select
            model_listbox.bind("<Double-1>", lambda e: model_var.set(model_listbox.get(model_listbox.curselection())))
            
            save_btn = ttk.Button(frame, text="Update", 
                                 command=lambda: self.update_state_field(state_name, field_name, model_var.get()))
            save_btn.pack(pady=20)
        
        elif field_name == 'transitions':
            # Multi-select for transitions
            trans_label = ttk.Label(frame, text="Allowed Transitions:")
            trans_label.pack(pady=(20, 10))
            
            # Create checkbuttons for all available states
            trans_vars = {}
            trans_frame = ttk.Frame(frame)
            trans_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            all_states = list(self.config_data['states'].keys())
            current_transitions = field_value
            
            for i, state in enumerate(all_states):
                var = tk.BooleanVar(value=state in current_transitions)
                trans_vars[state] = var
                check = ttk.Checkbutton(trans_frame, text=state, variable=var)
                check.grid(row=i//2, column=i%2, sticky=tk.W, padx=10, pady=5)
            
            save_btn = ttk.Button(frame, text="Update", 
                                 command=lambda: self.update_transitions(state_name, trans_vars))
            save_btn.pack(pady=20)
    
    def update_state_field(self, state_name, field_name, new_value):
        """
        Update a state field in the configuration.
        
        Args:
            state_name (str): The name of the state
            field_name (str): The name of the field to update
            new_value: The new value for the field
            
        Handles special processing for prompt fields and updates the graph
        if transitions were modified.
        """
        if field_name == 'prompt':
            new_value = new_value.strip()
        
        self.config_data['states'][state_name][field_name] = new_value
        messagebox.showinfo("Success", f"Updated {field_name} for state {state_name}")
        
        # If we updated transitions, refresh the graph
        if field_name == 'transitions':
            self.update_graph()
    
    def update_transitions(self, state_name, trans_vars):
        """
        Update the transitions for a state based on checkbox selections.
        
        Args:
            state_name (str): The name of the state
            trans_vars (dict): Dictionary mapping state names to BooleanVar objects
            
        Collects all selected transitions and updates the state configuration.
        """
        # Get all selected states
        transitions = [state for state, var in trans_vars.items() if var.get()]
        self.config_data['states'][state_name]['transitions'] = transitions
        messagebox.showinfo("Success", f"Updated transitions for state {state_name}")
        self.update_graph()  # Refresh the graph with new transitions
    
    def add_state(self):
        """
        Display a dialog for adding a new state.
        
        Creates a dialog with fields for the state name and an optional
        template state to clone settings from.
        """
        # Create a dialog to add a new state
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New State")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="New State Name:").pack(pady=(20, 5))
        
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Template (optional):").pack(pady=(20, 5))
        
        template_var = tk.StringVar()
        template_options = ["Empty"] + list(self.config_data['states'].keys())
        template_dropdown = ttk.Combobox(dialog, textvariable=template_var, values=template_options)
        template_dropdown.pack(pady=5)
        template_dropdown.current(0)
        
        def on_add():
            """
            Handle the "Add" button click in the add state dialog.
            
            Validates input, creates the new state, and updates the UI.
            """
            state_name = name_var.get().strip()
            if not state_name:
                messagebox.showerror("Error", "State name cannot be empty")
                return
            
            if state_name in self.config_data['states']:
                messagebox.showerror("Error", f"State '{state_name}' already exists")
                return
            
            # Create new state
            if template_var.get() == "Empty":
                self.config_data['states'][state_name] = {
                    'prompt': f"This is the prompt for {state_name} state.",
                    'temperature': 0.7,
                    'model': 'qwen/qwen-2.5-72b-instruct',
                    'transitions': []
                }
            else:
                # Clone from template
                template = template_var.get()
                self.config_data['states'][state_name] = dict(self.config_data['states'][template])
            
            self.populate_tree()
            self.update_graph()  # Refresh the graph with new state
            messagebox.showinfo("Success", f"Added new state: {state_name}")
            dialog.destroy()
        
        ttk.Button(dialog, text="Add", command=on_add).pack(pady=20)
    
    def delete_state(self, state_name):
        """
        Delete a state from the configuration.
        
        Args:
            state_name (str): The name of the state to delete
            
        Validates that the state exists and is not the initial state,
        then removes it and updates any transitions that referenced it.
        """
        if not state_name:
            messagebox.showerror("Error", "No state selected")
            return
        
        if state_name not in self.config_data['states']:
            messagebox.showerror("Error", f"State '{state_name}' not found")
            return
        
        # Confirm deletion
        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete state '{state_name}'?")
        if not confirm:
            return
        
        # Check if this is the initial state
        if self.config_data.get('initial_state') == state_name:
            messagebox.showerror("Error", f"Cannot delete initial state '{state_name}'. Change the initial state first.")
            return
        
        # Remove state
        del self.config_data['states'][state_name]
        
        # Update transitions in other states
        for other_state in self.config_data['states'].values():
            if 'transitions' in other_state and state_name in other_state['transitions']:
                other_state['transitions'].remove(state_name)
        
        self.populate_tree()
        self.update_graph()  # Refresh the graph without the deleted state
        messagebox.showinfo("Success", f"Deleted state: {state_name}")
    
    def edit_state(self, state_name):
        """
        Navigate to the editor for a specific state.
        
        Args:
            state_name (str): The name of the state to edit
            
        Finds the state in the navigation tree and selects it to show
        the state editor.
        """
        if not state_name:
            messagebox.showerror("Error", "No state selected")
            return
        
        if state_name not in self.config_data['states']:
            messagebox.showerror("Error", f"State '{state_name}' not found")
            return
        
        # Find the state item in the tree and select it
        for state_item in self.tree.get_children():
            if self.tree.item(state_item, "text") == "States":
                for child in self.tree.get_children(state_item):
                    if self.tree.item(child, "text") == state_name:
                        self.tree.selection_set(child)
                        self.tree.see(child)
                        self.on_tree_select(None)
                        return
    
    def save_config(self):
        """
        Save the configuration to the TOML file.
        
        Writes the current configuration data to the specified file path
        and displays a success or error message.
        """
        try:
            # Convert to TOML and save
            with open(self.config_path, "wb") as f:
                tomli_write.dump(self.config_data, f)
            messagebox.showinfo("Success", f"Configuration saved to {self.config_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")

def main():
    """
    Main entry point for the application.
    
    Parses command line arguments for the configuration file path,
    falls back to a default if not provided, and initializes the
    application UI.
    """
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        # Default to the sample config
        config_path = "agent_config.toml"
    
    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' not found.")
        return
    
    root = tk.Tk()
    app = ConfigEditorApp(root, config_path)
    root.mainloop()

if __name__ == "__main__":
    main()