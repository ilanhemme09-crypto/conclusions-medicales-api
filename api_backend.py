#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Backend v4.3.0 - CORRECTIFS MAJEURS
- {{ }} et [[ ]] fonctionnent
- Split uniquement sur points (sans afficher points)
- HDM avec 4 sous-sections
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import json
import re
import traceback

SUPABASE_URL = "https://bnlybntkwazgcuatuplb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJubHlibnRrd2F6Z2N1YXR1cGxiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNjU0NjUsImV4cCI6MjA4MTY0MTQ2NX0.b876YQvlECMZWxSzQG6z5i9wcCRba6_PA9g-BW0RLik"

app = FastAPI(title="API Conclusions v4.3.0")

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
    motifs_secondaires: list = []
    mode: str = "conclusion"

MODULES_CONCLUSION = {
    'diagnostic': {'titre': 'DIAGNOSTIC', 'icon': '🔍', 'ordre': 1},
    'signes_gravite': {'titre': 'SIGNES DE GRAVITÉ', 'icon': '⚠️', 'ordre': 2},
    'soins_urgences': {'titre': 'AUX URGENCES', 'icon': '🏥', 'ordre': 3},
    'conduite_tenir': {'titre': 'CONDUITE À TENIR', 'icon': '📋', 'ordre': 4},
    'conseils': {'titre': 'CONSEILS', 'icon': '💡', 'ordre': 5},
    'suivi': {'titre': 'SUIVI', 'icon': '📅', 'ordre': 6},
    'consignes_reconsultation': {'titre': 'CONSIGNES DE RECONSULTATION', 'icon': '🚨', 'ordre': 7}
}

MODULES_EXAMEN = {
    'examen_cardiologique': {'titre': 'EXAMEN CARDIOLOGIQUE', 'icon': '❤️', 'ordre': 1},
    'examen_pneumologique': {'titre': 'EXAMEN PNEUMOLOGIQUE', 'icon': '🫁', 'ordre': 2},
    'examen_neurologique': {'titre': 'EXAMEN NEUROLOGIQUE', 'icon': '🧠', 'ordre': 3},
    'examen_digestif': {'titre': 'EXAMEN DIGESTIF', 'icon': '🫃', 'ordre': 4},
    'examen_urologique': {'titre': 'EXAMEN UROLOGIQUE', 'icon': '💧', 'ordre': 5},
    'examen_traumatologique': {'titre': 'EXAMEN TRAUMATOLOGIQUE', 'icon': '🦴', 'ordre': 6},
    'examen_dermatologique': {'titre': 'EXAMEN DERMATOLOGIQUE', 'icon': '👤', 'ordre': 7},
    'examen_ophtalmologique': {'titre': 'EXAMEN OPHTALMOLOGIQUE', 'icon': '👁️', 'ordre': 8},
    'examen_orl': {'titre': 'EXAMEN ORL', 'icon': '👂', 'ordre': 9}
}

MODULES_HDM = ['hdm_motif', 'hdm_signes_associes', 'hdm_contexte', 'hdm_soins_anterieurs']

HDM_TITLES = {
    'hdm_motif': 'Histoire de la maladie : Motif',
    'hdm_signes_associes': 'Histoire de la maladie : Signes associés',
    'hdm_contexte': 'Histoire de la maladie : Contexte',
    'hdm_soins_anterieurs': 'Histoire de la maladie : Soins antérieurs'
}

def parse_bulles(texte: str):
    if not texte:
        return "", []
    try:
        bulles = []
        texte_propre = texte
        pattern = r'BULLE\s*:\s*([^:]+?)\s*:\s*(.*?)\s*FIN'
        for match in re.finditer(pattern, texte, re.IGNORECASE | re.DOTALL):
            titre = match.group(1).strip()
            contenu = match.group(2).strip()
            bulles.append({"titre": titre, "contenu": contenu})
        texte_propre = re.sub(pattern, '', texte_propre, flags=re.IGNORECASE | re.DOTALL)
        texte_propre = ' '.join(texte_propre.split())
        return texte_propre, bulles
    except Exception as e:
        print(f"Erreur parse_bulles: {e}")
        return texte, []

def traiter_ligne_avec_marqueurs(ligne: str):
    """Traite une ligne et extrait les marqueurs inline"""
    if not ligne:
        return []
    
    # Pattern pour trouver tous les marqueurs
    pattern_xxxx = r'XXXX(?:\s+PROPOSITION\s*:\s*([^F]+?)\s*FINI)?'
    pattern_alt = r'@@\s*([^@]+?)\s*@@'
    pattern_comment = r'\{\{\s*([^}]+?)\s*\}\}'
    pattern_delete = r'\[\[\s*([^\]]+?)\s*\]\]'
    
    result = []
    pos = 0
    
    # Trouver tous les marqueurs avec leur position
    marqueurs = []
    
    for m in re.finditer(pattern_xxxx, ligne, re.IGNORECASE):
        props = m.group(1)
        suggestions = [s.strip() for s in props.split(';')] if props else []
        marqueurs.append((m.start(), m.end(), 'XXXX', suggestions))
    
    for m in re.finditer(pattern_alt, ligne):
        alts = [a.strip() for a in m.group(1).split(';')]
        marqueurs.append((m.start(), m.end(), 'ALT', alts))
    
    for m in re.finditer(pattern_comment, ligne):
        marqueurs.append((m.start(), m.end(), 'COMMENT', m.group(1).strip()))
    
    for m in re.finditer(pattern_delete, ligne):
        marqueurs.append((m.start(), m.end(), 'DELETE', m.group(1).strip()))
    
    # Trier par position
    marqueurs.sort(key=lambda x: x[0])
    
    for start, end, mtype, data in marqueurs:
        # Texte avant le marqueur
        if pos < start:
            texte_avant = ligne[pos:start].strip()
            if texte_avant:
                result.append({
                    "texte": texte_avant,
                    "proposition": None,
                    "alternative": None,
                    "commentaire": None,
                    "deletable": False
                })
        
        # Le marqueur lui-même
        if mtype == 'XXXX':
            result.append({
                "texte": "XXXX",
                "proposition": {"suggestions": data} if data else None,
                "alternative": None,
                "commentaire": None,
                "deletable": False
            })
        elif mtype == 'ALT':
            result.append({
                "texte": data[0] if data else "",
                "proposition": None,
                "alternative": {"alternatives": data},
                "commentaire": None,
                "deletable": False
            })
        elif mtype == 'COMMENT':
            result.append({
                "texte": data,
                "proposition": None,
                "alternative": None,
                "commentaire": True,
                "deletable": False
            })
        elif mtype == 'DELETE':
            result.append({
                "texte": data,
                "proposition": None,
                "alternative": None,
                "commentaire": None,
                "deletable": True
            })
        
        pos = end
    
    # Texte après le dernier marqueur
    if pos < len(ligne):
        texte_apres = ligne[pos:].strip()
        if texte_apres:
            result.append({
                "texte": texte_apres,
                "proposition": None,
                "alternative": None,
                "commentaire": None,
                "deletable": False
            })
    
    # Si aucun marqueur, retourner la ligne brute
    if not result:
        result.append({
            "texte": ligne,
            "proposition": None,
            "alternative": None,
            "commentaire": None,
            "deletable": False
        })
    
    return result

def traiter_texte_complet(texte: str):
    """Split sur points uniquement, traite marqueurs inline"""
    if not texte:
        return []
    
    try:
        # Split sur les points UNIQUEMENT
        phrases = texte.split('.')
        
        lignes_finales = []
        
        for phrase in phrases:
            phrase = phrase.strip()
            if not phrase:
                continue
            
            # Traiter les marqueurs dans cette phrase
            lignes_phrase = traiter_ligne_avec_marqueurs(phrase)
            lignes_finales.extend(lignes_phrase)
        
        return lignes_finales
        
    except Exception as e:
        print(f"Erreur traiter_texte_complet: {e}")
        traceback.print_exc()
        return [{
            "texte": texte,
            "proposition": None,
            "alternative": None,
            "commentaire": None,
            "deletable": False
        }]

def supprimer_doublons(lignes):
    try:
        vues = set()
        resultat = []
        for ligne in lignes:
            ligne_norm = ' '.join(ligne["texte"].lower().split())
            if ligne_norm not in vues:
                vues.add(ligne_norm)
                resultat.append(ligne)
        return resultat
    except Exception as e:
        print(f"Erreur supprimer_doublons: {e}")
        return lignes

def parse_codes_cim(texte: str):
    if not texte:
        return []
    try:
        codes = []
        pattern = r'([A-Z]\d{2,3}(?:\.\d)?)\s*:\s*([^\n]+)'
        for match in re.finditer(pattern, texte):
            code = match.group(1).strip()
            libelle = match.group(2).strip()
            codes.append({"code": code, "libelle": libelle})
        return codes
    except Exception as e:
        print(f"Erreur parse_codes_cim: {e}")
        return []

@app.get("/")
async def root():
    return {"service": "API v4.3.0", "status": "running", "features": ["HDM 4 sections", "{{ }}", "[[ ]]", "split on dots"]}

@app.get("/health")
async def health_check():
    try:
        r = await client.get(f"{SUPABASE_URL}/rest/v1/vue_categories?select=count", headers=HEADERS)
        if r.status_code == 200:
            return {"status": "healthy", "database": "connected"}
        return {"status": "degraded"}
    except:
        return {"status": "unhealthy"}

@app.get("/categories")
async def get_categories():
    try:
        r = await client.get(f"{SUPABASE_URL}/rest/v1/vue_categories?select=*&order=ordre.asc", headers=HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/motifs/{table_name}")
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

@app.post("/fusion")
async def fusion_motifs(request: FusionRequest):
    try:
        print(f"=== FUSION MODE: {request.mode} ===")
        
        motif_principal = await get_motif_complet(request.table_principale, request.motif_principal_id)
        tous_les_motifs = [motif_principal]
        
        for motif_sec in request.motifs_secondaires:
            motif_data = await get_motif_complet(motif_sec["table"], motif_sec["id"])
            tous_les_motifs.append(motif_data)
        
        modules_finaux = []
        
        # ===== MODE EXAMEN : HDM + EXAMEN =====
        if request.mode in ["examen", "examen_conclusion"]:
            # HDM structuré avec 4 sections
            hdm_sections = {}
            
            for hdm_module in MODULES_HDM:
                hdm_sections[hdm_module] = []
                
                for motif in tous_les_motifs:
                    if motif.get(hdm_module):
                        texte_propre, _ = parse_bulles(motif[hdm_module])
                        lignes = traiter_texte_complet(texte_propre)
                        hdm_sections[hdm_module].extend(lignes)
                
                # Supprimer doublons dans chaque section
                hdm_sections[hdm_module] = supprimer_doublons(hdm_sections[hdm_module])
            
            # Créer le module HDM avec sections
            modules_finaux.append({
                "type": 'hdm',
                "titre": 'HISTOIRE DE LA MALADIE',
                "icon": '📝',
                "sections": [
                    {
                        "titre": HDM_TITLES['hdm_motif'],
                        "lignes": hdm_sections['hdm_motif']
                    },
                    {
                        "titre": HDM_TITLES['hdm_signes_associes'],
                        "lignes": hdm_sections['hdm_signes_associes']
                    },
                    {
                        "titre": HDM_TITLES['hdm_contexte'],
                        "lignes": hdm_sections['hdm_contexte']
                    },
                    {
                        "titre": HDM_TITLES['hdm_soins_anterieurs'],
                        "lignes": hdm_sections['hdm_soins_anterieurs']
                    }
                ],
                "bulles": []
            })
            
            for module_type, config in MODULES_EXAMEN.items():
                toutes_les_lignes = []
                toutes_les_bulles = []
                
                for motif in tous_les_motifs:
                    if motif.get(module_type):
                        texte = motif[module_type]
                        texte_propre, bulles = parse_bulles(texte)
                        lignes = traiter_texte_complet(texte_propre)
                        toutes_les_lignes.extend(lignes)
                        toutes_les_bulles.extend(bulles)
                
                lignes_uniques = supprimer_doublons(toutes_les_lignes)
                
                if lignes_uniques:
                    modules_finaux.append({
                        "type": module_type,
                        "titre": config['titre'],
                        "icon": config['icon'],
                        "lignes": lignes_uniques,
                        "bulles": toutes_les_bulles
                    })
        
        # ===== MODE CONCLUSION =====
        if request.mode in ["conclusion", "examen_conclusion"]:
            for module_type, config in MODULES_CONCLUSION.items():
                toutes_les_lignes = []
                toutes_les_bulles = []
                
                for idx, motif in enumerate(tous_les_motifs):
                    est_principal = (idx == 0)
                    
                    if module_type in ['diagnostic', 'signes_gravite']:
                        if motif.get(module_type):
                            texte = motif[module_type]
                            texte_propre, bulles = parse_bulles(texte)
                            lignes = traiter_texte_complet(texte_propre)
                            toutes_les_lignes.extend(lignes)
                            toutes_les_bulles.extend(bulles)
                    
                    elif est_principal and motif.get(module_type):
                        texte = motif[module_type]
                        texte_propre, bulles = parse_bulles(texte)
                        lignes = traiter_texte_complet(texte_propre)
                        toutes_les_lignes.extend(lignes)
                        toutes_les_bulles.extend(bulles)
                
                lignes_uniques = supprimer_doublons(toutes_les_lignes)
                
                if lignes_uniques:
                    modules_finaux.append({
                        "type": module_type,
                        "titre": config['titre'],
                        "icon": config['icon'],
                        "lignes": lignes_uniques,
                        "bulles": toutes_les_bulles
                    })
        
        # ===== ORDONNANCES =====
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
                texte_ordo = str(contenu_ordo)
                texte_propre, bulles = parse_bulles(texte_ordo)
                lignes = traiter_texte_complet(texte_propre)
                cle = f"{titre_ordo}_{lignes[0]['texte'][:30] if lignes else ''}"
                if cle not in ordos_vues:
                    ordos_vues.add(cle)
                    ordonnances_finales.append({
                        "titre": titre_ordo.replace('_', ' ').title(),
                        "lignes": lignes,
                        "bulles": bulles
                    })
        
        # ===== CODES CIM =====
        codes_finaux = []
        codes_vus = set()
        for motif in tous_les_motifs:
            if motif.get('codage_cim10'):
                codes = parse_codes_cim(motif['codage_cim10'])
                for code in codes:
                    if code["code"] not in codes_vus:
                        codes_vus.add(code["code"])
                        codes_finaux.append(code)
        
        print(f"=== FIN FUSION: {len(modules_finaux)} modules ===")
        
        return {
            "modules": modules_finaux,
            "ordonnances": ordonnances_finales,
            "codes_cim": codes_finaux
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERREUR: {e}")
        traceback.print_exc()
        raise HTTPException(500, f"Erreur: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 API v4.3.0 - HDM 4 sections + {{ }} + [[ ]]")
    uvicorn.run(app, host="0.0.0.0", port=8000)
