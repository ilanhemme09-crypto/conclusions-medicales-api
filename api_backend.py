from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
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

# VOTRE BASE SUPABASE
SUPABASE_URL = "https://bnlybntkwazgcuatuplb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJubHlibnRrd2F6Z2N1YXR1cGxiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjYwNjU0NjUsImV4cCI6MjA4MTY0MTQ2NX0.b876YQvlECMZWxSzQG6z5i9wcCRba6_PA9g-BW0RLik"

@app.get("/")
async def root():
    return {"service": "API v5.2-DOTDOT-SPLIT", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "5.2"}

@app.get("/categories")
async def get_categories():
    # Liste fixe des catégories (tables Supabase)
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
        try:
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
            
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/{table_name}?select=id,nom_motif&order=ordre",
                headers=headers
            )
            
            if resp.status_code == 200:
                return {"motifs": resp.json()}
            else:
                return {"motifs": []}
        except Exception as e:
            print(f"Erreur motifs: {e}")
            return {"motifs": []}

def traiter_ligne_simple(ligne: str):
    """Parse marqueurs de façon simple"""
    if not ligne:
        return []
    
    # Normaliser apostrophes
    ligne = ligne.replace(''', "'").replace(''', "'")
    
    elements = []
    
    # Trouver tous les XXXX
    xxxx_positions = [(m.start(), m.end()) for m in re.finditer(r'XXXX', ligne, re.IGNORECASE)]
    
    if not xxxx_positions:
        return [{"texte": ligne, "proposition": None, "alternative": None, "commentaire": None, "deletable": False}]
    
    pos = 0
    for start, end in xxxx_positions:
        # Texte avant
        if pos < start:
            texte_avant = ligne[pos:start]
            if texte_avant:
                elements.append({"texte": texte_avant, "proposition": None, "alternative": None, "commentaire": None, "deletable": False})
        
        # XXXX
        elements.append({"texte": "XXXX", "proposition": None, "alternative": None, "commentaire": None, "deletable": False})
        
        pos = end
    
    # Texte après
    if pos < len(ligne):
        texte_apres = ligne[pos:]
        if texte_apres:
            elements.append({"texte": texte_apres, "proposition": None, "alternative": None, "commentaire": None, "deletable": False})
    
    return elements

def traiter_texte_complet(texte: str):
    """Split sur RET et .. puis parse"""
    if not texte:
        return []
    
    # Split sur RET ET sur ..
    texte = texte.replace('..', ' RET ')  # Remplacer .. par RET pour uniformiser
    
    # Split sur RET
    phrases = []
    parts = texte.split('RET')
    for p in parts:
        p = p.strip()
        if p:
            phrases.append(p)
    
    # Parser chaque phrase
    lignes_finales = []
    
    for idx, phrase in enumerate(phrases):
        elements = traiter_ligne_simple(phrase)
        
        # Marquer nouvelle ligne
        if elements and idx > 0:
            elements[0]['newline'] = True
        
        lignes_finales.extend(elements)
    
    return lignes_finales

class FusionRequest(BaseModel):
    table_principale: str
    motif_principal_id: str  # UUID string
    motifs_secondaires: List[Dict[str, Any]] = []
    mode: str = "conclusion"

@app.post("/fusion")
async def fusion(request: FusionRequest):
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
            
            # Récupérer motif
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/{request.table_principale}?id=eq.{request.motif_principal_id}",
                headers=headers
            )
            
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail="Erreur Supabase")
            
            data = resp.json()
            if not data:
                raise HTTPException(status_code=404, detail="Motif non trouvé")
            
            motif = data[0]
            
            # Debug: afficher tous les champs disponibles
            print(f"[DEBUG] Motif ID: {request.motif_principal_id}")
            print(f"[DEBUG] Champs disponibles: {list(motif.keys())}")
            for key in ['hdm_motif', 'hdm_signes_associes', 'hdm_contexte', 'hdm_soins_anterieurs', 
                        'examen_clinique', 'examen_complementaire', 'diagnostic', 'conduite_a_tenir']:
                value = motif.get(key, '')
                print(f"[DEBUG] {key}: {'VIDE' if not value else f'{len(value)} chars'}")
            
            # Construire modules
            modules = []
            
            # HDM sections
            hdm_sections = []
            
            hdm_fields = {
                'hdm_motif': 'Histoire de la maladie : Motif',
                'hdm_signes_associes': 'Histoire de la maladie : Signes associés',
                'hdm_contexte': 'Histoire de la maladie : Contexte',
                'hdm_soins_anterieurs': 'Histoire de la maladie : Soins antérieurs'
            }
            
            for field, titre in hdm_fields.items():
                texte = motif.get(field, '')
                if texte:
                    lignes = traiter_texte_complet(texte)
                    if lignes:
                        hdm_sections.append({
                            "titre": titre,
                            "lignes": lignes
                        })
            
            if hdm_sections:
                modules.append({
                    "type": "hdm",
                    "titre": "Histoire de la maladie",
                    "sections": hdm_sections
                })
            
            # Autres champs simples
            simple_fields = {
                'examen_clinique': 'Examen clinique',
                'examen_complementaire': 'Examens complémentaires',
                'diagnostic': 'Diagnostic',
                'conduite_a_tenir': 'Conduite à tenir'
            }
            
            for field, titre in simple_fields.items():
                texte = motif.get(field, '')
                if texte:
                    lignes = traiter_texte_complet(texte)
                    if lignes:
                        modules.append({
                            "type": field,
                            "titre": titre,
                            "lignes": lignes
                        })
            
            return {
                "modules": modules,
                "ordonnances": [],
                "codes_cim": []
            }
            
    except Exception as e:
        print(f"Erreur fusion: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
