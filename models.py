import json
import time
from abc import abstractmethod
from sqlite3 import Row
from typing import List, Optional, Tuple

from pydantic import BaseModel

from lnbits.utils.exchange_rates import btc_price, fiat_amount_as_satoshis

from .helpers import (
    decrypt_message,
    encrypt_message,
    get_shared_secret,
    sign_message_hash,
)
from .nostr.event import NostrEvent

######################################## NOSTR ########################################


class Nostrable:
    @abstractmethod
    def to_nostr_event(self, pubkey: str) -> NostrEvent:
        pass

    @abstractmethod
    def to_nostr_delete_event(self, pubkey: str) -> NostrEvent:
        pass


######################################## MERCHANT ########################################


class MerchantProfile(BaseModel):
    name: Optional[str]
    about: Optional[str]
    picture: Optional[str]


class MerchantConfig(MerchantProfile):
    event_id: Optional[str]
    sync_from_nostr = False


class PartialMerchant(BaseModel):
    private_key: str
    public_key: str
    config: MerchantConfig = MerchantConfig()


class Merchant(PartialMerchant, Nostrable):
    id: str

    def sign_hash(self, hash: bytes) -> str:
        return sign_message_hash(self.private_key, hash)

    def decrypt_message(self, encrypted_message: str, public_key: str) -> str:
        encryption_key = get_shared_secret(self.private_key, public_key)
        return decrypt_message(encrypted_message, encryption_key)

    def encrypt_message(self, clear_text_message: str, public_key: str) -> str:
        encryption_key = get_shared_secret(self.private_key, public_key)
        return encrypt_message(clear_text_message, encryption_key)

    def build_dm_event(self, message: str, to_pubkey: str) -> NostrEvent:
        content = self.encrypt_message(message, to_pubkey)
        event = NostrEvent(
            pubkey=self.public_key,
            created_at=round(time.time()),
            kind=4,
            tags=[["p", to_pubkey]],
            content=content,
        )
        event.id = event.event_id
        event.sig = self.sign_hash(bytes.fromhex(event.id))

        return event

    @classmethod
    def from_row(cls, row: Row) -> "Merchant":
        merchant = cls(**dict(row))
        merchant.config = MerchantConfig(**json.loads(row["meta"]))
        return merchant

    def to_nostr_event(self, pubkey: str) -> NostrEvent:
        content = {
            "name": self.config.name,
            "about": self.config.about,
            "picture": self.config.picture,
        }
        event = NostrEvent(
            pubkey=pubkey,
            created_at=round(time.time()),
            kind=0,
            tags=[],
            content=json.dumps(content, separators=(",", ":"), ensure_ascii=False),
        )
        event.id = event.event_id

        return event

    def to_nostr_delete_event(self, pubkey: str) -> NostrEvent:
        content = {
            "name": f"{self.config.name} (deleted)",
            "about": "Merchant Deleted",
            "picture": "",
        }
        delete_event = NostrEvent(
            pubkey=pubkey,
            created_at=round(time.time()),
            kind=5,
            tags=[],
            content=json.dumps(content, separators=(",", ":"), ensure_ascii=False),
        )
        delete_event.id = delete_event.event_id

        return delete_event


######################################## ZONES ########################################
class PartialZone(BaseModel):
    name: Optional[str]
    currency: str
    cost: float
    countries: List[str] = []


class Zone(PartialZone):
    id: str

    @classmethod
    def from_row(cls, row: Row) -> "Zone":
        zone = cls(**dict(row))
        zone.countries = json.loads(row["regions"])
        return zone


######################################## STALLS ########################################


class StallConfig(BaseModel):
    """Last published nostr event id for this Stall"""

    event_id: Optional[str]
    image_url: Optional[str]
    description: Optional[str]


class PartialStall(BaseModel):
    wallet: str
    name: str
    currency: str = "sat"
    shipping_zones: List[Zone] = []
    config: StallConfig = StallConfig()

    def validate_stall(self):
        for z in self.shipping_zones:
            if z.currency != self.currency:
                raise ValueError(
                    f"Sipping zone '{z.name}' has different currency than stall."
                )


class Stall(PartialStall, Nostrable):
    id: str

    def to_nostr_event(self, pubkey: str) -> NostrEvent:
        content = {
            "id": self.id,
            "name": self.name,
            "description": self.config.description,
            "currency": self.currency,
            "shipping": [dict(z) for z in self.shipping_zones],
        }
        event = NostrEvent(
            pubkey=pubkey,
            created_at=round(time.time()),
            kind=30017,
            tags=[["d", self.id]],
            content=json.dumps(content, separators=(",", ":"), ensure_ascii=False),
        )
        event.id = event.event_id

        return event

    def to_nostr_delete_event(self, pubkey: str) -> NostrEvent:
        delete_event = NostrEvent(
            pubkey=pubkey,
            created_at=round(time.time()),
            kind=5,
            tags=[["e", self.config.event_id]],
            content=f"Stall '{self.name}' deleted",
        )
        delete_event.id = delete_event.event_id

        return delete_event

    @classmethod
    def from_row(cls, row: Row) -> "Stall":
        stall = cls(**dict(row))
        stall.config = StallConfig(**json.loads(row["meta"]))
        stall.shipping_zones = [Zone(**z) for z in json.loads(row["zones"])]
        return stall


######################################## STALLS ########################################


class ProductConfig(BaseModel):
    event_id: Optional[str]
    description: Optional[str]
    currency: Optional[str]


class PartialProduct(BaseModel):
    stall_id: str
    name: str
    categories: List[str] = []
    images: List[str] = []
    price: float
    quantity: int
    config: ProductConfig = ProductConfig()


class Product(PartialProduct, Nostrable):
    id: str

    def to_nostr_event(self, pubkey: str) -> NostrEvent:
        content = {
            "id": self.id,
            "stall_id": self.stall_id,
            "name": self.name,
            "description": self.config.description,
            "images": self.images,
            "currency": self.config.currency,
            "price": self.price,
            "quantity": self.quantity,
        }
        categories = [["t", tag] for tag in self.categories]

        event = NostrEvent(
            pubkey=pubkey,
            created_at=round(time.time()),
            kind=30018,
            tags=[["d", self.id]] + categories,
            content=json.dumps(content, separators=(",", ":"), ensure_ascii=False),
        )
        event.id = event.event_id

        return event

    def to_nostr_delete_event(self, pubkey: str) -> NostrEvent:
        delete_event = NostrEvent(
            pubkey=pubkey,
            created_at=round(time.time()),
            kind=5,
            tags=[["e", self.config.event_id]],
            content=f"Product '{self.name}' deleted",
        )
        delete_event.id = delete_event.event_id

        return delete_event

    @classmethod
    def from_row(cls, row: Row) -> "Product":
        product = cls(**dict(row))
        product.config = ProductConfig(**json.loads(row["meta"]))
        product.images = json.loads(row["image_urls"]) if "image_urls" in row else []
        product.categories = json.loads(row["category_list"])
        return product


class ProductOverview(BaseModel):
    id: str
    name: str
    price: float


######################################## ORDERS ########################################


class OrderItem(BaseModel):
    product_id: str
    quantity: int


class OrderContact(BaseModel):
    nostr: Optional[str]
    phone: Optional[str]
    email: Optional[str]


class OrderExtra(BaseModel):
    products: List[ProductOverview]
    currency: str
    btc_price: str
    shipping_cost: float = 0
    shipping_cost_sat: float = 0

    @classmethod
    async def from_products(cls, products: List[Product]):
        currency = products[0].config.currency
        exchange_rate = (
            (await btc_price(currency)) if currency and currency != "sat" else 1
        )
        return OrderExtra(products=products, currency=currency, btc_price=exchange_rate)


class PartialOrder(BaseModel):
    id: str
    event_id: Optional[str]
    event_created_at: Optional[int]
    public_key: str
    merchant_public_key: str
    shipping_id: str
    items: List[OrderItem]
    contact: Optional[OrderContact]
    address: Optional[str]

    def validate_order(self):
        assert len(self.items) != 0, f"Order has no items. Order: '{self.id}'"

    def validate_order_items(self, product_list: List[Product]):
        assert len(self.items) != 0, f"Order has no items. Order: '{self.id}'"
        assert (
            len(product_list) != 0
        ), f"No products found for order. Order: '{self.id}'"

        product_ids = [p.id for p in product_list]
        for item in self.items:
            if item.product_id not in product_ids:
                raise ValueError(
                    f"Order ({self.id}) item product does not exist: {item.product_id}"
                )

        stall_id = product_list[0].stall_id
        for p in product_list:
            if p.stall_id != stall_id:
                raise ValueError(
                    f"Order ({self.id}) has products from different stalls"
                )

    async def costs_in_sats(
        self, products: List[Product], shipping_cost: float
    ) -> Tuple[float, float]:
        product_prices = {}
        for p in products:
            product_prices[p.id] = p

        product_cost: float = 0  # todo
        for item in self.items:
            price = product_prices[item.product_id].price
            currency = product_prices[item.product_id].config.currency or "sat"
            if currency != "sat":
                price = await fiat_amount_as_satoshis(price, currency)
            product_cost += item.quantity * price

        if currency != "sat":
            shipping_cost = await fiat_amount_as_satoshis(shipping_cost, currency)

        return product_cost, shipping_cost


class Order(PartialOrder):
    stall_id: str
    invoice_id: str
    total: float
    paid: bool = False
    shipped: bool = False
    time: Optional[int]
    extra: OrderExtra

    @classmethod
    def from_row(cls, row: Row) -> "Order":
        contact = OrderContact(**json.loads(row["contact_data"]))
        extra = OrderExtra(**json.loads(row["extra_data"]))
        items = [OrderItem(**z) for z in json.loads(row["order_items"])]
        order = cls(**dict(row), contact=contact, items=items, extra=extra)
        return order


class OrderStatusUpdate(BaseModel):
    id: str
    message: Optional[str]
    paid: Optional[bool]
    shipped: Optional[bool]


class PaymentOption(BaseModel):
    type: str
    link: str


class PaymentRequest(BaseModel):
    id: str
    message: Optional[str]
    payment_options: List[PaymentOption]


######################################## MESSAGE ########################################


class PartialDirectMessage(BaseModel):
    event_id: Optional[str]
    event_created_at: Optional[int]
    message: str
    public_key: str
    incoming: bool = False
    time: Optional[int]


class DirectMessage(PartialDirectMessage):
    id: str

    @classmethod
    def from_row(cls, row: Row) -> "DirectMessage":
        dm = cls(**dict(row))
        return dm


######################################## CUSTOMERS ########################################


class CustomerProfile(BaseModel):
    name: Optional[str]
    about: Optional[str]


class Customer(BaseModel):
    merchant_id: str
    public_key: str
    event_created_at: Optional[int]
    profile: Optional[CustomerProfile]
    unread_messages: int = 0

    @classmethod
    def from_row(cls, row: Row) -> "Customer":
        customer = cls(**dict(row))
        customer.profile = CustomerProfile(**json.loads(row["meta"]))
        return customer
