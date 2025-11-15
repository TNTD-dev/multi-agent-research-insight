"""
🔬 Multi-Agent Research Intelligence Platform - Streamlit UI

Interactive web interface for running research queries and viewing results
"""

import streamlit as st
import sys
import os
from pathlib import Path
import json
from datetime import datetime
import time
import re
from PIL import Image

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import the research pipeline
from src.agentic_ai_pipeline import run_research_pipeline
from src.utils.visualization import create_interactive_kg_plotly, create_kg_statistics
from src.agents.state import KnowledgeGraph, KnowledgeGraphNode, KnowledgeGraphEdge

# Page configuration
st.set_page_config(
    page_title="Research Intelligence Platform",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(120deg, #4CAF50, #2196F3);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4CAF50;
        color: #1f1f1f;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .source-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 0.5rem;
        color: #1f1f1f;
    }
    .concept-badge {
        display: inline-block;
        background-color: #e3f2fd;
        color: #1976d2;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        margin: 0.25rem;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'research_result' not in st.session_state:
    st.session_state.research_result = None
if 'running' not in st.session_state:
    st.session_state.running = False

# Header
st.markdown('<h1 class="main-header">🔬 Research Intelligence Platform</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Autonomous Multi-Agent System for Academic Research Discovery & Analysis</p>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.markdown("### Environment Setup")
    
    # Automatically load from environment
    groq_key = os.getenv("GROQ_API_KEY", "")
    tavily_key = os.getenv("TAVILY_KEY", "")
    
    # Show status
    if groq_key:
        st.success("✅ GROQ API Key: Configured")
    else:
        st.error("❌ GROQ API Key: Not found")
        st.info("💡 Set `GROQ_API_KEY` in your `.env` file or environment variables")
    
    if tavily_key:
        st.success("✅ Tavily API Key: Configured (Optional)")
    else:
        st.warning("⚠️ Tavily API Key: Not configured (Web search disabled)")
        st.info("💡 Set `TAVILY_KEY` in your `.env` file for web search")
    
    st.markdown("---")
    st.markdown("### System Capabilities")
    st.markdown("""
    - 🔍 **Multi-Source Discovery**  
      ArXiv, Semantic Scholar, Web
    
    - ✅ **Smart Validation**  
      Credibility & relevance scoring
    
    - 🧬 **Synthesis**  
      Knowledge graphs & gap analysis
    
    - 📊 **Reporting**  
      Comprehensive research reports
    """)
    
    st.markdown("---")
    st.markdown("### About")
    st.info("""
    **Version:** 2.0  
    **Agents:** 4 specialized AI agents  
    **Framework:** LangGraph + Groq LLM
    """)

# Main content area
tab1, tab2, tab3 = st.tabs(["🚀 New Research", "📊 Results", "📚 History"])

with tab1:
    st.header("Start New Research")
    
    # Query input
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_input(
            "Research Query",
            placeholder="e.g., Large Language Models for code generation",
            help="Enter your research question or topic"
        )
    
    with col2:
        depth = st.selectbox(
            "Research Depth",
            options=["quick", "standard", "deep"],
            index=1,
            help="Select the depth of research analysis"
        )
        
        # Detailed depth descriptions
        with st.expander("📊 Depth Level Details"):
            st.markdown("""
            **🚀 Quick** (~3-5 min)
            - Minimal sources: 3 ArXiv, 3 Web, 2 Semantic Scholar
            - No reformulated searches
            - Basic validation (score ≥40)
            - 8 concepts, 3 findings, 2 gaps
            - Brief report (5 sources max)
            
            **⚖️ Standard** (~8-10 min) - *Recommended*
            - Balanced sources: 8 ArXiv, 8 Web, 5 Semantic Scholar
            - Reformulated searches if sources < 15
            - Standard validation (score ≥40)
            - 15 concepts, 7 findings, 5 gaps
            - Full report (10 sources)
            
            **🔬 Deep** (~12-15 min)
            - Comprehensive sources: 15 ArXiv, 12 Web, 10 Semantic Scholar
            - Always runs reformulated searches
            - Strict validation (score ≥50)
            - 20 concepts, 10 findings, 8 gaps
            - Detailed report (20 sources, extra sections)
            """)
    
    # Example queries
    with st.expander("💡 Example Queries"):
        st.markdown("""
        - `Transformer models for computer vision`
        - `Quantum computing in drug discovery`
        - `Few-shot learning in natural language processing`
        - `Graph neural networks for molecular property prediction`
        - `Federated learning privacy techniques`
        """)
    
    # Run button
    if st.button("🚀 Start Research", type="primary", disabled=st.session_state.running):
        if not query:
            st.error("Please enter a research query!")
        elif not groq_key:
            st.error("Please provide your GROQ API Key in the sidebar!")
        else:
            st.session_state.running = True
            
            # Create progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Agent progress stages
            stages = [
                ("🔍 Discovery Agent", "Searching ArXiv, Semantic Scholar, and Web..."),
                ("✅ Validation Agent", "Scoring source credibility and relevance..."),
                ("🧬 Synthesis Agent", "Building knowledge graph and finding gaps..."),
                ("📊 Reporter Agent", "Generating comprehensive report...")
            ]
            
            # Show progress
            for i, (agent, description) in enumerate(stages):
                progress = (i + 1) / len(stages)
                progress_bar.progress(progress)
                status_text.markdown(f"### {agent}\n{description}")
                
                # Run the actual pipeline when reaching the first stage
                if i == 0:
                    try:
                        result = run_research_pipeline(query=query, research_depth=depth)
                        st.session_state.research_result = result
                        
                        # Update progress for remaining stages
                        for j in range(i + 1, len(stages)):
                            time.sleep(0.5)
                            progress = (j + 1) / len(stages)
                            progress_bar.progress(progress)
                            status_text.markdown(f"### {stages[j][0]}\n{stages[j][1]}")
                        
                    except Exception as e:
                        st.error(f"Research failed: {str(e)}")
                        st.session_state.running = False
                        st.stop()
            
            # Complete
            progress_bar.progress(1.0)
            status_text.markdown("### ✅ Research Complete!")
            st.success("Research completed successfully! Switch to the 'Results' tab to view the report.")
            st.session_state.running = False
            st.balloons()

with tab2:
    st.header("Research Results")
    
    if st.session_state.research_result is None:
        st.info("👈 Run a research query in the 'New Research' tab to see results here.")
    else:
        # Convert ResearchState (Pydantic model) to dict if needed
        def convert_to_dict(obj):
            """Recursively convert Pydantic models and other objects to dicts."""
            if hasattr(obj, 'dict'):
                return obj.dict()
            elif hasattr(obj, 'model_dump'):
                return obj.model_dump()
            elif isinstance(obj, dict):
                return {k: convert_to_dict(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_dict(item) for item in obj]
            else:
                return obj
        
        raw_result = st.session_state.research_result
        result = convert_to_dict(raw_result)
        
        # Helper function to reconstruct KnowledgeGraph from dict
        def dict_to_kg(kg_dict):
            """Convert dict back to KnowledgeGraph object if needed."""
            if not kg_dict:
                return None
            if isinstance(kg_dict, KnowledgeGraph):
                return kg_dict
            try:
                nodes = [KnowledgeGraphNode(**node) for node in kg_dict.get('nodes', [])]
                edges = [KnowledgeGraphEdge(**edge) for edge in kg_dict.get('edges', [])]
                return KnowledgeGraph(nodes=nodes, edges=edges, metadata=kg_dict.get('metadata', {}))
            except Exception:
                return None
        
        # Helper function to parse Notable Insights and Conclusion from detailed report
        def parse_report_sections(report_text):
            """Extract Notable Insights and Conclusion from detailed report."""
            insights = []
            conclusion = ""
            
            if not report_text:
                return insights, conclusion
            
            # Split report into lines
            lines = report_text.split('\n')
            
            # Find Notable Insights section
            insights_started = False
            insights_section = []
            
            # Find Conclusion section
            conclusion_started = False
            conclusion_section = []
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                line_stripped = line.strip()
                
                # Check for Notable Insights section (various formats)
                # Match patterns like "**3. Notable Insights**", "**4. notable insights**", etc.
                insights_pattern = re.compile(r'\*\*\s*\d+\.\s*notable\s+insights\s*\*\*', re.IGNORECASE)
                if insights_pattern.search(line_lower) or \
                   ('**notable insights**' in line_lower) or \
                   (line_lower.startswith('**') and 'notable insights' in line_lower and i > 10):  # Avoid early false positives
                    insights_started = True
                    continue
                
                # Check for Conclusion section (various formats)
                # Match patterns like "**7. Conclusion**", "**6. conclusion**", "**Conclusion**", etc.
                conclusion_pattern = re.compile(r'\*\*\s*\d+\.\s*conclusion\s*\*\*', re.IGNORECASE)
                if conclusion_pattern.search(line_lower) or \
                   ('**conclusion**' in line_lower and not 'conflicting' in line_lower) or \
                   (line_lower.startswith('**') and 'conclusion' in line_lower and not 'conflicting' in line_lower and i > 20):  # Avoid early false positives
                    conclusion_started = True
                    insights_started = False
                    continue
                
                # Stop collecting insights when we hit next major section
                # Match any numbered section header after Notable Insights
                if insights_started:
                    # Check for Research Gaps (any number)
                    gaps_pattern = re.compile(r'\*\*\s*\d+\.\s*(research\s+gaps|research\s+gaps\s+&)', re.IGNORECASE)
                    # Check for Conflicting Evidence (any number)
                    conflict_pattern = re.compile(r'\*\*\s*\d+\.\s*conflicting\s+evidence\s*\*\*', re.IGNORECASE)
                    # Check for Conclusion (any number)
                    conclusion_check_pattern = re.compile(r'\*\*\s*\d+\.\s*conclusion\s*\*\*', re.IGNORECASE)
                    
                    if gaps_pattern.search(line_lower) or \
                       conflict_pattern.search(line_lower) or \
                       conclusion_check_pattern.search(line_lower) or \
                       ('## sources' in line_lower) or \
                       (line_stripped.startswith('## SOURCES')) or \
                       (line_stripped.startswith('## CONFLICTING')):
                        insights_started = False
                
                # Stop collecting conclusion when we hit Sources, Conflicting Evidence, or Recommendations
                if conclusion_started:
                    if ('## sources' in line_lower) or \
                       ('## conflicting evidence' in line_lower) or \
                       ('**recommendations**' in line_lower) or \
                       ('**future work**' in line_lower) or \
                       (line_stripped.startswith('## SOURCES')) or \
                       (line_stripped.startswith('## CONFLICTING')):
                        break
                
                # Collect insights
                if insights_started and line_stripped:
                    # Skip empty lines and section headers
                    if not line_stripped.startswith('#') and not line_stripped.startswith('**') and len(line_stripped) > 5:
                        # Remove markdown formatting but keep the content
                        clean_line = line_stripped.lstrip('- •*').strip()
                        # Remove bold markers but keep text
                        clean_line = clean_line.replace('**', '').strip()
                        if clean_line and len(clean_line) > 10:  # Filter out very short lines
                            insights_section.append(clean_line)
                
                # Collect conclusion
                if conclusion_started and line_stripped:
                    # Skip section headers and empty lines
                    if not line_stripped.startswith('#') and not line_stripped.startswith('**') and len(line_stripped) > 5:
                        clean_line = line_stripped.strip()
                        # Remove markdown formatting
                        clean_line = clean_line.replace('**', '').strip()
                        if clean_line:
                            conclusion_section.append(clean_line)
            
            # Process insights - extract bullet points
            for line in insights_section:
                # Remove markdown bold but keep content
                line = line.replace('**', '').strip()
                if line and not line.startswith('#') and len(line) > 10:
                    # If line already has bullet, keep it; otherwise add one
                    if not (line.startswith('-') or line.startswith('•')):
                        line = f"- {line}"
                    insights.append(line)
            
            # Join conclusion lines and clean up
            conclusion = ' '.join(conclusion_section).strip()
            # Remove excessive markdown formatting
            conclusion = conclusion.replace('**', '').strip()
            # Remove multiple spaces
            conclusion = ' '.join(conclusion.split())
            
            return insights, conclusion
        
        # Executive Summary
        st.markdown("## 🎯 Executive Summary")
        st.markdown(f"""
        <div class="metric-card">
        {result.get('executive_summary', 'No summary available')}
        </div>
        """, unsafe_allow_html=True)
        
        # Key Metrics
        st.markdown("## 📊 Key Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Sources Found",
                result.get('discovery_metadata', {}).get('total_found', 0),
                delta=None
            )
        
        with col2:
            st.metric(
                "Sources Validated",
                len(result.get('validated_sources', [])),
                delta=None
            )
        
        with col3:
            st.metric(
                "Quality Score",
                f"{result.get('source_quality_avg', 0):.1f}/100",
                delta=None
            )
        
        with col4:
            st.metric(
                "Key Concepts",
                len(result.get('key_concepts', [])),
                delta=None
            )
        
        # Interactive Knowledge Graph
        st.markdown("## 🕸️ Interactive Knowledge Graph")
        
        kg_data = result.get('knowledge_graph')
        knowledge_graph = dict_to_kg(kg_data)
        
        if knowledge_graph and knowledge_graph.nodes:
            # Statistics
            kg_stats = create_kg_statistics(knowledge_graph)
            if kg_stats:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Nodes", kg_stats.get('total_nodes', 0))
                with col2:
                    st.metric("Concepts", kg_stats.get('concept_nodes', 0))
                with col3:
                    st.metric("Sources", kg_stats.get('source_nodes', 0))
                with col4:
                    st.metric("Connections", kg_stats.get('total_edges', 0))
            
            # Interactive Graph
            try:
                fig = create_interactive_kg_plotly(knowledge_graph)
                if fig:
                    st.plotly_chart(fig, use_container_width=True, height=800)
                    
                    # Additional controls and info
                    with st.expander("📊 Graph Controls & Info"):
                        st.markdown("""
                        **Interactive Features:**
                        - 🖱️ **Hover**: See detailed information about nodes
                        - 🔍 **Zoom**: Use mouse wheel or toolbar
                        - 📍 **Pan**: Click and drag to move around
                        - 🎯 **Select**: Click on nodes to highlight
                        - 🔄 **Reset**: Use the "Reset View" button or double-click
                        
                        **Node Types:**
                        - 🟢 **Green circles**: Research concepts
                        - 🔴 **Red squares**: Research sources/papers
                        
                        **Tips:**
                        - Larger nodes have more connections
                        - Hover over nodes to see full details and links
                        - Click on source nodes to open the paper URL
                        """)
                        
                        # Show relation breakdown
                        if kg_stats.get('relation_breakdown'):
                            st.markdown("**Connection Types:**")
                            for rel, count in kg_stats['relation_breakdown'].items():
                                st.write(f"- **{rel}**: {count}")
                else:
                    st.warning("Could not create interactive graph")
                    # Fallback to static image
                    kg_files = list(Path("visualisations").glob("kg_*.png"))
                    if kg_files:
                        latest_kg = max(kg_files, key=os.path.getctime)
                        try:
                            image = Image.open(latest_kg)
                            st.image(image, caption="Research Knowledge Graph (Static Fallback)", use_container_width=True)
                        except:
                            st.warning("Could not load knowledge graph visualization")
            except Exception as e:
                st.error(f"Error displaying interactive graph: {e}")
                # Fallback to static image
                kg_files = list(Path("visualisations").glob("kg_*.png"))
                if kg_files:
                    latest_kg = max(kg_files, key=os.path.getctime)
                    try:
                        image = Image.open(latest_kg)
                        st.image(image, caption="Research Knowledge Graph (Static Fallback)", use_container_width=True)
                    except:
                        st.warning("Could not load knowledge graph visualization")
        else:
            st.info("No knowledge graph available for this research")
        
        # Key Concepts
        st.markdown("## 🔑 Key Concepts")
        concepts = result.get('key_concepts', [])[:20]
        if concepts:
            concept_html = "".join([f'<span class="concept-badge">{c}</span>' for c in concepts])
            st.markdown(concept_html, unsafe_allow_html=True)
        else:
            st.info("No concepts extracted")
        
        # Consensus Findings
        st.markdown("## ✅ Consensus Findings")
        findings = result.get('consensus_findings', [])
        if findings:
            for i, finding in enumerate(findings, 1):
                st.markdown(f"{i}. {finding}")
        else:
            st.info("No consensus findings available")
        
        # Notable Insights
        detailed_report = result.get('detailed_report', '')
        insights, conclusion = parse_report_sections(detailed_report)
        
        if insights:
            st.markdown("## 💡 Notable Insights")
            for i, insight in enumerate(insights, 1):
                # Check if insight already has bullet point formatting
                if insight.startswith('-') or insight.startswith('•'):
                    st.markdown(f"{insight}")
                else:
                    st.markdown(f"- {insight}")
        else:
            st.markdown("## 💡 Notable Insights")
            st.info("No notable insights extracted from the report")
        
        # Conclusion
        if conclusion:
            st.markdown("## 📝 Conclusion")
            st.markdown(f"""
            <div class="metric-card">
            {conclusion}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("## 📝 Conclusion")
            st.info("No conclusion available in the report")
        
        # Research Gaps
        st.markdown("## 🔍 Research Gaps")
        gaps = result.get('research_gaps', [])
        if gaps:
            for i, gap in enumerate(gaps, 1):
                # Gap is already converted to dict by convert_to_dict
                gap_text = gap.get('gap', 'Unknown') if isinstance(gap, dict) else str(gap)
                importance = gap.get('importance', 'N/A') if isinstance(gap, dict) else 'N/A'
                with st.expander(f"Gap {i}: {gap_text}", expanded=False):
                    st.markdown(f"**Why it matters:** {importance}")
        else:
            st.info("No research gaps identified")
        
        # Top Sources
        st.markdown("## 📚 Top Sources")
        citation_map = result.get('citation_map', {})
        top_cited = citation_map.get('top_cited', [])  # Display all sources
        
        if top_cited:
            for i, source_item in enumerate(top_cited, 1):
                # Handle both old format (title, citations) and new format (title, citations, url)
                if len(source_item) == 3:
                    title, citations, url = source_item
                elif len(source_item) == 2:
                    title, citations = source_item
                    url = ""
                else:
                    title = str(source_item[0]) if source_item else "Unknown"
                    citations = source_item[1] if len(source_item) > 1 else 0
                    url = source_item[2] if len(source_item) > 2 else ""
                
                # Display source with URL if available
                with st.container():
                    st.markdown(f"""
                    <div class="source-card">
                    <strong>{i}. {title[:100]}</strong><br>
                    <small>Citations: {citations}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    if url:
                        # Display URL as clickable link
                        st.markdown(f"🔗 [View Source]({url})", unsafe_allow_html=False)
        else:
            st.info("No source citation data available")
        
        # Download Options
        st.markdown("## 💾 Download")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Download full report
            report_files = list(Path("reports").glob("report_*.txt"))
            if report_files:
                latest_report = max(report_files, key=os.path.getctime)
                with open(latest_report, 'r', encoding='utf-8') as f:
                    report_content = f.read()
                st.download_button(
                    label="📄 Download Report (TXT)",
                    data=report_content,
                    file_name=f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
        
        with col2:
            # Download as JSON
            # Result is already converted to dict, but ensure it's fully serializable
            json_result = {
                "query": result.get('query'),
                "executive_summary": result.get('executive_summary'),
                "key_concepts": result.get('key_concepts'),
                "consensus_findings": result.get('consensus_findings'),
                "research_gaps": result.get('research_gaps', []),
                "metadata": {
                    "sources_found": result.get('discovery_metadata', {}).get('total_found'),
                    "sources_validated": len(result.get('validated_sources', [])),
                    "quality_score": result.get('source_quality_avg'),
                    "timestamp": result.get('completed_at')
                }
            }
            json_data = json.dumps(json_result, indent=2, default=str)
            
            st.download_button(
                label="📦 Download Data (JSON)",
                data=json_data,
                file_name=f"research_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col3:
            # Download knowledge graph
            kg_files = list(Path("visualisations").glob("kg_*.png"))
            if kg_files:
                latest_kg = max(kg_files, key=os.path.getctime)
                with open(latest_kg, 'rb') as f:
                    st.download_button(
                        label="🖼️ Download Graph (PNG)",
                        data=f,
                        file_name=f"knowledge_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                        mime="image/png"
                    )
            else:
                st.info("No knowledge graph available to download")

with tab3:
    st.header("Research History")
    st.info("🚧 Research history feature coming soon! Your past research sessions will be saved and accessible here.")
    
    # Show recent report files
    report_files = sorted(Path("reports").glob("report_*.txt"), key=os.path.getctime, reverse=True)
    kg_files = sorted(Path("visualisations").glob("kg_*.png"), key=os.path.getctime, reverse=True)
    
    if report_files or kg_files:
        st.markdown("### Recent Files")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Reports:**")
            for report in report_files[:5]:
                st.markdown(f"- `{report.name}` ({report.stat().st_size // 1024} KB)")
        
        with col2:
            st.markdown("**Knowledge Graphs:**")
            for kg in kg_files[:5]:
                st.markdown(f"- `{kg.name}` ({kg.stat().st_size // 1024} KB)")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>Multi-Agent Research Intelligence Platform | Powered by LangGraph, Groq LLM & ChromaDB</p>
    <p>Built with ❤️ using Streamlit | © 2025</p>
</div>
""", unsafe_allow_html=True)
