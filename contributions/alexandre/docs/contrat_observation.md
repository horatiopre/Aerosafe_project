# Contrat observation v1
Proposition initiale à valider avec Horatio et Adam. Le format actuel décrit un état normalisé ; ce n’est pas le tableau brut renvoyé par OpenSky.

## Format
Un fichier JSONL contient un objet JSON par ligne, encodé en UTF-8. Exemple fictif :
```json
{
  "icao24": "a0b1c2",
  "source": "synthetic",
  "callsign": "FICT01",
  "position_time": "2026-01-01T10:00:00Z",
  "last_contact": "2026-01-01T10:00:02Z",
  "latitude_deg": 48.7,
  "longitude_deg": 2.3,
  "baro_altitude_m": 1000,
  "velocity_mps": 100,
  "true_track_deg": 359
}
```
L’exemple est indenté pour la lecture ; dans le fichier, chaque objet occupe une seule ligne.

| Champ | Format et signification |
|---|---|
| icao24 | Texte de 6 caractères hexadécimaux, normalisé en minuscules ; obligatoire |
| source | `synthetic` pour les exemples, `opensky` pour les futurs états réels ; obligatoire |
| callsign | Indicatif au moment de l’observation, texte ou null |
| position_time | Heure de dernière mise à jour de la position, ISO 8601 avec fuseau, ou null |
| last_contact | Heure du dernier contact source, ISO 8601 avec fuseau ; obligatoire |
| latitude_deg | Degrés entre -90 et 90, ou null |
| longitude_deg | Degrés entre -180 et 180, ou null |
| baro_altitude_m | Altitude barométrique en mètres, ou null |
| velocity_mps | Vitesse au sol en mètres par seconde, positive ou nulle, ou null |
| true_track_deg | Route au sol en degrés, de 0 inclus à 360 exclu, ou null |

Les champs facultatifs absents deviennent null. Les champs inconnus sont refusés pour détecter les erreurs de noms ou d’unités. Les nombres non finis et les dates sans fuseau sont refusés. Les états sans position sont conservés mais exclus du tracé.

## Horodatages et rejeu
`position_time` et `last_contact` sont des horodatages de la source. La base ajoute `collected_at`, l’heure d’enregistrement initial, et `ingest_mode` : `replay` pour les fichiers importés. Un adaptateur de collecte future pourra utiliser `live`. Ces deux champs ne font pas partie de l’identité de l’observation.

Un fichier rejoué ne devient jamais une observation récente : ses heures source ne changent pas. L’heure de collecte conservée est celle de la première insertion. Les tentatives de collecte répétées ne sont pas encore historisées.

## Identité et trajectoires
L’identité est le SHA-256 du contenu normalisé : avion, source, indicatif, heures source et mesures. Un même contenu, même avec un fuseau exprimé différemment, est inséré une seule fois. Un état enrichi ou modifié est conservé séparément. La future collecte devra utiliser exactement cette normalisation.

La trajectoire est triée par `position_time`, filtrée par source et par aéronef. Pour un même instant de position, le dernier contact est retenu ; en cas d’égalité, l’état enregistré en dernier est sélectionné. La politique d’enrichissement en cas de mesures contradictoires reste à discuter avant l’intégration des données réelles.

## Échanges avec l’équipe
- Horatio peut réutiliser la liste d’objets produite par `trajectory` comme base de réponse de son API.
- Adam peut exploiter les états stockés, y compris ceux sans position, et définir avec l’équipe l’horloge adaptée à R1 et R2.
- Les seuils des alertes, les tables de comptes et les règles ne sont pas figés dans ce premier exercice.
- `359° → 1°` doit être traité comme un écart circulaire de 2° par le futur moteur.

Définition des champs source : [documentation OpenSky](https://openskynetwork.github.io/opensky-api/rest.html).
