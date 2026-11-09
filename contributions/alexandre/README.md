# AeroSafe
Premier exercice de la partie données : importer des observations dans PostgreSQL, refaire l’import sans doublons et lire une trajectoire chronologique.

## Ce qui est prêt
- Deux tables métier : `aeronef` et `observation`, avec une migration versionnée.
- Un import JSONL validé avant toute écriture.
- Une identité stable pour chaque observation et une contrainte d’unicité en base.
- Une commande de lecture des trajectoires avec période facultative.
- Un jeu **entièrement fictif** de 7 lignes : 2 avions, 6 observations distinctes et 1 doublon.
- Des tests de validation et des tests PostgreSQL séparés.

La première collecte OpenSky est disponible : voir le [guide de collecte](docs/collecte_opensky.md). La première carte est disponible dans le [guide cartographique](docs/carte.md). L’API d’Horatio et les règles d’Adam restent à raccorder. Les noms et unités du [contrat de données](docs/contrat_observation.md) sont une proposition à leur faire relire.

## 1 Vérifier les données dès maintenant
Ouvrir un terminal dans ce dossier. Python 3.12 ou plus récent suffit pour cette étape, sans installation de bibliothèque :
```powershell
python -m aerosafe validate data/sample_observations.jsonl
python -m unittest discover -s tests -v
```
Résultat attendu de la validation : **7 lignes valides, 6 observations distinctes, 1 doublon, 2 aéronefs**. Sans PostgreSQL, les 6 tests d’intégration sont explicitement ignorés.

## 2 Lancer la base et le premier exercice
Installer et ouvrir [Docker Desktop pour Windows](https://docs.docker.com/desktop/setup/install/windows-install/), avec les conteneurs Linux. Ensuite, depuis ce dossier :
```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
docker compose up -d --wait db
docker compose run --build --rm app demo data/sample_observations.jsonl
```
Le premier lancement télécharge les images et la bibliothèque Python. La commande `demo` crée les tables puis importe le fichier deux fois.

Sur une base vide, résultats attendus :
- premier import : 6 observations ajoutées et 1 doublon ignoré ;
- second import : 0 ajout et 7 observations déjà présentes ;
- total : 2 aéronefs et 6 observations ;
- trajectoire de `a0b1c2` : 3 positions triées de 10:00:00 à 10:00:20 UTC.

Relancer la démonstration conserve ces totaux. Si d’autres données ont été ajoutées, les totaux globaux reflètent aussi ces données.

## 3 Consulter les données
```powershell
docker compose run --rm app stats
docker compose run --rm app trajectory a0b1c2
docker compose run --rm app trajectory a0b1c2 --from 2026-01-01T10:00:10Z --to 2026-01-01T10:00:20Z
```
Le début de période est inclus, la fin exclue. Pour lire de futures données OpenSky, ajouter `--source opensky`. Le jeu fictif reste séparé.

Pour tester un autre fichier, le placer dans `data`, puis utiliser `validate` et `import`. Une base nouvelle doit recevoir `init-db` avant son premier import ; `demo` le fait automatiquement.

## 4 Vérifier réellement PostgreSQL
```powershell
docker compose run --rm -e AEROSAFE_INTEGRATION=1 --entrypoint python app -m unittest discover -s tests -v
```
Les 6 tests PostgreSQL utilisent un schéma temporaire propre et le suppriment à la fin. Ils vérifient le rejeu sans doublons, l’ordre des positions, la période, les valeurs absentes, les migrations et l’annulation d’un lot en erreur. Les tables du projet restent intactes.

## Comprendre les fichiers
| Fichier | Rôle |
|---|---|
| `aerosafe/observations.py` | Vérifier les champs, normaliser les heures, identifier les doublons |
| `aerosafe/storage.py` | Écrire et lire dans PostgreSQL |
| `aerosafe/__main__.py` | Exposer les commandes du premier exercice |
| `migrations/001_initial.sql` | Définir les tables et contraintes |
| `data/sample_observations.jsonl` | Fournir le jeu fictif |
| `compose.yaml` | Lancer PostgreSQL et les commandes Python |
| `docs/contrat_observation.md` | Expliquer le format à Horatio et Adam |
| `docs/verification.md` | État des vérifications réalisées |

## Choix à comprendre
- Les heures sont conservées avec leur fuseau et normalisées en UTC.
- Une altitude manquante reste `null` ; elle ne devient pas zéro.
- La déduplication porte sur le contenu normalisé d’un état, pas sur l’heure du téléchargement.
- Deux états différents d’un même avion peuvent conserver la même heure de position. La trajectoire n’affiche qu’un point par heure de position, choisi selon le dernier contact puis l’ordre d’enregistrement. Tous les états restent conservés pour l’analyse.
- Une ligne invalide refuse le fichier entier. Une erreur en base annule tout le lot.
- Le nom `true_track_deg` désigne la route au sol, à distinguer du cap.
- La première migration appliquée ne doit plus être modifiée ; ajouter une migration `002_...` pour faire évoluer le schéma.

## Arrêter et reprendre
```powershell
docker compose down
docker compose up -d --wait db
```
Le volume conserve les données entre deux lancements. La base est accessible uniquement depuis ce poste, au port 5433 par défaut. Le mot de passe d’exemple sert à cet exercice local ; les paramètres réels se mettent dans `.env`, exclu de Git.

## Ta prochaine séance
1. Lire une ligne du fichier et expliquer chaque unité.
2. Lancer la validation, puis la démonstration PostgreSQL lorsque Docker est disponible.
3. Vérifier les totaux après deux imports.
4. Faire relire le contrat par Horatio et Adam.
5. Suivre le guide de collecte OpenSky pour importer un premier échantillon réel.

## Documentation des composants
- [Docker Compose et disponibilité des services](https://docs.docker.com/compose/how-tos/startup-order/)
- [Image officielle PostgreSQL](https://hub.docker.com/_/postgres)
- [Psycopg et requêtes paramétrées](https://www.psycopg.org/psycopg3/docs/basic/usage.html)
- [OpenSky et définition des champs](https://openskynetwork.github.io/opensky-api/rest.html)
