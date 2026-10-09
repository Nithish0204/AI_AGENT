"""
Seed Data: Realistic Customers, Orders, and Edge Cases
=======================================================

This generates 20 customers and 40 orders covering EVERY scenario:
- On-time delivery, late delivery, damaged items, wrong items
- Within/outside return window, already refunded, cancelled
- Double charges, high-value orders, VIP customers
- Repeat complainers, address mismatches, fraud patterns

Each scenario maps to specific eval test cases, so we can
systematically test the agent's behavior.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from app.models.database import Customer, Order, Case, init_db_sync


def get_seed_customers() -> list[dict]:
    """20 customers covering every tier and scenario."""
    return [
        # === STANDARD CUSTOMERS ===
        {"id": "CUST-001", "name": "Rahul Sharma", "email": "rahul.sharma@email.com",
         "phone": "+91-9876543210", "tier": "standard", "total_orders": 5, "total_spent": 15000.0,
         "address": "42 MG Road, Bengaluru, Karnataka 560001"},
        {"id": "CUST-002", "name": "Priya Patel", "email": "priya.patel@email.com",
         "phone": "+91-8765432109", "tier": "standard", "total_orders": 3, "total_spent": 8500.0,
         "address": "15 Anna Nagar, Chennai, Tamil Nadu 600040"},
        {"id": "CUST-003", "name": "Anil Kumar", "email": "anil.kumar@email.com",
         "phone": "+91-7654321098", "tier": "standard", "total_orders": 2, "total_spent": 4200.0,
         "address": "78 Jubilee Hills, Hyderabad, Telangana 500033"},
        {"id": "CUST-004", "name": "Sneha Reddy", "email": "sneha.reddy@email.com",
         "phone": "+91-9988776655", "tier": "standard", "total_orders": 8, "total_spent": 22000.0,
         "address": "23 Banjara Hills, Hyderabad, Telangana 500034"},
        {"id": "CUST-005", "name": "Mohammed Farhan", "email": "farhan.m@email.com",
         "phone": "+91-8877665544", "tier": "standard", "total_orders": 1, "total_spent": 1200.0,
         "address": "56 Koramangala, Bengaluru, Karnataka 560034"},
        
        # === PREMIUM CUSTOMERS ===
        {"id": "CUST-006", "name": "Deepa Iyer", "email": "deepa.iyer@email.com",
         "phone": "+91-9123456789", "tier": "premium", "total_orders": 15, "total_spent": 85000.0,
         "address": "101 Powai, Mumbai, Maharashtra 400076"},
        {"id": "CUST-007", "name": "Vikram Singh", "email": "vikram.s@email.com",
         "phone": "+91-8234567890", "tier": "premium", "total_orders": 12, "total_spent": 67000.0,
         "address": "34 Sector 18, Noida, Uttar Pradesh 201301"},
        {"id": "CUST-008", "name": "Lakshmi Narasimhan", "email": "lakshmi.n@email.com",
         "phone": "+91-7345678901", "tier": "premium", "total_orders": 20, "total_spent": 120000.0,
         "address": "67 T Nagar, Chennai, Tamil Nadu 600017"},
        {"id": "CUST-009", "name": "Arjun Kapoor", "email": "arjun.k@email.com",
         "phone": "+91-6456789012", "tier": "premium", "total_orders": 10, "total_spent": 55000.0,
         "address": "89 Indiranagar, Bengaluru, Karnataka 560038"},
        {"id": "CUST-010", "name": "Kavitha Sundaram", "email": "kavitha.s@email.com",
         "phone": "+91-9567890123", "tier": "premium", "total_orders": 18, "total_spent": 95000.0,
         "address": "12 Adyar, Chennai, Tamil Nadu 600020"},
        
        # === VIP CUSTOMERS ===
        {"id": "CUST-011", "name": "Rajesh Gupta", "email": "rajesh.gupta@corp.com",
         "phone": "+91-9000000001", "tier": "vip", "total_orders": 50, "total_spent": 500000.0,
         "address": "1 Lutyens Zone, New Delhi 110001"},
        {"id": "CUST-012", "name": "Anita Desai", "email": "anita.desai@corp.com",
         "phone": "+91-9000000002", "tier": "vip", "total_orders": 35, "total_spent": 350000.0,
         "address": "5 Malabar Hill, Mumbai, Maharashtra 400006"},
        {"id": "CUST-013", "name": "Srinivas Rao", "email": "srinivas.rao@corp.com",
         "phone": "+91-9000000003", "tier": "vip", "total_orders": 45, "total_spent": 450000.0,
         "address": "22 Road No 10, Jubilee Hills, Hyderabad, Telangana 500033"},
        
        # === EDGE CASE CUSTOMERS ===
        # Repeat complainer / potential fraud
        {"id": "CUST-014", "name": "Ravi Teja", "email": "ravi.teja@email.com",
         "phone": "+91-8111222333", "tier": "standard", "total_orders": 6, "total_spent": 18000.0,
         "address": "45 Madhapur, Hyderabad, Telangana 500081"},
        # New customer, first order
        {"id": "CUST-015", "name": "Meera Joshi", "email": "meera.j@email.com",
         "phone": "+91-7222333444", "tier": "standard", "total_orders": 1, "total_spent": 2500.0,
         "address": "78 Koregaon Park, Pune, Maharashtra 411001"},
        # Address mismatch customer (fraud signal)
        {"id": "CUST-016", "name": "Suresh Babu", "email": "suresh.b@email.com",
         "phone": "+91-6333444555", "tier": "standard", "total_orders": 4, "total_spent": 12000.0,
         "address": "90 Whitefield, Bengaluru, Karnataka 560066"},
        # Multilingual customer (Telugu)
        {"id": "CUST-017", "name": "Venkata Ramana", "email": "venkat.r@email.com",
         "phone": "+91-9444555666", "tier": "standard", "total_orders": 7, "total_spent": 21000.0,
         "address": "33 Kukatpally, Hyderabad, Telangana 500072"},
        # Multilingual customer (Hindi)
        {"id": "CUST-018", "name": "Pooja Mishra", "email": "pooja.m@email.com",
         "phone": "+91-8555666777", "tier": "standard", "total_orders": 4, "total_spent": 11000.0,
         "address": "56 Gomti Nagar, Lucknow, Uttar Pradesh 226010"},
        # Customer with many past refunds (fraud pattern)
        {"id": "CUST-019", "name": "Kiran Deshmukh", "email": "kiran.d@email.com",
         "phone": "+91-7666777888", "tier": "standard", "total_orders": 10, "total_spent": 35000.0,
         "address": "12 Hinjewadi, Pune, Maharashtra 411057"},
        # VIP with high-value issue
        {"id": "CUST-020", "name": "Nandini Krishnan", "email": "nandini.k@corp.com",
         "phone": "+91-9777888999", "tier": "vip", "total_orders": 30, "total_spent": 280000.0,
         "address": "8 Boat Club Road, Chennai, Tamil Nadu 600028"},
    ]


def get_seed_orders() -> list[dict]:
    """40 orders covering every scenario the agent needs to handle."""
    now = datetime.now(timezone.utc)
    
    return [
        # === ON-TIME DELIVERIES (happy path) ===
        {"id": "ORD-1001", "customer_id": "CUST-001", "product_name": "Wireless Earbuds Pro",
         "product_category": "electronics", "quantity": 1, "amount": 2499.0,
         "status": "delivered", "ordered_at": now - timedelta(days=10),
         "shipped_at": now - timedelta(days=8), "delivered_at": now - timedelta(days=5),
         "expected_delivery": now - timedelta(days=4), "carrier": "BlueDart",
         "tracking_number": "BD1234567890", "shipping_address": "42 MG Road, Bengaluru"},
        
        {"id": "ORD-1002", "customer_id": "CUST-002", "product_name": "Cotton Kurta Set",
         "product_category": "clothing", "quantity": 2, "amount": 1899.0,
         "status": "delivered", "ordered_at": now - timedelta(days=15),
         "shipped_at": now - timedelta(days=13), "delivered_at": now - timedelta(days=10),
         "expected_delivery": now - timedelta(days=9), "carrier": "Delhivery",
         "tracking_number": "DL9876543210", "shipping_address": "15 Anna Nagar, Chennai"},
        
        # === LATE DELIVERIES ===
        {"id": "ORD-1003", "customer_id": "CUST-003", "product_name": "Smart Watch Ultra",
         "product_category": "electronics", "quantity": 1, "amount": 8999.0,
         "status": "delivered", "ordered_at": now - timedelta(days=20),
         "shipped_at": now - timedelta(days=18), "delivered_at": now - timedelta(days=7),
         "expected_delivery": now - timedelta(days=14), "carrier": "DTDC",
         "tracking_number": "DT1111222233", "shipping_address": "78 Jubilee Hills, Hyderabad",
         "notes": "Delayed by 7 days due to logistics issue"},
        
        {"id": "ORD-1004", "customer_id": "CUST-004", "product_name": "Yoga Mat Premium",
         "product_category": "fitness", "quantity": 1, "amount": 1599.0,
         "status": "shipped", "ordered_at": now - timedelta(days=12),
         "shipped_at": now - timedelta(days=10), "delivered_at": None,
         "expected_delivery": now - timedelta(days=5), "carrier": "Ecom Express",
         "tracking_number": "EE4444555566",
         "shipping_address": "23 Banjara Hills, Hyderabad",
         "notes": "Still in transit, 5 days past expected delivery"},
        
        # === DAMAGED ITEMS ===
        {"id": "ORD-1005", "customer_id": "CUST-001", "product_name": "Ceramic Coffee Mug Set",
         "product_category": "home", "quantity": 4, "amount": 1299.0,
         "status": "delivered", "ordered_at": now - timedelta(days=8),
         "shipped_at": now - timedelta(days=6), "delivered_at": now - timedelta(days=3),
         "expected_delivery": now - timedelta(days=3), "carrier": "BlueDart",
         "tracking_number": "BD2222333344", "shipping_address": "42 MG Road, Bengaluru",
         "notes": "Customer reported 2 of 4 mugs arrived broken"},
        
        {"id": "ORD-1006", "customer_id": "CUST-006", "product_name": "Premium Leather Laptop Bag",
         "product_category": "accessories", "quantity": 1, "amount": 4599.0,
         "status": "delivered", "ordered_at": now - timedelta(days=5),
         "shipped_at": now - timedelta(days=3), "delivered_at": now - timedelta(days=1),
         "expected_delivery": now - timedelta(days=1), "carrier": "FedEx",
         "tracking_number": "FX5555666677", "shipping_address": "101 Powai, Mumbai",
         "notes": "Zipper broken on arrival"},
        
        # === WRONG ITEMS ===
        {"id": "ORD-1007", "customer_id": "CUST-007", "product_name": "Running Shoes Size 10",
         "product_category": "footwear", "quantity": 1, "amount": 3999.0,
         "status": "delivered", "ordered_at": now - timedelta(days=7),
         "shipped_at": now - timedelta(days=5), "delivered_at": now - timedelta(days=2),
         "expected_delivery": now - timedelta(days=2), "carrier": "BlueDart",
         "tracking_number": "BD3333444455", "shipping_address": "34 Sector 18, Noida",
         "notes": "Customer received Size 8 instead of Size 10"},
        
        # === OUTSIDE RETURN WINDOW ===
        {"id": "ORD-1008", "customer_id": "CUST-008", "product_name": "Silk Saree Collection",
         "product_category": "clothing", "quantity": 1, "amount": 12999.0,
         "status": "delivered", "ordered_at": now - timedelta(days=45),
         "shipped_at": now - timedelta(days=43), "delivered_at": now - timedelta(days=40),
         "expected_delivery": now - timedelta(days=39), "carrier": "Delhivery",
         "tracking_number": "DL6666777788", "shipping_address": "67 T Nagar, Chennai",
         "notes": "30-day return window expired"},
        
        # === CANCELLED ORDERS ===
        {"id": "ORD-1009", "customer_id": "CUST-009", "product_name": "Bluetooth Speaker",
         "product_category": "electronics", "quantity": 1, "amount": 2999.0,
         "status": "cancelled", "ordered_at": now - timedelta(days=3),
         "shipped_at": None, "delivered_at": None,
         "expected_delivery": now + timedelta(days=4), "carrier": "",
         "tracking_number": "", "shipping_address": "89 Indiranagar, Bengaluru",
         "notes": "Cancelled by customer before shipping"},
        
        {"id": "ORD-1010", "customer_id": "CUST-010", "product_name": "Gold Necklace",
         "product_category": "jewelry", "quantity": 1, "amount": 25999.0,
         "status": "cancelled", "ordered_at": now - timedelta(days=2),
         "shipped_at": None, "delivered_at": None,
         "expected_delivery": now + timedelta(days=5), "carrier": "",
         "tracking_number": "", "shipping_address": "12 Adyar, Chennai",
         "notes": "Cancelled but payment already charged - DOUBLE CHARGE SCENARIO"},
        
        # === DOUBLE CHARGE ===
        {"id": "ORD-1011", "customer_id": "CUST-010", "product_name": "Gold Necklace (duplicate charge)",
         "product_category": "jewelry", "quantity": 1, "amount": 25999.0,
         "status": "payment_error", "ordered_at": now - timedelta(days=2),
         "shipped_at": None, "delivered_at": None,
         "expected_delivery": None, "carrier": "",
         "tracking_number": "", "shipping_address": "12 Adyar, Chennai",
         "notes": "DUPLICATE CHARGE - same amount charged twice for ORD-1010"},
        
        # === HIGH-VALUE ORDERS ===
        {"id": "ORD-1012", "customer_id": "CUST-011", "product_name": "MacBook Pro 16-inch",
         "product_category": "electronics", "quantity": 1, "amount": 249999.0,
         "status": "delivered", "ordered_at": now - timedelta(days=6),
         "shipped_at": now - timedelta(days=4), "delivered_at": now - timedelta(days=1),
         "expected_delivery": now - timedelta(days=1), "carrier": "FedEx",
         "tracking_number": "FX8888999900", "shipping_address": "1 Lutyens Zone, New Delhi",
         "notes": "High-value VIP order"},
        
        {"id": "ORD-1013", "customer_id": "CUST-012", "product_name": "Diamond Earrings",
         "product_category": "jewelry", "quantity": 1, "amount": 89999.0,
         "status": "shipped", "ordered_at": now - timedelta(days=3),
         "shipped_at": now - timedelta(days=1), "delivered_at": None,
         "expected_delivery": now + timedelta(days=2), "carrier": "FedEx",
         "tracking_number": "FX1010111213", "shipping_address": "5 Malabar Hill, Mumbai",
         "notes": "VIP order, insured shipping"},
        
        # === ALREADY REFUNDED ===
        {"id": "ORD-1014", "customer_id": "CUST-004", "product_name": "Fitness Tracker Band",
         "product_category": "electronics", "quantity": 1, "amount": 1999.0,
         "status": "delivered", "ordered_at": now - timedelta(days=25),
         "shipped_at": now - timedelta(days=23), "delivered_at": now - timedelta(days=20),
         "expected_delivery": now - timedelta(days=19), "carrier": "Delhivery",
         "tracking_number": "DL1414151516", "shipping_address": "23 Banjara Hills, Hyderabad",
         "is_refunded": True, "refund_amount": 1999.0,
         "refund_date": now - timedelta(days=18),
         "notes": "Full refund processed - defective product"},
        
        # === REPEAT COMPLAINER / FRAUD PATTERN ===
        {"id": "ORD-1015", "customer_id": "CUST-014", "product_name": "Wireless Mouse",
         "product_category": "electronics", "quantity": 1, "amount": 899.0,
         "status": "delivered", "ordered_at": now - timedelta(days=30),
         "shipped_at": now - timedelta(days=28), "delivered_at": now - timedelta(days=25),
         "expected_delivery": now - timedelta(days=24), "carrier": "DTDC",
         "tracking_number": "DT1515161617",
         "shipping_address": "45 Madhapur, Hyderabad",
         "is_refunded": True, "refund_amount": 899.0,
         "refund_date": now - timedelta(days=23),
         "notes": "Claimed item not received - refund processed"},
        
        {"id": "ORD-1016", "customer_id": "CUST-014", "product_name": "USB Hub 4-Port",
         "product_category": "electronics", "quantity": 1, "amount": 699.0,
         "status": "delivered", "ordered_at": now - timedelta(days=20),
         "shipped_at": now - timedelta(days=18), "delivered_at": now - timedelta(days=15),
         "expected_delivery": now - timedelta(days=14), "carrier": "DTDC",
         "tracking_number": "DT1616171718",
         "shipping_address": "45 Madhapur, Hyderabad",
         "is_refunded": True, "refund_amount": 699.0,
         "refund_date": now - timedelta(days=13),
         "notes": "Claimed item defective - refund processed"},
        
        {"id": "ORD-1017", "customer_id": "CUST-014", "product_name": "Laptop Stand Adjustable",
         "product_category": "accessories", "quantity": 1, "amount": 1499.0,
         "status": "delivered", "ordered_at": now - timedelta(days=10),
         "shipped_at": now - timedelta(days=8), "delivered_at": now - timedelta(days=5),
         "expected_delivery": now - timedelta(days=5), "carrier": "DTDC",
         "tracking_number": "DT1717181819",
         "shipping_address": "45 Madhapur, Hyderabad",
         "is_refunded": True, "refund_amount": 1499.0,
         "refund_date": now - timedelta(days=3),
         "notes": "Claimed item damaged - 3rd refund in 30 days - FRAUD FLAG"},
        
        {"id": "ORD-1018", "customer_id": "CUST-014", "product_name": "Mechanical Keyboard",
         "product_category": "electronics", "quantity": 1, "amount": 3499.0,
         "status": "delivered", "ordered_at": now - timedelta(days=5),
         "shipped_at": now - timedelta(days=3), "delivered_at": now - timedelta(days=1),
         "expected_delivery": now - timedelta(days=1), "carrier": "BlueDart",
         "tracking_number": "BD1818192020",
         "shipping_address": "45 Madhapur, Hyderabad",
         "notes": "Latest order - if refund requested, should trigger fraud alert"},
        
        # === ADDRESS MISMATCH ===
        {"id": "ORD-1019", "customer_id": "CUST-016", "product_name": "Tablet 10-inch",
         "product_category": "electronics", "quantity": 1, "amount": 15999.0,
         "status": "delivered", "ordered_at": now - timedelta(days=7),
         "shipped_at": now - timedelta(days=5), "delivered_at": now - timedelta(days=2),
         "expected_delivery": now - timedelta(days=2), "carrier": "Delhivery",
         "tracking_number": "DL1919202021",
         "shipping_address": "123 Different Address, Mumbai, Maharashtra 400001",
         "notes": "Shipping address differs from customer profile address - ADDRESS MISMATCH"},
        
        # === WARRANTY CLAIMS ===
        {"id": "ORD-1020", "customer_id": "CUST-003", "product_name": "Electric Kettle 1.5L",
         "product_category": "appliances", "quantity": 1, "amount": 1899.0,
         "status": "delivered", "ordered_at": now - timedelta(days=200),
         "shipped_at": now - timedelta(days=198), "delivered_at": now - timedelta(days=195),
         "expected_delivery": now - timedelta(days=194), "carrier": "BlueDart",
         "tracking_number": "BD2020212122",
         "shipping_address": "78 Jubilee Hills, Hyderabad",
         "notes": "Delivered 6+ months ago - under 1-year warranty for appliances"},
        
        # === VIP HIGH VALUE ===
        {"id": "ORD-1021", "customer_id": "CUST-013", "product_name": "Custom Suit Set",
         "product_category": "clothing", "quantity": 1, "amount": 45999.0,
         "status": "delivered", "ordered_at": now - timedelta(days=14),
         "shipped_at": now - timedelta(days=12), "delivered_at": now - timedelta(days=8),
         "expected_delivery": now - timedelta(days=7), "carrier": "FedEx",
         "tracking_number": "FX2121222324",
         "shipping_address": "22 Road No 10, Jubilee Hills, Hyderabad",
         "notes": "VIP order - late by 1 day"},
        
        # === NEW CUSTOMER FIRST ORDER ===
        {"id": "ORD-1022", "customer_id": "CUST-015", "product_name": "Aromatherapy Diffuser",
         "product_category": "home", "quantity": 1, "amount": 2499.0,
         "status": "delivered", "ordered_at": now - timedelta(days=6),
         "shipped_at": now - timedelta(days=4), "delivered_at": now - timedelta(days=2),
         "expected_delivery": now - timedelta(days=2), "carrier": "DTDC",
         "tracking_number": "DT2222232425",
         "shipping_address": "78 Koregaon Park, Pune",
         "notes": "First order - product has defect"},
        
        # === MULTILINGUAL CUSTOMER ORDERS ===
        {"id": "ORD-1023", "customer_id": "CUST-017", "product_name": "Stainless Steel Lunch Box",
         "product_category": "home", "quantity": 2, "amount": 799.0,
         "status": "shipped", "ordered_at": now - timedelta(days=8),
         "shipped_at": now - timedelta(days=6), "delivered_at": None,
         "expected_delivery": now - timedelta(days=2), "carrier": "DTDC",
         "tracking_number": "DT2323242526",
         "shipping_address": "33 Kukatpally, Hyderabad",
         "notes": "Telugu-speaking customer, order delayed"},
        
        {"id": "ORD-1024", "customer_id": "CUST-018", "product_name": "Pressure Cooker 5L",
         "product_category": "appliances", "quantity": 1, "amount": 2199.0,
         "status": "delivered", "ordered_at": now - timedelta(days=10),
         "shipped_at": now - timedelta(days=8), "delivered_at": now - timedelta(days=4),
         "expected_delivery": now - timedelta(days=5), "carrier": "Delhivery",
         "tracking_number": "DL2424252627",
         "shipping_address": "56 Gomti Nagar, Lucknow",
         "notes": "Hindi-speaking customer, delivered 1 day late"},
        
        # === PAYMENT FAILURES ===
        {"id": "ORD-1025", "customer_id": "CUST-005", "product_name": "Bluetooth Headphones",
         "product_category": "electronics", "quantity": 1, "amount": 1799.0,
         "status": "payment_failed", "ordered_at": now - timedelta(days=1),
         "shipped_at": None, "delivered_at": None,
         "expected_delivery": None, "carrier": "",
         "tracking_number": "",
         "shipping_address": "56 Koramangala, Bengaluru",
         "notes": "Payment failed - amount deducted but order not confirmed"},
        
        # === ADDITIONAL ORDERS FOR VARIETY ===
        {"id": "ORD-1026", "customer_id": "CUST-006", "product_name": "Designer Handbag",
         "product_category": "accessories", "quantity": 1, "amount": 7999.0,
         "status": "delivered", "ordered_at": now - timedelta(days=12),
         "shipped_at": now - timedelta(days=10), "delivered_at": now - timedelta(days=7),
         "expected_delivery": now - timedelta(days=6), "carrier": "FedEx",
         "tracking_number": "FX2626272829",
         "shipping_address": "101 Powai, Mumbai"},
        
        {"id": "ORD-1027", "customer_id": "CUST-007", "product_name": "Camping Tent 4-Person",
         "product_category": "outdoors", "quantity": 1, "amount": 5499.0,
         "status": "delivered", "ordered_at": now - timedelta(days=18),
         "shipped_at": now - timedelta(days=16), "delivered_at": now - timedelta(days=11),
         "expected_delivery": now - timedelta(days=12), "carrier": "Delhivery",
         "tracking_number": "DL2727282930",
         "shipping_address": "34 Sector 18, Noida",
         "notes": "Delivered 1 day late"},
        
        {"id": "ORD-1028", "customer_id": "CUST-009", "product_name": "Office Chair Ergonomic",
         "product_category": "furniture", "quantity": 1, "amount": 12999.0,
         "status": "delivered", "ordered_at": now - timedelta(days=22),
         "shipped_at": now - timedelta(days=20), "delivered_at": now - timedelta(days=15),
         "expected_delivery": now - timedelta(days=16), "carrier": "Delhivery",
         "tracking_number": "DL2828293031",
         "shipping_address": "89 Indiranagar, Bengaluru",
         "notes": "Within return window"},
        
        {"id": "ORD-1029", "customer_id": "CUST-002", "product_name": "Air Purifier HEPA",
         "product_category": "appliances", "quantity": 1, "amount": 8999.0,
         "status": "shipped", "ordered_at": now - timedelta(days=4),
         "shipped_at": now - timedelta(days=2), "delivered_at": None,
         "expected_delivery": now + timedelta(days=1), "carrier": "BlueDart",
         "tracking_number": "BD2929303132",
         "shipping_address": "15 Anna Nagar, Chennai",
         "notes": "In transit, on schedule"},
        
        {"id": "ORD-1030", "customer_id": "CUST-011", "product_name": "Luxury Watch",
         "product_category": "accessories", "quantity": 1, "amount": 150000.0,
         "status": "delivered", "ordered_at": now - timedelta(days=9),
         "shipped_at": now - timedelta(days=7), "delivered_at": now - timedelta(days=4),
         "expected_delivery": now - timedelta(days=4), "carrier": "FedEx",
         "tracking_number": "FX3030313233",
         "shipping_address": "1 Lutyens Zone, New Delhi",
         "notes": "VIP high-value order"},
        
        # === MORE EDGE CASES ===
        {"id": "ORD-1031", "customer_id": "CUST-019", "product_name": "Wireless Charger",
         "product_category": "electronics", "quantity": 1, "amount": 999.0,
         "status": "delivered", "ordered_at": now - timedelta(days=28),
         "shipped_at": now - timedelta(days=26), "delivered_at": now - timedelta(days=23),
         "expected_delivery": now - timedelta(days=22), "carrier": "DTDC",
         "tracking_number": "DT3131323334",
         "shipping_address": "12 Hinjewadi, Pune",
         "is_refunded": True, "refund_amount": 999.0,
         "refund_date": now - timedelta(days=20),
         "notes": "Refunded - claimed not working"},
        
        {"id": "ORD-1032", "customer_id": "CUST-019", "product_name": "Phone Case Premium",
         "product_category": "accessories", "quantity": 1, "amount": 499.0,
         "status": "delivered", "ordered_at": now - timedelta(days=21),
         "shipped_at": now - timedelta(days=19), "delivered_at": now - timedelta(days=16),
         "expected_delivery": now - timedelta(days=15), "carrier": "DTDC",
         "tracking_number": "DT3232333435",
         "shipping_address": "12 Hinjewadi, Pune",
         "is_refunded": True, "refund_amount": 499.0,
         "refund_date": now - timedelta(days=14),
         "notes": "Refunded - claimed wrong color"},
        
        {"id": "ORD-1033", "customer_id": "CUST-019", "product_name": "Earphone Wired",
         "product_category": "electronics", "quantity": 1, "amount": 599.0,
         "status": "delivered", "ordered_at": now - timedelta(days=14),
         "shipped_at": now - timedelta(days=12), "delivered_at": now - timedelta(days=9),
         "expected_delivery": now - timedelta(days=8), "carrier": "DTDC",
         "tracking_number": "DT3333343536",
         "shipping_address": "12 Hinjewadi, Pune",
         "is_refunded": True, "refund_amount": 599.0,
         "refund_date": now - timedelta(days=7),
         "notes": "Refunded - claimed defective. 3rd refund in 30 days - FRAUD PATTERN"},
        
        {"id": "ORD-1034", "customer_id": "CUST-019", "product_name": "Power Bank 20000mAh",
         "product_category": "electronics", "quantity": 1, "amount": 1299.0,
         "status": "delivered", "ordered_at": now - timedelta(days=5),
         "shipped_at": now - timedelta(days=3), "delivered_at": now - timedelta(days=1),
         "expected_delivery": now - timedelta(days=1), "carrier": "DTDC",
         "tracking_number": "DT3434353637",
         "shipping_address": "12 Hinjewadi, Pune",
         "notes": "Latest order - if refund requested, definite fraud pattern"},
        
        # === VIP HIGH VALUE ISSUE ===
        {"id": "ORD-1035", "customer_id": "CUST-020", "product_name": "Designer Saree Collection",
         "product_category": "clothing", "quantity": 3, "amount": 75000.0,
         "status": "delivered", "ordered_at": now - timedelta(days=8),
         "shipped_at": now - timedelta(days=6), "delivered_at": now - timedelta(days=3),
         "expected_delivery": now - timedelta(days=3), "carrier": "FedEx",
         "tracking_number": "FX3535363738",
         "shipping_address": "8 Boat Club Road, Chennai",
         "notes": "VIP order - one saree has wrong color"},
        
        # === ORDERS IN PROCESSING ===
        {"id": "ORD-1036", "customer_id": "CUST-003", "product_name": "Air Fryer Digital",
         "product_category": "appliances", "quantity": 1, "amount": 4999.0,
         "status": "processing", "ordered_at": now - timedelta(hours=6),
         "shipped_at": None, "delivered_at": None,
         "expected_delivery": now + timedelta(days=5), "carrier": "",
         "tracking_number": "",
         "shipping_address": "78 Jubilee Hills, Hyderabad",
         "notes": "Fresh order, not yet shipped"},
        
        {"id": "ORD-1037", "customer_id": "CUST-001", "product_name": "Book: AI Engineering",
         "product_category": "books", "quantity": 1, "amount": 599.0,
         "status": "processing", "ordered_at": now - timedelta(hours=2),
         "shipped_at": None, "delivered_at": None,
         "expected_delivery": now + timedelta(days=3), "carrier": "",
         "tracking_number": "",
         "shipping_address": "42 MG Road, Bengaluru"},
        
        # === INTERNATIONAL SHIPPING ===
        {"id": "ORD-1038", "customer_id": "CUST-012", "product_name": "Handloom Shawl Collection",
         "product_category": "clothing", "quantity": 5, "amount": 35000.0,
         "status": "shipped", "ordered_at": now - timedelta(days=5),
         "shipped_at": now - timedelta(days=3), "delivered_at": None,
         "expected_delivery": now + timedelta(days=4), "carrier": "DHL",
         "tracking_number": "DHL3838394041",
         "shipping_address": "5 Malabar Hill, Mumbai",
         "notes": "Premium gift packaging requested"},
        
        # === REPLACEMENT ALREADY IN PROGRESS ===
        {"id": "ORD-1039", "customer_id": "CUST-008", "product_name": "Kitchen Mixer Grinder",
         "product_category": "appliances", "quantity": 1, "amount": 3499.0,
         "status": "delivered", "ordered_at": now - timedelta(days=15),
         "shipped_at": now - timedelta(days=13), "delivered_at": now - timedelta(days=10),
         "expected_delivery": now - timedelta(days=9), "carrier": "Delhivery",
         "tracking_number": "DL3939404142",
         "shipping_address": "67 T Nagar, Chennai",
         "notes": "Motor defective - replacement already shipped as ORD-1040"},
        
        {"id": "ORD-1040", "customer_id": "CUST-008", "product_name": "Kitchen Mixer Grinder (Replacement)",
         "product_category": "appliances", "quantity": 1, "amount": 0.0,
         "status": "shipped", "ordered_at": now - timedelta(days=5),
         "shipped_at": now - timedelta(days=3), "delivered_at": None,
         "expected_delivery": now + timedelta(days=1), "carrier": "Delhivery",
         "tracking_number": "DL4040414243",
         "shipping_address": "67 T Nagar, Chennai",
         "notes": "Replacement for ORD-1039, no charge"},
    ]


def seed_database():
    """Insert all seed data into the database."""
    # Ensure data directory exists
    os.makedirs("./data", exist_ok=True)
    
    session = init_db_sync()
    
    try:
        # Check if already seeded
        existing = session.query(Customer).first()
        if existing:
            print("⚡ Database already seeded, skipping...")
            return
        
        # Insert customers
        customers = get_seed_customers()
        for c in customers:
            session.add(Customer(**c))
        print(f"✅ Inserted {len(customers)} customers")
        
        # Insert orders
        orders = get_seed_orders()
        for o in orders:
            session.add(Order(**o))
        print(f"✅ Inserted {len(orders)} orders")
        
        session.commit()
        print("🎉 Database seeded successfully!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error seeding database: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
