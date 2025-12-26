from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import httpx
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = "https://bnlybntkwazgcuatuplb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJubHlibnRrd2F6Z2N1YXR1cGxiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNjU0NjUsImV4cCI6MjA4MTY0MTQ2NX0.b876YQvlECMZWxSzQG6z5i9wcCRba6_PA9g-BW0RLik"

@app.get("/")
async def root():
    return {"service": "API STABLE", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "STABLE"}

@app.get("/categories")
async def get_categories():
    categories = [
        {"table_name": "CARDIOLOGIE", "nom": "Cardiologie"},
        {"table_name": "dermatologie", "nom": "Dermatologie"},
        {"table_name": "gastro_enterologie", "nom": "Gastro-entérologie"},
        {"table_name": "infectieux", "nom": "Infectieux"},
        {"table_name": "medecine_interne", "nom": "Médecine interne"},
        {"table_name": "neurologie", "nom": "Neurologie"},
        {"table_name": "orl", "nom": "ORL"},
        {"table_name": "pneumologie", "nom": "Pneumologie"},
        {"table_name": "traumatologie", "nom": "Traumatologie"},
        {"table_name": "urologie", "nom": "Urologie"}
    ]
    return {"categories": categories}

@app.get("/motifs/{table_name}")
async def get_motifs(table_name: str):
    async with httpx.AsyncClient() as client:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        try:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/{table_name}?select=id,nom_motif&order=ordre",
                headers=headers
            )
            if resp.status_code == 200:
                return {"motifs": resp.json()}
            return {"motifs": []}
        except:
            return {"motifs": []}

def traiter_ligne_avec_marqueurs(ligne: str):
    if not ligne:
        return []
    
    ligne = ligne.replace(''', "'").replace(''', "'")
    
    pattern_xxxx = r'XXXX(?:\s+PROPOSITION\s*:\s*([^F]+?)\s*FINI)?'
    pattern_alt = r'@@\s*([^@]+?)\s*@@'
    pattern_comment = r'\{\{([^}]+?)\}\}'
    pattern_delete = r'\[\[([^\]]+?)\]\]'
    
    marqueurs = []
    
    for m in re.finditer(pattern_xxxx, ligne, re.IGNORECASE):
        props = m.group(1)
        suggestions = [s.strip() for s in props.split(';')] if props else []
        marqueurs.append((m.start(), m.end(), 'XXXX', suggestions))
    
    for m in re.finditer(pattern_alt, ligne):
        alt_text = m.group(1)
        alts = [a.strip() for a in alt_text.split('/') if a.strip()]
        marqueurs.append((m.start(), m.end(), 'ALT', alts))
    
    for m in re.finditer(pattern_comment, ligne):
        marqueurs.append((m.start(), m.end(), 'COMMENT', m.group(1).strip()))
    
    for m in re.finditer(pattern_delete, ligne):
        marqueurs.append((m.start(), m.end(), 'DELETE', m.group(1).strip()))
    
    if not marqueurs:
        return [{"texte": ligne, "proposition": None, "alternative": None, "commentaire": None, "deletable": False}]
    
    marqueurs.sort(key=lambda x: x[0])
    
    elements = []
    pos = 0
    
    for start, end, mtype, data in marqueurs:
        if pos < start:
            texte_avant = ligne[pos:start]
            if texte_avant:
                elements.append({"texte": texte_avant, "proposition": None, "alternative": None, "commentaire": None, "deletable": False})
        
        if mtype == 'XXXX':
            elements.append({"texte": "XXXX", "proposition": {"suggestions": data} if data else None, "alternative": None, "commentaire": None, "deletable": False})
        elif mtype == 'ALT':
            elements.append({"texte": data[0] if data else "", "proposition": None, "alternative": {"alternatives": data}, "commentaire": None, "deletable": False})
        elif mtype == 'COMMENT':
            elements.append({"texte": data, "proposition": None, "alternative": None, "commentaire": True, "deletable": False})
        elif mtype == 'DELETE':
            elements.append({"texte": data, "proposition": None, "alternative": None, "commentaire": None, "deletable": True})
        
        pos = end
    
    if pos < len(ligne):
        texte_apres = ligne[pos:]
        if texte_apres:
            elements.append({"texte": texte_apres, "proposition": None, "alternative": None, "commentaire": None, "deletable": False})
    
    return elements

def traiter_texte_complet(texte: str):
    if not texte:
        return []
    
    texte = texte.replace('..', ' RET ')
    
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
        else:
            phrase_courante += texte[i]
            i += 1
    
    if phrase_courante.strip():
        phrases.append(phrase_courante.strip())
    
    lignes_finales = []
    
    for idx, phrase in enumerate(phrases):
        if not phrase:
            continue
        elements = traiter_ligne_avec_marqueurs(phrase)
        if elements and idx > 0:
            elements[0]['newline'] = True
        lignes_finales.extend(elements)
    
    return lignes_finales

class FusionRequest(BaseModel):
    table_principale: str
    motif_principal_id: str
    motifs_secondaires: List[Dict[str, Any]] = []
    mode: str = "conclusion"

@app.post("/fusion")
async def fusion(request: FusionRequest):
    async with httpx.AsyncClient() as client:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        
        try:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/{request.table_principale}?id=eq.{request.motif_principal_id}&select=*",
                headers=headers
            )
            
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail="Erreur Supabase")
            
            data = resp.json()
            if not data:
                raise HTTPException(status_code=404, detail="Motif non trouvé")
            
            motif = data[0]
            modules = []
            
            # HDM
            hdm_sections = []
            hdm_fields = [
                ('hdm_motif', 'Histoire de la maladie : Motif'),
                ('hdm_signes_associes', 'Histoire de la maladie : Signes associés'),
                ('hdm_contexte', 'Histoire de la maladie : Contexte'),
                ('hdm_soins_anterieurs', 'Histoire de la maladie : Soins antérieurs')
            ]
            
            for field, titre in hdm_fields:
                texte = motif.get(field, '')
                if texte and texte.strip():
                    lignes = traiter_texte_complet(texte)
                    if lignes:
                        hdm_sections.append({"titre": titre, "lignes": lignes})
            
            if hdm_sections:
                modules.append({"type": "hdm", "titre": "Histoire de la maladie", "sections": hdm_sections})
            
            # Autres modules
            simple_fields = [
                ('examen_clinique', 'Examen clinique'),
                ('examen_complementaire', 'Examens complémentaires'),
                ('diagnostic', 'Diagnostic'),
                ('conduite_a_tenir', 'Conduite à tenir')
            ]
            
            for field, titre in simple_fields:
                texte = motif.get(field, '')
                if texte and texte.strip():
                    lignes = traiter_texte_complet(texte)
                    if lignes:
                        modules.append({"type": field, "titre": titre, "lignes": lignes})
            
            return {"modules": modules, "ordonnances": [], "codes_cim": []}
            
        except Exception as e:
            print(f"Erreur: {e}")
            raise HTTPException(status_code=500, detail=str(e))
