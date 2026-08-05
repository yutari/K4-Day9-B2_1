"""Load Olist CSVs một lần duy nhất và dùng chung cho toàn bộ các agents.

Cách dùng (Usage):
    from src.data_store import DataStore
    store = DataStore()
"""
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class DataStore:
    """Class hỗ trợ load toàn bộ các file CSV của Olist.

    Tất cả các cột được đọc dưới dạng str để giữ nguyên định dạng ID gốc.
    Các agent cụ thể sẽ tự chịu trách nhiệm parse số/ngày tháng nếu cần.
    """

    def __init__(self, data_dir: Path = DATA_DIR):
        self.orders = pd.read_csv(
            data_dir / "olist_orders_dataset.csv", dtype=str
        )
        self.customers = pd.read_csv(
            data_dir / "olist_customers_dataset.csv", dtype=str
        )
        self.order_items = pd.read_csv(
            data_dir / "olist_order_items_dataset.csv", dtype=str
        )
        self.order_payments = pd.read_csv(
            data_dir / "olist_order_payments_dataset.csv", dtype=str
        )
        self.products = pd.read_csv(
            data_dir / "olist_products_dataset.csv", dtype=str
        )
        self.sellers = pd.read_csv(
            data_dir / "olist_sellers_dataset.csv", dtype=str
        )
        self.category_translation = pd.read_csv(
            data_dir / "product_category_name_translation.csv", dtype=str
        )

    def get_order_status(self, order_id: str) -> str | None:
        rows = self.orders.loc[self.orders["order_id"] == order_id]
        if rows.empty:
            return None
        return rows.iloc[0]["order_status"]
