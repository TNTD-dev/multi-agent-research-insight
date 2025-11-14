"""
Interactive Knowledge Graph Visualization using Plotly
"""
from __future__ import annotations

import networkx as nx
from typing import Optional
import plotly.graph_objects as go

from src.agents.state import KnowledgeGraph
from src.utils.logger import default_logger as logger


def create_interactive_kg_plotly(knowledge_graph: Optional[KnowledgeGraph]) -> Optional[go.Figure]:
    """Create an interactive knowledge graph visualization using Plotly."""
    
    if not knowledge_graph or not knowledge_graph.nodes:
        logger.warning("Knowledge graph is empty; skipping interactive visualization")
        return None

    # Build NetworkX graph
    G = nx.Graph()
    
    # Add nodes with attributes
    node_data = {}
    for node in knowledge_graph.nodes:
        G.add_node(
            node.id,
            label=node.label,
            type=node.type,
            url=node.url or ""
        )
        node_data[node.id] = {
            "label": node.label,
            "type": node.type,
            "url": node.url or ""
        }
    
    # Add edges
    for edge in knowledge_graph.edges:
        G.add_edge(edge.source, edge.target, relation=edge.relation)
    
    if not G.nodes:
        return None

    # Calculate layout
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Separate nodes by type
    concept_nodes = [n for n, data in G.nodes(data=True) if data.get("type") == "concept"]
    source_nodes = [n for n, data in G.nodes(data=True) if data.get("type") == "source"]
    
    # Prepare edge traces
    edge_x = []
    edge_y = []
    
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    # Create edge trace
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1.5, color='#888'),
        hoverinfo='none',
        mode='lines',
        showlegend=False
    )
    
    # Prepare node traces
    def create_node_trace(node_list, color, size, name, symbol):
        node_x = [pos[node][0] for node in node_list]
        node_y = [pos[node][1] for node in node_list]
        
        node_text = []
        node_hovertext = []
        node_urls = []
        
        for node in node_list:
            label = node_data[node]["label"]
            node_type = node_data[node]["type"]
            url = node_data[node]["url"]
            
            # Truncate long labels
            display_label = label[:50] + "..." if len(label) > 50 else label
            
            # Count connections
            connections = len(list(G.neighbors(node)))
            
            node_text.append(display_label)
            hover_text = (
                f"<b>{label}</b><br>"
                f"Type: {node_type}<br>"
                f"Connections: {connections}<br>"
            )
            if url:
                hover_text += f"<a href='{url}' target='_blank'>View Source</a>"
            node_hovertext.append(hover_text)
            node_urls.append(url)
        
        # Use dark text for better visibility on white background
        # For colored nodes, we'll use dark text with white background effect via larger font
        text_color = '#000000'  # Pure black for maximum contrast
        text_font = dict(
            size=12, 
            color=text_color, 
            family='Arial Black, sans-serif'
        )
        
        return go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            name=name,
            marker=dict(
                size=size,
                color=color,
                line=dict(width=2.5, color='white'),
                opacity=0.95
            ),
            text=node_text,
            textposition="middle center",
            textfont=text_font,
            hovertext=node_hovertext,
            hoverinfo='text',
            customdata=node_urls,
            showlegend=True
        )
    
    # Create node traces
    concept_trace = create_node_trace(
        concept_nodes, 
        color='#4CAF50', 
        size=25, 
        name='Concepts',
        symbol='circle'
    )
    
    source_trace = create_node_trace(
        source_nodes,
        color='#FF6B6B',
        size=20,
        name='Sources',
        symbol='square'
    )
    
    # Create figure
    fig = go.Figure(
        data=[edge_trace, concept_trace, source_trace],
        layout=go.Layout(
            title=dict(
                text='<b>Interactive Research Knowledge Graph</b>',
                x=0.5,
                font=dict(size=20, color='#1a1a1a')
            ),
            showlegend=True,
            legend=dict(
                font=dict(size=12, color='#1a1a1a', family='Arial, sans-serif'),
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='#cccccc',
                borderwidth=1
            ),
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    text="💡 <b>Tips:</b> Hover for details | Click to select | Zoom & Pan | Double-click to reset",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.5, y=-0.05,
                    xanchor="center", yanchor="top",
                    font=dict(size=10, color='gray')
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=800,
            clickmode='event+select'
        )
    )
    
    # Add interactivity: Update layout for better UX
    fig.update_layout(
        dragmode='pan',  # Allow panning
        selectdirection='h',  # Selection direction
    )
    
    # Add buttons for layout algorithms
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                active=0,
                x=0.1,
                y=1.02,
                xanchor="left",
                yanchor="bottom",
                buttons=list([
                    dict(
                        label="Reset View",
                        method="relayout",
                        args=[{"xaxis.range": None, "yaxis.range": None}]
                    ),
                ]),
            )
        ]
    )
    
    logger.info("Interactive knowledge graph created with %d nodes and %d edges", 
                len(G.nodes()), len(G.edges()))
    
    return fig


def create_kg_statistics(knowledge_graph: Optional[KnowledgeGraph]) -> dict:
    """Extract statistics from knowledge graph for display."""
    if not knowledge_graph:
        return {}
    
    concept_count = sum(1 for node in knowledge_graph.nodes if node.type == "concept")
    source_count = sum(1 for node in knowledge_graph.nodes if node.type == "source")
    
    # Count edges by relation type
    relation_counts = {}
    for edge in knowledge_graph.edges:
        rel = edge.relation
        relation_counts[rel] = relation_counts.get(rel, 0) + 1
    
    return {
        "total_nodes": len(knowledge_graph.nodes),
        "concept_nodes": concept_count,
        "source_nodes": source_count,
        "total_edges": len(knowledge_graph.edges),
        "relation_breakdown": relation_counts
    }

