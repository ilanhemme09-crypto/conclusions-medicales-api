# 🏥 Conclusions Médicales v4.0.0

## 🆕 NOUVEAUTÉS MAJEURES

### Système complet à 3 modes

**1. EXAMEN TYPE** 🩺
- Histoire de la maladie (HDM) regroupée en un seul module
- Examens cliniques séparés par spécialité
- Idéal pour rédiger un examen clinique complet

**2. CONCLUSION TYPE** 📋
- Diagnostic, signes de gravité, conduite à tenir
- Tous les modules de conclusion habituels
- Format conclusion standard

**3. EXAMEN + CONCLUSION** 📋+🩺
- Affichage en 2 colonnes côte à côte
- Gauche : Examen type
- Droite : Conclusion type
- Bouton copier séparé pour chaque partie

---

## 📊 STRUCTURE DE LA BASE DE DONNÉES

### Catégories en MAJUSCULES

- **CARDIOLOGIE**
- **PNEUMOLOGIE**
- **NEUROLOGIE**
- **GASTRO-ENTÉROLOGIE**
- **TRAUMATOLOGIE**
- **DERMATOLOGIE**
- **OPHTALMOLOGIE**
- **ORL**
- **UROLOGIE**

### Nouveaux modules HDM (Histoire de la Maladie)

```sql
hdm_motif                -- Motif de consultation
hdm_signes_associes      -- Signes associés
hdm_contexte             -- Contexte médical
hdm_soins_anterieurs     -- Soins déjà réalisés
```

**Affichage :** Les 4 modules HDM sont fusionnés en un seul module "HISTOIRE DE LA MALADIE"

### Modules EXAMEN (par spécialité)

```sql
examen_cardiologique     ❤️
examen_pneumologique     🫁
examen_neurologique      🧠
examen_digestif          🫃
examen_urologique        💧
examen_traumatologique   🦴
examen_dermatologique    👤
examen_ophtalmologique   👁️
examen_orl               👂
```

### Modules CONCLUSION (existants)

```sql
diagnostic               🔍
signes_gravite          ⚠️
soins_urgences          🏥
conduite_tenir          📋
conseils                💡
suivi                   📅
consignes_reconsultation 🚨
```

---

## 🚀 INSTALLATION

### 1. Créer la base Supabase

1. Aller sur https://supabase.com
2. Créer un nouveau projet
3. Aller dans **SQL Editor**
4. Coller tout le contenu de `supabase_schema.sql`
5. Exécuter (Run)

✅ Cela crée :
- 9 tables (une par spécialité)
- Vue des catégories
- Données d'exemple (cardiologie, neurologie, pneumologie)

### 2. Déployer le backend sur Render

1. Créer un repo GitHub avec :
   - `api_backend.py`
   - `requirements.txt`

2. Render.com → New Web Service
   - **Repository** : Votre repo GitHub
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `uvicorn api_backend:app --host 0.0.0.0 --port $PORT`

3. Copier l'URL : `https://votre-app.onrender.com`

### 3. Déployer le frontend sur Netlify

1. **Modifier** `index.html` ligne 7 :
   ```javascript
   const API_URL='https://votre-app.onrender.com';
   ```

2. Netlify.com → Deploy manually
   - Glisser `index.html`

3. Votre site est en ligne : `https://votre-site.netlify.app`

---

## 🎯 GUIDE D'UTILISATION

### Workflow standard

1. **Sélectionner une catégorie principale** (ex: NEUROLOGIE)
2. **Cliquer sur un motif** → Il devient vert (motif principal)
3. *Optionnel :* Ajouter des motifs secondaires (catégories secondaires) → Bleu
4. **Cliquer sur "🔄 Générer"**
5. **Choisir le mode :**
   - 🩺 EXAMEN TYPE
   - 📋 CONCLUSION TYPE
   - 📋+🩺 EXAMEN + CONCLUSION

### Mode EXAMEN TYPE 🩺

**Affiche :**
- 📝 **HISTOIRE DE LA MALADIE** (HDM fusionné)
- ❤️ **EXAMEN CARDIOLOGIQUE**
- 🫁 **EXAMEN PNEUMOLOGIQUE**
- 🧠 **EXAMEN NEUROLOGIQUE**
- *etc...*

**Utilisation :**
- Tous les modules sont éditables
- Les XXXX sont cliquables
- Les bulles d'information sont disponibles

### Mode CONCLUSION TYPE 📋

**Affiche :**
- 🔍 **DIAGNOSTIC**
- ⚠️ **SIGNES DE GRAVITÉ**
- 🏥 **AUX URGENCES**
- 📋 **CONDUITE À TENIR**
- 💡 **CONSEILS**
- 📅 **SUIVI**
- 🚨 **CONSIGNES DE RECONSULTATION**
- 📊 **Codes CIM-10**

**Utilisation :**
- Conduite à tenir avec boutons ↑ ↓ 🗑
- Ordonnances disponibles
- Codes CIM-10 en bas

### Mode EXAMEN + CONCLUSION 📋+🩺

**Affichage split-screen :**

```
┌──────────────────┬──────────────────┐
│   🩺 EXAMEN     │  📋 CONCLUSION  │
│                  │                  │
│  [HDM]          │  [Diagnostic]   │
│  [Examen       │  [Signes de     │
│   cardio]      │   gravité]      │
│  [Examen       │  [Conduite]     │
│   neuro]       │  [Conseils]     │
│                  │                  │
│  📋 Copier      │  📋 Copier      │
└──────────────────┴──────────────────┘
```

**Boutons indépendants :**
- Bouton "📋 Copier" sur l'examen
- Bouton "📋 Copier" sur la conclusion

---

## 🎨 FONCTIONNALITÉS COMPLÈTES

### Toujours actives

- ✅ Retours à la ligne sur majuscules
- ✅ Suppression des phrases en double
- ✅ Validation par Entrée dans XXXX
- ✅ Modal XXXX au-dessus des autres
- ✅ 3 états hover sur modules
- ✅ Style conduite avec numéros circulaires
- ✅ Police Inter professionnelle
- ✅ Codes CIM-10 violet
- ✅ Propositions XXXX intelligentes
- ✅ Bulles d'information orange
- ✅ Ordonnances avec filtres

### Nouvelles fonctionnalités v4.0

- ✅ **Modal de sélection du mode**
- ✅ **Module HDM fusionné**
- ✅ **9 modules d'examen clinique**
- ✅ **Affichage split-screen**
- ✅ **Copie séparée examen/conclusion**
- ✅ **Catégories en MAJUSCULES**

---

## 📋 EXEMPLES DE DONNÉES

### Exemple Neurologie - Céphalée

**HDM :**
```
Céphalée depuis XXXX heures
Localisation XXXX
Intensité XXXX/10
Signes associés : Nausées, Vomissements, Photophobie
```

**Examen neurologique :**
```
Examen neurologique normal
Glasgow 15/15
Pas de déficit sensitivomoteur
ROT présents et symétriques
Pas de syndrome méningé
```

**Diagnostic :**
```
Céphalée primaire probable
```

**Conduite à tenir :**
```
1. Traitement antalgique
2. Surveillance
3. Repos dans le calme et l'obscurité
```

---

## 🔧 API ENDPOINTS

### `GET /categories`
Retourne toutes les catégories en MAJUSCULES

### `GET /motifs/{table_name}`
Retourne les motifs d'une catégorie

### `POST /fusion`
Génère le document selon le mode

**Body :**
```json
{
  "table_principale": "neurologie",
  "motif_principal_id": "abc-123",
  "motifs_secondaires": [
    {"table": "cardiologie", "id": "def-456"}
  ],
  "mode": "examen_conclusion"
}
```

**Modes possibles :**
- `"examen"` → Examen type uniquement
- `"conclusion"` → Conclusion type uniquement
- `"examen_conclusion"` → Les deux

---

## 🗂️ STRUCTURE DES FICHIERS

```
📁 Projet
├── 📄 supabase_schema.sql    # Schema SQL complet
├── 📄 api_backend.py          # Backend FastAPI
├── 📄 index.html              # Frontend complet
├── 📄 requirements.txt        # Dépendances Python
└── 📄 README.md               # Ce fichier
```

---

## 🎯 AJOUT DE NOUVELLES DONNÉES

### Dans Supabase

1. Aller dans **Table Editor**
2. Sélectionner une table (ex: `neurologie`)
3. Cliquer **Insert row**
4. Remplir les champs :
   - `nom_motif` : Nom du motif
   - `ordre` : Ordre d'affichage
   - `hdm_motif` : Histoire de la maladie - motif
   - `hdm_signes_associes` : Signes associés
   - `examen_neurologique` : Examen neuro
   - `diagnostic` : Diagnostic
   - `conduite_tenir` : Conduite à tenir
   - `ordonnances` : Format JSON
   - `codage_cim10` : Code CIM-10

5. Sauvegarder

**Format ordonnances :**
```json
{
  "Antalgique": "Paracétamol 1g x3/jour",
  "Anti_inflammatoire": "Ibuprofène 400mg x3/jour"
}
```

---

## 🐛 DÉBOGAGE

### Problème : Modal ne s'affiche pas

**Solution :** Vérifier que l'API est connectée (✅ Connecté)

### Problème : Split view ne fonctionne pas

**Solution :** Vérifier que le mode est bien `"examen_conclusion"`

### Problème : HDM vide

**Solution :** Vérifier que les champs `hdm_*` sont remplis dans la base

---

## 📞 SUPPORT

En cas de problème :

1. **Console navigateur (F12)** → Voir les erreurs JS
2. **Logs Render** → Voir les erreurs backend
3. **Tester l'API** : `curl https://votre-app.onrender.com/health`

---

✅ **Système v4.0.0 complet et fonctionnel !**

**Prochaines étapes suggérées :**
- Ajouter plus de motifs dans Supabase
- Personnaliser les styles CSS
- Ajouter des statistiques d'utilisation
