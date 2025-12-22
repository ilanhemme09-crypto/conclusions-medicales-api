#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Backend v4.0.0 - Examens + Conclusions
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Literal
import httpx
import json
import re
import traceback

SUPABASE_URL = "https://bnlybntkwazgcuatuplb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJubHlibnRrd2F6Z2N1YXR1cGxiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNjU0NjUsImV4cCI6MjA4MTY0MTQ2NX0.b876YQvlECMZWxSzQG6z5i9wcCRba6_PA9g-BW0RLik"

app = FastAPI(title="API Conclusions v4.0.0")

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
    proposition: Optional[Proposition] = None

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
    mode: Literal["examen", "conclusion", "examen_conclusion"] = "conclusion"

class FusionResponse(BaseModel):
    modules: List[Module]
    ordonnances: List[Ordonnance]
    codes_cim: List[CodeCIM]

# Configuration modules CONCLUSION
MODULES_CONCLUSION = {
    'diagnostic': {'titre': 'DIAGNOSTIC', 'icon': '🔍', 'ordre': 1},
    'signes_gravite': {'titre': 'SIGNES DE GRAVITÉ', 'icon': '⚠️', 'ordre': 2},
    'soins_urgences': {'titre': 'AUX URGENCES', 'icon': '🏥', 'ordre': 3},
    'conduite_tenir': {'titre': 'CONDUITE À TENIR', 'icon': '📋', 'ordre': 4},
    'conseils': {'titre': 'CONSEILS', 'icon': '💡', 'ordre': 5},
    'suivi': {'titre': 'SUIVI', 'icon': '📅', 'ordre': 6},
    'consignes_reconsultation': {'titre': 'CONSIGNES DE RECONSULTATION', 'icon': '🚨', 'ordre': 7}
}

# Configuration modules EXAMEN
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

# Modules HDM (regroupés)
MODULES_HDM = ['hdm_motif', 'hdm_signes_associes', 'hdm_contexte', 'hdm_soins_anterieurs']

# ===== FONCTIONS PARSING =====

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
            bulles.append(Bulle(titre=titre, contenu=contenu))
        texte_propre = re.sub(pattern, '', texte_propre, flags=re.IGNORECASE | re.DOTALL)
        texte_propre = ' '.join(texte_propre.split())
        return texte_propre, bulles
    except Exception as e:
        print(f"Erreur parse_bulles: {e}")
        return texte, []

def extraire_propositions(texte: str):
    propositions_map = {}
    try:
        pattern = r'XXXX\s+PROPOSITION\s*:\s*([^F]+?)\s*FINI'
        for match in re.finditer(pattern, texte, re.IGNORECASE):
            position = match.start()
            suggestions_str = match.group(1).strip()
            suggestions = [s.strip() for s in suggestions_str.split(';') if s.strip()]
            if suggestions:
                propositions_map[position] = suggestions
        texte_propre = re.sub(r'\s+PROPOSITION\s*:[^F]+?FINI', '', texte, flags=re.IGNORECASE)
        return texte_propre, propositions_map
    except Exception as e:
        print(f"Erreur extraire_propositions: {e}")
        return texte, {}

def extraire_lignes(texte: str) -> List[str]:
    if not texte:
        return []
    try:
        lignes = []
        parties = texte.split('\n')
        for partie in parties:
            partie = partie.strip()
            if not partie:
                continue
            if '. ' in partie:
                phrases = partie.split('. ')
                for phrase in phrases:
                    phrase = phrase.strip()
                    if phrase:
                        if not phrase.endswith('.'):
                            phrase += '.'
                        lignes.append(phrase)
            else:
                sous_phrases = re.split(r'(?<=\s)(?=[A-ZÀ-Ÿ])', partie)
                for sp in sous_phrases:
                    sp = sp.strip()
                    if sp:
                        if not sp.endswith('.'):
                            sp += '.'
                        lignes.append(sp)
        return lignes
    except Exception as e:
        print(f"Erreur extraire_lignes: {e}")
        return [texte] if texte else []

def traiter_texte_avec_xxxx(texte: str):
    if not texte:
        return []
    try:
        texte_propre, propositions_map = extraire_propositions(texte)
        xxxx_positions = [m.start() for m in re.finditer(r'XXXX', texte_propre, re.IGNORECASE)]
        xxxx_avec_props = []
        for pos in xxxx_positions:
            props = None
            for prop_pos, suggestions in propositions_map.items():
                if abs(pos - prop_pos) < 50:
                    props = Proposition(suggestions=suggestions)
                    break
            xxxx_avec_props.append((pos, props))
        
        lignes_finales = []
        derniere_pos = 0
        
        for idx, (xxxx_pos, props) in enumerate(xxxx_avec_props):
            texte_avant = texte_propre[derniere_pos:xxxx_pos].strip()
            if texte_avant:
                lignes_texte = extraire_lignes(texte_avant)
                for ligne in lignes_texte:
                    lignes_finales.append(LigneAvecProposition(texte=ligne, proposition=None))
            lignes_finales.append(LigneAvecProposition(texte="XXXX", proposition=props))
            derniere_pos = xxxx_pos + 4
        
        texte_apres = texte_propre[derniere_pos:].strip()
        if texte_apres:
            lignes_texte = extraire_lignes(texte_apres)
            for ligne in lignes_texte:
                lignes_finales.append(LigneAvecProposition(texte=ligne, proposition=None))
        
        if not xxxx_avec_props:
            lignes_texte = extraire_lignes(texte_propre)
            for ligne in lignes_texte:
                lignes_finales.append(LigneAvecProposition(texte=ligne, proposition=None))
        
        return lignes_finales
        
    except Exception as e:
        print(f"Erreur traiter_texte_avec_xxxx: {e}")
        traceback.print_exc()
        lignes_simple = extraire_lignes(texte)
        return [LigneAvecProposition(texte=l, proposition=None) for l in lignes_simple]

def supprimer_doublons(lignes: List[LigneAvecProposition]) -> List[LigneAvecProposition]:
    try:
        vues = set()
        resultat = []
        for ligne in lignes:
            ligne_norm = ' '.join(ligne.texte.lower().split())
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
            codes.append(CodeCIM(code=code, libelle=libelle))
        return codes
    except Exception as e:
        print(f"Erreur parse_codes_cim: {e}")
        return []

# ===== ENDPOINTS =====

@app.get("/")
async def root():
    return {"service": "API v4.0.0", "status": "running", "features": ["examen", "conclusion", "examen_conclusion"]}

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
        print(f"=== FUSION MODE: {request.mode} ===")
        
        motif_principal = await get_motif_complet(request.table_principale, request.motif_principal_id)
        tous_les_motifs = [motif_principal]
        
        for motif_sec in request.motifs_secondaires:
            motif_data = await get_motif_complet(motif_sec.table, motif_sec.id)
            tous_les_motifs.append(motif_data)
        
        modules_finaux = []
        
        # ===== MODE EXAMEN : HDM + EXAMEN =====
        if request.mode in ["examen", "examen_conclusion"]:
            # Fusion des 4 modules HDM en un seul
            hdm_lignes_totales = []
            for motif in tous_les_motifs:
                for hdm_module in MODULES_HDM:
                    if motif.get(hdm_module):
                        texte_propre, _ = parse_bulles(motif[hdm_module])
                        lignes = traiter_texte_avec_xxxx(texte_propre)
                        hdm_lignes_totales.extend(lignes)
            
            if hdm_lignes_totales:
                hdm_uniques = supprimer_doublons(hdm_lignes_totales)
                modules_finaux.append(Module(
                    type='hdm',
                    titre='HISTOIRE DE LA MALADIE',
                    icon='📝',
                    lignes=hdm_uniques,
                    bulles=[]
                ))
            
            # Modules EXAMEN séparés
            for module_type, config in MODULES_EXAMEN.items():
                toutes_les_lignes = []
                toutes_les_bulles = []
                
                for idx, motif in enumerate(tous_les_motifs):
                    if motif.get(module_type):
                        texte = motif[module_type]
                        texte_propre, bulles = parse_bulles(texte)
                        lignes = traiter_texte_avec_xxxx(texte_propre)
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
                            lignes = traiter_texte_avec_xxxx(texte_propre)
                            toutes_les_lignes.extend(lignes)
                            toutes_les_bulles.extend(bulles)
                    
                    elif est_principal and motif.get(module_type):
                        texte = motif[module_type]
                        texte_propre, bulles = parse_bulles(texte)
                        lignes = traiter_texte_avec_xxxx(texte_propre)
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
        
        # ===== ORDONNANCES (toujours incluses) =====
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
                lignes = traiter_texte_avec_xxxx(texte_propre)
                cle = f"{titre_ordo}_{lignes[0].texte[:30] if lignes else ''}"
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
        
        print(f"=== FIN FUSION: {len(modules_finaux)} modules ===")
        
        return FusionResponse(
            modules=modules_finaux,
            ordonnances=ordonnances_finales,
            codes_cim=codes_finaux
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERREUR: {e}")
        traceback.print_exc()
        raise HTTPException(500, f"Erreur: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 API v4.0.0 - Examens + Conclusions")
    uvicorn.run(app, host="0.0.0.0", port=8000)
