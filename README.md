# Multi-Agent Research Intelligence Platform

Hệ thống nghiên cứu thông minh sử dụng nhiều AI agent để tự động thu thập, phân tích và tổng hợp thông tin từ nhiều nguồn.

## Tính năng

- 🔍 **Discovery Agent**: Tìm kiếm tài liệu từ ArXiv, Semantic Scholar và web
- ✅ **Validation Agent**: Đánh giá chất lượng nguồn thông tin
- 📚 **RAG Agent**: Tích hợp RAG với ChromaDB để truy xuất thông tin
- 🔬 **Synthesis Agent**: Tổng hợp và phân tích thông tin
- 📊 **Reporter Agent**: Tạo báo cáo chi tiết
- 📈 **Monitoring Agent**: Giám sát và cảnh báo

## Cài đặt

1. Clone repository:
```bash
git clone <repository-url>
cd multi-agent-research
```

2. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

3. Tạo file `.env` trong thư mục gốc:
```env
GROQ_API_KEY=your_groq_api_key_here
TAVILY_KEY=your_tavily_api_key_here  # Tùy chọn
```

## Sử dụng

### Chạy từ command line:
```bash
python main.py
```

Chương trình sẽ yêu cầu:
- Nhập câu hỏi nghiên cứu
- Chọn độ sâu nghiên cứu: `quick`, `standard`, hoặc `deep`

### Sử dụng trong code:
```python
from src.agentic_ai_pipeline import run_research_pipeline

state = run_research_pipeline(
    query="Câu hỏi nghiên cứu của bạn",
    research_depth="standard"
)
```

## Kết quả

Sau khi chạy, kết quả được lưu tại:
- **Báo cáo**: `reports/report_*.txt`
- **Biểu đồ knowledge graph**: `visualisations/kg_*.png`
- **Logs**: `logs/research_pipeline.log`

## Cấu trúc dự án

```
multi-agent-research/
├── main.py                 # Entry point
├── src/
│   ├── agentic_ai_pipeline.py  # Pipeline chính
│   ├── agents/            # Các agent chuyên biệt
│   ├── config.py          # Cấu hình
│   └── utils/             # Tiện ích
├── reports/               # Báo cáo đầu ra
├── visualisations/        # Biểu đồ
└── chroma_db/            # Vector database
```

## Yêu cầu

- Python 3.8+
- GROQ API key (bắt buộc)
- Tavily API key (tùy chọn, cho tìm kiếm web)



