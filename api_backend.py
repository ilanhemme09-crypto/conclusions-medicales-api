#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Backend - Conclusions Médicales v3.0.0
Améliorations : Propositions XXXX + Retours à ligne sur majuscules
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
import httpx
import json
import re

SUPABASE_URL = "https://bnlybntkwazgcuatuplb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJubHlibnRrd2F6Z2N1YXR1cGxiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNjU0NjUsImV4cCI6MjA4MTY0MTQ2NX0.b876YQvlECMZWxSzQG6z5i9wcCRba6_PA9g-BW0RLik"

app = FastAPI(title="API Conclusions v3", version="3.0.0")

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

class Proposition(BaseModel):
    suggestions: List[str]

class LigneAvecProposition(BaseModel):
    texte: str
    proposition: Proposition = None

class Module(BaseModel):
    type: str
    titre: str
    icon: str
    lignes: List[LigneAvecProposition]
    bulles: List[Bulle]

class Ordonnance(BaseModel):
    titre: str
    lignes: List[LigneAvecProposition]
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

# ===== FONCTIONS PARSING =====

def parse_bulles(texte: str):
    """Parse BULLE : titre : contenu FIN"""
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

def parse_propositions_et_xxxx(texte: str) -> List[LigneAvecProposition]:
    """
    Parse le texte en détectant :
    1. Les XXXX
    2. Les PROPOSITION...FINI qui suivent
    
    Retourne une liste de lignes avec propositions liées
    """
    lignes_finales = []
    
    # Séparer le texte en segments (XXXX...PROPOSITION...FINI)
    # Pattern : XXXX suivi éventuellement de PROPOSITION...FINI
    pattern = r'XXXX(?:\s*PROPOSITION\s*:\s*(.*?)\s*FINI)?'
    
    # Découper le texte en segments
    derniere_pos = 0
    for match in re.finditer(pattern, texte, re.IGNORECASE | re.DOTALL):
        # Texte avant XXXX
        texte_avant = texte[derniere_pos:match.start()].strip()
        if texte_avant:
            lignes_finales.append(LigneAvecProposition(texte=texte_avant, proposition=None))
        
        # XXXX avec ou sans proposition
        if match.group(1):  # Il y a PROPOSITION...FINI
            suggestions_str = match.group(1).strip()
            suggestions = [s.strip() for s in suggestions_str.split(';') if s.strip()]
            lignes_finales.append(LigneAvecProposition(
                texte="XXXX",
                proposition=Proposition(suggestions=suggestions)
            ))
        else:  # XXXX seul
            lignes_finales.append(LigneAvecProposition(texte="XXXX", proposition=None))
        
        derniere_pos = match.end()
    
    # Texte après le dernier match
    texte_apres = texte[derniere_pos:].strip()
    if texte_apres:
        lignes_finales.append(LigneAvecProposition(texte=texte_apres, proposition=None))
    
    return lignes_finales

def extraire_lignes(texte: str) -> List[str]:
    """
    Sépare le texte en lignes :
    - Par \n
    - Par ". " (point + espace)
    - Par majuscule après espace (nouvelle phrase)
    """
    if not texte:
        return []
    
    lignes = []
    
    # Étape 1 : Séparer par \n
    parties = texte.split('\n')
    
    for partie in parties:
        partie = partie.strip()
        if not partie:
            continue
        
        # Étape 2 : Séparer par ". "
        if '. ' in partie:
            phrases = partie.split('. ')
            for phrase in phrases:
                phrase = phrase.strip()
                if phrase:
                    if not phrase.endswith('.'):
                        phrase += '.'
                    lignes.append(phrase)
        else:
            # Étape 3 : Séparer par majuscule après espace
            # Pattern : Espace suivi d'une majuscule
            sous_phrases = re.split(r'(?<=\s)(?=[A-ZÀ-ÿ])', partie)
            for sp in sous_phrases:
                sp = sp.strip()
                if sp:
                    if not sp.endswith('.'):
                        sp += '.'
                    lignes.append(sp)
    
    return lignes

def supprimer_doublons(lignes: List[str]) -> List[str]:
    """Supprime les doublons"""
    vues = set()
    resultat = []
    
    for ligne in lignes:
        ligne_norm = ' '.join(ligne.lower().split())
        if ligne_norm not in vues:
            vues.add(ligne_norm)
            resultat.append(ligne)
    
    return resultat

def parse_codes_cim(texte: str):
    """Parse codes CIM-10"""
    if not texte:
        return []
    
    codes = []
    pattern = r'([A-Z]\d{2,3}(?:\.\d)?)\s*:\s*([^\n]+)'
    
    for match in re.finditer(pattern, texte):
        code = match.group(1).strip()
        libelle = match.group(2).strip()
        codes.append(CodeCIM(code=code, libelle=libelle))
    
    return codes

def traiter_texte_complet(texte: str) -> tuple:
    """
    Traite le texte complet :
    1. Parse bulles
    2. Parse propositions XXXX
    3. Extrait lignes
    4. Reconstruit avec propositions
    """
    # 1. Parser bulles
    texte_propre, bulles = parse_bulles(texte)
    
    # 2. Parser propositions et XXXX
    segments = parse_propositions_et_xxxx(texte_propre)
    
    # 3. Convertir segments en lignes avec propositions
    lignes_finales = []
    
    for segment in segments:
        if segment.texte == "XXXX":
            # C'est un XXXX, garder tel quel avec sa proposition
            lignes_finales.append(segment)
        else:
            # C'est du texte normal, séparer en lignes
            lignes_texte = extraire_lignes(segment.texte)
            for ligne in lignes_texte:
                lignes_finales.append(LigneAvecProposition(texte=ligne, proposition=None))
    
    return lignes_finales, bulles

# ===== ENDPOINTS =====

@app.get("/")
async def root():
    return {"service": "API Conclusions v3", "version": "3.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    try:
        r = await client.get(f"{SUPABASE_URL}/rest/v1/vue_categories?select=count", headers=HEADERS)
        if r.status_code == 200:
            return {"status": "healthy", "database": "connected"}
        return {"status": "degraded"}
    except:
        return {"status": "unhealthy"}

@app.get("/categories", response_model=List[Categorie])
async def get_categories():
    try:
        r = await client.get(f"{SUPABASE_URL}/rest/v1/vue_categories?select=*&order=ordre.asc", headers=HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/motifs/{table_name}", response_model=List[Motif])
async def get_motifs(table_name: str):
    try:
        r = await client.get(f"{SUPABASE_URL}/rest/v1/{table_name}?select=id,nom_motif,ordre&order=ordre.asc", headers=HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(500, str(e))

async def get_motif_complet(table_name: str, motif_id: str):
    try:
        r = await client.get(f"{SUPABASE_URL}/rest/v1/{table_name}?id=eq.{motif_id}&select=*", headers=HEADERS)
        r.raise_for_status()
        data = r.json()
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
        
        # ===== FUSION MODULES =====
        modules_finaux = []
        
        for module_type, config in MODULES_CONFIG.items():
            toutes_les_lignes = []
            toutes_les_bulles = []
            
            for idx, motif in enumerate(tous_les_motifs):
                est_principal = (idx == 0)
                
                if module_type in ['diagnostic', 'signes_gravite']:
                    if motif.get(module_type):
                        lignes, bulles = traiter_texte_complet(motif[module_type])
                        toutes_les_lignes.extend(lignes)
                        toutes_les_bulles.extend(bulles)
                
                elif est_principal and motif.get(module_type):
                    lignes, bulles = traiter_texte_complet(motif[module_type])
                    toutes_les_lignes.extend(lignes)
                    toutes_les_bulles.extend(bulles)
            
            # Supprimer doublons (comparer seulement le texte)
            lignes_vues = set()
            lignes_uniques = []
            for ligne in toutes_les_lignes:
                ligne_norm = ' '.join(ligne.texte.lower().split())
                if ligne_norm not in lignes_vues:
                    lignes_vues.add(ligne_norm)
                    lignes_uniques.append(ligne)
            
            if lignes_uniques:
                modules_finaux.append(Module(
                    type=module_type,
                    titre=config['titre'],
                    icon=config['icon'],
                    lignes=lignes_uniques,
                    bulles=toutes_les_bulles
                ))
        
        # ===== FUSION ORDONNANCES =====
        ordonnances_finales = []
        ordos_vues = set()
        
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
                
                lignes, bulles = traiter_texte_complet(str(contenu_ordo))
                
                cle = f"{titre_ordo}_{lignes[0].texte[:50] if lignes else ''}"
                
                if cle not in ordos_vues:
                    ordos_vues.add(cle)
                    ordonnances_finales.append(Ordonnance(
                        titre=titre_ordo.replace('_', ' ').title(),
                        lignes=lignes,
                        bulles=bulles
                    ))
        
        # ===== CODES CIM =====
        codes_finaux = []
        codes_vus = set()
        
        for motif in tous_les_motifs:
            if motif.get('codage_cim10'):
                codes = parse_codes_cim(motif['codage_cim10'])
                for code in codes:
                    if code.code not in codes_vus:
                        codes_vus.add(code.code)
                        codes_finaux.append(code)
        
        return FusionResponse(
            modules=modules_finaux,
            ordonnances=ordonnances_finales,
            codes_cim=codes_finaux
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 API v3.0.0 - Propositions XXXX + Retours ligne majuscules")
    uvicorn.run(app, host="0.0.0.0", port=8000)
