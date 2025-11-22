from pydantic import BaseModel
from typing import List

class PriceInput(BaseModel):
    brand: str
    model: str
    fuel_type: str
    transmission: str
    variant: str

class PriceOutput(BaseModel):
    price: int

class VariantsInput(BaseModel):
    brand: str
    model: str
    fuel_type: str
    transmission: str

class VariantsOutput(BaseModel):
    variants: List[str]

class ExShowroomPriceInput(BaseModel):
    brand: str
    model: str
    fuel_type: str
    transmission: str
    variant: str

class ExShowroomPriceOutput(BaseModel):
    ex_showroom_price: int

class RoadTaxMultiplierInput(BaseModel):
    state: str
    ex_showroom_price: int
    fuel_type: str

class RoadTaxMultiplierOutput(BaseModel):
    multiplier: float

class OnRoadPriceInput(BaseModel):
    ex_showroom_price: int
    road_tax_multiplier: float

class OnRoadPriceOutput(BaseModel):
    on_road_price: float

class PreferencesOutput(BaseModel):
    state: List[str]
    fuel_type: str
    transmission: str
    minPrice: int
    maxPrice: int


