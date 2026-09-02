from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    name: str
    price: float
    quantity: int = 1
