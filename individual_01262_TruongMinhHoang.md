# BÁO CÁO CÁ NHÂN LAB DAY 09 - MULTI-AGENT E-COMMERCE DISPUTE RESOLUTION

**Họ và tên**: Trương Minh Hoàng  
**Mã học viên (MHV)**: 01262  
**Nhóm**: B2_1  
**Vai trò trong dự án**: Data Analyst (Order & Payment)  

---

## 1. Công việc được phân công (Assigned Responsibilities)

- **Module phụ trách**: `Order & Product Agent`
- **Chi tiết nhiệm vụ**:
  - Viết hàm đọc `order_items.csv`, `products.csv`, `sellers.csv`.
  - Đếm số lượng để check `multi_item_order`, `multi_seller_order`, `multiple_categories`.
  - Trả về danh sách `item_ids`, `seller_ids`, `product_ids`, `category_names`.

---

## 2. Kết quả đạt được (Key Contributions & Outputs)

1. Hoàn thành module phụ trách đúng tiến độ, hỗ trợ ghép nối thành công vào pipeline chung `main.py`.
2. Hệ thống chạy thành công 50/50 case khiếu nại (`EC_001.json` - `EC_050.json`) không phát sinh ngoại lệ.
3. Đảm bảo toàn bộ phán quyết đều dựa trên Evidence ID hợp lệ từ dữ liệu Olist CSV.

---

## 3. Bài học kinh nghiệm (Key Takeaways)

- Hiểu rõ nguyên lý thiết kế hệ thống Multi-Agent phân tán (A2A Handoff).
- Kỹ năng xử lý dữ liệu và tuân thủ chặt chẽ các giới hạn nghiệp vụ (Constraint Validation).
- Kinh nghiệm làm việc nhóm trên Git và quy trình CI/CD nộp bài competition.
