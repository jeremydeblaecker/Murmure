# Murmure

**Murmure** est un lecteur EPUB desktop conçu pour lire des livres à voix haute avec une voix naturelle, tout en restant utilisable hors ligne.

L'objectif principal est d'éviter l'effet « voix GPS » des moteurs TTS traditionnels grâce à un moteur neuronal local et à un meilleur traitement du texte avant synthèse.

## Objectifs

- 📚 ouvrir et parcourir des fichiers EPUB ;
- 🔊 lire le texte à voix haute avec une voix française naturelle ;
- 📴 fonctionner sans connexion Internet pendant la lecture ;
- 🧠 utiliser un moteur TTS neuronal local ;
- ✂️ segmenter intelligemment le texte pour conserver une prosodie naturelle ;
- 💾 mettre en cache l'audio déjà généré ;
- ⏯️ proposer une expérience de lecture fluide : lecture, pause, navigation entre chapitres ;
- 🪟 cibler en priorité Windows.

## Moteur vocal

Le moteur prioritaire est **Kokoro ONNX**.

Pourquoi Kokoro :

- exécution locale ;
- modèle relativement léger ;
- bonne qualité par rapport aux TTS classiques ;
- support du français ;
- compatible avec Python 3.12 ;
- accélération possible via ONNX Runtime.

La voix française utilisée par défaut est actuellement :

```text
ff_siwis
```

Le moteur est encapsulé derrière une interface afin de pouvoir ajouter plus tard d'autres moteurs, par exemple XTTS.

## Architecture

```text
src/murmure/
├── app.py
├── epub/
│   ├── __init__.py
│   └── reader.py
├── text/
│   ├── __init__.py
│   └── chunker.py
├── tts/
│   ├── __init__.py
│   ├── base.py
│   ├── kokoro.py
│   └── cache.py
└── ui/
    ├── __init__.py
    └── main_window.py
```

Le flux visé est :

```text
EPUB
  ↓
Extraction du chapitre
  ↓
Nettoyage HTML
  ↓
Segmentation en phrases / paragraphes
  ↓
Chunks de quelques phrases
  ↓
Kokoro ONNX
  ↓
Cache WAV local
  ↓
Lecture avec Qt Multimedia
```

## Installation

### 1. Prérequis

- Windows 10/11 ;
- Python 3.12 recommandé.

### 2. Créer l'environnement

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

### 3. Installer les modèles Kokoro

Créez le dossier :

```text
models/
```

Puis placez dedans :

```text
models/kokoro-v1.0.onnx
models/voices-v1.0.bin
```

Ces fichiers ne sont volontairement pas versionnés dans Git.

Le projet Kokoro ONNX fournit les modèles séparément.

### 4. Lancer Murmure

```powershell
murmure
```

ou :

```powershell
python -m murmure.app
```

## Fonctionnalités présentes dans le socle initial

- ouverture d'un EPUB ;
- extraction des chapitres textuels ;
- navigation entre chapitres ;
- affichage du contenu nettoyé ;
- segmentation du texte en morceaux adaptés au TTS ;
- synthèse Kokoro locale ;
- cache WAV ;
- lecture / pause de l'audio généré ;
- réglage de la vitesse ;
- sélection de la voix préparée côté moteur.

## Traitement du texte

Une lecture naturelle dépend autant du prétraitement que du modèle.

Murmure évite de synthétiser un chapitre entier en une seule fois. Le texte est découpé en groupes courts tout en essayant de conserver :

- les phrases complètes ;
- les paragraphes ;
- les dialogues ;
- les ponctuations fortes ;
- une taille raisonnable pour le moteur TTS.

Exemple :

```text
Paragraphe
↓
2 à 5 phrases
↓
Synthèse
↓
Lecture
↓
Préparation du morceau suivant
```

## Cache audio

L'audio généré est stocké dans :

```text
.cache/murmure/
```

La clé dépend notamment :

- du texte ;
- de la voix ;
- de la vitesse ;
- du moteur.

Relire le même passage avec les mêmes paramètres évite donc une nouvelle synthèse.

## Sécurité et confidentialité

Murmure est pensé comme une application locale :

- les EPUB restent sur la machine ;
- le texte du livre n'est pas envoyé à un service externe ;
- l'audio est généré localement ;
- aucun compte n'est requis.

## Roadmap

### V0.1

- [x] structure du projet ;
- [x] extraction EPUB ;
- [x] chunking ;
- [x] moteur Kokoro ;
- [x] cache local ;
- [x] interface desktop minimale.

### V0.2

- [ ] pré-génération du morceau suivant pendant la lecture ;
- [ ] sauvegarde de la position de lecture ;
- [ ] réglage fin des pauses ;
- [ ] meilleure détection des dialogues ;
- [ ] sélection de plusieurs voix françaises ;
- [ ] barre de progression du chapitre ;
- [ ] bibliothèque de livres.

### V0.3

- [ ] mode haute qualité alternatif ;
- [ ] prise en charge optionnelle de XTTS ;
- [ ] voix personnalisées ;
- [ ] export audio d'un chapitre ;
- [ ] packaging Windows.

## Licence

Projet personnel en cours de développement.

Les modèles TTS utilisés par Murmure conservent leurs propres licences.
