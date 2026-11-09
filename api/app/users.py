# Comptes TEMPORAIRES, en attendant la table Compte du Lot 1.
from app.security import hash_password

FAKE_USERS = {
    "utilisateur": {
        "username": "utilisateur",
        "hashed_password": hash_password("utilisateur123"),
        "role": "utilisateur",
    },
    "superviseur": {
        "username": "superviseur",
        "hashed_password": hash_password("superviseur123"),
        "role": "superviseur",
    },
}