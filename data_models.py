from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Shared Models ---

class MoneyV2(BaseModel):
    amount: str
    currencyCode: str

class ShopMoney(BaseModel):
    shopMoney: MoneyV2

class Address(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    company: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    provinceCode: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None
    countryCodeV2: Optional[str] = None
    phone: Optional[str] = None

# --- Customer Models ---

class Customer(BaseModel):
    id: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    numberOfOrders: Optional[str] = None
    defaultAddress: Optional[Address] = None

# --- Product Models ---

class SelectedOption(BaseModel):
    name: str
    value: str

class Variant(BaseModel):
    id: str
    sku: Optional[str] = None
    title: Optional[str] = None
    displayName: Optional[str] = None
    inventoryQuantity: Optional[int] = None
    selectedOptions: List[SelectedOption] = []
    price: Optional[str] = None

class Product(BaseModel):
    id: str
    title: str
    handle: Optional[str] = None
    description: Optional[str] = None
    descriptionHtml: Optional[str] = None
    productType: Optional[str] = None
    vendor: Optional[str] = None
    tags: List[str] = []
    variants: List[Variant] = []
    images: List[Dict[str, Any]] = []

# --- Order Models ---

class LineItem(BaseModel):
    id: str
    title: str
    quantity: int
    variant: Optional[Variant] = None
    originalUnitPriceSet: Optional[ShopMoney] = None
    discountedUnitPriceSet: Optional[ShopMoney] = None
    taxable: bool = True

class Order(BaseModel):
    id: str
    name: str
    createdAt: datetime
    displayFinancialStatus: Optional[str] = None
    displayFulfillmentStatus: Optional[str] = None
    customer: Optional[Customer] = None
    lineItems: List[LineItem] = []
    totalPriceSet: Optional[ShopMoney] = None
    currentSubtotalPriceSet: Optional[ShopMoney] = None
    shippingAddress: Optional[Address] = None
    billingAddress: Optional[Address] = None
    note: Optional[str] = None
    tags: List[str] = []
