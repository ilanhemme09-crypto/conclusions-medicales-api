#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Backend v4.4.2 - CORRECTION COMPLETE
Corrige le format pour /categories ET /motifs
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

app = FastAPI(title="API Conclusions v4.4.2")

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

def ensure_array(data, key_name=None):
    """
    Utilitaire pour s'assurer qu'on renvoie toujours un tableau
    Gère : tableau direct, {key: tableau}, objet unique
    """
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if key_name and key_name in data and isinstance(data[key_name], list):
            return data[key_name]
        # Si c'est un objet mais pas avec la clé attendue, le mettre dans un tableau
        return [data]
    else:
        logger.error(f"Type inattendu: {type(data)}")
        return []

@app.get("/")
async def root():
    return {
        "app": "API Conclusions Médicales",
        "version": "4.4.2",
        "status": "Format corrigé pour /categories et /motifs",
        "endpoints": ["/health", "/categories", "/motifs/{table}", "/fusion"]
    }

@app.get("/health")
async def health():
    """Health check avec test Supabase"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/vue_categories?select=count&limit=1"
        r = await client.get(url, headers=HEADERS, timeout=5.0)
        
        if r.status_code == 200:
            return {
                "status": "healthy",
                "database": "connected",
                "version": "4.4.2",
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
    Récupère les catégories - RENVOIE TOUJOURS UN TABLEAU
    """
    try:
        logger.info("📥 GET /categories")
        url = f"{SUPABASE_URL}/rest/v1/vue_categories?select=*&order=ordre.asc"
        
        r = await client.get(url, headers=HEADERS)
        r.raise_for_status()
        
        data = r.json()
        logger.info(f"Type reçu: {type(data)}")
        
        # Conversion en tableau si nécessaire
        categories = ensure_array(data, 'categories')
        
        if not isinstance(categories, list):
            logger.error(f"❌ Impossible de créer un tableau")
            raise HTTPException(500, "Format incorrect")
        
        logger.info(f"✅ Renvoi de {len(categories)} catégories")
        return categories
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Erreur HTTP: {e.response.status_code}")
        raise HTTPException(500, f"Erreur Supabase: {e.response.status_code}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        raise HTTPException(500, str(e))

@app.get("/motifs/{table_name}")
async def get_motifs(table_name: str):
    """
    Récupère les motifs - RENVOIE TOUJOURS UN TABLEAU
    """
    try:
        logger.info(f"📥 GET /motifs/{table_name}")
        url = f"{SUPABASE_URL}/rest/v1/{table_name}?select=id,nom_motif,ordre&order=ordre.asc"
        
        r = await client.get(url, headers=HEADERS)
        r.raise_for_status()
        
        data = r.json()
        logger.info(f"Type reçu: {type(data)}")
        
        # Conversion en tableau si nécessaire
        motifs = ensure_array(data, 'motifs')
        
        if not isinstance(motifs, list):
            logger.error(f"❌ Impossible de créer un tableau")
            raise HTTPException(500, "Format incorrect")
        
        logger.info(f"✅ Renvoi de {len(motifs)} motifs")
        return motifs
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Erreur HTTP: {e.response.status_code}")
        raise HTTPException(500, f"Erreur Supabase: {e.response.status_code}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        raise HTTPException(500, str(e))

# ... (Le reste de votre code pour /fusion reste identique)

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 API v4.4.2 - Correction complète categories + motifs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
