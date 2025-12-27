#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Backend v4.4.1 - CORRECTION FORMAT CATEGORIES
Renvoie directement un tableau, pas un objet
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import httpx
import json
import re
import traceback
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SUPABASE_URL = "https://bnlybntkwazgcuatuplb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJubHlibnRrd2F6Z2N1YXR1cGxiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNjU0NjUsImV4cCI6MjA4MTY0MTQ2NX0.b876YQvlECMZWxSzQG6z5i9wcCRba6_PA9g-BW0RLik"

app = FastAPI(title="API Conclusions v4.4.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = httpx.AsyncClient(timeout=30.0)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

@app.get("/")
async def root():
    return {
        "app": "API Conclusions Médicales",
        "version": "4.4.1",
        "endpoints": ["/health", "/categories", "/motifs/{table}", "/fusion"]
    }

@app.get("/health")
async def health():
    """Health check avec test Supabase"""
    try:
        logger.info("Health check")
        url = f"{SUPABASE_URL}/rest/v1/vue_categories?select=count&limit=1"
        r = await client.get(url, headers=HEADERS, timeout=5.0)
        
        if r.status_code == 200:
            return {
                "status": "healthy",
                "database": "connected",
                "version": "4.4.1",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "degraded",
                "database": f"error_{r.status_code}",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/categories")
async def get_categories():
    """
    Récupère les catégories - RENVOIE DIRECTEMENT UN TABLEAU
    Format: [{nom, table_name, ordre}, ...]
    """
    try:
        logger.info("Récupération catégories")
        url = f"{SUPABASE_URL}/rest/v1/vue_categories?select=*&order=ordre.asc"
        
        r = await client.get(url, headers=HEADERS)
        r.raise_for_status()
        
        data = r.json()
        logger.info(f"Type reçu de Supabase: {type(data)}")
        logger.info(f"Données: {data}")
        
        # CORRECTION CRITIQUE : S'assurer de renvoyer un TABLEAU
        # Si Supabase renvoie {categories: [...]}, extraire le tableau
        if isinstance(data, dict):
            if 'categories' in data:
                logger.info("Format objet détecté, extraction du tableau")
                categories = data['categories']
            else:
                # Si c'est un objet mais sans clé 'categories'
                logger.warning("Format objet inattendu, conversion en liste")
                categories = [data]
        elif isinstance(data, list):
            logger.info("Format tableau correct")
            categories = data
        else:
            logger.error(f"Type inattendu: {type(data)}")
            raise HTTPException(500, "Format de données incorrect")
        
        # Vérification finale
        if not isinstance(categories, list):
            logger.error(f"Erreur: categories n'est pas une liste: {type(categories)}")
            raise HTTPException(500, "Impossible de créer un tableau")
        
        logger.info(f"✅ Renvoi de {len(categories)} catégories (type: {type(categories)})")
        return categories  # ← RENVOIE DIRECTEMENT LE TABLEAU
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Erreur HTTP: {e.response.status_code}")
        raise HTTPException(500, f"Erreur Supabase: {e.response.status_code}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Erreur serveur: {str(e)}")

@app.get("/motifs/{table_name}")
async def get_motifs(table_name: str):
    """Récupère les motifs d'une table"""
    try:
        logger.info(f"Récupération motifs: {table_name}")
        url = f"{SUPABASE_URL}/rest/v1/{table_name}?select=id,nom_motif,ordre&order=ordre.asc"
        
        r = await client.get(url, headers=HEADERS)
        r.raise_for_status()
        
        data = r.json()
        logger.info(f"✅ {len(data)} motifs récupérés")
        return data
        
    except Exception as e:
        logger.error(f"Erreur motifs: {e}")
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 API v4.4.1 - Correction format categories")
    uvicorn.run(app, host="0.0.0.0", port=8000)
