import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import networkx as nx
import math


class GraphVisualizer:
    def __init__(self, parent_frame):
        self.fig = Figure(figsize=(7, 7), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.fig.patch.set_facecolor("white")

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent_frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def update_graph(self, nx_graph):
        self.ax.clear()

        if nx_graph is None or len(nx_graph.nodes) == 0:
            self.ax.text(0.5, 0.5, "No relationships extracted yet...", ha="center", va="center", fontsize=12)
            self.ax.axis("off")
            self.canvas.draw_idle()
            return

        node_count = nx_graph.number_of_nodes()
        if node_count <= 15:
            try:
                pos = nx.kamada_kawai_layout(nx_graph)
            except Exception:
                pos = nx.spring_layout(nx_graph, k=1.2, iterations=200, seed=42)
        else:
            k = 1.5 / max(1.0, math.sqrt(node_count))
            try:
                pos = nx.spring_layout(nx_graph, k=k, iterations=400, seed=42)
            except Exception:
                pos = nx.circular_layout(nx_graph)

        degrees = dict(nx_graph.degree())
        node_sizes = [280 + int(520 * math.log(degrees.get(n, 0) + 1)) for n in nx_graph.nodes]

        nx.draw_networkx_nodes(nx_graph, pos, ax=self.ax, node_color="skyblue", node_size=node_sizes, edgecolors="k")

        edges = list(nx_graph.edges())
        for idx, (u, v) in enumerate(edges):
            du = degrees.get(u, 0)
            dv = degrees.get(v, 0)
            hub = du > 10 or dv > 10
            base = 0.1 if hub else 0.06
            offset = ((idx % 5) - 2) / 2.0
            rad = base * offset
            nx.draw_networkx_edges(
                nx_graph,
                pos,
                ax=self.ax,
                edgelist=[(u, v)],
                edge_color="#888888",
                arrows=True,
                arrowsize=12,
                width=0.8 if hub else 0.6,
                alpha=0.6 if hub else 0.8,
                connectionstyle=f"arc3,rad={rad}",
            )
        sorted_nodes = sorted(nx_graph.nodes, key=lambda n: degrees.get(n, 0), reverse=True)
        max_labeled = 35 if node_count > 80 else 50
        label_nodes = set(sorted_nodes[:max_labeled])
        labels = {n: n for n in nx_graph.nodes if n in label_nodes}

        nx.draw_networkx_labels(nx_graph, pos, labels=labels, ax=self.ax, font_size=7, font_weight="normal")

        edge_labels = nx.get_edge_attributes(nx_graph, "relation")
        if edge_labels and len(edge_labels) <= 40:
            nx.draw_networkx_edge_labels(nx_graph, pos, edge_labels=edge_labels, ax=self.ax, font_size=7)

        self.ax.set_axis_off()
        self.ax.margins(0.25)
        self.fig.tight_layout(pad=2.0)
        self.canvas.draw_idle()

