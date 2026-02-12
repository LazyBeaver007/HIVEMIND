import PyPDF2
import networkx as nx
import chromadb
from chromadb.utils import embedding_functions
import json
from pathlib import Path
from util import ChatMemory


class HiveProcessor:
    def __init__(self, HiveMind):
        self.core = HiveMind
        base_path = Path(__file__).resolve().parent
        data_dir = base_path / "Data"
        data_dir.mkdir(exist_ok=True)
        self.memory = ChatMemory(data_dir / "nexus_history.db")
        self.chroma_client = chromadb.PersistentClient(path=str(data_dir / "chroma"))
        try:
            self.collection = self.chroma_client.create_collection(name="research_papers")
        except Exception:
            self.collection = self.chroma_client.get_collection(name="research_papers")
        self.graph = nx.DiGraph()

    def process_pdf(self, file_path):
        reader = PyPDF2.PdfReader(file_path)
        full_text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text

        chunks = [full_text[i:i+1000] for i in range(0, len(full_text), 1000)]

        for i, chunk in enumerate(chunks):
            self.collection.add(
                documents=[chunk],
                metadatas=[{"source": file_path, "chunk_id": i}],
                ids=[f"{file_path}_{i}"]
            )

            if i % 5 == 0:
                if hasattr(self.core, 'extract_entities_and_relations'):
                    relations = self.core.extract_entities_and_relations(chunk)
                else:
                    relations = ""
                self.parse_and_add_to_graph(relations)

    def parse_and_add_to_graph(self, ai_output):
        try:
            lines = ai_output.strip().split('\n')
            for line in lines:
                
                parts = line.replace('(', '').replace(')', '').split(',')
                if len(parts) == 3:
                    sub, rel, obj = [p.strip() for p in parts]
                    self.graph.add_edge(sub, obj, relation=rel)
        except Exception as e:
            print(f"Graph error:{e}")

    def query_nexus(self, user_query, session_id=None):
        entry_entities = [node for node in self.graph.nodes if node.lower() in user_query.lower()]
        extended_context = []
        graph_connections = []
        for entity in entry_entities:
            for neighbor in self.graph.neighbors(entity):
                relation = self.graph[entity][neighbor].get('relation', '')
                graph_connections.append(f"({entity} --{relation}--> {neighbor})")
                extended_context.append(f"Related: {entity} {relation} {neighbor}")

                try:
                    neighbor_results = self.collection.query(query_texts=[neighbor], n_results=1)
                    docs = neighbor_results.get("documents") if neighbor_results else None
                    if docs and len(docs) > 0:
                        extended_context.extend(docs[0])
                except Exception:
                    pass
        try:
            vector_results = self.collection.query(query_texts=[user_query], n_results=2)
            docs = vector_results.get("documents") if vector_results else None
            vector_docs = docs[0] if docs and len(docs) > 0 else []
        except Exception:
            vector_docs = []
        combined = list(set(extended_context + vector_docs))
        full_context = "\n".join(combined)

        history_context = ""
        if session_id is not None:
            history_context = self.memory.get_recent_context(session_id)

        kg_connections_text = "\n".join(graph_connections) if graph_connections else "No direct graph connections found."

        final_prompt = f"""
        You are Nexus-Scholar. Answer the user's question using the provided Context and Knowledge Graph.

        [Chat History]:
        {history_context}

        [Knowledge Graph Connections]:
        {kg_connections_text}

        [Combined Context]:
        {full_context}

        [User Question]:
        {user_query}

        Instruction: If the graph shows a connection, mention it to show how concepts are linked.
        """

        response = None
        if hasattr(self.core, 'generate_content'):
            response = self.core.generate_content(final_prompt)
        elif hasattr(self.core, 'model') and hasattr(self.core.model, 'generate_content'):
            response = self.core.model.generate_content(final_prompt)
        else:
            return "No model available to answer the query."

        if hasattr(response, 'text'):
            answer_text = response.text
        else:
            answer_text = str(response)

        if session_id is not None:
            try:
                self.memory.add_message(session_id, "user", user_query, context=full_context)
                self.memory.add_message(session_id, "assistant", answer_text, context=kg_connections_text)
            except Exception:
                pass

        return answer_text

    def reset_graph(self):
        self.graph = nx.DiGraph()

    def list_sessions(self, limit=None):
        return self.memory.list_sessions(limit=limit)

    def get_session_messages(self, session_id):
        return self.memory.get_session_messages(session_id)