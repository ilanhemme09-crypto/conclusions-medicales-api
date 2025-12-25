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
    return {"service": "API v5.3-TOUS-MODULES", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "5.3"}

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

def traiter_ligne_avec_marqueurs(ligne: str):
    """Parse TOUS les marqueurs dans une ligne"""
    if not ligne:
        return []
    
    # Normaliser apostrophes et caractères spéciaux
    ligne = ligne.replace(''', "'").replace(''', "'").replace('´', "'").replace('`', "'")
    ligne = ligne.replace('"', '"').replace('"', '"')
    ligne = ligne.replace('／', '/').replace('⁄', '/')
    
    # Patterns
    pattern_xxxx = r'XXXX(?:\s+PROPOSITION\s*:\s*([^F]+?)\s*FINI)?'
    pattern_alt = r'@@\s*([^@]+?)\s*@@'
    pattern_comment = r'\{\{([^}]+?)\}\}'
    pattern_delete = r'\[\[([^\]]+?)\]\]'
    
    # Trouver tous les marqueurs
    marqueurs = []
    
    # XXXX avec propositions optionnelles
    for m in re.finditer(pattern_xxxx, ligne, re.IGNORECASE):
        props = m.group(1)
        suggestions = [s.strip() for s in props.split(';')] if props else []
        marqueurs.append((m.start(), m.end(), 'XXXX', suggestions))
    
    # Alternatives @@
    for m in re.finditer(pattern_alt, ligne):
        alt_text = m.group(1)
        alts = [a.strip() for a in alt_text.split('/') if a.strip()]
        if not alts:
            alts = [m.group(1).strip()]
        marqueurs.append((m.start(), m.end(), 'ALT', alts))
    
    # Commentaires {{}}
    for m in re.finditer(pattern_comment, ligne):
        marqueurs.append((m.start(), m.end(), 'COMMENT', m.group(1).strip()))
    
    # Suppressibles [[]]
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
    """Split sur RET et .. puis parse marqueurs"""
    if not texte:
        return []
    
    try:
        # Split sur .. ET RET
        texte = texte.replace('..', ' RET ')
        
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
    table_principale: str
    motif_principal_id: str  # UUID
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
            
            # Récupérer TOUS les champs
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/{request.table_principale}?id=eq.{request.motif_principal_id}&select=*",
                headers=headers
            )
            
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Erreur Supabase: {resp.status_code}")
            
            data = resp.json()
            if not data:
                raise HTTPException(status_code=404, detail="Motif non trouvé")
            
            motif = data[0]
            
            # Debug
            print(f"\n[DEBUG] ========== FUSION ==========")
            print(f"[DEBUG] Motif: {motif.get('nom_motif', 'Unknown')}")
            print(f"[DEBUG] Tous les champs: {list(motif.keys())}")
            
            # Construire modules
            modules = []
            ordonnances = []
            codes_cim = []
            
            # ==================== HDM SECTIONS ====================
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
                        hdm_sections.append({
                            "titre": titre,
                            "lignes": lignes
                        })
                        print(f"[DEBUG] ✓ {field}: {len(lignes)} éléments")
                else:
                    print(f"[DEBUG] ✗ {field}: VIDE")
            
            if hdm_sections:
                modules.append({
                    "type": "hdm",
                    "titre": "Histoire de la maladie",
                    "sections": hdm_sections
                })
            
            # ==================== EXAMEN TYPE ====================
            # Tous les champs d'examen possibles
            examen_fields = [
                ('examen_clinique', 'Examen clinique'),
                ('examen_general', 'Examen général'),
                ('examen_neurologique', 'Examen neurologique'),
                ('examen_cardiovasculaire', 'Examen cardiovasculaire'),
                ('examen_respiratoire', 'Examen respiratoire'),
                ('examen_abdominal', 'Examen abdominal'),
                ('examen_cutane', 'Examen cutané'),
                ('examen_orl', 'Examen ORL'),
                ('examen_ophtalmologique', 'Examen ophtalmologique'),
                ('examen_locomoteur', 'Examen locomoteur'),
            ]
            
            for field, titre in examen_fields:
                texte = motif.get(field, '')
                if texte and texte.strip():
                    lignes = traiter_texte_complet(texte)
                    if lignes:
                        modules.append({
                            "type": field,
                            "titre": titre,
                            "lignes": lignes
                        })
                        print(f"[DEBUG] ✓ {field}: {len(lignes)} éléments")
                else:
                    print(f"[DEBUG] ✗ {field}: VIDE")
            
            # ==================== EXAMENS COMPLÉMENTAIRES ====================
            complementaire_fields = [
                ('examen_complementaire', 'Examens complémentaires'),
                ('biologie', 'Biologie'),
                ('imagerie', 'Imagerie'),
                ('ecg', 'ECG'),
                ('echographie', 'Échographie'),
                ('scanner', 'Scanner'),
                ('irm', 'IRM'),
                ('radiographie', 'Radiographie'),
            ]
            
            for field, titre in complementaire_fields:
                texte = motif.get(field, '')
                if texte and texte.strip():
                    lignes = traiter_texte_complet(texte)
                    if lignes:
                        modules.append({
                            "type": field,
                            "titre": titre,
                            "lignes": lignes
                        })
                        print(f"[DEBUG] ✓ {field}: {len(lignes)} éléments")
                else:
                    print(f"[DEBUG] ✗ {field}: VIDE")
            
            # ==================== CONCLUSION TYPE ====================
            conclusion_fields = [
                ('diagnostic', 'Diagnostic'),
                ('diagnostic_differentiel', 'Diagnostic différentiel'),
                ('diagnostic_retenu', 'Diagnostic retenu'),
                ('conduite_a_tenir', 'Conduite à tenir'),
                ('traitement', 'Traitement'),
                ('surveillance', 'Surveillance'),
                ('complications', 'Complications'),
                ('criteres_hospitalisation', 'Critères d\'hospitalisation'),
                ('criteres_gravite', 'Critères de gravité'),
                ('orientation', 'Orientation'),
                ('consignes', 'Consignes'),
                ('suivi', 'Suivi'),
                ('pronostic', 'Pronostic'),
                ('education_therapeutique', 'Éducation thérapeutique'),
            ]
            
            for field, titre in conclusion_fields:
                texte = motif.get(field, '')
                if texte and texte.strip():
                    lignes = traiter_texte_complet(texte)
                    if lignes:
                        modules.append({
                            "type": field,
                            "titre": titre,
                            "lignes": lignes
                        })
                        print(f"[DEBUG] ✓ {field}: {len(lignes)} éléments")
                else:
                    print(f"[DEBUG] ✗ {field}: VIDE")
            
            # ==================== ORDONNANCES ====================
            ordonnance_texte = motif.get('ordonnance', '')
            if ordonnance_texte and ordonnance_texte.strip():
                ordonnances_list = [o.strip() for o in ordonnance_texte.split('RET') if o.strip()]
                ordonnances = ordonnances_list
                print(f"[DEBUG] ✓ ordonnances: {len(ordonnances)} lignes")
            else:
                print(f"[DEBUG] ✗ ordonnances: VIDE")
            
            # ==================== CIM-10 ====================
            cim_texte = motif.get('cim10', '')
            if cim_texte and cim_texte.strip():
                codes_list = [c.strip() for c in cim_texte.split('RET') if c.strip()]
                codes_cim = codes_list
                print(f"[DEBUG] ✓ cim10: {len(codes_cim)} codes")
            else:
                print(f"[DEBUG] ✗ cim10: VIDE")
            
            print(f"[DEBUG] TOTAL MODULES: {len(modules)}")
            print(f"[DEBUG] ==============================\n")
            
            return {
                "modules": modules,
                "ordonnances": ordonnances,
                "codes_cim": codes_cim
            }
            
    except Exception as e:
        print(f"\n[ERREUR] fusion: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
