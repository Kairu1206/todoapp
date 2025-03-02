import json
import os
import re
import tkinter as tk
import requests
import threading
import markdown
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk, messagebox, simpledialog
from tkcalendar import DateEntry
from tkinter.font import Font
from datetime import datetime
from pathlib import Path

TODO_FILE = str(Path.home()) + "/TODOapp/todo.txt"
CHARACTER_FILE = str(Path.home()) + "/TODOapp/character.txt"
VERSION_FILE = str(Path.home()) + "/TODOapp/version.txt"

class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TODO App")
        self.root.geometry("1000x700")

        self.inside_think = False  # Track if we're inside a <think> block
        self.think_buffer = ''     # Buffer for partial tags between chunks
        self.show_thinking = True  # Default state
        self.show_thinking_var = tk.BooleanVar(value=self.show_thinking)
        self.load_config()
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'))
        self.style.configure("Treeview", rowheight=25)
        
        # Character stats
        self.level = 0
        self.tasks_completed = 0
        
        # Create widgets
        self.create_widgets()
        self.load_character()
        self.refresh_task_list()

        # Version
        self.version = "0.0.0"

    def load_app_version(self):
        try:
            with open(VERSION_FILE, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return "0.0.0 (dev)"

    def create_widgets(self):
        menubar = tk.Menu(self.root)
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_checkbutton(label="Show Thinking Messages", 
                                command=self.toggle_thinking,
                                variable=self.show_thinking_var)
        menubar.add_cascade(label="Options", menu=options_menu)
        self.root.config(menu=menubar)

        # Character stats frame
        char_frame = ttk.Frame(self.root)
        char_frame.pack(pady=10, padx=10, fill=tk.X)

        # Level row
        level_frame = ttk.Frame(char_frame)
        level_frame.pack(fill=tk.X, pady=2)
        ttk.Label(level_frame, text="Level:", font=('Helvetica', 12, 'bold')).pack(side=tk.LEFT)
        self.level_label = ttk.Label(level_frame, text="0", font=('Helvetica', 12))
        self.level_label.pack(side=tk.LEFT, padx=5)

        # Tasks Completed row
        completed_frame = ttk.Frame(char_frame)
        completed_frame.pack(fill=tk.X, pady=2)
        ttk.Label(completed_frame, text="Tasks Completed:", font=('Helvetica', 12, 'bold')).pack(side=tk.LEFT)
        self.tasks_label = ttk.Label(completed_frame, text="0", font=('Helvetica', 12))
        self.tasks_label.pack(side=tk.LEFT, padx=5)

        # Tasks Remaining row
        remaining_frame = ttk.Frame(char_frame)
        remaining_frame.pack(fill=tk.X, pady=2)
        ttk.Label(remaining_frame, text="Tasks Remaining:", font=('Helvetica', 12, 'bold')).pack(side=tk.LEFT)
        self.remaining_label = ttk.Label(remaining_frame, text="0", font=('Helvetica', 12))
        self.remaining_label.pack(side=tk.LEFT, padx=5)

        # Task list
        self.tree = ttk.Treeview(self.root, columns=("Task", "Due Date", "Priority"), show="headings")
        self.tree.heading("Task", text="Task", command=lambda: self.sort_column("Task", False))
        self.tree.heading("Due Date", text="Due Date", command=lambda: self.sort_column("Due Date", False))
        self.tree.heading("Priority", text="Priority", command=lambda: self.sort_column("Priority", False))
        self.tree.column("Task", width=400)
        self.tree.column("Due Date", width=150)
        self.tree.column("Priority", width=100)
        self.tree.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Controls
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=10, fill=tk.X)
        
        ttk.Button(control_frame, text="Add Task", command=self.add_task_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Finish Task", command=self.remove_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Delete Task", command=self.delete_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Edit Task", command=self.edit_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Character Info", command=self.show_character).pack(side=tk.LEFT, padx=5)

        # Add this with other buttons in control_frame
        ttk.Button(control_frame, text="AI Assistant", command=self.open_ai_dialog).pack(side=tk.LEFT, padx=5)

        # Add time display aligned to the right
        self.time_label = ttk.Label(control_frame, font=('Helvetica', 12, 'bold'))
        self.time_label.pack(side=tk.RIGHT, padx=10)
        self.update_time()


        # Version label at bottom right
        version_frame = ttk.Frame(self.root)
        version_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=2)
        
        ttk.Label(
            version_frame,
            text=f"v {self.load_app_version()}",
            font=('Helvetica', 8),
            foreground="gray50",
            anchor="e"  # Right-align text
        ).pack(side=tk.RIGHT, fill=tk.X, expand=True)

    def update_time(self):
        current_time = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)  # Update every second


    def sort_column(self, column, reverse):
        # Get current tasks
        tasks = [(self.tree.set(child, column), child) for child in self.tree.get_children('')]
        
        # Custom sorting
        if column == "Due Date":
            tasks.sort(key=lambda x: datetime.strptime(x[0], "%m-%d-%Y"), reverse=reverse)
        elif column == "Priority":
            tasks.sort(key=lambda x: int(x[0]), reverse=reverse)
        else:
            tasks.sort(reverse=reverse)

        # Rearrange items in sorted positions
        for index, (val, child) in enumerate(tasks):
            self.tree.move(child, '', index)

        # Reverse sort next time
        self.tree.heading(column, command=lambda: self.sort_column(column, not reverse))

    def load_character(self):
        if os.path.exists(CHARACTER_FILE):
            with open(CHARACTER_FILE, "r") as f:
                parts = f.read().strip().split(" | ")
                if len(parts) == 2:
                    self.level = int(parts[0])
                    self.tasks_completed = int(parts[1])
        self.update_character_labels()

    def save_character(self):
        with open(CHARACTER_FILE, "w") as f:
            f.write(f"{self.level} | {self.tasks_completed}")

    def update_character_labels(self):
        self.level_label.config(text=str(self.level))
        self.tasks_label.config(text=str(self.tasks_completed))

    def parse_date(self, raw_date):
        digits = re.sub(r"\D", "", raw_date)
        if len(digits) not in [6, 8]:
            return None
        
        mm = digits[:2].zfill(2)
        dd = digits[2:4].zfill(2) if len(digits) >=4 else "01"
        yy = digits[4:6] if len(digits) ==6 else digits[6:8]
        yyyy = f"20{yy}" if len(digits) ==6 else digits[4:8]
        
        try:
            datetime.strptime(f"{mm}-{dd}-{yyyy}", "%m-%d-%Y")
            return f"{mm}-{dd}-{yyyy}"
        except ValueError:
            return None

    def add_task_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Task")
        
        ttk.Label(dialog, text="Task:").grid(row=0, column=0, padx=5, pady=5)
        task_entry = ttk.Entry(dialog, width=40)
        task_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Due Date:").grid(row=1, column=0, padx=5, pady=5)
        date_entry = DateEntry(dialog,
                             date_pattern="mm-dd-yyyy",
                             background="darkblue",
                             foreground="white",
                             borderwidth=2)
        date_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text="Priority (1-5):").grid(row=2, column=0, padx=5, pady=5)
        priority_entry = ttk.Spinbox(dialog, from_=1, to=5)
        priority_entry.grid(row=2, column=1, padx=5, pady=5)
        
        def validate_and_add():
            date = self.parse_date(date_entry.get())
            if not date:
                messagebox.showerror("Error", "Invalid date format")
                return
            
            try:
                priority = int(priority_entry.get())
                if not 1 <= priority <= 5:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Priority must be 1-5")
                return
            
            self.add_task(task_entry.get(), date, priority)
            dialog.destroy()

        ttk.Button(dialog, text="Add", command=validate_and_add).grid(row=3, columnspan=2, pady=10)

    def add_task(self, task, date, priority):
        tasks = self.load_tasks()
        tasks.append((task, date, priority))
        tasks = sorted(tasks, key=lambda x: (datetime.strptime(x[1], "%m-%d-%Y"), -int(x[2])))
        self.save_tasks(tasks)
        self.refresh_task_list()

    def remove_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a task to remove")
            return
        
        task_values = self.tree.item(selected[0], 'values')
        task_to_remove = (task_values[0], task_values[1], task_values[2])
        
        tasks = self.load_tasks()
        try:
            index = tasks.index(task_to_remove)
        except ValueError:
            messagebox.showerror("Error", "Task not found in data file")
            return
        
        tasks = self.load_tasks()
        if 0 <= index < len(tasks):
            del tasks[index]
            self.tasks_completed += 1
            if self.tasks_completed % 5 == 0:
                self.level += 1
            self.save_character()
            self.update_character_labels()
            self.save_tasks(tasks)
            self.refresh_task_list()
        
    def edit_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a task to edit")
            return
        
        task_values = self.tree.item(selected[0], 'values')
        task_to_edit = (task_values[0], task_values[1], task_values[2])

        tasks = self.load_tasks()
        try:
            # Find the index by content instead of Treeview position
            index = tasks.index(task_to_edit)
        except ValueError:
            messagebox.showerror("Error", "Task not found in data file")
            return
        
        tasks = self.load_tasks()
        if 0 <= index < len(tasks):
            dialog = tk.Toplevel(self.root)
            dialog.title("Edit Task")
            
            ttk.Label(dialog, text="Task:").grid(row=0, column=0, padx=5, pady=5)
            task_entry = ttk.Entry(dialog, width=40)
            task_entry.grid(row=0, column=1, padx=5, pady=5)
            task_entry.insert(0, tasks[index][0])
            
            ttk.Label(dialog, text="Due Date:").grid(row=1, column=0, padx=5, pady=5)
            date_entry = DateEntry(dialog,
                                 date_pattern="mm-dd-yyyy",
                                 background="darkblue", 
                                 foreground="white",
                                 borderwidth=2)
            date_entry.grid(row=1, column=1, padx=5, pady=5)
            date_entry.set_date(datetime.strptime(tasks[index][1], "%m-%d-%Y"))
            
            ttk.Label(dialog, text="Priority (1-5):").grid(row=2, column=0, padx=5, pady=5)
            priority_entry = ttk.Spinbox(dialog, from_=1, to=5)
            priority_entry.grid(row=2, column=1, padx=5, pady=5)
            priority_entry.insert(0, tasks[index][2])
            
        def validate_and_edit():
            date = self.parse_date(date_entry.get())
            if not date:
                messagebox.showerror("Error", "Invalid date format")
                return
            
            try:
                priority = int(priority_entry.get())
                if not 1 <= priority <= 5:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Priority must be 1-5")
                return
            
            tasks[index] = (task_entry.get(), date, priority)
            self.save_tasks(tasks)
            self.refresh_task_list()
            dialog.destroy()
            
        ttk.Button(dialog, text="Save", command=validate_and_edit).grid(row=3, columnspan=2, pady=10)

    def delete_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a task to delete")
            return
        
        task_values = self.tree.item(selected[0], 'values')
        task_to_remove = (task_values[0], task_values[1], task_values[2])
        
        tasks = self.load_tasks()
        try:
            index = tasks.index(task_to_remove)
        except ValueError:
            messagebox.showerror("Error", "Task not found in data file")
            return
        
        tasks = self.load_tasks()
        if 0 <= index < len(tasks):
            del tasks[index]
            self.save_tasks(tasks)
            self.refresh_task_list()        
        else:
            messagebox.showerror("Error", "Invalid task index")

    def refresh_task_list(self):
        self.tree.delete(*self.tree.get_children())  # Clear existing tasks
        tasks = self.load_tasks()  # Load tasks from file
        today = datetime.today().date()
        
        # Categorize tasks
        overdue_tasks = []
        today_tasks = []
        upcoming_tasks = []

        for task in tasks:
            task_name, due_date_str, priority = task
            due_date = datetime.strptime(due_date_str, "%m-%d-%Y").date()

            if due_date < today:
                overdue_tasks.append(task)  # Overdue tasks
            elif due_date == today:
                today_tasks.append(task)  # Due today
            else:
                upcoming_tasks.append(task)  # Future tasks

        # Sort each category
        overdue_tasks.sort(key=lambda x: ((datetime.strptime(x[1], "%m-%d-%Y")), (int(x[2]))))  # Earliest first
        today_tasks.sort(key=lambda x: int(x[2]))  # Sort by priority (higher first)
        upcoming_tasks.sort(key=lambda x: ((datetime.strptime(x[1], "%m-%d-%Y")), (int(x[2]))))  # Earliest first

        # Insert into Treeview with colors
        for task in overdue_tasks:
            self.tree.insert("", tk.END, values=task, tags=("overdue",), text= task[0])
        for task in today_tasks:
            self.tree.insert("", tk.END, values=task, tags=("today",), text= task[0])
        for task in upcoming_tasks:
            self.tree.insert("", tk.END, values=task, text= task[0])

        # Configure row colors
        self.tree.tag_configure("overdue", foreground="red")
        self.tree.tag_configure("today", foreground="orange")

        # Update the remaining tasks count
        self.remaining_label.config(text=str(len(self.tree.get_children())))

    def load_tasks(self):
        if not os.path.exists(TODO_FILE):
            return []
        with open(TODO_FILE, "r") as f:
            tasks = []
            for line in f.readlines():
                parts = line.strip().split(" | ")
                if len(parts) == 3:
                    tasks.append((parts[0], parts[1], parts[2]))
            return sorted(tasks, key=lambda x: (datetime.strptime(x[1], "%m-%d-%Y"), -int(x[2])))

    def save_tasks(self, tasks):
        with open(TODO_FILE, "w") as f:
            for task in tasks:
                f.write(" | ".join(str(x) for x in task) + "\n")

    def show_character(self):
        message = f"Character Level: {self.level}\nTasks Completed: {self.tasks_completed}"
        messagebox.showinfo("Character Info", message)

    def open_ai_dialog(self):
        self.ai_dialog = tk.Toplevel(self.root)
        self.ai_dialog.title("AI Assistant")
        self.ai_dialog.geometry("1000x500")
        
        self.chat_history = ScrolledText(self.ai_dialog, wrap=tk.WORD, state='disabled')
        self.chat_history.pack(padx=10, pady=10, fill=tk.BOTH, expand=False)
        
        input_frame = ttk.Frame(self.ai_dialog)
        input_frame.pack(padx=10, pady=10, fill=tk.X)
        
        self.user_input = ttk.Entry(input_frame)
        self.user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.user_input.bind("<Return>", lambda e: self.send_to_ai())
        
        self.send_button = ttk.Button(input_frame, text="Send", command=self.send_to_ai)
        self.send_button.pack(side=tk.RIGHT)

        # Configure Markdown tags
        self.chat_history.tag_config("bold", font=('Helvetica', 10, 'bold'))
        self.chat_history.tag_config("italic", font=('Helvetica', 10, 'italic'))
        self.chat_history.tag_config("header", font=('Helvetica', 12, 'bold'))
        self.chat_history.tag_config("list", lmargin2=20, spacing3=3)
        self.chat_history.tag_config("code", background="#f0f0f0", relief='groove')
        
        # Add initial greeting
        self.update_chat_history("Assistant: Hi! I am your personal AI assistant. How can I help you today?")

    def update_chat_history(self, message):
        self.chat_history.config(state='normal')
        self.chat_history.insert(tk.END, message + "\n\n")
        self.chat_history.config(state='disabled')
        self.chat_history.see(tk.END)

    def send_to_ai(self):
        user_text = self.user_input.get()
        if not user_text:
            return
        
        self.update_chat_history(f"You: {user_text}")
        self.user_input.delete(0, tk.END)
        
        # Disable input while processing
        self.user_input.config(state='disabled')
        self.ai_dialog.config(cursor="watch")
        self.send_button.config(state='disabled')
        
        # Start processing in a separate thread
        threading.Thread(target=self.get_ai_response, args=(user_text,)).start()

    # Update the get_ai_response method with streaming support
    def get_ai_response(self, prompt):
        try:
            response = requests.post(
                'http://localhost:11434/api/generate',
                json={
                    'model': 'deepseek-r1:14b',
                    'prompt': f"""You are a TODO assistant. Use these commands when needed:
    <command>add;[task];[date];[priority]</command>
    <command>finish;[task]</command>
    <command>delete;[task]</command>
    <command>edit;[old task];[new task];[new date];[new priority]</command>
    DO NOT ADD IN THIS EXAMPLE:
    example:(<command>add;Buy milk;05-25-2024;3</command>
    Current time: {datetime.now().strftime("%m-%d-%Y")})
    User: {prompt}""",
                    'stream': True
                },
                stream=True
            )

            # Initialize response tracking
            self.root.after(0, self.prepare_ai_response)
            accumulated_response = ""

            # Remove thinking message if enabled
            if self.show_thinking:
                self.root.after(0, self.remove_thinking_message)

            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if 'response' in chunk:
                        accumulated_response += chunk['response']
                        # Update GUI with partial response
                        self.root.after(0, self.update_ai_response, accumulated_response)

            # Add final newlines after completion
            self.root.after(0, self.finalize_ai_response)
            self.root.after(0, self.handle_ai_commands, accumulated_response)

        except requests.exceptions.ConnectionError:
            self.root.after(0, self.update_chat_history, "Assistant: Could not connect to Ollama. Make sure it's running!")
        except Exception as e:
            self.root.after(0, self.update_chat_history, f"Assistant: Error - {str(e)}")
        finally:
            self.root.after(0, lambda: self.user_input.config(state='normal'))
            self.root.after(0, lambda: self.ai_dialog.config(cursor=""))
            self.root.after(0, lambda: self.send_button.config(state='normal'))

    def prepare_ai_response(self):
        self.chat_history.config(state='normal')
        # Insert AI prefix and set start position
        self.chat_history.insert(tk.END, "Assistant :")
        self.ai_response_start = self.chat_history.index("end-1c")
        self.chat_history.config(state='disabled')
        self.chat_history.see(tk.END)
        self.inside_think = False
        self.think_buffer = ''

    def update_ai_response(self, text):
        if not self.show_thinking:
            # Combine buffer with new text
            full_text = self.think_buffer + text
            self.think_buffer = ''
            processed = []
            i = 0
            
            while i < len(full_text):
                if self.inside_think:
                    # Look for closing tag
                    end_idx = full_text.find('</think>', i)
                    if end_idx != -1:
                        i = end_idx + len('</think>')
                        self.inside_think = False
                    else:
                        # Save remaining text for next chunk
                        self.think_buffer = full_text[i:]
                        break
                else:
                    # Look for opening tag
                    start_idx = full_text.find('<think>', i)
                    if start_idx != -1:
                        # Add text before the tag
                        processed.append(full_text[i:start_idx])
                        i = start_idx + len('<think>')
                        self.inside_think = True
                    else:
                        # Add remaining text
                        processed.append(full_text[i:])
                        break
            text = ''.join(processed)
        self.chat_history.config(state='normal')
        # Clear previous partial response
        self.chat_history.delete(self.ai_response_start, tk.END)
        # Insert updated response
        self.insert_with_markdown(text)
        self.chat_history.config(state='disabled')
        self.chat_history.see(tk.END)

    def finalize_ai_response(self):
        self.chat_history.config(state='normal')
        # Add spacing after completion
        self.chat_history.insert(tk.END, "\n\n")
        self.chat_history.config(state='disabled')
        self.chat_history.see(tk.END)

    # Add this new method for markdown processing
    def insert_with_markdown(self, text):
        # Split into lines for block-level processing
        lines = text.split('\n')
        list_mode = False
        
        for line in lines:
            # Headers
            if line.startswith('#'):
                header_level = min(line.count('#'), 3)
                clean_line = line.lstrip('#').strip()
                self.chat_history.insert(tk.END, clean_line + '\n', f"h{header_level}")
                continue
                
            # Lists
            if line.startswith(('- ', '* ', '+ ')):
                if not list_mode:
                    list_mode = True
                    self.chat_history.insert(tk.END, '\n')
                self.chat_history.insert(tk.END, '• ' + line[2:] + '\n', "list")
                continue
            else:
                list_mode = False
                
            # Bold and italic
            pos = 0
            while pos < len(line):
                # Handle bold (**...**)
                bold_start = line.find('**', pos)
                if bold_start != -1:
                    bold_end = line.find('**', bold_start + 2)
                    if bold_end != -1:
                        self.chat_history.insert(tk.END, line[pos:bold_start])
                        self.chat_history.insert(tk.END, line[bold_start+2:bold_end], "bold")
                        pos = bold_end + 2
                        continue
                        
                # Handle italic (*...* or _..._)
                italic_start = max(line.find('*', pos), line.find('_', pos))
                if italic_start != -1:
                    italic_end = max(line.find('*', italic_start + 1), 
                                line.find('_', italic_start + 1))
                    if italic_end != -1:
                        self.chat_history.insert(tk.END, line[pos:italic_start])
                        self.chat_history.insert(tk.END, line[italic_start+1:italic_end], "italic")
                        pos = italic_end + 1
                        continue
                        
                # Handle code blocks (`...`)
                code_start = line.find('`', pos)
                if code_start != -1:
                    code_end = line.find('`', code_start + 1)
                    if code_end != -1:
                        self.chat_history.insert(tk.END, line[pos:code_start])
                        self.chat_history.insert(tk.END, line[code_start+1:code_end], "code")
                        pos = code_end + 1
                        continue
                        
                # Insert remaining text
                self.chat_history.insert(tk.END, line[pos:])
                break
                
            self.chat_history.insert(tk.END, '\n')

    def load_config(self):
        config_file = str(Path.home()) + "/TODOapp/config.txt"
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    self.show_thinking = f.read().strip() == "True"
                    self.show_thinking_var.set(self.show_thinking)
            except:
                self.show_thinking = True
                self.show_thinking_var.set(True)

    def save_config(self):
        config_file = str(Path.home()) + "/TODOapp/config.txt"
        with open(config_file, "w") as f:
            f.write(str(self.show_thinking))

    def toggle_thinking(self):
        self.show_thinking = not self.show_thinking
        self.show_thinking_var.set(self.show_thinking)
        self.save_config()

    def remove_thinking_message(self):
        self.chat_history.config(state='normal')
        self.chat_history.delete("end-3l", "end")
        self.chat_history.config(state='disabled')

    # Add these methods to the TodoApp class
    def handle_ai_commands(self, full_response):
        # Extract commands from response
        command_pattern = re.compile(r'<command>(.*?)</command>', re.DOTALL)
        commands = command_pattern.findall(full_response)
        
        # Remove commands from displayed message
        display_message = command_pattern.sub('', full_response).strip()
        if display_message:
            self.update_chat_history(f"Assistant: {display_message}")

        # Process commands
        for cmd in commands:
            self.process_command(cmd.strip())

    def process_command(self, cmd_text):
        parts = [p.strip() for p in cmd_text.split(';')]
        if not parts:
            return

        action = parts[0].lower()
        
        try:
            if action == "add":
                task = parts[1]
                date = parts[2]
                priority = parts[3]
                self.add_task_programmatically(task, date, priority)
            elif action == "finish":
                task = parts[1]
                self.complete_task_by_name(task)
            elif action == "delete":
                task = parts[1]
                self.delete_task_by_name(task)
            elif action == "edit":
                old_task = parts[1]
                new_task = parts[2]
                new_date = parts[3]
                new_priority = parts[4]
                self.edit_task_programmatically(old_task, new_task, new_date, new_priority)
        except (IndexError, ValueError) as e:
            self.update_chat_history(f"Assistant: Error processing command: {str(e)}")

    def add_task_programmatically(self, task, date_str, priority_str):
        date = self.parse_date(date_str)
        if not date:
            raise ValueError("Invalid date format")
        
        try:
            priority = int(priority_str)
            if not 1 <= priority <= 5:
                raise ValueError
        except ValueError:
            raise ValueError("Priority must be 1-5")

        self.add_task(task, date, priority)
        self.update_chat_history(f"Assistant: Task '{task}' added successfully!")

    def complete_task_by_name(self, task_name):
        tasks = self.load_tasks()
        for t in tasks:
            if t[0] == task_name:
                tasks.remove(t)
                self.tasks_completed += 1
                if self.tasks_completed % 5 == 0:
                    self.level += 1
                self.save_character()
                self.update_character_labels()
                self.save_tasks(tasks)
                self.refresh_task_list()
                self.update_chat_history(f"Assistant: Task '{task_name}' completed!")
                return
        raise ValueError("Task not found")

    def delete_task_by_name(self, task_name):
        tasks = self.load_tasks()
        new_tasks = [t for t in tasks if t[0] != task_name]
        if len(new_tasks) != len(tasks):
            self.save_tasks(new_tasks)
            self.refresh_task_list()
            self.update_chat_history(f"Assistant: Task '{task_name}' deleted!")
        else:
            raise ValueError("Task not found")

    def edit_task_programmatically(self, old_task_name, new_task_name, new_date_str, new_priority_str):
        new_date = self.parse_date(new_date_str)
        if not new_date:
            raise ValueError("Invalid new date format")
        
        try:
            new_priority = int(new_priority_str)
            if not 1 <= new_priority <= 5:
                raise ValueError
        except ValueError:
            raise ValueError("Priority must be 1-5")

        tasks = self.load_tasks()
        for i, t in enumerate(tasks):
            if t[0] == old_task_name:
                tasks[i] = (new_task_name, new_date, new_priority)
                self.save_tasks(tasks)
                self.refresh_task_list()
                self.update_chat_history(f"Assistant: Task updated successfully!")
                return
        raise ValueError("Task not found")

if __name__ == "__main__":
    root = tk.Tk()
    app = TodoApp(root)
    root.mainloop()