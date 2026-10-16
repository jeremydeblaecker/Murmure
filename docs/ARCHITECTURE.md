# Architecture de Murmure

## Principes

1. Aucun moteur TTS ne doit être couplé directement à l'interface.
2. Les modèles vocaux ne sont jamais versionnés dans Git.
3. Un passage identique ne doit pas être synthétisé plusieurs fois inutilement.
4. Le thread UI ne doit pas effectuer la synthèse vocale.
5. Les EPUB sont lus localement et ne quittent jamais la machine.

## Modules

### epub

Responsable de l'extraction structurée du contenu EPUB.

### text

Responsable du nettoyage et de la segmentation avant synthèse.

### tts

Expose une interface commune pour les moteurs vocaux.

### ui

Contient uniquement la présentation et l'orchestration utilisateur.

## Évolution prévue

La prochaine étape importante est d'ajouter un worker de synthèse asynchrone avec file d'attente :

```text
Chunk N en lecture
        │
        └── Chunk N+1 synthétisé en arrière-plan
```

Cela doit permettre une lecture continue sans attente audible entre les morceaux.
