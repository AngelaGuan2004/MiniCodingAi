from checkout import calculate_total
from models import Item


def test_free_shipping_boundary():
    items = [
        Item("Keyboard", 60),
        Item("Mouse", 40),
    ]

    # 100 + 8% tax = 108
    assert calculate_total(items) == 108.00


def test_vip_discount_affects_shipping():
    items = [
        Item("Mechanical Keyboard", 110),
    ]

    # VIP: 110 * 0.9 = 99
    # shipping = 12
    # tax = 99 * 0.08 = 7.92
    # total = 118.92
    assert calculate_total(items, is_vip=True) == 118.92


def test_shipping_is_not_taxed():
    items = [
        Item("Headphones", 80),
    ]

    # 80 + 12 shipping + 6.4 tax
    assert calculate_total(items) == 98.40


def test_quantity():
    items = [
        Item("Cable", 25, quantity=4),
    ]

    # subtotal = 100
    # free shipping + 8 tax
    assert calculate_total(items) == 108.00


test_free_shipping_boundary()
test_vip_discount_affects_shipping()
test_shipping_is_not_taxed()
test_quantity()

print("all checkout tests passed")
