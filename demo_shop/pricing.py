VIP_DISCOUNT = 0.10
TAX_RATE = 0.08
SHIPPING_FEE = 12.0
FREE_SHIPPING_THRESHOLD = 100.0


def subtotal(items):
    return sum(item.price * item.quantity for item in items)


def apply_discount(amount, is_vip):
    if is_vip:
        return amount * (1 - VIP_DISCOUNT)
    return amount


def shipping_fee(amount_after_discount):
    # bug: 恰好 100 元本应免运费
    if amount_after_discount > FREE_SHIPPING_THRESHOLD:
        return 0.0
    return SHIPPING_FEE


def calculate_tax(amount_after_discount):
    return amount_after_discount * TAX_RATE
