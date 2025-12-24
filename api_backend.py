from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import traceback
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = "https://lqsknjgtdszxdltyxdjy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxxc2tuamd0ZHN6eGRsdHl4ZGp5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQzNjM3MjksImV4cCI6MjA3OTkzOTcyOX0.Dxog-tz5OIrH_ypUn4GGKSOMWuL72M_q1gD8EuGHOno"

MODULES_HDM = ['hdm_motif', 'hdm_signes_associes', 'hdm_contexte', 'hdm_soins_anterieurs']

HDM_TITLES = {
    'hdm_motif': 'Histoire de la maladie : Motif',
    'hdm_signes_associes': 'Histoire de la maladie : Signes associés',
    'hdm_contexte': 'Histoire de la maladie : Contexte',
    'hdm_soins_anterieurs': 'Histoire de la maladie : Soins antérieurs'
}

@app.get("/")
async def root():
    return {"service": "API v4.4.4-STABLE", "status": "running"}

def traiter_ligne_avec_marqueurs(ligne: str):
    """Parse TOUS les marqueurs dans une ligne"""
    if not ligne:
        return []
    
    # Normaliser apostrophes
    ligne = ligne.replace(''', "'").replace(''', "'").replace('´', "'").replace('`', "'")
    ligne = ligne.replace('"', '"').replace('"', '"')
    
    # Patterns
    pattern_xxxx = r'XXXX(?:\s+PROPOSITION\s*:\s*([^F]+?)\s*FINI)?'
    pattern_alt = r'@@\s*([^@]+?)\s*@@'
    pattern_comment = r'\{\{([^}]+?)\}\}'
    pattern_delete = r'\[\[([^\]]+?)\]\]'
    
    # Trouver marqueurs
    marqueurs = []
    
    # XXXX
    for m in re.finditer(pattern_xxxx, ligne, re.IGNORECASE):
        props = m.group(1)
        suggestions = [s.strip() for s in props.split(';')] if props else []
        marqueurs.append((m.start(), m.end(), 'XXXX', suggestions))
    
    # Alternatives
    for m in re.finditer(pattern_alt, ligne):
        alt_text = m.group(1)
        alts = [a.strip() for a in alt_text.split('/') if a.strip()]
        if not alts:
            alts = [m.group(1).strip()]
        marqueurs.append((m.start(), m.end(), 'ALT', alts))
    
    # Commentaires
    for m in re.finditer(pattern_comment, ligne):
        marqueurs.append((m.start(), m.end(), 'COMMENT', m.group(1).strip()))
    
    # Suppressibles
    for m in re.finditer(pattern_delete, ligne):
        marqueurs.append((m.start(), m.end(), 'DELETE', m.group(1).strip()))
    
    # Si aucun marqueur
    if not marqueurs:
        return [{"texte": ligne, "proposition": None, "alternative": None, "commentaire": None, "deletable": False}]
    
    # Trier par position
    marqueurs.sort(key=lambda x: x[0])
    
    # Construire éléments
    elements = []
    pos = 0
    
    for start, end, mtype, data in marqueurs:
        # Texte avant
        if pos < start:
            texte_avant = ligne[pos:start]
            if texte_avant:
                elements.append({"texte": texte_avant, "proposition": None, "alternative": None, "commentaire": None, "deletable": False})
        
        # Marqueur
        if mtype == 'XXXX':
            elements.append({"texte": "XXXX", "proposition": {"suggestions": data} if data else None, "alternative": None, "commentaire": None, "deletable": False})
        elif mtype == 'ALT':
            elements.append({"texte": data[0], "proposition": None, "alternative": {"alternatives": data}, "commentaire": None, "deletable": False})
        elif mtype == 'COMMENT':
            elements.append({"texte": data, "proposition": None, "alternative": None, "commentaire": True, "deletable": False})
        elif mtype == 'DELETE':
            elements.append({"texte": data, "proposition": None, "alternative": None, "commentaire": None, "deletable": True})
        
        pos = end
    
    # Texte après
    if pos < len(ligne):
        texte_apres = ligne[pos:]
        if texte_apres:
            elements.append({"texte": texte_apres, "proposition": None, "alternative": None, "commentaire": None, "deletable": False})
    
    return elements

def traiter_texte_complet(texte: str):
    """Split sur RET et parse marqueurs"""
    if not texte:
        return []
    
    try:
        # Split sur RET
        phrases = []
        phrase_courante = ""
        
        i = 0
        while i < len(texte):
            if i + 2 < len(texte) and texte[i:i+3] == 'RET':
                if phrase_courante.strip():
                    phrases.append(phrase_courante.strip())
                phrase_courante = ""
                i += 3
                while i < len(texte) and texte[i] == ' ':
                    i += 1
                continue
            else:
                phrase_courante += texte[i]
                i += 1
        
        if phrase_courante.strip():
            phrases.append(phrase_courante.strip())
        
        # Parser chaque phrase
        lignes_finales = []
        
        for idx, phrase in enumerate(phrases):
            if not phrase:
                continue
            
            elements = traiter_ligne_avec_marqueurs(phrase)
            
            # Marquer nouvelle ligne
            if elements and idx > 0:
                elements[0]['newline'] = True
            
            lignes_finales.extend(elements)
        
        return lignes_finales
        
    except Exception as e:
        print(f"Erreur traiter_texte_complet: {e}")
        return [{"texte": texte, "proposition": None, "alternative": None, "commentaire": None, "deletable": False}]

class FusionRequest(BaseModel):
    motif_id: int
    categories: List[str]

@app.post("/fusion")
async def fusion(request: FusionRequest):
    try:
        async with httpx.AsyncClient() as client:
            # Récupérer motif
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
            
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/traumatologie?id=eq.{request.motif_id}",
                headers=headers
            )
            
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail="Erreur Supabase")
            
            data = resp.json()
            if not data:
                raise HTTPException(status_code=404, detail="Motif non trouvé")
            
            motif = data[0]
            
            # Construire modules
            modules = []
            ordonnances = []
            codes_cim = []
            
            # HDM sections
            hdm_sections = {}
            for field in MODULES_HDM:
                texte = motif.get(field, '')
                if texte:
                    hdm_sections[field] = traiter_texte_complet(texte)
            
            # Autres champs simples
            for field in ['examen_clinique', 'examen_complementaire', 'diagnostic', 'conduite_a_tenir']:
                texte = motif.get(field, '')
                if texte:
                    lignes = traiter_texte_complet(texte)
                    modules.append({
                        "type": field,
                        "titre": field.replace('_', ' ').title(),
                        "lignes": lignes
                    })
            
            # HDM module
            if any(hdm_sections.values()):
                sections = []
                for field in MODULES_HDM:
                    if field in hdm_sections and hdm_sections[field]:
                        sections.append({
                            "titre": HDM_TITLES[field],
                            "lignes": hdm_sections[field]
                        })
                
                if sections:
                    modules.insert(0, {
                        "type": "hdm",
                        "titre": "Histoire de la maladie",
                        "sections": sections
                    })
            
            # Ordonnances
            for i in range(1, 6):
                ordo_text = motif.get(f'ordonnance_{i}', '')
                if ordo_text:
                    ordonnances.append({
                        "titre": f"Ordonnance {i}",
                        "lignes": traiter_texte_complet(ordo_text)
                    })
            
            # CIM-10
            for i in range(1, 4):
                code = motif.get(f'code_cim10_{i}', '')
                if code:
                    codes_cim.append(code)
            
            return {
                "modules": modules,
                "ordonnances": ordonnances,
                "codes_cim": codes_cim
            }
            
    except Exception as e:
        print(f"Erreur fusion: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
