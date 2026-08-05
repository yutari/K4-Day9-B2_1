from src.order_agent import process_order_and_product
from src.payment_agent import process_payment

ORDER_ID = input("Order ID: ")

order = process_order_and_product(ORDER_ID)

print("\n===== ORDER =====")
print(order.model_dump())

expected = float(input("\nExpected Total BRL: "))

payment = process_payment(
    ORDER_ID,
    expected
)

print("\n===== PAYMENT =====")
print(payment.model_dump())