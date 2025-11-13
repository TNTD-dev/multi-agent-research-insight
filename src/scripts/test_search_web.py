import os
import sys
import hashlib
import json
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
from pathlib import Path

# Load biến môi trường từ file .env
try:
    from dotenv import load_dotenv
    # Load .env từ thư mục gốc của project
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    # Nếu không có dotenv, vẫn chạy được nhưng không load .env
    pass

# Cố gắng import thư viện serpapi
try:
    from serpapi import GoogleSearch
except ImportError:
    print("Lỗi: Thư viện 'serpapi' (google-search-results) chưa được cài đặt.")
    print("Hãy chạy: pip install google-search-results")
    sys.exit(1)

# Thiết lập logging cơ bản
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. ĐỊNH NGHĨA LỚP DATA TƯƠNG TỰ
# Đây là một bản sao đơn giản của lớp ResearchSource
# chỉ chứa các trường mà hàm search_web sử dụng.
@dataclass
class ResearchSource:
    id: str
    title: str
    summary: str
    full_text: str
    url: str
    source_type: str
    metadata: Dict[str, Any]

# 2. HÀM TÌM KIẾM (ĐÃ CHỈNH SỬA TỪ CODE CỦA BẠN)
# Đã loại bỏ 'self' và nhận 'api_key' làm tham số
def search_web_standalone(
    api_key: str, query: str, num_results: int = 5
) -> List[ResearchSource]:
    """Search general web sources using SerpAPI."""
    
    try:
        # Khởi tạo tìm kiếm
        search = GoogleSearch(
            {
                "q": query,
                "api_key": api_key,
                "num": num_results,
            }
        )

        # Lấy kết quả
        # Hàm search.get_dict() sẽ thực hiện yêu cầu API
        results = search.get_dict().get("organic_results", [])
        
        if not results:
            logger.warning("Không tìm thấy kết quả 'organic_results' nào.")
            return []

        formatted: List[ResearchSource] = []

        for result in results:
            link = result.get("link", "") or result.get("url", "")
            if not link:
                logger.warning(
                    "Kết quả web thiếu URL, bỏ qua: %s",
                    result.get("title", "Unknown"),
                )
                continue
            
            # Tạo ID y hệt logic của bạn
            result_id = f"web_{hashlib.md5(link.encode()).hexdigest()[:8]}"
            snippet = result.get("snippet", "")

            formatted.append(
                ResearchSource(
                    id=result_id,
                    title=result.get("title", "No title"),
                    summary=snippet,      # Lấy snippet
                    full_text=snippet,    # Lấy snippet (giống code của bạn)
                    url=link,
                    source_type="web",
                    metadata={"position": result.get("position", 999)},
                )
            )

        logger.info("Tìm kiếm web: %d kết quả", len(formatted))
        return formatted
        
    except Exception as exc:
        logger.exception("Tìm kiếm web thất bại: %s", exc)
        return []

# 3. PHẦN THỰC THI SCRIPT
if __name__ == "__main__":
    
    # Lấy API key từ biến môi trường (đã load từ .env nếu có)
    SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
    
    if not SERPAPI_KEY:
        logger.error("LỖI: Biến môi trường SERPAPI_KEY chưa được đặt.")
        logger.error("Hãy đặt key bằng một trong các cách sau:")
        logger.error("  1. Tạo file .env trong thư mục gốc và thêm: SERPAPI_KEY=your_key_here")
        logger.error("  2. Hoặc set biến môi trường trong PowerShell: $env:SERPAPI_KEY='your_key_here'")
        logger.error("  3. Hoặc set biến môi trường trong CMD: set SERPAPI_KEY=your_key_here")
        sys.exit(1) # Thoát script

    # Truy vấn để test
    TEST_QUERY = "What is a Transformer model in AI?"
    NUM_RESULTS = 3

    print(f"--- Bắt đầu tìm kiếm web cho: '{TEST_QUERY}' ---")

    # Gọi hàm test
    search_results = search_web_standalone(
        api_key=SERPAPI_KEY,
        query=TEST_QUERY,
        num_results=NUM_RESULTS
    )

    if search_results:
        print(f"\n--- Đã tìm thấy {len(search_results)} kết quả ---")
        
        # Chuyển đổi dataclass thành dict để in JSON cho đẹp
        results_as_dict = [asdict(r) for r in search_results]
        
        # In kết quả
        print(json.dumps(results_as_dict, indent=2, ensure_ascii=False))
    else:
        print("\n--- Không tìm thấy kết quả nào. ---")