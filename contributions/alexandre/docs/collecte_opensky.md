# Première collecte OpenSky

Le collecteur interroge une seule fois la zone 48°–50° de latitude et 1°–3,5° de longitude, autour de Paris. Aucun service de collecte continue n’est lancé.

## Collecter et importer
Depuis le dossier AeroSafe, avec Docker Desktop ouvert :
```powershell
docker compose run --build --rm app collect --import-db
```
Le résultat indique le mode, la date source, les observations acceptées et rejetées, les chemins des fichiers et le bilan d’import. Le nombre d’avions varie selon le moment.

Pour collecter sans PostgreSQL :
```powershell
python -m aerosafe collect
```
Cette commande utilise seulement les bibliothèques standard de Python. Elle sauvegarde les fichiers sans écrire dans la base.

## Fichiers sauvegardés
Le dossier `captures` contient :
- `*_raw.json` : réponse OpenSky brute, zone et date de récupération ;
- `*_observations.jsonl` : observations normalisées au contrat v1 ;
- `*_report.json` : résultat de collecte et motifs des rejets ;
- `cache_*.json` : dernière réponse valide pour une zone donnée.

Les captures restent présentes sur le poste après l’arrêt du conteneur. Elles sont exclues de Git et du contexte de construction Docker. Les jetons et secrets ne sont pas enregistrés dans ces fichiers.

Une zone vide est un résultat valide : le rapport indique zéro observation et le fichier JSONL est vide. Ne pas utiliser la commande `validate` sur ce fichier vide, car elle attend un fichier d’import non vide.

## Essai réel déjà réalisé
Le 9 novembre 2026 à 09:40:14 UTC, une requête anonyme a fourni **84 observations valides, 84 avions distincts et aucun rejet**. Cet échantillon de 84 observations est conservé localement. Une collecte ultérieure à 09:45:25 UTC a été importée avec succès sur le poste utilisateur : 85 observations ajoutées dans PostgreSQL, aucun rejet.

Pour importer cet échantillon sauvegardé sans nouvelle requête :
```powershell
docker compose run --build --rm app import captures/20261109T094014_3ec46819_observations.jsonl
```
Cet import de fichier est enregistré en mode `replay` et conserve ses dates source.

## Commencer une trajectoire
Effectuer deux ou trois collectes manuelles, espacées par exemple de 30 secondes :
```powershell
docker compose run --rm app collect --import-db
```
Choisir un identifiant parmi `aeronefs_exemples` du rapport, puis :
```powershell
docker compose run --rm app trajectory IDENTIFIANT --source opensky
```
Remplacer `IDENTIFIANT` par les six caractères de l’avion. Un avion peut quitter la zone entre deux collectes ; il peut donc rester un seul point. Les données réelles et fictives sont filtrées séparément.

## Panne et cache
Le comportement normal signale l’erreur et s’arrête. Pour autoriser explicitement un repli sur le cache :
```powershell
docker compose run --rm app collect --import-db --use-cache-on-error
```
Seul un cache de la même zone, récupéré depuis moins d’une heure, est utilisable. Le rapport indique `mode: cache`, sa date, son âge et la raison du repli. L’import est alors en mode `replay` ; les dates source et les observations déjà présentes restent inchangées.

En cas de quota HTTP 429, la commande indique le délai communiqué par OpenSky et ne réessaie pas automatiquement. Respecter ce délai avant une nouvelle requête. Le cache ne dispense pas de cette attente.

## Accès authentifié facultatif
Le premier essai fonctionne sans compte. Pour un accès authentifié, créer un client API sur le compte OpenSky, puis ajouter localement dans `.env` :
```dotenv
OPENSKY_CLIENT_ID=valeur_du_client
OPENSKY_CLIENT_SECRET=valeur_du_secret
```
Ne pas transmettre ces valeurs dans le chat ni les ajouter à Git. Il s’agit des identifiants du client API, pas du mot de passe du compte. La commande obtient un jeton pour chaque exécution authentifiée ; aucune conservation de jeton n’est nécessaire pour ces collectes ponctuelles.

## Autre zone
```powershell
docker compose run --rm app collect --bbox 48 1 50 3.5 --import-db
```
Ordre des quatre bornes : latitude minimum, longitude minimum, latitude maximum, longitude maximum. Le cache est distinct pour chaque zone.

## Vérifications
```powershell
docker compose run --build --rm -e AEROSAFE_INTEGRATION=1 --entrypoint python app -m unittest discover -s tests -v
```
Résultat attendu pour cette version : **34 tests réussis, aucun ignoré**. Les tests OpenSky utilisent des réponses simulées et ne consomment pas de quota. Une requête réelle a été testée séparément ; l’authentification OAuth a été testée avec une réponse simulée.

Référence : [documentation officielle OpenSky](https://openskynetwork.github.io/opensky-api/rest.html).

