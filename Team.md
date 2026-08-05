# PHÂN CÔNG CÔNG VIỆC DỰ ÁN MULTI-AGENT E-COMMERCE DISPUTE RESOLUTION

## Danh sách thành viên nhóm
| Họ và tên | Mã sinh viên |
|---|---|
| Phan Văn Hoàng Nam | 2A202601160 |
| Trương Minh Hoàng | 2A202601262 |
| Tạ Kim Ngân | 2A202601258 |
| Phạm Thế Đăng | 2A202601766 |
| Đào Trung Hiếu | 2A202601238 |

Dựa trên bản thiết kế `architecture.md`, dưới đây là phương án phân chia công việc chi tiết cho 5 thành viên: **Nam, Hoàng, Ngân, Đăng, Hiếu**. Mục tiêu của phương án này là **đảm bảo tính độc lập tối đa khi code** (không ai giẫm chân lên code của ai) và **khớp nối hoàn hảo khi merge code** nhờ việc thống nhất Interface (Đầu vào/Đầu ra) từ trước.

---

## 🎯 1. Nguyên tắc làm việc chung (Bắt buộc để ghép code không lỗi)
1. **Thống nhất Model (Pydantic / Dataclasses)**: Mọi người sẽ import các class cấu trúc dữ liệu từ 1 file `models.py` dùng chung. Không ai được tự ý return về dạng dictionary tự do (unstructured dict).
2. **Không tự ý ghi file**: Trừ Đăng (phụ trách output), các thành viên khác chỉ viết hàm xử lý logic, nhận parameter vào và `return` ra data object.
3. **Thư mục làm việc**: Mỗi người code trong 1 file python riêng (ví dụ: `policy_agent.py`, `order_agent.py`, v.v.).

---

## 👤 2. Chi tiết công việc từng thành viên

### 👩‍💻 1. Ngân - Core Logic & Policy (Trái tim hệ thống)
Ngân phụ trách định nghĩa cấu trúc dữ liệu chung để 3 người còn lại dùng, và xử lý bộ não nghiệp vụ quyết định hoàn tiền.
* **Module đảm nhiệm**: `models.py` (A2A Protocol & Schema) và `Policy Agent`.
* **Nhiệm vụ chi tiết**:
  1. **Tạo `models.py`**: Khai báo các class lưu trữ Payload theo chuẩn `architecture.md` (ví dụ: `CustomerPayload`, `PaymentPayload`, `ResolutionOutput`...).
  2. **Viết hàm `evaluate_policy(context: AggregatedContext) -> ResolutionOutput`**:
     * Nhận đầu vào là cục data tổng hợp (từ Hoàng và Hiếu gửi lên qua Đăng).
     * Áp dụng luật `input`: Ưu tiên tuyệt đối (canceled -> unavailable -> late seller -> late logistics -> valid split...).
     * Xác định Secondary issues đúng thứ tự (multi_item -> multi_seller...).
     * Tạo danh sách `evidence_ids` đúng format string.
* **Đầu vào (Input)**: Aggregated data từ các Agent khác.
* **Đầu ra (Output)**: Quyết định cuối cùng (Root cause, Refund amount, Actions, Evidences) - chưa cần ghi file.

---

### 👨‍💻 2. Hoàng - Data Context Analysts 1 (Order & Product)
Hoàng phụ trách làm việc với các file CSV liên quan đến Hàng hóa.
* **Module đảm nhiệm**: `Order & Product Agent`.
* **Nhiệm vụ chi tiết**:
  1. **Order & Product Agent**: 
     * Viết hàm đọc `order_items.csv`, `products.csv`, `sellers.csv`.
     * Input: `claimed_order_id`.
     * Output (Return): Object chứa danh sách `item_ids`, `seller_ids`, `product_ids`, `category_names`. Đếm số lượng để check `multi_item_order`, `multi_seller_order`, `multiple_categories`.
* **Đầu vào (Input)**: `claimed_order_id` (được Đăng truyền vào).
* **Đầu ra (Output)**: `OrderPayload` (Dùng class Ngân đã định nghĩa).

---

### 👨‍💻 3. Nam - Data Context Analysts 3 (Payment)
Nam phụ trách làm việc với các file CSV liên quan đến Dòng tiền.
* **Module đảm nhiệm**: `Payment Agent`.
* **Nhiệm vụ chi tiết**:
  1. **Payment Agent**:
     * Viết hàm đọc `order_payments.csv`.
     * Tính tiền: `expected_total_brl` (cộng giá item + ship), so với `payment_total_brl`.
     * Output (Return): Object chứa `difference_brl`, cờ `reconciled` (sai số <= 0.10), cờ `split_payment`, danh sách `payment_types`. Chú ý bắt lỗi `null` nếu đơn không có item.
* **Đầu vào (Input)**: `claimed_order_id` (được Đăng truyền vào).
* **Đầu ra (Output)**: `PaymentPayload` (Dùng class Ngân đã định nghĩa).

---

### 👨‍💻 4. Hiếu - Data Context Analysts 2 (Customer & Delivery)
Hiếu phụ trách làm việc với các file CSV liên quan đến Khách hàng và Thời gian vận chuyển.
* **Module đảm nhiệm**: `Customer Agent` và `Delivery Agent`.
* **Nhiệm vụ chi tiết**:
  1. **Customer Agent**:
     * Viết hàm lấy `customer_unique_id` từ `orders.csv` và `customers.csv`.
     * Quét lịch sử mua hàng để lấy `related_order_ids`.
     * Output (Return): Object chứa danh tính khách và cờ `repeat_customer`.
  2. **Delivery Agent**:
     * Viết hàm xử lý Datetime (Thời gian).
     * Tính `delivery_variance_hours` (giao khách) và `handoff_variance_hours` (seller giao cho vận chuyển).
     * Output (Return): Object chỉ ra seller nào trễ hạn (`late_handoff_seller_ids`), trễ do seller hay do logistics.
* **Đầu vào (Input)**: `claimed_order_id` (được Đăng truyền vào).
* **Đầu ra (Output)**: `CustomerPayload` và `DeliveryPayload` (Dùng class Ngân đã định nghĩa).

---

### 👨‍💻 5. Đăng - Orchestration & Validation (Điều phối & Lắp ráp)
Đăng là người cầm trịch file chạy chính `main.py`, gọi code của Nam, Hoàng, Hiếu, Ngân và kiểm chứng đầu ra.
* **Module đảm nhiệm**: `Coordinator Agent` và `Verifier Agent`.
* **Nhiệm vụ chi tiết**:
  1. **Coordinator Agent (`main.py`)**:
     * Viết vòng lặp đọc 50 file `input/EC_xxx.json`.
     * Gọi hàm của **Hoàng** (lấy Order), **Nam** (lấy Payment) và **Hiếu** (lấy Customer, Delivery).
     * Gom data của Hoàng và Hiếu thành một `AggregatedContext`, đưa cho hàm Policy của **Ngân**.
  2. **Verifier Agent**:
     * Lấy output từ Ngân, chạy script validate (kiểm tra max 5 order_ids, max 3 sellers_ids, null array, làm tròn `round(x, 2)`...).
     * Ghi kết quả cuối cùng ra folder `output/EC_xxx.json`.
     * Ghi log vào `logging/trace.jsonl`.
* **Đầu vào (Input)**: Folder `input/`.
* **Đầu ra (Output)**: Ghi file `output/` chuẩn xác và file `trace.jsonl`.

---

## 🚀 3. Kịch bản khi ghép code (Integration Flow)
Để quá trình ghép code không sinh ra conflict, cả team làm theo thứ tự sau:

1. **Ngày 1 - Ngân đi trước 1 bước**: Ngân tạo file `models.py` định nghĩa tất cả Interface. Push lên Github.
2. **Ngày 2 - Code song song**: 
   * Nam import `models.py`, viết logic xử lý dòng tiền.
   * Hoàng import `models.py`, viết logic xử lý hàng hóa.
   * Hiếu import `models.py`, viết logic xử lý user và datetime.
   * Đăng import `models.py`, viết khung hàm `main.py` (tạo mock data để test luồng ghi file trước).
   * Ngân viết logic Rule engine (EC_POLICY_V2) nhận input từ Model.
3. **Ngày 3 - Lắp ráp tại `main.py` của Đăng**: 
   * Đăng chỉ cần `from order_agent import process_order`, `from policy_agent import evaluate_policy`... và cắm các hàm của 4 bạn kia vào pipeline là hệ thống tự động chạy luột nà!
