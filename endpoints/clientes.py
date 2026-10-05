from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import database
import models
import req_res_models

router = APIRouter(prefix="/clientes", tags=["Clientes"])


# Tiene que declararse antes de /{id}; si no, FastAPI interpreta "count" como un id.
@router.get("/count")
def get_clientes_count(db: Session = Depends(database.get_db)):
    return db.query(models.Cliente).count()


@router.get("/{id}", response_model=req_res_models.ClienteResponse)
def get_cliente(id: str, db: Session = Depends(database.get_db)):
    cliente = db.get(models.Cliente, id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Número de cuenta no encontrado.")
    return cliente


@router.post("/", response_model=req_res_models.ClienteResponse)
def create_cliente(cliente: req_res_models.ClienteCreate, db: Session = Depends(database.get_db)):
    nuevo_cliente = models.Cliente(**cliente.model_dump())
    db.add(nuevo_cliente)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El número de cuenta (ID) ya existe.")
    db.refresh(nuevo_cliente)
    return nuevo_cliente


# Solo se pueden editar la ocupación y el tipo de cuenta: los datos personales del titular quedan fijos.
@router.put("/{id}", response_model=req_res_models.ClienteResponse)
def update_cliente(id: str, cliente: req_res_models.ClienteUpdate, db: Session = Depends(database.get_db)):
    db_cliente = db.get(models.Cliente, id)
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Este número de cuenta no existe.")
    # exclude_unset evita pisar con None los campos que el front no mandó.
    for field, value in cliente.model_dump(exclude_unset=True).items():
        setattr(db_cliente, field, value)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente


@router.delete("/{id}")
def delete_cliente(id: str, db: Session = Depends(database.get_db)):
    db_cliente = db.get(models.Cliente, id)
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Este número de cuenta no existe.")
    db.delete(db_cliente)
    db.commit()
    return {"message": "Número de cuenta eliminado."}


@router.get("/", response_model=List[req_res_models.ClienteResponse])
def get_all_cliente(skip: int = 0, limit: int = 30, db: Session = Depends(database.get_db)):
    return db.query(models.Cliente).order_by(models.Cliente.id).offset(skip).limit(limit).all()
