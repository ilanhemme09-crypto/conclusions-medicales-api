# 🏥 Conclusions Médicales - Guide de Déploiement

## 📦 Fichiers fournis

- `api_backend.py` - Backend FastAPI avec clés Supabase intégrées (316 lignes)
- `index.html` - Frontend HTML complet (75 lignes minifiées)
- `requirements.txt` - Dépendances Python

---

## 🚀 DÉPLOIEMENT EN 10 MINUTES

### ÉTAPE 1 : Déployer le Backend sur Render

1. **Créer un compte sur Render.com**
   - Aller sur https://render.com
   - Créer un compte gratuit

2. **Créer un nouveau repository GitHub**
   - Créer un nouveau repo : `conclusions-medicales-api`
   - Uploader les fichiers :
     - `api_backend.py`
     - `requirements.txt`

3. **Créer le Web Service sur Render**
   - Cliquer sur "New +" → "Web Service"
   - Connecter votre repository GitHub
   - Nom : `conclusions-medicales-api`
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `uvicorn api_backend:app --host 0.0.0.0 --port $PORT`
   - Cliquer sur "Create Web Service"

4. **Récupérer l'URL de votre API**
   - Une fois déployé, copier l'URL : `https://VOTRE-APP.onrender.com`

---

### ÉTAPE 2 : Déployer le Frontend sur Netlify

1. **Modifier l'URL de l'API dans index.html**
   - Ouvrir `index.html` dans un éditeur de texte
   - Chercher la ligne (environ ligne 5 du script) :
     ```javascript
     const API_URL='https://conclusions-medicales-api-1oa1.onrender.com';
     ```
   - Remplacer par votre URL Render :
     ```javascript
     const API_URL='https://VOTRE-APP.onrender.com';
     ```
   - Sauvegarder

2. **Déployer sur Netlify**
   - Aller sur https://netlify.com
   - Créer un compte gratuit
   - Cliquer sur "Add new site" → "Deploy manually"
   - **Glisser-déposer le fichier `index.html`**
   - Attendre quelques secondes

3. **Votre site est en ligne !**
   - URL : `https://VOTRE-SITE.netlify.app`

---

## ✅ VÉRIFICATIONS

### 1. Tester le Backend

Ouvrir dans le navigateur :
```
https://VOTRE-APP.onrender.com/health
```

Vous devriez voir :
```json
{"status": "healthy", "database": "connected"}
```

### 2. Tester le Frontend

1. Ouvrir `https://VOTRE-SITE.netlify.app`
2. Vérifier que le statut API affiche "✅ Connecté"
3. Cliquer sur une catégorie (ex: "Neurologie")
4. Sélectionner un motif (il devient vert)
5. Cliquer sur "🔄 Générer"
6. La conclusion s'affiche !

---

## 🎯 FONCTIONNALITÉS

### ✅ Implémentées

- **Clés Supabase intégrées** : Pas de configuration nécessaire
- **Retours à la ligne automatiques** : Chaque phrase sur une ligne
- **Bulles d'information** : Boutons orange cliquables avec titres
- **Conduite à tenir numérotée** : 1. 2. 3. avec boutons ↑ ↓ 🗑
- **Effet survol** : Modules brillent au survol
- **XXXX cliquables** : Dans tous les modules et ordonnances
- **Fusion sans doublons** : Phrases identiques supprimées
- **Modal ordonnances** : Avec filtres catégorie + motif
- **2 boutons générer** : En haut et en bas de la sidebar
- **Sidebar rouge foncé** : Design exact

---

## 🔧 STRUCTURE DES DONNÉES

### Backend Parse les Bulles

```
BULLE : Drapeaux rouges : Céphalée coup de tonerre, Trouble conscience FIN
```

Devient :

```json
{
  "titre": "Drapeaux rouges",
  "contenu": "Céphalée coup de tonerre, Trouble conscience"
}
```

### Retours à la Ligne

```
Pas de signe de gravité
Patient stable
Apyrétique
```

Devient :

```json
["Pas de signe de gravité.", "Patient stable.", "Apyrétique."]
```

---

## 📞 SUPPORT

Si ça ne fonctionne pas :

1. **Vérifier que le backend est déployé** :
   - Ouvrir `https://VOTRE-APP.onrender.com/health`
   - Doit afficher `{"status": "healthy"}`

2. **Vérifier l'URL dans le frontend** :
   - Ouvrir `index.html`
   - Vérifier que `API_URL` correspond à votre URL Render

3. **Console du navigateur** :
   - Appuyer sur F12
   - Onglet "Console"
   - Vérifier s'il y a des erreurs

---

## 📝 NOTES

- **Render free tier** : L'API se met en veille après 15 min d'inactivité
- **Premier chargement** : Peut prendre 30 secondes si l'API était en veille
- **Netlify** : Frontend toujours instantané

---

✅ **Système complet et fonctionnel !**
