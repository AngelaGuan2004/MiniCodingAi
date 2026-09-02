from pricing import (
    subtotal,
    apply_discount,
    shipping_fee,
    calculate_tax,
)


def calculate_total(items, is_vip=False):
    raw_subtotal = subtotal(items)
    discounted = apply_discount(raw_subtotal, is_vip)

    # bug 1:
    # 运费错误地根据折扣前金额判断
    shipping = shipping_fee(raw_subtotal)

    # bug 2:
    # 运费错误地参与了税费计算
    tax = calculate_tax(discounted + shipping)

    total = discounted + shipping + tax
    return round(total, 2)
