from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import re
from difflib import SequenceMatcher

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
    return {"service": "API v6.0-FUSION-INTELLIGENTE", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "6.0"}

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

def normaliser_texte(texte: str) -> str:
    """Normalise le texte pour comparaison"""
    if not texte:
        return ""
    # Supprimer espaces multiples, convertir en minuscules
    texte = re.sub(r'\s+', ' ', texte.strip().lower())
    # Normaliser ponctuation
    texte = texte.replace('...', '').replace('..', '')
    return texte

def textes_similaires(texte1: str, texte2: str, seuil: float = 0.85) -> bool:
    """Compare deux textes et retourne True s'ils sont très similaires"""
    if not texte1 or not texte2:
        return False
    
    norm1 = normaliser_texte(texte1)
    norm2 = normaliser_texte(texte2)
    
    if norm1 == norm2:
        return True
    
    # Similarité par ratio
    ratio = SequenceMatcher(None, norm1, norm2).ratio()
    return ratio >= seuil

def dedupliquer_lignes(lignes_list: List[List[Dict]]) -> List[Dict]:
    """
    Fusionne plusieurs listes de lignes en évitant les doublons
    lignes_list: Liste de listes de lignes (une liste par motif)
    Retourne: Une seule liste de lignes dédupliquées
    """
    if not lignes_list:
        return []
    
    # Première liste = base
    lignes_finales = []
    textes_vus = []
    
    for lignes_motif in lignes_list:
        for ligne in lignes_motif:
            texte_ligne = ligne.get('texte', '')
            
            # Ignorer lignes vides
            if not texte_ligne or not texte_ligne.strip():
                continue
            
            # Vérifier si similaire à une ligne déjà vue
            est_doublon = False
            for texte_vu in textes_vus:
                if textes_similaires(texte_ligne, texte_vu):
                    est_doublon = True
                    break
            
            # Si pas doublon, ajouter
            if not est_doublon:
                lignes_finales.append(ligne)
                textes_vus.append(texte_ligne)
    
    return lignes_finales

def dedupliquer_liste_simple(listes: List[List[str]]) -> List[str]:
    """Déduplique une liste de listes de strings simples"""
    if not listes:
        return []
    
    resultats = []
    textes_vus = []
    
    for liste in listes:
        for item in liste:
            if not item or not item.strip():
                continue
            
            est_doublon = False
            for texte_vu in textes_vus:
                if textes_similaires(item, texte_vu):
                    est_doublon = True
                    break
            
            if not est_doublon:
                resultats.append(item)
                textes_vus.append(item)
    
    return resultats

def traiter_ligne_avec_marqueurs(ligne: str):
    """Parse TOUS les marqueurs dans une ligne"""
    if not ligne:
        return []
    
    # Normaliser apostrophes et caractères spéciaux
    ligne = ligne.replace(''', "'").replace(''', "'").replace('´', "'").replace('`', "'")
    ligne = ligne.replace('"', '"').replace('"', '"')
    ligne = ligne.replace('ï¼', '/').replace('â„', '/')
    
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

async def recuperer_motif(client: httpx.AsyncClient, table_name: str, motif_id: str, headers: dict) -> Optional[Dict]:
    """Récupère un motif depuis Supabase"""
    try:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/{table_name}?id=eq.{motif_id}&select=*",
            headers=headers
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0]
        return None
    except Exception as e:
        print(f"Erreur récupération motif {motif_id}: {e}")
        return None

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
            
            print(f"\n[DEBUG] ========== FUSION INTELLIGENTE ==========")
            print(f"[DEBUG] Motif principal: {request.motif_principal_id}")
            print(f"[DEBUG] Nombre de motifs secondaires: {len(request.motifs_secondaires)}")
            
            # ===== RÉCUPÉRATION DE TOUS LES MOTIFS =====
            motifs_data = []
            
            # 1. Motif principal
            motif_principal = await recuperer_motif(
                client, 
                request.table_principale, 
                request.motif_principal_id, 
                headers
            )
            if not motif_principal:
                raise HTTPException(status_code=404, detail="Motif principal non trouvé")
            
            motifs_data.append(motif_principal)
            print(f"[DEBUG] ✓ Motif principal: {motif_principal.get('nom_motif', 'Unknown')}")
            
            # 2. Motifs secondaires
            for idx, motif_sec in enumerate(request.motifs_secondaires):
                table = motif_sec.get('table_name')
                motif_id = motif_sec.get('id')
                
                if table and motif_id:
                    motif_data = await recuperer_motif(client, table, motif_id, headers)
                    if motif_data:
                        motifs_data.append(motif_data)
                        print(f"[DEBUG] ✓ Motif secondaire {idx+1}: {motif_data.get('nom_motif', 'Unknown')}")
            
            print(f"[DEBUG] Total motifs à fusionner: {len(motifs_data)}")
            
            # ===== FUSION DES CHAMPS =====
            modules = []
            
            # ==================== HDM SECTIONS ====================
            hdm_fields = [
                ('hdm_motif', 'Histoire de la maladie : Motif'),
                ('hdm_signes_associes', 'Histoire de la maladie : Signes associés'),
                ('hdm_contexte', 'Histoire de la maladie : Contexte'),
                ('hdm_soins_anterieurs', 'Histoire de la maladie : Soins antérieurs')
            ]
            
            hdm_sections = []
            for field, titre in hdm_fields:
                # Collecter toutes les versions de ce champ
                lignes_multiples = []
                for motif in motifs_data:
                    texte = motif.get(field, '')
                    if texte and texte.strip():
                        lignes = traiter_texte_complet(texte)
                        if lignes:
                            lignes_multiples.append(lignes)
                
                # Dédupliquer
                if lignes_multiples:
                    lignes_fusionnees = dedupliquer_lignes(lignes_multiples)
                    if lignes_fusionnees:
                        hdm_sections.append({
                            "titre": titre,
                            "lignes": lignes_fusionnees
                        })
                        print(f"[DEBUG] ✓ {field}: {len(lignes_fusionnees)} lignes (fusionnées de {len(lignes_multiples)} sources)")
            
            if hdm_sections:
                modules.append({
                    "type": "hdm",
                    "titre": "Histoire de la maladie",
                    "sections": hdm_sections
                })
            
            # ==================== EXAMENS ====================
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
                lignes_multiples = []
                for motif in motifs_data:
                    texte = motif.get(field, '')
                    if texte and texte.strip():
                        lignes = traiter_texte_complet(texte)
                        if lignes:
                            lignes_multiples.append(lignes)
                
                if lignes_multiples:
                    lignes_fusionnees = dedupliquer_lignes(lignes_multiples)
                    if lignes_fusionnees:
                        modules.append({
                            "type": field,
                            "titre": titre,
                            "lignes": lignes_fusionnees
                        })
                        print(f"[DEBUG] ✓ {field}: {len(lignes_fusionnees)} lignes")
            
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
                lignes_multiples = []
                for motif in motifs_data:
                    texte = motif.get(field, '')
                    if texte and texte.strip():
                        lignes = traiter_texte_complet(texte)
                        if lignes:
                            lignes_multiples.append(lignes)
                
                if lignes_multiples:
                    lignes_fusionnees = dedupliquer_lignes(lignes_multiples)
                    if lignes_fusionnees:
                        modules.append({
                            "type": field,
                            "titre": titre,
                            "lignes": lignes_fusionnees
                        })
                        print(f"[DEBUG] ✓ {field}: {len(lignes_fusionnees)} lignes")
            
            # ==================== CONCLUSIONS ====================
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
                lignes_multiples = []
                for motif in motifs_data:
                    texte = motif.get(field, '')
                    if texte and texte.strip():
                        lignes = traiter_texte_complet(texte)
                        if lignes:
                            lignes_multiples.append(lignes)
                
                if lignes_multiples:
                    lignes_fusionnees = dedupliquer_lignes(lignes_multiples)
                    if lignes_fusionnees:
                        modules.append({
                            "type": field,
                            "titre": titre,
                            "lignes": lignes_fusionnees
                        })
                        print(f"[DEBUG] ✓ {field}: {len(lignes_fusionnees)} lignes")
            
            # ==================== ORDONNANCES ====================
            ordonnances_multiples = []
            for motif in motifs_data:
                ordonnance_texte = motif.get('ordonnance', '')
                if ordonnance_texte and ordonnance_texte.strip():
                    ordos = [o.strip() for o in ordonnance_texte.split('RET') if o.strip()]
                    if ordos:
                        ordonnances_multiples.append(ordos)
            
            ordonnances = dedupliquer_liste_simple(ordonnances_multiples)
            print(f"[DEBUG] ✓ Ordonnances: {len(ordonnances)} lignes fusionnées")
            
            # ==================== CIM-10 ====================
            cim_multiples = []
            for motif in motifs_data:
                cim_texte = motif.get('cim10', '')
                if cim_texte and cim_texte.strip():
                    codes = [c.strip() for c in cim_texte.split('RET') if c.strip()]
                    if codes:
                        cim_multiples.append(codes)
            
            codes_cim = dedupliquer_liste_simple(cim_multiples)
            print(f"[DEBUG] ✓ CIM-10: {len(codes_cim)} codes fusionnés")
            
            print(f"[DEBUG] TOTAL MODULES: {len(modules)}")
            print(f"[DEBUG] ==========================================\n")
            
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
