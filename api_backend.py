#!/usr/bin/env python3
"""
Backend FastAPI - Système de Conclusions Médicales
Version corrigée avec fusion sans doublons
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import os
from dotenv import load_dotenv
import json
import re

load_dotenv()

SUPABASE_URL = os.getenv("https://bnlybntkwazgcuatuplb.supabase.co")
SUPABASE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJubHlibnRrd2F6Z2N1YXR1cGxiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNjU0NjUsImV4cCI6MjA4MTY0MTQ2NX0.b876YQvlECMZWxSzQG6z5i9wcCRba6_PA9g-BW0RLik")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Variables SUPABASE_URL et SUPABASE_KEY requises")

app = FastAPI(title="API Conclusions Médicales", version="4.0.0")

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

# Modèles
class Categorie(BaseModel):
    nom: str
    table_name: str
    ordre: int

class Motif(BaseModel):
    id: str
    nom_motif: str
    ordre: int

class FusionRequest(BaseModel):
    table_principale: str
    motif_principal_id: str
    motifs_secondaires: List[Dict[str, str]] = []

class Bulle(BaseModel):
    nom: str
    contenu: str

class Proposition(BaseModel):
    placeholder: str
    suggestions: List[str]

class Module(BaseModel):
    type: str
    titre: str
    icon: str
    contenu: str
    ordre: int
    bulles: List[Bulle] = []
    propositions: List[Proposition] = []

class Ordonnance(BaseModel):
    id: str
    titre: str
    categorie_ordo: str
    contenu: str
    bulles: List[Bulle] = []
    propositions: List[Proposition] = []

class CodeCCAM(BaseModel):
    code: str
    libelle: str

class FusionResponse(BaseModel):
    motifs_utilises: List[Dict[str, str]]
    modules: List[Module]
    ordonnances: List[Ordonnance]
    codes_ccam: List[CodeCCAM]

MODULE_CONFIG = {
    'diagnostic': {'titre': 'DIAGNOSTIC', 'icon': '🔍', 'ordre': 1},
    'signes_gravite': {'titre': 'SIGNES DE GRAVITÉ', 'icon': '⚠️', 'ordre': 2},
    'soins_urgences': {'titre': 'AUX URGENCES', 'icon': '🏥', 'ordre': 3},
    'conduite_tenir': {'titre': 'CONDUITE À TENIR', 'icon': '📋', 'ordre': 4},
    'conseils': {'titre': 'CONSEILS', 'icon': '💡', 'ordre': 5},
    'suivi': {'titre': 'SUIVI ET RECONSULTATION POST URGENCE', 'icon': '📅', 'ordre': 6},
    'consignes_reconsultation': {'titre': 'CONSIGNES DE RECONSULTATION', 'icon': '🚨', 'ordre': 7}
}

def parse_bulles(text: str) -> tuple[str, List[Bulle]]:
    """
    Extrait les bulles et nettoie le texte.
    Format: BULLE : nom : contenu FIN
    Retourne: (texte_nettoyé, liste_bulles)
    """
    if not text:
        return "", []
    
    bulles = []
    clean_text = text
    
    # Pattern: BULLE : nom : contenu FIN
    pattern = r'BULLE\s*:\s*([^:]+?)\s*:\s*(.*?)\s*FIN'
    matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        nom = match.group(1).strip()
        contenu = match.group(2).strip()
        bulles.append(Bulle(nom=nom, contenu=contenu))
    
    # Supprimer tous les marqueurs BULLE...FIN
    clean_text = re.sub(r'BULLE\s*:.*?FIN', '', clean_text, flags=re.IGNORECASE | re.DOTALL)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text, bulles

def parse_propositions(text: str) -> List[Proposition]:
    """Extrait les propositions du texte"""
    if not text:
        return []
    
    propositions = []
    pattern = r'PROPOSITION\s*:\s*(.*?)\s*FINI'
    matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        content = match.group(1).strip()
        suggestions = [s.strip() for s in re.split(r'\s*;\s*', content) if s.strip()]
        
        if suggestions:
            propositions.append(Proposition(
                placeholder="XXXX",
                suggestions=suggestions
            ))
    
    return propositions

def parse_codes_ccam(text: str) -> List[CodeCCAM]:
    """Parse les codes CCAM/CIM-10"""
    if not text:
        return []
    
    codes = []
    pattern = r'([A-Z]\d{2,3}(?:\.\d{1,2})?)\s*:\s*([^\n]+)'
    matches = re.finditer(pattern, text)
    
    for match in matches:
        code = match.group(1).strip()
        libelle = match.group(2).strip()
        codes.append(CodeCCAM(code=code, libelle=libelle))
    
    return codes

def split_sentences(text: str) -> List[str]:
    """Sépare le texte en phrases (par points)"""
    if not text:
        return []
    
    # Séparer par point suivi d'espace ou fin de ligne
    sentences = re.split(r'\.(?:\s+|$)', text)
    # Nettoyer et rajouter les points
    sentences = [s.strip() + '.' for s in sentences if s.strip()]
    return sentences

def remove_duplicate_sentences(sentences: List[str]) -> List[str]:
    """Supprime les phrases en double en gardant l'ordre"""
    seen = set()
    result = []
    
    for sentence in sentences:
        # Normaliser pour comparaison (minuscules, espaces)
        normalized = sentence.lower().strip()
        
        if normalized not in seen:
            seen.add(normalized)
            result.append(sentence)
    
    return result

@app.get("/")
async def root():
    return {
        "message": "API Conclusions Médicales",
        "version": "4.0.0",
        "status": "ready"
    }

@app.get("/health")
async def health_check():
    try:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/vue_categories?select=count",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            return {"status": "healthy", "database": "connected", "version": "4.0.0"}
        else:
            return {"status": "degraded", "database": "error"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/categories", response_model=List[Categorie])
async def get_categories():
    try:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/vue_categories?select=*&order=ordre.asc",
            headers=HEADERS
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")

@app.get("/motifs/{table_name}", response_model=List[Motif])
async def get_motifs(table_name: str):
    try:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/{table_name}?select=id,nom_motif,ordre&order=ordre.asc",
            headers=HEADERS
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")

async def get_motif_complet(table_name: str, motif_id: str) -> Dict:
    """Récupère un motif complet"""
    try:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/{table_name}?id=eq.{motif_id}&select=*",
            headers=HEADERS
        )
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise HTTPException(404, f"Motif introuvable")
        
        return data[0]
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")

def fusionner_modules(motifs_data: List[Dict]) -> List[Module]:
    """
    Fusionne les modules en supprimant les doublons de phrases.
    - diagnostic et signes_gravite : fusion avec suppression doublons
    - autres modules : motif principal uniquement
    """
    modules_result = []
    
    for module_type, config in MODULE_CONFIG.items():
        all_sentences = []
        all_bulles = []
        all_propositions = []
        
        for idx, motif in enumerate(motifs_data):
            is_principal = (idx == 0)
            
            # Pour diagnostic et signes_gravite : fusion
            if module_type in ['diagnostic', 'signes_gravite']:
                if motif.get(module_type):
                    text = motif[module_type]
                    # Extraire bulles et nettoyer
                    clean_text, bulles = parse_bulles(text)
                    # Séparer en phrases
                    sentences = split_sentences(clean_text)
                    all_sentences.extend(sentences)
                    all_bulles.extend(bulles)
                    all_propositions.extend(parse_propositions(text))
            
            # Autres modules : uniquement motif principal
            elif is_principal and motif.get(module_type):
                text = motif[module_type]
                clean_text, bulles = parse_bulles(text)
                sentences = split_sentences(clean_text)
                all_sentences.extend(sentences)
                all_bulles.extend(bulles)
                all_propositions.extend(parse_propositions(text))
        
        # Supprimer doublons de phrases
        unique_sentences = remove_duplicate_sentences(all_sentences)
        
        if unique_sentences:
            # Reconstruire le texte avec phrases uniques
            contenu_fusionne = '\n'.join(unique_sentences)
            
            modules_result.append(Module(
                type=module_type,
                titre=config['titre'],
                icon=config['icon'],
                contenu=contenu_fusionne,
                ordre=config['ordre'],
                bulles=all_bulles,
                propositions=all_propositions
            ))
    
    return modules_result

def fusionner_ordonnances(motifs_data: List[Dict]) -> List[Ordonnance]:
    """Fusionne les ordonnances en supprimant les doublons"""
    ordonnances_map = {}
    ordo_counter = 0
    
    for motif in motifs_data:
        if not motif.get('ordonnances'):
            continue
        
        ordos = motif['ordonnances']
        
        if isinstance(ordos, str):
            try:
                ordos = json.loads(ordos)
            except:
                continue
        
        for ordo_type, contenu in ordos.items():
            if not contenu or not str(contenu).strip():
                continue
            
            # Nettoyer le contenu
            clean_contenu, bulles = parse_bulles(str(contenu))
            propositions = parse_propositions(str(contenu))
            
            # Clé unique
            key = f"{ordo_type}_{clean_contenu[:50]}"
            
            if key not in ordonnances_map:
                ordo_counter += 1
                titre = ordo_type.replace('_', ' ').title()
                
                ordonnances_map[key] = Ordonnance(
                    id=f"ordo_{ordo_counter}",
                    titre=titre,
                    categorie_ordo=ordo_type,
                    contenu=clean_contenu,
                    bulles=bulles,
                    propositions=propositions
                )
    
    return list(ordonnances_map.values())

def fusionner_codes_ccam(motifs_data: List[Dict]) -> List[CodeCCAM]:
    """Fusionne les codes CCAM en supprimant les doublons"""
    codes_map = {}
    
    for motif in motifs_data:
        if motif.get('codage_cim10'):
            codes = parse_codes_ccam(motif['codage_cim10'])
            
            for code in codes:
                if code.code not in codes_map:
                    codes_map[code.code] = code
    
    return list(codes_map.values())

@app.post("/fusion", response_model=FusionResponse)
async def fusion_motifs(request: FusionRequest):
    """
    Fusionne motifs avec suppression des doublons de phrases.
    """
    try:
        # Motif principal
        motif_principal = await get_motif_complet(
            request.table_principale,
            request.motif_principal_id
        )
        
        all_motifs_data = [motif_principal]
        
        # Motifs secondaires
        for motif_sec in request.motifs_secondaires:
            motif_data = await get_motif_complet(
                motif_sec['table'],
                motif_sec['id']
            )
            all_motifs_data.append(motif_data)
        
        # Info motifs
        motifs_utilises = [{
            'id': motif_principal['id'],
            'nom': motif_principal['nom_motif'],
            'type': 'principal'
        }]
        
        for motif in all_motifs_data[1:]:
            motifs_utilises.append({
                'id': motif['id'],
                'nom': motif['nom_motif'],
                'type': 'secondaire'
            })
        
        # Fusion
        modules = fusionner_modules(all_motifs_data)
        ordonnances = fusionner_ordonnances(all_motifs_data)
        codes_ccam = fusionner_codes_ccam(all_motifs_data)
        
        return FusionResponse(
            motifs_utilises=motifs_utilises,
            modules=modules,
            ordonnances=ordonnances,
            codes_ccam=codes_ccam
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur fusion: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 API Conclusions Médicales v4.0.0")
    uvicorn.run(app, host="0.0.0.0", port=8000)
