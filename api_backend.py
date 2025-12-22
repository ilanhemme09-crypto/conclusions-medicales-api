#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Backend - Conclusions Médicales
Fichier: api_backend.py
Version: 1.0.0
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import httpx
import json
import re

# ===== CONFIGURATION SUPABASE =====
SUPABASE_URL = "https://bnlybntkwazgcuatuplb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJubHlibnRrd2F6Z2N1YXR1cGxiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNjU0NjUsImV4cCI6MjA4MTY0MTQ2NX0.b876YQvlECMZWxSzQG6z5i9wcCRba6_PA9g-BW0RLik"

app = FastAPI(title="API Conclusions Médicales")

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

# ===== MODÈLES =====
class Categorie(BaseModel):
    nom: str
    table_name: str
    ordre: int

class Motif(BaseModel):
    id: str
    nom_motif: str
    ordre: int

class Bulle(BaseModel):
    titre: str
    contenu: str

class Module(BaseModel):
    type: str
    titre: str
    icon: str
    lignes: List[str]
    bulles: List[Bulle]

class Ordonnance(BaseModel):
    titre: str
    lignes: List[str]
    bulles: List[Bulle]

class CodeCIM(BaseModel):
    code: str
    libelle: str

class MotifSecondaire(BaseModel):
    table: str
    id: str

class FusionRequest(BaseModel):
    table_principale: str
    motif_principal_id: str
    motifs_secondaires: List[MotifSecondaire] = []

class FusionResponse(BaseModel):
    modules: List[Module]
    ordonnances: List[Ordonnance]
    codes_cim: List[CodeCIM]

MODULES_CONFIG = {
    'diagnostic': {'titre': 'DIAGNOSTIC', 'icon': '🔍', 'ordre': 1},
    'signes_gravite': {'titre': 'SIGNES DE GRAVITÉ', 'icon': '⚠️', 'ordre': 2},
    'soins_urgences': {'titre': 'AUX URGENCES', 'icon': '🏥', 'ordre': 3},
    'conduite_tenir': {'titre': 'CONDUITE À TENIR', 'icon': '📋', 'ordre': 4},
    'conseils': {'titre': 'CONSEILS', 'icon': '💡', 'ordre': 5},
    'suivi': {'titre': 'SUIVI', 'icon': '📅', 'ordre': 6},
    'consignes_reconsultation': {'titre': 'CONSIGNES DE RECONSULTATION', 'icon': '🚨', 'ordre': 7}
}

def parse_bulles(texte: str):
    if not texte:
        return "", []
    
    bulles = []
    texte_propre = texte
    pattern = r'BULLE\s*:\s*([^:]+?)\s*:\s*(.*?)\s*FIN'
    
    for match in re.finditer(pattern, texte, re.IGNORECASE | re.DOTALL):
        titre = match.group(1).strip()
        contenu = match.group(2).strip()
        bulles.append(Bulle(titre=titre, contenu=contenu))
    
    texte_propre = re.sub(pattern, '', texte_propre, flags=re.IGNORECASE | re.DOTALL)
    texte_propre = ' '.join(texte_propre.split())
    
    return texte_propre, bulles

def extraire_lignes(texte: str):
    if not texte:
        return []
    
    lignes = []
    parties = texte.split('\n')
    
    for partie in parties:
        partie = partie.strip()
        if not partie:
            continue
        
        if '. ' in partie or partie.endswith('.'):
            sous_parties = re.split(r'\.\s+', partie)
            for sp in sous_parties:
                sp = sp.strip()
                if sp:
                    if not sp.endswith('.'):
                        sp += '.'
                    lignes.append(sp)
        else:
            if not partie.endswith('.'):
                partie += '.'
            lignes.append(partie)
    
    return lignes

def supprimer_doublons(lignes: List[str]):
    vues = set()
    resultat = []
    
    for ligne in lignes:
        ligne_norm = ligne.lower().strip()
        if ligne_norm not in vues:
            vues.add(ligne_norm)
            resultat.append(ligne)
    
    return resultat

def parse_codes_cim(texte: str):
    if not texte:
        return []
    
    codes = []
    pattern = r'([A-Z]\d{2,3}(?:\.\d)?)\s*:\s*([^\n]+)'
    
    for match in re.finditer(pattern, texte):
        code = match.group(1).strip()
        libelle = match.group(2).strip()
        codes.append(CodeCIM(code=code, libelle=libelle))
    
    return codes

@app.get("/")
async def root():
    return {"service": "API Conclusions Médicales", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    try:
        response = await client.get(f"{SUPABASE_URL}/rest/v1/vue_categories?select=count", headers=HEADERS)
        if response.status_code == 200:
            return {"status": "healthy", "database": "connected"}
        return {"status": "degraded"}
    except:
        return {"status": "unhealthy"}

@app.get("/categories", response_model=List[Categorie])
async def get_categories():
    try:
        response = await client.get(f"{SUPABASE_URL}/rest/v1/vue_categories?select=*&order=ordre.asc", headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/motifs/{table_name}", response_model=List[Motif])
async def get_motifs(table_name: str):
    try:
        response = await client.get(f"{SUPABASE_URL}/rest/v1/{table_name}?select=id,nom_motif,ordre&order=ordre.asc", headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(500, str(e))

async def get_motif_complet(table_name: str, motif_id: str):
    try:
        response = await client.get(f"{SUPABASE_URL}/rest/v1/{table_name}?id=eq.{motif_id}&select=*", headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        if not data:
            raise HTTPException(404, "Motif introuvable")
        return data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/fusion", response_model=FusionResponse)
async def fusion_motifs(request: FusionRequest):
    try:
        motif_principal = await get_motif_complet(request.table_principale, request.motif_principal_id)
        tous_les_motifs = [motif_principal]
        
        for motif_sec in request.motifs_secondaires:
            motif_data = await get_motif_complet(motif_sec.table, motif_sec.id)
            tous_les_motifs.append(motif_data)
        
        modules_finaux = []
        
        for module_type, config in MODULES_CONFIG.items():
            toutes_les_lignes = []
            toutes_les_bulles = []
            
            for idx, motif in enumerate(tous_les_motifs):
                est_principal = (idx == 0)
                
                if module_type in ['diagnostic', 'signes_gravite']:
                    if motif.get(module_type):
                        texte = motif[module_type]
                        texte_propre, bulles = parse_bulles(texte)
                        lignes = extraire_lignes(texte_propre)
                        toutes_les_lignes.extend(lignes)
                        toutes_les_bulles.extend(bulles)
                
                elif est_principal and motif.get(module_type):
                    texte = motif[module_type]
                    texte_propre, bulles = parse_bulles(texte)
                    lignes = extraire_lignes(texte_propre)
                    toutes_les_lignes.extend(lignes)
                    toutes_les_bulles.extend(bulles)
            
            lignes_uniques = supprimer_doublons(toutes_les_lignes)
            
            if lignes_uniques:
                modules_finaux.append(Module(
                    type=module_type,
                    titre=config['titre'],
                    icon=config['icon'],
                    lignes=lignes_uniques,
                    bulles=toutes_les_bulles
                ))
        
        ordonnances_finales = []
        ordos_deja_vues = set()
        
        for motif in tous_les_motifs:
            if not motif.get('ordonnances'):
                continue
            
            ordos = motif['ordonnances']
            
            if isinstance(ordos, str):
                try:
                    ordos = json.loads(ordos)
                except:
                    continue
            
            if not isinstance(ordos, dict):
                continue
            
            for titre_ordo, contenu_ordo in ordos.items():
                if not contenu_ordo or not str(contenu_ordo).strip():
                    continue
                
                contenu_str = str(contenu_ordo)
                texte_propre, bulles = parse_bulles(contenu_str)
                lignes = extraire_lignes(texte_propre)
                
                cle_unique = f"{titre_ordo}_{texte_propre[:50]}"
                
                if cle_unique not in ordos_deja_vues:
                    ordos_deja_vues.add(cle_unique)
                    ordonnances_finales.append(Ordonnance(
                        titre=titre_ordo.replace('_', ' ').title(),
                        lignes=lignes,
                        bulles=bulles
                    ))
        
        codes_finaux = []
        codes_deja_vus = set()
        
        for motif in tous_les_motifs:
            if motif.get('codage_cim10'):
                codes = parse_codes_cim(motif['codage_cim10'])
                for code in codes:
                    if code.code not in codes_deja_vus:
                        codes_deja_vus.add(code.code)
                        codes_finaux.append(code)
        
        return FusionResponse(
            modules=modules_finaux,
            ordonnances=ordonnances_finales,
            codes_cim=codes_finaux
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur fusion: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 API Conclusions Médicales démarrée")
    uvicorn.run(app, host="0.0.0.0", port=8000)
