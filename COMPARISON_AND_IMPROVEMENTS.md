# So sánh hệ thống Research và Đề xuất Cải thiện

## Tổng quan

Sau khi phân tích notebook `systematic_review_of_scientific_articles.ipynb` và hệ thống hiện tại, đây là bản so sánh chi tiết và các đề xuất cải thiện.

---

## 1. KIẾN TRÚC WORKFLOW

### Hệ thống trong Notebook (LangGraph)
- ✅ **Sử dụng LangGraph với StateGraph**: Workflow dạng đồ thị có hướng (directed graph)
- ✅ **Các node chuyên biệt**: 
  - `planner` → `researcher` → `search_articles` → `article_decisions` → `download_articles`
  - `paper_analyzer` → (parallel) → `write_abstract`, `write_introduction`, `write_methods`, `write_results`, `write_conclusion`, `write_references`
  - `aggregate_paper` → `critique_paper` → (loop) → `revise_paper` → `final_draft`
- ✅ **Có vòng lặp phản hồi**: Critique → Revise → Critique (cho đến khi đạt chất lượng)
- ✅ **Parallel processing**: Nhiều phần của bài review được viết song song

### Hệ thống hiện tại (Sequential Pipeline)
- ⚠️ **Pipeline tuần tự đơn giản**: discovery → validation → rag → synthesis → ml → reporter → monitoring
- ⚠️ **Không có vòng lặp phản hồi**: Một lần chạy, không có cơ chế revise/critique
- ⚠️ **Không có parallel processing**: Tất cả chạy tuần tự

### **Đề xuất cải thiện:**
1. **Chuyển sang LangGraph** để có workflow linh hoạt hơn
2. **Thêm vòng lặp critique-revise** cho báo cáo
3. **Parallel processing** cho các phần báo cáo độc lập

---

## 2. QUY TRÌNH SYSTEMATIC REVIEW

### Hệ thống trong Notebook
- ✅ **Có Planning Phase**: Tạo outline và strategy trước khi research
- ✅ **Có Research Strategy**: Phân tích query và lập kế hoạch tìm kiếm
- ✅ **Có Decision Node**: Quyết định có cần thêm papers không
- ✅ **Có Article Download**: Tải và xử lý full text papers
- ✅ **Có Paper Analyzer**: Phân tích chi tiết từng paper (Introduction, Methods, Results, Conclusions)
- ✅ **Có Aggregator**: Tổng hợp thông tin từ nhiều papers
- ✅ **Có Critique & Revise Loop**: Đảm bảo chất lượng báo cáo
- ✅ **Có Final Draft**: Tạo bản cuối cùng publication-ready

### Hệ thống hiện tại
- ⚠️ **Thiếu Planning Phase**: Bắt đầu search ngay lập tức
- ⚠️ **Thiếu Research Strategy**: Không có phân tích query trước
- ⚠️ **Không có Decision Logic**: Không quyết định có cần thêm sources
- ⚠️ **Chỉ dùng Abstract/Summary**: Không tải full text papers
- ⚠️ **Phân tích nông**: Chỉ dùng summary, không phân tích chi tiết sections
- ⚠️ **Không có Critique-Revise**: Báo cáo được tạo một lần, không có feedback loop

### **Đề xuất cải thiện:**
1. **Thêm Planning Agent**: Phân tích query và tạo research strategy
2. **Thêm Decision Agent**: Quyết định có cần thêm sources dựa trên coverage
3. **Tích hợp PDF Download & Extraction**: Tải full text papers (arXiv PDF, Semantic Scholar)
4. **Thêm Paper Analyzer Agent**: Phân tích chi tiết từng section (Introduction, Methods, Results, Conclusions)
5. **Thêm Critique Agent**: Đánh giá chất lượng báo cáo
6. **Thêm Revise Agent**: Cải thiện báo cáo dựa trên critique

---

## 3. XỬ LÝ FULL TEXT PAPERS

### Hệ thống trong Notebook
- ✅ **Có article_download node**: Tải papers từ URLs
- ✅ **Có paper_analyzer**: Phân tích full text với các sections riêng biệt
- ✅ **Extract từng section**: Introduction, Methods, Results, Conclusions được xử lý riêng

### Hệ thống hiện tại
- ❌ **Chỉ dùng Abstract/Summary**: Không có full text
- ❌ **Thiếu PDF extraction**: Không tải và parse PDF files
- ❌ **Thiếu section extraction**: Không phân tích các phần riêng biệt

### **Đề xuất cải thiện:**
1. **Thêm PDF Download Module**: 
   - Tải PDF từ arXiv (đã có URL)
   - Tải PDF từ Semantic Scholar (nếu có)
   - Sử dụng thư viện như `pymupdf4llm` hoặc `PyPDF2`
2. **Thêm PDF Parser Agent**: 
   - Extract text từ PDF
   - Phân chia sections (Introduction, Methods, Results, Conclusions)
   - Extract tables và figures metadata
3. **Cập nhật RAG Agent**: 
   - Index full text thay vì chỉ abstract
   - Chunk theo sections để retrieval tốt hơn

---

## 4. CẤU TRÚC BÁO CÁO

### Hệ thống trong Notebook
- ✅ **Cấu trúc Systematic Review chuẩn**:
  - Abstract (structured)
  - Introduction
  - Methods (comparative analysis)
  - Results
  - Conclusions
  - References
- ✅ **Có critique prompts**: Đánh giá từng phần
- ✅ **Có revision prompts**: Cải thiện dựa trên feedback

### Hệ thống hiện tại
- ⚠️ **Cấu trúc đơn giản**: Executive Summary + Detailed Report
- ⚠️ **Thiếu Methods section**: Không có phần so sánh phương pháp
- ⚠️ **Thiếu structured format**: Không theo chuẩn systematic review

### **Đề xuất cải thiện:**
1. **Restructure Reporter Agent**:
   - Tạo các methods riêng: `write_abstract()`, `write_introduction()`, `write_methods()`, `write_results()`, `write_conclusions()`, `write_references()`
   - Mỗi method có prompt chuyên biệt
2. **Thêm Methods Section**: So sánh approaches trong các papers
3. **Structured Abstract**: Background, Methods, Results, Conclusion

---

## 5. PROMPT ENGINEERING

### Hệ thống trong Notebook
- ✅ **Prompts chuyên biệt cho từng task**: 
  - `planner_prompt`: Tạo outline
  - `research_prompt`: Tìm kiếm papers
  - `analyze_paper_prompt`: Phân tích chi tiết từng section
  - `abstract_prompt`, `introduction_prompt`, `methods_prompt`, etc.
  - `critique_draft_prompt`: Đánh giá chất lượng
  - `revise_draft_prompt`: Cải thiện báo cáo
- ✅ **Prompts có context rõ ràng**: Mỗi prompt giải thích role và output format

### Hệ thống hiện tại
- ⚠️ **Prompts đơn giản**: Một số prompts có thể được cải thiện
- ⚠️ **Thiếu specialized prompts**: Một số agents dùng prompts chung

### **Đề xuất cải thiện:**
1. **Cải thiện prompts trong Synthesis Agent**: Thêm context về systematic review
2. **Cải thiện prompts trong Reporter Agent**: Tạo prompts riêng cho từng section
3. **Thêm critique prompts**: Đánh giá chất lượng báo cáo
4. **Thêm revision prompts**: Hướng dẫn cải thiện

---

## 6. STATE MANAGEMENT

### Hệ thống trong Notebook
- ✅ **Sử dụng LangGraph StateGraph**: State được quản lý tự động
- ✅ **TypedDict cho type safety**: `AgentState` với các fields rõ ràng
- ✅ **Message history**: Lưu trữ conversation history

### Hệ thống hiện tại
- ✅ **ResearchState với Pydantic**: Type-safe state management
- ✅ **DictLikeModel**: Dễ dàng update và serialize
- ⚠️ **Có thể cải thiện**: Thêm message history cho critique-revise loop

### **Đề xuất cải thiện:**
1. **Thêm critique history**: Lưu các lần critique và revision
2. **Thêm draft versions**: Lưu các phiên bản báo cáo
3. **Thêm decision history**: Lưu các quyết định về việc thêm sources

---

## 7. TOOLS & INTEGRATIONS

### Hệ thống trong Notebook
- ✅ **AcademicPaperSearchTool**: Tool chuyên biệt cho Semantic Scholar
- ✅ **Tool integration với LangChain**: Sử dụng BaseTool

### Hệ thống hiện tại
- ✅ **Có Discovery Agent**: Tìm kiếm từ ArXiv, Semantic Scholar, Web
- ✅ **Có RAG Agent**: Vector store với ChromaDB
- ⚠️ **Có thể cải thiện**: Thêm tools cho PDF processing

### **Đề xuất cải thiện:**
1. **Thêm PDF Download Tool**: Tải và extract text từ PDFs
2. **Thêm Section Extractor Tool**: Phân chia papers thành sections
3. **Thêm Citation Extractor Tool**: Extract citations và references

---

## 8. ERROR HANDLING & ROBUSTNESS

### Hệ thống trong Notebook
- ⚠️ **Cần kiểm tra**: Error handling trong các nodes

### Hệ thống hiện tại
- ✅ **Có try-except blocks**: Xử lý lỗi trong các agents
- ✅ **Có logging**: Ghi log chi tiết
- ⚠️ **Có thể cải thiện**: Retry logic cho API calls

### **Đề xuất cải thiện:**
1. **Thêm retry logic**: Retry với exponential backoff cho API calls
2. **Thêm fallback mechanisms**: Nếu một source fail, dùng source khác
3. **Thêm validation**: Validate outputs của mỗi agent trước khi chuyển sang agent tiếp theo

---

## 9. PRIORITIZED IMPROVEMENT ROADMAP

### Phase 1: Core Improvements (Ưu tiên cao)
1. **Thêm Planning Agent**
   - Phân tích query và tạo research strategy
   - Tạo outline cho systematic review
   
2. **Thêm PDF Download & Extraction**
   - Tải PDF từ arXiv và Semantic Scholar
   - Extract full text và sections
   
3. **Thêm Paper Analyzer Agent**
   - Phân tích chi tiết từng section
   - Extract key information từ Methods, Results, etc.

4. **Restructure Reporter Agent**
   - Tách thành các methods: abstract, introduction, methods, results, conclusions
   - Mỗi method có prompt chuyên biệt

### Phase 2: Quality Improvements (Ưu tiên trung bình)
5. **Thêm Critique-Revise Loop**
   - Critique Agent đánh giá chất lượng
   - Revise Agent cải thiện dựa trên feedback
   - Loop cho đến khi đạt chất lượng

6. **Thêm Decision Agent**
   - Quyết định có cần thêm sources
   - Đánh giá coverage của research

7. **Chuyển sang LangGraph**
   - Workflow linh hoạt hơn
   - Parallel processing
   - Better state management

### Phase 3: Advanced Features (Ưu tiên thấp)
8. **Cải thiện Prompts**
   - Specialized prompts cho từng task
   - Better context và instructions

9. **Thêm Tools**
   - PDF processing tools
   - Section extraction tools
   - Citation extraction tools

10. **Cải thiện Error Handling**
    - Retry logic
    - Fallback mechanisms
    - Better validation

---

## 10. WEB SEARCH & VALIDATION COMPARISON

### Web Search

#### Hệ thống trong Notebook
- ⚠️ **Chỉ dùng Semantic Scholar**: Sử dụng `AcademicPaperSearchTool` chỉ tìm kiếm academic papers từ Semantic Scholar API
- ⚠️ **Không có general web search**: Không tìm kiếm trên web chung (blogs, news, websites)
- ✅ **Tool-based approach**: Sử dụng LangChain BaseTool để tích hợp search
- ✅ **Structured output**: Kết quả được format chuẩn với metadata đầy đủ

#### Hệ thống hiện tại
- ✅ **Đa nguồn tìm kiếm**: 
  - ArXiv (academic preprints)
  - Semantic Scholar (peer-reviewed papers)
  - Web search qua Tavily API (blogs, news, websites)
- ✅ **Web search linh hoạt**: Có thể tìm kiếm cả academic và non-academic sources
- ✅ **Domain reputation check**: Validation agent kiểm tra domain (.edu, .gov, .org) để đánh giá credibility
- ⚠️ **Có thể cải thiện**: 
  - Thêm filtering cho web sources (chỉ lấy academic websites)
  - Thêm source type classification (academic vs non-academic)

#### **So sánh chi tiết:**

| Tính năng | Notebook | Hệ thống hiện tại | Đánh giá |
|-----------|----------|-------------------|----------|
| Academic search | ✅ Semantic Scholar | ✅ ArXiv + Semantic Scholar | **Hiện tại tốt hơn** |
| Web search | ❌ Không có | ✅ Tavily API | **Hiện tại tốt hơn** |
| Source diversity | ⚠️ Chỉ academic | ✅ Academic + Web | **Hiện tại tốt hơn** |
| Tool integration | ✅ LangChain BaseTool | ⚠️ Direct API calls | **Notebook tốt hơn** |
| Structured output | ✅ Tool format | ✅ ResearchSource model | **Tương đương** |

#### **Đề xuất cải thiện:**
1. **Giữ nguyên đa nguồn**: Tiếp tục search từ ArXiv, Semantic Scholar, và Web
2. **Thêm filtering cho web sources**: 
   - Ưu tiên academic domains (.edu, .gov, .org)
   - Filter out spam/low-quality sites
   - Classify source type (academic paper, blog, news, etc.)
3. **Chuyển sang Tool-based approach**: Sử dụng LangChain Tools để dễ tích hợp và mở rộng
4. **Thêm source type metadata**: Đánh dấu rõ ràng academic vs non-academic sources

---

### Validation & Decision Logic

#### Hệ thống trong Notebook
- ✅ **Có Decision Node (`article_decisions`)**: 
  - Sử dụng LLM để quyết định papers nào cần download
  - Quyết định có cần thêm papers không
  - Có feedback loop: nếu cần thêm → quay lại `search_articles`
- ✅ **Decision prompt chuyên biệt**: 
  ```python
  decision_prompt = '''You are an academic researcher that is searching Academic and Scientific Research Papers.
  Evaluate the papers found and decide:
  1. Which papers to download and analyze
  2. Whether more papers are needed
  3. Return URLs of selected papers'''
  ```
- ✅ **Iterative search**: Có thể search nhiều lần cho đến khi đủ papers
- ⚠️ **Không có scoring system**: Không có điểm số credibility chi tiết
- ⚠️ **Validation đơn giản**: Chủ yếu dựa vào LLM decision, không có heuristic scoring

#### Hệ thống hiện tại
- ✅ **Validation Agent với scoring system chi tiết**:
  - **Credibility Score** (0-100) dựa trên:
    - Source type (semantic_scholar: +28, arxiv: +25, web: +18 với domain bonus)
    - Citation count (0-30 điểm)
    - Recency (0-20 điểm)
    - Author information (0-5 điểm)
    - Summary quality (0-15 điểm)
    - URL validity
  - **Domain reputation check**: Kiểm tra .edu, .gov, .org
  - **Content quality check**: Phát hiện spam, kiểm tra meaningful content
- ✅ **Relevance check với LLM**: 
  - Đánh giá relevance với query
  - Confidence level (HIGH/MEDIUM/LOW)
  - Reason cho decision
- ✅ **Dynamic threshold**: Threshold tự động điều chỉnh dựa trên average score
- ✅ **Acceptance criteria thông minh**: 
  - Relevant AND (high confidence OR score >= threshold)
  - Hoặc medium confidence AND score >= threshold + 5
- ❌ **Không có Decision Logic**: Không quyết định có cần thêm sources
- ❌ **Không có feedback loop**: Một lần search và validate, không có iterative search

#### **So sánh chi tiết:**

| Tính năng | Notebook | Hệ thống hiện tại | Đánh giá |
|-----------|----------|-------------------|----------|
| Scoring system | ❌ Không có | ✅ Chi tiết (0-100) | **Hiện tại tốt hơn** |
| Relevance check | ✅ LLM-based | ✅ LLM-based | **Tương đương** |
| Domain check | ❌ Không có | ✅ Có (.edu, .gov, .org) | **Hiện tại tốt hơn** |
| Content quality | ❌ Không có | ✅ Spam detection | **Hiện tại tốt hơn** |
| Decision logic | ✅ Có (cần thêm papers?) | ❌ Không có | **Notebook tốt hơn** |
| Feedback loop | ✅ Có (iterative search) | ❌ Không có | **Notebook tốt hơn** |
| Dynamic threshold | ❌ Không có | ✅ Có | **Hiện tại tốt hơn** |

#### **Đề xuất cải thiện:**

1. **Giữ nguyên Validation Agent tốt**:
   - Tiếp tục dùng scoring system chi tiết
   - Giữ domain reputation check
   - Giữ content quality check

2. **Thêm Decision Agent** (kết hợp tốt nhất của cả hai):
   ```python
   class DecisionAgent:
       """Agent that decides if more sources are needed."""
       
       def should_search_more(self, state: ResearchState) -> Dict[str, Any]:
           """Decide if more sources are needed."""
           validated_count = len(state.validated_sources)
           avg_score = state.source_quality_avg
           key_concepts = state.key_concepts
           
           prompt = f"""Evaluate if we have enough sources for a systematic review.
           
           Current status:
           - Validated sources: {validated_count}
           - Average quality score: {avg_score:.1f}
           - Key concepts found: {len(key_concepts)}
           - Query: {state.query}
           
           Consider:
           1. Do we have enough sources? (typically need 5-15 for systematic review)
           2. Are key concepts well covered?
           3. Is the quality sufficient?
           4. Are there research gaps that need more papers?
           
           Return:
           NEED_MORE: [YES/NO]
           REASON: [explanation]
           SEARCH_QUERY: [if YES, suggest a new search query]"""
           
           response = self.llm.invoke(prompt)
           # Parse response
           return decision_result
   ```

3. **Thêm Iterative Search Logic**:
   - Sau validation, check xem có đủ sources không
   - Nếu chưa đủ, tự động search thêm với query mới
   - Lặp lại cho đến khi đủ hoặc đạt max iterations

4. **Cải thiện Integration**:
   - Decision Agent sử dụng output của Validation Agent
   - Kết hợp scoring với LLM decision để có quyết định tốt hơn

5. **Thêm Coverage Analysis**:
   - Phân tích xem các key concepts đã được cover chưa
   - Identify gaps trong research coverage
   - Suggest specific search queries để fill gaps

---

## 11. CODE EXAMPLES

### Example 1: Thêm Planning Agent

```python
class PlanningAgent:
    """Agent responsible for creating research strategy and outline."""
    
    def __init__(self, llm):
        self.llm = llm
    
    def create_research_strategy(self, query: str) -> Dict[str, Any]:
        """Analyze query and create research strategy."""
        prompt = f"""You are an academic researcher planning a systematic review.
        
Query: {query}

Create a research strategy including:
1. Key search terms and synonyms
2. Inclusion/exclusion criteria
3. Databases to search
4. Expected number of papers
5. Research questions to answer

Format as JSON."""
        
        response = self.llm.invoke(prompt)
        # Parse and return strategy
        return strategy
    
    def create_outline(self, query: str) -> Dict[str, Any]:
        """Create outline for systematic review."""
        prompt = f"""Create a structured outline for a systematic review on: {query}
        
Include:
- Abstract (Background, Methods, Results, Conclusion)
- Introduction
- Methods (Search strategy, Selection criteria, Data extraction)
- Results (Study characteristics, Findings)
- Discussion
- Conclusions
- References"""
        
        response = self.llm.invoke(prompt)
        return outline
```

### Example 2: Thêm PDF Download Module

```python
import pymupdf4llm  # or PyPDF2

class PDFDownloader:
    """Download and extract text from PDFs."""
    
    def download_pdf(self, url: str) -> bytes:
        """Download PDF from URL."""
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    
    def extract_text(self, pdf_content: bytes) -> str:
        """Extract text from PDF."""
        # Using pymupdf4llm
        md_text = pymupdf4llm.to_markdown(pdf_content)
        return md_text
    
    def extract_sections(self, text: str) -> Dict[str, str]:
        """Extract sections from paper."""
        sections = {
            "introduction": "",
            "methods": "",
            "results": "",
            "conclusions": ""
        }
        
        # Use regex or LLM to identify sections
        # ...
        
        return sections
```

### Example 3: Critique-Revise Loop

```python
class CritiqueAgent:
    """Agent that critiques the research report."""
    
    def critique(self, report: str, query: str) -> Dict[str, Any]:
        """Critique the report and provide feedback."""
        prompt = f"""You are an expert reviewer evaluating a systematic review.
        
Query: {query}
Report: {report}

Evaluate:
1. Completeness: Are all sections present?
2. Quality: Is the analysis thorough?
3. Coverage: Are enough papers included?
4. Clarity: Is the writing clear?

Provide:
- Overall score (1-10)
- Strengths
- Weaknesses
- Recommendations for improvement
- Should we revise? (YES/NO)"""
        
        response = self.llm.invoke(prompt)
        return critique_result

class ReviseAgent:
    """Agent that revises the report based on critique."""
    
    def revise(self, report: str, critique: Dict[str, Any]) -> str:
        """Revise the report based on critique."""
        prompt = f"""Revise this systematic review based on the critique.
        
Original Report: {report}
Critique: {critique}

Implement the recommendations and improve the report."""
        
        response = self.llm.invoke(prompt)
        return revised_report
```

---

## KẾT LUẬN

Hệ thống hiện tại của bạn đã có nền tảng tốt với các agents chuyên biệt và RAG integration. Tuy nhiên, để đạt được chất lượng systematic review như trong notebook, cần:

1. **Thêm Planning & Strategy Phase**
2. **Tích hợp Full Text Processing** (PDF download & extraction)
3. **Thêm Critique-Revise Loop** để đảm bảo chất lượng
4. **Restructure Report** theo chuẩn systematic review
5. **Cải thiện Workflow** với LangGraph cho flexibility

Ưu tiên bắt đầu với Phase 1 (Core Improvements) để có impact lớn nhất.

