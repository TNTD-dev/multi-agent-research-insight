import requests
import json

# 1. Truy vấn và các trường (fields) y hệt code của bạn
query = "Attention Is All You Need"
fields = "title,authors,abstract,year,citationCount,url,publicationDate,paperId"
limit = 1 # Chúng ta chỉ cần 1 kết quả để làm ví dụ

# 2. Tạo request y hệt code của bạn
try:
    response = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={
            "query": query,
            "limit": limit,
            "fields": fields,
        },
        timeout=10, # Đặt timeout
    )
    response.raise_for_status() # Kiểm tra lỗi HTTP

    # 3. Xử lý dữ liệu
    data = response.json()
    papers = data.get("data", [])

    if papers:
        # Lấy bài báo đầu tiên
        paper = papers[0]
        
        # 4. Trích xuất thông tin y hệt code của bạn
        title = paper.get("title", "Unknown")
        
        # Đây là nguồn của 'summary' và 'full_text' trong code của bạn
        abstract = paper.get("abstract", "") 
        
        summary_truncated = (abstract or "")[:500] # Đây là trường 'summary'

        print("--- KẾT QUẢ TỪ THƯ VIỆN PYTHON (REQUESTS) ---")
        print(f"\nTiêu đề (paper.get('title')):\n{title}")
        print(f"\nTóm tắt (paper.get('abstract')):\n{abstract}")
        print(f"\nSummary bị cắt ngắn (trường 'summary' của bạn):\n{summary_truncated}...")

except requests.RequestException as exc:
    print(f"Lỗi khi gọi API: {exc}")