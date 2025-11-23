from pydantic import BaseModel
from typing import List, Optional

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
    result: List[str]

class ExShowroomPriceInput(BaseModel):
    brand: str
    model: str
    fuel_type: str
    transmission: str
    variant: str

class ExShowroomPriceOutput(BaseModel):
    result: int

class RoadTaxMultiplierInput(BaseModel):
    state: str
    ex_showroom_price: int
    fuel_type: str

class RoadTaxMultiplierOutput(BaseModel):
    result: float

class OnRoadPriceInput(BaseModel):
    ex_showroom_price: int
    road_tax_multiplier: float

class OnRoadPriceOutput(BaseModel):
    result: float

class FactsOutput(BaseModel):
    state: List[str]
    brand: str
    model: str
    fuel_type: str
    transmission: str
    minPrice: int
    maxPrice: int

class PreferencesOutput(BaseModel):
    state: str
    minPrice: int
    maxPrice: int


