import tkinter as tk
from tkinter import filedialog, messagebox
import processor
import util
import os
import threading
import visualizer
from visualizer import GraphVisualizer
import uuid


class NexusApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HIVEMIND")
        self.root.geometry("800x600")
        self.paned = tk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        self.left_frame = tk.Frame(self.paned)
        self.paned.add(self.left_frame)

        self.label = tk.Label(self.left_frame, text="HIVEMIND", font=("Arial", 18, "bold"))
        self.label.pack(pady=10)

        self.upload_btn = tk.Button(self.left_frame, text="Upload Documents", command=self.upload_files)
        self.upload_btn.pack(pady=5)

        self.session_frame = tk.Frame(self.left_frame)
        self.session_frame.pack(pady=2)

        self.new_session_btn = tk.Button(self.session_frame, text="New Session", command=self.new_session)
        self.new_session_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.history_btn = tk.Button(self.session_frame, text="View History", command=self.show_history)
        self.history_btn.pack(side=tk.LEFT)

        self.chat_history = tk.Text(self.left_frame, height=20, width=60)
        self.chat_history.pack(padx=8, pady=8, fill=tk.BOTH, expand=True)
        # Text tags for simple markdown rendering
        self.chat_history.tag_configure('user_tag', foreground='#0b63ce', spacing1=4)
        self.chat_history.tag_configure('nexus_tag', foreground='#006400', spacing1=4)
        self.chat_history.tag_configure('bold', font=('Arial', 10, 'bold'))
        self.chat_history.tag_configure('italic', font=('Arial', 10, 'italic'))
        self.chat_history.tag_configure('inline_code', font=('Courier', 9), background='#f3f3f3')
        self.chat_history.tag_configure('codeblock', font=('Courier', 9), background='#f3f3f3')
        self.chat_history.tag_configure('heading', font=('Arial', 12, 'bold'))

        # Bottom input area inside left pane
        self.input_frame = tk.Frame(self.left_frame)
        self.input_frame.pack(fill=tk.X, padx=8, pady=6)

        self.query_entry = tk.Entry(self.input_frame, width=60)
        self.query_entry.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)

        self.send_btn = tk.Button(self.input_frame, text="Ask Nexus", command=self.ask_question)
        self.send_btn.pack(side=tk.LEFT)
        self.right_frame = tk.Frame(self.paned, bg="white")
        self.paned.add(self.right_frame)
        self.visualizer = GraphVisualizer(self.right_frame)
        self.session_id = str(uuid.uuid4())
        api_key = os.getenv("GENAI_API_KEY")
        self.engine = processor.HiveProcessor(util.HiveMind(api_key))


    def upload_files(self):
        files = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        if files:
            messagebox.showinfo("Success", f"Loaded {len(files)} papers. Starting Graph Indexing...")

            def worker(file_list):
                for f in file_list:
                    try:
                        self.root.after(0, lambda f=f: self.chat_history.insert(tk.END, f"System: Indexing {os.path.basename(f)}...\n"))
                        self.engine.process_pdf(f)
                        #update and refresh
                        self.root.after(0, lambda f=f: self.chat_history.insert(tk.END, f"Indexed: {os.path.basename(f)}\n"))
                        self.root.after(0, lambda: self.visualizer.update_graph(self.engine.graph))
                    except Exception as e:
                        self.root.after(0, lambda f=f, e=e: messagebox.showerror("Processing Error", f"Could not process {f}: {e}"))
                self.root.after(0, lambda: messagebox.showinfo("Done", f"Processed {len(file_list)} files."))

            t = threading.Thread(target=worker, args=(files,), daemon=True)
            t.start()

    def ask_question(self):
        query = self.query_entry.get()
        if not query:
            return
        self.chat_history.insert(tk.END, f"\nUser: {query}\n", "user_tag")

        
        answer = self.engine.query_nexus(query, session_id=self.session_id)

        
        self.chat_history.insert(tk.END, "Nexus: ", 'nexus_tag')
        self._insert_markdown(answer)
        self.chat_history.insert(tk.END, "\n")
        self.query_entry.delete(0, tk.END)
        self.chat_history.see(tk.END) # Auto-scroll

    def new_session(self):
        self.session_id = str(uuid.uuid4())
        self.chat_history.delete("1.0", tk.END)
        self.chat_history.insert(tk.END, f"System: Started new session {self.session_id[:8]}\n")
        if hasattr(self.engine, "reset_graph"):
            self.engine.reset_graph()
        self.visualizer.update_graph(self.engine.graph)

    def show_history(self):
        sessions = self.engine.list_sessions(limit=100)
        if not sessions:
            messagebox.showinfo("History", "No past sessions found.")
            return

        win = tk.Toplevel(self.root)
        win.title("Session History")
        win.geometry("700x500")

        left = tk.Frame(win)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        right = tk.Frame(win)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        listbox = tk.Listbox(left, width=40)
        listbox.pack(side=tk.TOP, fill=tk.Y, expand=True)

        transcript = tk.Text(right, wrap=tk.WORD)
        transcript.pack(fill=tk.BOTH, expand=True)

        for idx, s in enumerate(sessions):
            sid = s["session_id"]
            start = s["start_at"] or ""
            end = s["end_at"] or ""
            count = s["count"]
            label = f"{idx+1}. {sid[:8]}... ({count} messages)"\
                    f"\n   {start} -> {end}"
            listbox.insert(tk.END, label)

        def on_select(event):
            selection = listbox.curselection()
            if not selection:
                return
            i = selection[0]
            s = sessions[i]
            msgs = self.engine.get_session_messages(s["session_id"])
            transcript.delete("1.0", tk.END)
            for role, content, created_at in msgs:
                header = f"[{created_at}] {role.capitalize()}:\n"
                transcript.insert(tk.END, header)
                transcript.insert(tk.END, content + "\n\n")

        listbox.bind("<<ListboxSelect>>", on_select)

    def _insert_markdown(self, md_text):
        import re

        
        md_text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", md_text)

        code_block = False
        for line in md_text.splitlines():
            if line.strip().startswith('```'):
                code_block = not code_block
                continue

            if code_block:
                self.chat_history.insert(tk.END, line + '\n', ('codeblock',))
                continue

            # Headings
            m = re.match(r'^(#{1,6})\s+(.*)', line)
            if m:
                self.chat_history.insert(tk.END, m.group(2) + '\n', ('heading',))
                continue

            # Lists
            m = re.match(r'^[\-\*\+]\s+(.*)', line)
            if m:
                self.chat_history.insert(tk.END, '• ')
                line = m.group(1)

            # Inline code
            parts = re.split(r'(`[^`]+`)', line)
            for part in parts:
                if part.startswith('`') and part.endswith('`'):
                    self.chat_history.insert(tk.END, part[1:-1], ('inline_code',))
                    continue

                # Bold
                subparts = re.split(r'(\*\*[^*]+\*\*)', part)
                for sp in subparts:
                    if sp.startswith('**') and sp.endswith('**'):
                        self.chat_history.insert(tk.END, sp[2:-2], ('bold',))
                    else:
                        # Italic
                        subsub = re.split(r'(\*[^*]+\*)', sp)
                        for ssp in subsub:
                            if ssp.startswith('*') and ssp.endswith('*'):
                                self.chat_history.insert(tk.END, ssp[1:-1], ('italic',))
                            else:
                                self.chat_history.insert(tk.END, ssp)
            self.chat_history.insert(tk.END, '\n')

if __name__ == "__main__":
    root = tk.Tk()
    app = NexusApp(root)
    root.mainloop()