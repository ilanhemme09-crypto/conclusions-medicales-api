#!/usr/bin/env python3
"""
Backend FastAPI - Système de Conclusions Médicales
Version finale avec structure simplifiée (16 tables)
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

# Charger variables d'environnement
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Variables SUPABASE_URL et SUPABASE_KEY requises dans .env")

app = FastAPI(
    title="API Conclusions Médicales",
    description="API complète avec fusion intelligente de motifs",
    version="3.0.0"
)

# CORS : permet au frontend d'appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, remplacer par l'URL du frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Client HTTP pour Supabase
client = httpx.AsyncClient(timeout=30.0)

# Headers Supabase
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ============================================================================
# MODÈLES PYDANTIC
# ============================================================================

class Categorie(BaseModel):
    nom: str
    table_name: str
    ordre: int


class Motif(BaseModel):
    id: str
    nom_motif: str
    ordre: int


class FusionRequest(BaseModel):
    """Requête de fusion de motifs"""
    table_principale: str
    motif_principal_id: str
    motifs_secondaires: List[Dict[str, str]] = []  # [{"table": "...", "id": "..."}]


class Bulle(BaseModel):
    """Bulle d'information"""
    mot: str
    info: str


class Proposition(BaseModel):
    """Proposition pour remplir un XXXX"""
    placeholder: str
    suggestions: List[str]


class Module(BaseModel):
    """Module de texte (diagnostic, signes de gravité, etc.)"""
    type: str
    titre: str
    icon: str
    contenu: str
    ordre: int
    bulles: List[Bulle] = []
    propositions: List[Proposition] = []


class Ordonnance(BaseModel):
    """Ordonnance"""
    id: str
    titre: str
    categorie_ordo: str
    contenu: str
    bulles: List[Bulle] = []
    propositions: List[Proposition] = []


class CodeCCAM(BaseModel):
    """Code de codage CCAM/CIM-10"""
    code: str
    libelle: str


class FusionResponse(BaseModel):
    """Réponse de fusion"""
    motifs_utilises: List[Dict[str, str]]
    modules: List[Module]
    ordonnances: List[Ordonnance]
    codes_ccam: List[CodeCCAM]


# ============================================================================
# CONFIGURATION DES MODULES
# ============================================================================

MODULE_CONFIG = {
    'diagnostic': {
        'titre': 'DIAGNOSTIC',
        'icon': '🔍',
        'ordre': 1
    },
    'signes_gravite': {
        'titre': 'SIGNES DE GRAVITÉ',
        'icon': '⚠️',
        'ordre': 2
    },
    'soins_urgences': {
        'titre': 'AUX URGENCES',
        'icon': '🏥',
        'ordre': 3
    },
    'conduite_tenir': {
        'titre': 'CONDUITE À TENIR',
        'icon': '📋',
        'ordre': 4
    },
    'conseils': {
        'titre': 'CONSEILS',
        'icon': '💡',
        'ordre': 5
    },
    'suivi': {
        'titre': 'SUIVI ET RECONSULTATION POST URGENCE',
        'icon': '📅',
        'ordre': 6
    },
    'consignes_reconsultation': {
        'titre': 'CONSIGNES DE RECONSULTATION',
        'icon': '🚨',
        'ordre': 7
    }
}


# ============================================================================
# FONCTIONS DE PARSING
# ============================================================================

def parse_bulles(text: str) -> List[Bulle]:
    """
    Extrait les bulles d'information du texte.
    Format: BULLE : [mot-clé] : [contenu] FIN
    """
    if not text:
        return []
    
    bulles = []
    pattern = r'BULLE\s*:\s*(.*?)\s*FIN'
    matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        content = match.group(1).strip()
        
        # Essayer de séparer mot-clé et contenu avec ":"
        if ':' in content:
            parts = content.split(':', 1)
            if len(parts) == 2:
                mot_cle = parts[0].strip()
                info = parts[1].strip()
            else:
                # Pas de séparateur clair
                words = content.split()
                mot_cle = ' '.join(words[:3]) if len(words) >= 3 else content[:30]
                info = content
        else:
            # Prendre les 3 premiers mots comme mot-clé
            words = content.split()
            mot_cle = ' '.join(words[:3]) if len(words) >= 3 else content[:30]
            info = content
        
        bulles.append(Bulle(mot=mot_cle, info=info))
    
    return bulles


def parse_propositions(text: str) -> List[Proposition]:
    """
    Extrait les propositions du texte.
    Format: PROPOSITION : option1 ; option2 ; option3 FINI
    """
    if not text:
        return []
    
    propositions = []
    pattern = r'PROPOSITION\s*:\s*(.*?)\s*FINI'
    matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        content = match.group(1).strip()
        # Séparer par ";" 
        suggestions = [s.strip() for s in re.split(r'\s*;\s*', content) if s.strip()]
        
        if suggestions:
            propositions.append(Proposition(
                placeholder="XXXX",
                suggestions=suggestions
            ))
    
    return propositions


def clean_text(text: str) -> str:
    """
    Nettoie le texte en supprimant les marqueurs BULLE et PROPOSITION.
    Garde les XXXX pour qu'ils soient remplaçables.
    """
    if not text:
        return ""
    
    # Supprimer BULLE...FIN
    text = re.sub(r'BULLE\s*:.*?FIN', '', text, flags=re.IGNORECASE | re.DOTALL)
    # Supprimer PROPOSITION...FINI
    text = re.sub(r'PROPOSITION\s*:.*?FINI', '', text, flags=re.IGNORECASE | re.DOTALL)
    # Supprimer espaces multiples
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def parse_codes_ccam(text: str) -> List[CodeCCAM]:
    """
    Parse les codes CCAM/CIM-10 depuis le texte.
    Format: CODE : Libellé
    """
    if not text:
        return []
    
    codes = []
    # Pattern pour codes CIM-10/CCAM
    pattern = r'([A-Z]\d{2,3}(?:\.\d{1,2})?)\s*:\s*([^\n]+)'
    matches = re.finditer(pattern, text)
    
    for match in matches:
        code = match.group(1).strip()
        libelle = match.group(2).strip()
        codes.append(CodeCCAM(code=code, libelle=libelle))
    
    return codes


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Page d'accueil de l'API"""
    return {
        "message": "API Conclusions Médicales",
        "version": "3.0.0",
        "description": "Système complet avec fusion intelligente",
        "endpoints": {
            "health": "GET /health",
            "categories": "GET /categories",
            "motifs": "GET /motifs/{table_name}",
            "fusion": "POST /fusion"
        }
    }


@app.get("/health")
async def health_check():
    """Vérification de l'état de l'API et de la connexion Supabase"""
    try:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/vue_categories?select=count",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            return {
                "status": "healthy",
                "database": "connected",
                "version": "3.0.0"
            }
        else:
            return {
                "status": "degraded",
                "database": "error",
                "code": response.status_code
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/categories", response_model=List[Categorie])
async def get_categories():
    """
    Récupère toutes les catégories disponibles.
    """
    try:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/vue_categories?select=*&order=ordre.asc",
            headers=HEADERS
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur récupération catégories: {str(e)}"
        )


@app.get("/motifs/{table_name}", response_model=List[Motif])
async def get_motifs(table_name: str):
    """
    Récupère les motifs d'une catégorie (table).
    """
    try:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/{table_name}?select=id,nom_motif,ordre&order=ordre.asc",
            headers=HEADERS
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur récupération motifs: {str(e)}"
        )


# ============================================================================
# FUSION DE MOTIFS - LOGIQUE COMPLÈTE
# ============================================================================

async def get_motif_complet(table_name: str, motif_id: str) -> Dict:
    """Récupère un motif complet depuis une table"""
    try:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/{table_name}?id=eq.{motif_id}&select=*",
            headers=HEADERS
        )
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise HTTPException(404, f"Motif {motif_id} introuvable")
        
        return data[0]
    except Exception as e:
        raise HTTPException(500, f"Erreur récupération motif: {str(e)}")


def fusionner_modules(motifs_data: List[Dict]) -> List[Module]:
    """
    Fusionne les modules de plusieurs motifs.
    Règles de fusion :
    - diagnostic et signes_gravite : CONCATÉNATION de tous les motifs
    - autres modules : MOTIF PRINCIPAL uniquement
    """
    modules_result = []
    
    for module_type, config in MODULE_CONFIG.items():
        contenus = []
        all_bulles = []
        all_propositions = []
        
        for idx, motif in enumerate(motifs_data):
            is_principal = (idx == 0)
            
            # Pour diagnostic et signes_gravite : prendre tous les motifs
            if module_type in ['diagnostic', 'signes_gravite']:
                if motif.get(module_type):
                    text = motif[module_type]
                    contenus.append(clean_text(text))
                    all_bulles.extend(parse_bulles(text))
                    all_propositions.extend(parse_propositions(text))
            
            # Pour les autres modules : uniquement le motif principal
            elif is_principal and motif.get(module_type):
                text = motif[module_type]
                contenus.append(clean_text(text))
                all_bulles.extend(parse_bulles(text))
                all_propositions.extend(parse_propositions(text))
        
        # Si on a du contenu, créer le module
        if contenus:
            contenu_fusionne = '\n\n'.join(contenus)
            
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
    """
    Fusionne les ordonnances de tous les motifs.
    Supprime les doublons (même type + même contenu).
    """
    ordonnances_map = {}
    ordo_counter = 0
    
    for motif in motifs_data:
        if not motif.get('ordonnances'):
            continue
        
        ordos = motif['ordonnances']
        
        # Gérer le cas où c'est une string JSON
        if isinstance(ordos, str):
            try:
                ordos = json.loads(ordos)
            except:
                continue
        
        # Parcourir chaque type d'ordonnance
        for ordo_type, contenu in ordos.items():
            if not contenu or not str(contenu).strip():
                continue
            
            # Clé unique pour détecter doublons
            key = f"{ordo_type}_{contenu[:50]}"
            
            if key not in ordonnances_map:
                ordo_counter += 1
                titre = ordo_type.replace('_', ' ').title()
                
                ordonnances_map[key] = Ordonnance(
                    id=f"ordo_{ordo_counter}",
                    titre=titre,
                    categorie_ordo=ordo_type,
                    contenu=clean_text(contenu),
                    bulles=parse_bulles(contenu),
                    propositions=parse_propositions(contenu)
                )
    
    return list(ordonnances_map.values())


def fusionner_codes_ccam(motifs_data: List[Dict]) -> List[CodeCCAM]:
    """
    Fusionne les codes CCAM/CIM-10 de tous les motifs.
    Supprime les doublons (même code).
    """
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
    Fusionne un motif principal avec des motifs secondaires.
    
    Règles de fusion :
    - Modules diagnostic et signes_gravite : concaténation de tous
    - Autres modules : motif principal uniquement
    - Ordonnances : fusion avec suppression des doublons
    - Codes CCAM : fusion avec suppression des doublons
    - Bulles et propositions : préservées pour chaque module
    """
    try:
        # Récupérer le motif principal
        motif_principal = await get_motif_complet(
            request.table_principale,
            request.motif_principal_id
        )
        
        # Liste de tous les motifs
        all_motifs_data = [motif_principal]
        
        # Récupérer les motifs secondaires
        for motif_sec in request.motifs_secondaires:
            motif_data = await get_motif_complet(
                motif_sec['table'],
                motif_sec['id']
            )
            all_motifs_data.append(motif_data)
        
        # Info sur les motifs utilisés
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
        
        # Fusionner les modules
        modules = fusionner_modules(all_motifs_data)
        
        # Fusionner les ordonnances
        ordonnances = fusionner_ordonnances(all_motifs_data)
        
        # Fusionner les codes CCAM
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
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la fusion: {str(e)}"
        )


# ============================================================================
# LANCEMENT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("🚀 Démarrage de l'API...")
    print(f"📊 Version: 3.0.0")
    print(f"🔗 URL: http://localhost:8000")
    print(f"📚 Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
