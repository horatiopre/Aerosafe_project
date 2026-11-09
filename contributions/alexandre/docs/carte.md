# Première carte AeroSafe

Cette version affiche un instantané des positions enregistrées. Elle permet de rechercher un aéronef, sélectionner sa trajectoire, consulter les mesures et recentrer la carte.

## 1 Exporter depuis PostgreSQL
Depuis le dossier AeroSafe, avec Docker Desktop ouvert :
```powershell
docker compose run --build --rm app map
```
La commande crée `maps/carte.html` à partir des dernières 24 heures de positions OpenSky en base. Le nombre de positions et d’avions est affiché.

Pour limiter à deux heures :
```powershell
docker compose run --rm app map --hours 2
```

## 2 Ouvrir la carte
Depuis le même dossier, lancer :
```powershell
python -m http.server 8000 --bind 127.0.0.1 --directory maps
```
Garder ce terminal ouvert et visiter [la carte locale](http://127.0.0.1:8000/carte.html) dans le navigateur. Pour arrêter le serveur, appuyer sur Ctrl+C.

Si le port 8000 est occupé, utiliser 8001 dans la commande et dans l’adresse. Seul le dossier des cartes est servi ; les secrets du projet et le reste des fichiers ne sont pas exposés.

## 3 Vérifier le parcours
- La vue d’ensemble affiche la dernière position connue de chaque avion.
- Rechercher un indicatif ou un identifiant ICAO24, puis sélectionner l’avion.
- Les positions connues apparaissent en bleu-vert ; la dernière est orange.
- Cliquer sur un point pour voir son heure UTC, son altitude, sa vitesse et sa route au sol.
- Le tableau sous la carte reprend les mesures. Une valeur absente reste « Non disponible ».
- Pour un avion avec un seul point, un message explique qu’une trajectoire nécessite plusieurs collectes.
- Vérifier qu’une recherche sans résultat permet de revenir à la vue d’ensemble.

Les segments relient les positions observées. Les intervalles supérieurs à cinq minutes et les passages de longitude supérieurs à 180 degrés ne sont pas reliés : la carte n’invente pas de parcours entre des observations trop éloignées.

## Actualiser les données
Cette version n’effectue aucune collecte et aucun rafraîchissement automatique. Dans un second terminal :
```powershell
docker compose run --rm app collect --import-db
docker compose run --rm app map
```
Actualiser ensuite la page du navigateur. La date d’export et la période sont affichées dans la colonne de gauche.

## Aperçu à partir des captures
Un aperçu a déjà été généré depuis les fichiers locaux : 136 aéronefs et 316 positions au moment de la préparation. Il inclut aussi la première capture de 84 avions, dont l’import en base n’était pas confirmé. Les totaux de PostgreSQL peuvent donc être différents.

Pour régénérer ce mode sans Docker :
```powershell
python -m aerosafe map --from-captures
```
La page affiche explicitement « captures locales » ou « PostgreSQL » selon son origine.

## Connexion et fonctionnement dégradé
Leaflet 1.9.4 est chargé depuis un CDN ; le fond de carte provient d’OpenStreetMap. Une connexion Internet est donc nécessaire au premier affichage complet.

Si le fond de carte échoue, les points et le tableau restent accessibles tant que Leaflet est chargé. Si Leaflet lui-même ne charge pas, la sélection et le tableau restent disponibles avec un message explicite. Décocher « Afficher le fond OpenStreetMap » désactive les tuiles.

Aucune tuile n’est préchargée ni téléchargée pour un usage hors connexion. L’attribution OpenStreetMap reste visible sur la carte.

## Limites actuelles
- Période maximale : 168 heures ; maximum 50 000 positions par export.
- Le tableau montre les 500 derniers points de l’avion sélectionné, avec une indication lorsque cette limite est atteinte.
- Les heures sont en UTC, l’altitude en mètres et la vitesse en mètres par seconde.
- Les alertes, l’authentification et le rejeu animé ne sont pas encore raccordés.
- La vue d’ensemble et la sélection d’une trajectoire ont été confirmées par captures sur le poste utilisateur. Les infobulles et le tableau détaillé restent à vérifier manuellement.

## Tests
```powershell
docker compose run --build --rm -e AEROSAFE_INTEGRATION=1 --entrypoint python app -m unittest discover -s tests -v
```
Résultat attendu : **42 tests réussis**, sans test ignoré. Les 42 tests, dont les 6 tests PostgreSQL, ont réussi sur le poste utilisateur le 9 novembre 2026 (capture de terminal : 1,064 seconde).

Le code d’affichage est dans `aerosafe/templates/map.html`. Le contenu embarqué dans la page pourra ensuite être remplacé par des réponses de l’API d’Horatio.

Références : [Leaflet 1.9.4](https://leafletjs.com/reference-1.9.4.html) et [conditions des tuiles OpenStreetMap](https://operations.osmfoundation.org/policies/tiles/).

