# Vérifications du premier exercice

Suivi mis à jour le 9 novembre 2026.

## Validation locale
- 15 tests de validation réussis avec Python 3.14.2 et Python 3.12.14 dans l’environnement de développement.
- Commande `validate` exécutée : 7 lignes valides, 6 observations distinctes, 1 doublon et 2 aéronefs.
- Dates avec fuseau normalisées, valeurs absentes conservées et nombres invalides refusés.
- Les tests de lecture d’un fichier invalide et d’un fichier vide utilisent des flux en mémoire. Le jeu principal est lu depuis le disque.

## Validation PostgreSQL sur le poste utilisateur
L’utilisateur a lancé la démonstration puis la suite complète dans Docker Desktop. Les captures transmises dans la conversation montrent la trajectoire de trois positions triées et le résultat suivant :

```text
Ran 20 tests in 1.113s
OK
```

Les 20 tests réussissent, dont les 5 tests PostgreSQL ; aucun test n’est ignoré. Cette preuve provient de l’exécution sur le poste utilisateur, et non d’un accès direct au moteur Docker depuis l’environnement de développement.

Les tests PostgreSQL valident :
- le réimport sans doublons ;
- l’ordre chronologique, le filtrage de période et la conservation d’une altitude absente ;
- la réexécution des migrations ;
- l’annulation complète d’un lot en erreur ;
- la conservation d’un nouvel état sans répéter le même point de trajectoire.

Le premier exercice de stockage et de lecture sur le jeu fictif est validé.

## Reproduire la validation
Depuis le dossier AeroSafe, après le lancement de la base :

```powershell
docker compose run --rm -e AEROSAFE_INTEGRATION=1 --entrypoint python app -m unittest discover -s tests -v
```

Résultat attendu pour la version actuelle avec carte : 42 tests réussis, aucun test ignoré.

## Extension OpenSky
Le 9 novembre 2026, le collecteur ponctuel a reçu une réponse réelle en accès anonyme : 84 observations valides pour 84 avions distincts, aucun rejet. Le fichier normalisé a été relu avec la commande validate : aucun doublon. La réponse source est datée de 09:40:07 UTC ; la récupération s’est achevée à 09:40:14 UTC.

La suite étendue compte 34 tests. Dans l’environnement de développement, 29 réussissent et les 5 tests PostgreSQL restent ignorés faute d’accès direct au moteur Docker. Le résultat utilisateur précédent de 20 tests réussis concerne le socle antérieur. La réussite de cette suite a ensuite été confirmée par l’utilisateur.

Les 14 nouveaux tests couvrent la conversion, les valeurs absentes, les états rejetés, les réponses invalides, les zones vides, les quotas, les erreurs réseau, le cache et l’authentification simulée. La configuration Compose modifiée a passé la commande config --quiet.

Le premier import réel OpenSky est confirmé sur le poste utilisateur : le rapport captures/20261109T094525_58875bb0_report.json indique 85 observations reçues, 85 ajoutées et aucun rejet, en mode live, le 9 novembre 2026 à 09:45:25 UTC (10:45:25 à Paris). Le rapport sauvegardé et la capture utilisateur concordent. Un essai OAuth avec de vrais identifiants reste à confirmer. L’API et le moteur d’alertes restent à réaliser ; l’état de la carte est décrit ci-dessous.

## Extension cartographique
La réussite de la suite de 34 tests et la lecture d’une trajectoire réelle ont été confirmées par l’utilisateur dans la conversation.

La version cartographique ajoute sept tests locaux et un test de requête PostgreSQL. Résultat local : 36 tests réussis et 6 tests PostgreSQL ignorés, soit 42 tests au total. Les tests vérifient notamment le tri, la période, la séparation des sources, les coordonnées manquantes et la protection du contenu HTML embarqué.

Un aperçu depuis les captures a été généré : 136 aéronefs et 316 positions. La syntaxe JavaScript et la configuration Compose ont été vérifiées. Le navigateur intégré a échoué à joindre le serveur local. Les captures fournies ensuite par l’utilisateur confirment le rendu sur son poste : fond de carte chargé, vue d’ensemble de 113 aéronefs et 232 positions, sélection de EZY97WF (40836d), deux positions reliées et dernière position orange. Le panneau affiche la date, l’altitude et la vitesse. Les infobulles et le tableau détaillé ne sont pas visibles dans ces captures et restent à confirmer manuellement.

La dernière capture de terminal confirme la suite complète sur le poste utilisateur :

```text
Ran 42 tests in 1.064s
OK
```

Les 42 tests réussissent sans test ignoré, dont les six tests PostgreSQL. Aucun changement de code n’a été effectué après cette validation ; seules les notes de suivi ont été actualisées. La carte reste un export historique, sans rafraîchissement automatique ni rejeu animé.
