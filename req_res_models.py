from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

# Modelos de request y response de la API. Los *Response usan from_attributes
# para poder devolver directamente los objetos de SQLAlchemy.


class TipoTransaccionCreate(BaseModel):
    nombre: str


class TipoTransaccionResponse(BaseModel):
    id: int
    nombre: str

    class Config:
        from_attributes = True


class CajeroCreate(BaseModel):
    id: str
    nombre: str
    ciudad: str
    provincia: str
    pais: str


class CajeroResponse(CajeroCreate):
    class Config:
        from_attributes = True


class ClienteCreate(BaseModel):
    id: str
    nombre: str
    apellido: str
    genero: str
    fecha_nacimiento: date
    ocupacion: str
    tipo_cuenta: str


class ClienteResponse(ClienteCreate):
    class Config:
        from_attributes = True


class ClienteUpdate(BaseModel):
    ocupacion: Optional[str] = None
    tipo_cuenta: Optional[str] = None


class TransaccionCreate(BaseModel):
    id: str
    fecha_hora: datetime
    id_cliente: str
    id_cajero: str
    id_tipo_transaccion: int
    monto: Decimal


class TransaccionResponse(TransaccionCreate):
    class Config:
        from_attributes = True


class TransaccionSospechosaResponse(TransaccionCreate):
    nombre: str
    apellido: str
    sospechosa_por: List[str]
    score_anomalia: float


class ClienteSospechosoResponse(BaseModel):
    id_cliente: str
    nombre: str
    apellido: str
    sospechoso_por: List[str]
