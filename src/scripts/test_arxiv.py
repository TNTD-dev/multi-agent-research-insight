import arxiv

# ID của bài báo "Attention Is All You Need"
paper_id = "1706.03762"

# 1. Tạo một đối tượng tìm kiếm
# Chúng ta dùng id_list để tìm chính xác
search = arxiv.Search(id_list=[paper_id])

# 2. Lấy kết quả
# Vì ta tìm theo ID, nên chỉ có 1 kết quả
paper = next(search.results())

# 3. In ra thông tin
print("--- KẾT QUẢ TỪ THƯ VIỆN PYTHON ---")
print(f"\nTiêu đề (paper.title):\n{paper.title}")
print(f"\nTóm tắt (paper.summary):\n{paper.summary}")