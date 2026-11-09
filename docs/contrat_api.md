# AeroSafe : contrat d'API (v0.1, brouillon)

*Responsable : Horatio Presse (Lot 2). À relire avec Alexandre (Lots 1 et 4) et Adam (Lots 3 et 6) avant le mercredi 11 novembre 2026.*

Ce document fixe ce que l'API reçoit et renvoie. Le front peut se développer avec ces exemples avant que la base et le moteur soient prêts. Toute modification après validation est annoncée au groupe et notée dans l'historique en bas de page.

Les points marqués **[À VALIDER]** sont des propositions à trancher ensemble.

---

## 1. Conventions communes

| Sujet | Règle |
|---|---|
| Adresse en local | `http://localhost:8000` · documentation interactive : `/docs` |
| Format | JSON, encodage UTF‑8 |
| Noms des champs | anglais, `snake_case`, alignés sur OpenSky quand le champ en vient (`icao24`, `callsign`, `time_position`, `last_contact`, `true_track`) |
| Identifiant d'aéronef | adresse **ICAO24** en minuscules, 6 caractères hexadécimaux (ex. `3c6444`) |
| Dates et heures | **UTC**, format ISO 8601 avec `Z` (ex. `2026-11-09T14:05:00Z`) |
| Unités | dans le nom du champ : `_m` (mètres), `_ms` (mètres/seconde), `_deg` (degrés). Conversion en ft / kt éventuelle **côté interface uniquement** |
| Valeur absente | `null`. **Jamais 0**, jamais champ supprimé |
| Période | paramètres `start` et `end` (ISO 8601 UTC). `end` doit être après `start`. **[À VALIDER]** durée max 7 jours par requête |
| Authentification | en‑tête `Authorization: Bearer <jeton>` sur toutes les routes sauf `/auth/login` et `/health` |

### Codes de réponse

| Code | Signification | Corps |
|---|---|---|
| 200 | Succès | la donnée demandée |
| 401 | Pas de jeton, jeton faux ou expiré | `{"detail": "Jeton invalide ou expiré"}` |
| 403 | Jeton valide mais rôle insuffisant | `{"detail": "Accès non autorisé pour ce profil"}` |
| 404 | Ressource inexistante (aéronef, alerte, règle) | `{"detail": "Aéronef 3c6444 introuvable"}` |
| 422 | Paramètre invalide (date mal formée, `end` avant `start`…) | format standard FastAPI |

Une recherche ou une période **sans résultat** renvoie **200 avec une liste vide** et un champ `message`, pas une erreur. C'est l'interface qui affiche le message (exigence « résultat vide expliqué »).

---

## 2. Matrice des droits

| Route | Sans compte | Utilisateur | Superviseur |
|---|:-:|:-:|:-:|
| `GET /health` | ✅ | ✅ | ✅ |
| `POST /auth/login` | ✅ | ✅ | ✅ |
| `GET /auth/me` | ❌ 401 | ✅ | ✅ |
| `GET /status` | ❌ 401 | ✅ | ✅ |
| `GET /aircraft/...` (recherche, fiche, observations, trajectoire, stats) | ❌ 401 | ✅ | ✅ |
| `GET /alerts`, `GET /alerts/{id}` | ❌ 401 | ❌ 403 | ✅ |
| `GET /dashboard` | ❌ 401 | ❌ 403 | ✅ |
| `GET /rules` | ❌ 401 | ❌ 403 **[À VALIDER]** | ✅ |
| `PATCH /rules/{code}` | ❌ 401 | ❌ 403 | ✅ **[À VALIDER avec l'enseignante]** |

**[À VALIDER]** La V2 dit qu'un Utilisateur « consulte les données autorisées mais ne modifie pas les règles ». Question : l'Utilisateur peut‑il **voir** les règles et les alertes d'un aéronef (lecture seule) ? Le cahier des charges réserve F07 et F08 au Superviseur ; le tableau ci‑dessus suit le cahier des charges.

Chaque ligne ❌ de ce tableau a un test automatique (401 et 403).

---

## 3. Authentification

### `POST /auth/login`
Corps au format **formulaire** (`application/x-www-form-urlencoded`), pas JSON :
```
username=superviseur&password=superviseur123
```
Réponse 200 :
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "superviseur"
}
```
Réponse 401 : `{"detail": "Identifiant ou mot de passe incorrect"}`

Le jeton expire au bout de 60 minutes. L'interface le garde en mémoire et renvoie l'utilisateur vers la connexion sur un 401.

### `GET /auth/me`
```json
{ "username": "superviseur", "role": "superviseur" }
```
`role` vaut `"utilisateur"` ou `"superviseur"`.

---

## 4. Système

### `GET /health`
```json
{ "status": "ok" }
```

### `GET /status`
Sert au bandeau « mode et fraîcheur des données » (exigence panne et reprise).
```json
{
  "mode": "local",
  "last_successful_collection": "2026-11-09T13:58:00Z",
  "last_observation_time": "2026-11-09T13:57:41Z",
  "message": "OpenSky indisponible : affichage des données enregistrées."
}
```
`mode` vaut `"direct"` (collecte OpenSky active) ou `"local"` (jeu enregistré / cache). **Dépend du Lot 1 (Alexandre)**.

---

## 5. Aéronefs (F02 à F05)

### `GET /aircraft/search?q=AFR`
Recherche par ICAO24 **ou** par indicatif (début de chaîne, sans tenir compte des majuscules).
```json
{
  "query": "AFR",
  "results": [
    { "icao24": "3946e1", "callsign": "AFR1234", "last_seen": "2026-11-09T13:57:41Z" },
    { "icao24": "39856a", "callsign": "AFR56KL", "last_seen": "2026-11-09T13:55:02Z" }
  ],
  "message": null
}
```
Sans résultat :
```json
{ "query": "ZZZ", "results": [], "message": "Aucun aéronef ne correspond à « ZZZ »." }
```
**[À VALIDER]** nombre max de résultats (proposition : 20).

### `GET /aircraft/{icao24}`
Fiche de l'aéronef.
```json
{
  "icao24": "3946e1",
  "callsign": "AFR1234",
  "origin_country": "France",
  "first_seen": "2026-11-09T10:12:00Z",
  "last_seen": "2026-11-09T13:57:41Z",
  "observation_count": 742
}
```
404 si l'ICAO24 est inconnu.

### `GET /aircraft/{icao24}/observations?start=...&end=...`
Toutes les observations de la période, triées par `time_position` croissant (les observations sans position à la fin, triées par `last_contact`).
```json
{
  "icao24": "3946e1",
  "start": "2026-11-09T12:00:00Z",
  "end": "2026-11-09T14:00:00Z",
  "observations": [
    {
      "id": 18452,
      "time_position": "2026-11-09T12:00:05Z",
      "last_contact": "2026-11-09T12:00:06Z",
      "collected_at": "2026-11-09T12:00:10Z",
      "latitude": 48.7262,
      "longitude": 2.3652,
      "baro_altitude_m": 3048.0,
      "geo_altitude_m": 3120.5,
      "velocity_ms": 154.3,
      "true_track_deg": 271.4,
      "vertical_rate_ms": -2.6,
      "on_ground": false,
      "source_mode": "direct"
    },
    {
      "id": 18453,
      "time_position": null,
      "last_contact": "2026-11-09T12:00:16Z",
      "collected_at": "2026-11-09T12:00:20Z",
      "latitude": null,
      "longitude": null,
      "baro_altitude_m": 3040.0,
      "geo_altitude_m": null,
      "velocity_ms": 154.0,
      "true_track_deg": null,
      "vertical_rate_ms": null,
      "on_ground": false,
      "source_mode": "direct"
    }
  ],
  "message": null
}
```
Période vide : `"observations": []` et `"message": "Aucune observation pour cet aéronef sur la période choisie."`

Différence importante (cf. V2 et doc OpenSky) : `time_position` = heure de la dernière **position** ; `last_contact` = heure du dernier **message reçu**, quel qu'il soit. R1 utilise `last_contact`, R2 utilise `time_position`.

**[À VALIDER avec Alexandre]** liste exacte des champs stockés, et quelle altitude (`baro` ou `geo`) sert de référence aux courbes et à R3. Proposition : `baro_altitude_m`.

### `GET /aircraft/{icao24}/trajectory?start=...&end=...`
Uniquement les positions **valides** (latitude et longitude non nulles), triées par `time_position`. Format allégé pour la carte (Lot 4).
```json
{
  "icao24": "3946e1",
  "start": "2026-11-09T12:00:00Z",
  "end": "2026-11-09T14:00:00Z",
  "points": [
    { "time_position": "2026-11-09T12:00:05Z", "latitude": 48.7262, "longitude": 2.3652, "baro_altitude_m": 3048.0, "true_track_deg": 271.4 },
    { "time_position": "2026-11-09T12:00:25Z", "latitude": 48.7270, "longitude": 2.3521, "baro_altitude_m": 3061.0, "true_track_deg": 271.9 }
  ],
  "excluded_observations": 3,
  "message": null
}
```
`excluded_observations` = nombre d'observations écartées faute de position (pour l'expliquer à l'utilisateur).

### `GET /aircraft/{icao24}/stats?start=...&end=...`
Statistiques et séries pour les graphiques (Lot 6, Adam).
```json
{
  "icao24": "3946e1",
  "start": "2026-11-09T12:00:00Z",
  "end": "2026-11-09T14:00:00Z",
  "observation_count": 360,
  "altitude": { "unit": "m", "min": 0.0, "max": 10668.0, "mean": 8321.4, "missing": 4 },
  "velocity": { "unit": "m/s", "min": 0.0, "max": 251.2, "mean": 212.7, "missing": 0 },
  "series": [
    { "time": "2026-11-09T12:00:05Z", "baro_altitude_m": 3048.0, "velocity_ms": 154.3 },
    { "time": "2026-11-09T12:00:15Z", "baro_altitude_m": null, "velocity_ms": 154.0 }
  ],
  "alerts_in_period": [
    { "id": 77, "rule_code": "R3", "triggered_at": "2026-11-09T12:41:10Z" }
  ]
}
```
`missing` = nombre de valeurs absentes, exclues des calculs. `alerts_in_period` sert aux repères d'alerte sur les courbes ; **vide pour un Utilisateur** si la lecture des alertes lui est refusée **[À VALIDER]**.

**[À VALIDER avec Adam]** les séries suffisent‑elles aux graphiques, ou faut‑il d'autres grandeurs (`vertical_rate_ms`…) ?

---

## 6. Alertes et supervision (F06, F07) : Superviseur uniquement

### `GET /alerts?start=...&end=...&icao24=...&rule=R3&limit=50`
Tous les filtres sont facultatifs. Tri : plus récente d'abord.
```json
{
  "total": 2,
  "alerts": [
    {
      "id": 77,
      "icao24": "3946e1",
      "callsign": "AFR1234",
      "rule_code": "R3",
      "rule_version": 1,
      "triggered_at": "2026-11-09T12:41:10Z",
      "observed_value": 610.0,
      "threshold": 500.0,
      "unit": "m",
      "message": "Variation d'altitude de 610 m en 20 s (seuil 500 m)."
    },
    {
      "id": 76,
      "icao24": "39856a",
      "callsign": "AFR56KL",
      "rule_code": "R1",
      "rule_version": 1,
      "triggered_at": "2026-11-09T12:30:00Z",
      "observed_value": 420.0,
      "threshold": 300.0,
      "unit": "s",
      "message": "Aucun contact depuis 420 s (seuil 300 s)."
    }
  ]
}
```

### `GET /alerts/{id}`
Détail avec les observations qui ont provoqué le déclenchement (exigence de traçabilité).
```json
{
  "id": 77,
  "icao24": "3946e1",
  "callsign": "AFR1234",
  "rule_code": "R3",
  "rule_version": 1,
  "rule_description": "Variation importante d'altitude entre deux observations valides",
  "triggered_at": "2026-11-09T12:41:10Z",
  "observed_value": 610.0,
  "threshold": 500.0,
  "unit": "m",
  "message": "Variation d'altitude de 610 m en 20 s (seuil 500 m).",
  "source_observations": [
    { "id": 18601, "time_position": "2026-11-09T12:40:50Z", "baro_altitude_m": 7010.0 },
    { "id": 18603, "time_position": "2026-11-09T12:41:10Z", "baro_altitude_m": 7620.0 }
  ]
}
```
Pour R1 et R2 (pas de paire d'observations), `source_observations` contient la dernière observation connue. **[À VALIDER avec Adam]** format exact de l'alerte, valeurs et unités de chaque règle.

### `GET /dashboard?start=...&end=...`
Vue d'ensemble du tableau de bord.
```json
{
  "tracked_aircraft": 42,
  "alerts_total": 17,
  "alerts_by_rule": { "R1": 5, "R2": 3, "R3": 4, "R4": 2, "R5": 3 },
  "recent_alerts": [
    { "id": 77, "icao24": "3946e1", "callsign": "AFR1234", "rule_code": "R3", "triggered_at": "2026-11-09T12:41:10Z" }
  ],
  "aircraft": [
    { "icao24": "3946e1", "callsign": "AFR1234", "last_seen": "2026-11-09T13:57:41Z", "alert_count": 2 }
  ]
}
```
Sans `start`/`end` : dernières 24 h **[À VALIDER]**.

---

## 7. Règles (F08)

### `GET /rules`
```json
[
  {
    "code": "R3",
    "description": "Variation importante d'altitude entre deux observations valides",
    "version": 1,
    "threshold": 500.0,
    "unit": "m",
    "parameters": { "max_interval_s": 60 },
    "editable": true,
    "updated_at": "2026-11-09T09:00:00Z"
  }
]
```
Une entrée par règle R1 à R5. Seuils et paramètres définitifs : **Adam**, après validation par l'enseignante.

### `PATCH /rules/{code}` **[À VALIDER avec l'enseignante]**
Corps JSON :
```json
{ "threshold": 600.0 }
```
Réponse 200 : la règle mise à jour, avec `version` incrémentée. Les alertes passées gardent leur `rule_version` d'origine (V2 : « une modification de règle conserve l'historique »). Refus 422 si le seuil est négatif ou nul.

---

## 8. Questions ouvertes à régler mercredi

| # | Question | Avec qui |
|---|---|---|
| 1 | Liste exacte des champs d'observation stockés, et altitude de référence (baro ou géo) | Alexandre |
| 2 | `/status` : comment l'API sait‑elle si la collecte est en mode direct ou local ? | Alexandre |
| 3 | Format définitif d'une alerte, unités et valeurs observées de chaque règle | Adam |
| 4 | Séries nécessaires aux graphiques | Adam |
| 5 | L'Utilisateur peut‑il lire les règles et les alertes ? | Groupe, puis enseignante |
| 6 | Modification des seuils depuis l'interface autorisée ? | Enseignante |
| 7 | Durée max d'une période, nombre max de résultats | Groupe |

---

## Historique

| Version | Date | Auteur | Changement |
|---|---|---|---|
| 0.1 | 9 nov. 2026 | Horatio Presse | Premier jet |
