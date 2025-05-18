# Stratego-Tezos : Implémentation Blockchain du Jeu Stratego

## Cas d'usage du projet

Stratego-Tezos implémente le jeu de stratégie classique Stratego sur la blockchain Tezos. Ce jeu de plateau oppose deux joueurs qui déplacent leurs pièces sur un échiquier 8×8 avec l'objectif de capturer le drapeau adverse. L'innovation principale réside dans l'utilisation de mécanismes cryptographiques avancés (arbres de Merkle et système de commit-reveal) pour garantir la confidentialité des pièces tout en assurant l'intégrité du jeu sans nécessiter de tiers de confiance.

Le projet répond à une problématique fondamentale des jeux à information imparfaite : comment garantir la confidentialité des informations tout en vérifiant l'honnêteté des joueurs ? Dans Stratego traditionnel, les joueurs ne connaissent pas l'identité des pièces adverses avant une confrontation. La blockchain permet de maintenir cette opacité tout en éliminant le besoin d'un arbitre central.

## Pourquoi ce cas d'usage bénéficie de la blockchain

1. **Confidentialité avec vérifiabilité** : La blockchain permet de mettre en œuvre un système où les joueurs peuvent prouver qu'ils respectent les règles sans révéler l'identité de leurs pièces grâce au mécanisme de commit-reveal et aux preuves Merkle.

2. **Élimination du tiers de confiance** : Le jeu traditionnel de Stratego nécessite soit un arbitre, soit une confiance mutuelle entre les joueurs. La blockchain agit comme un arbitre neutre et impartial qui vérifie le respect des règles sans avoir accès à l'information complète.

3. **Preuves cryptographiques d'équité** : Grâce à l'utilisation d'arbres de Merkle, les joueurs peuvent prouver mathématiquement qu'ils n'ont pas changé la position ou le rang de leurs pièces après le début de la partie.

4. **Persistance et immuabilité** : L'historique des parties est conservé de façon permanente sur la blockchain, permettant de vérifier les mouvements passés et d'analyser les stratégies.

5. **Identité numérique des joueurs** : L'utilisation de NFTs (contrat PlayerNFT) pour représenter les joueurs crée un système d'identité et de réputation vérifiable qui ajoute une dimension sociale et compétitive au jeu.

6. **Économie de jetons** : Le modèle peut facilement être étendu pour intégrer des mécanismes économiques comme des tournois avec frais d'entrée ou des récompenses pour les vainqueurs.

## Principe de fonctionnement et smart contracts

### Architecture globale

Stratego-Tezos utilise une architecture hybride combinant composants on-chain (smart contracts) et off-chain (client) :

#### Composants on-chain :

1. **StrategoGame** : Le contrat principal qui gère la logique du jeu, incluant :
   - Création et gestion des parties
   - Vérification des mouvements
   - Résolution des batailles
   - Vérification des preuves Merkle

2. **PlayerNFT** : Contrat conforme au standard FA2 (TZIP-12) qui :
   - Gère les identités des joueurs sous forme de NFTs
   - Stocke les clés publiques et statistiques des joueurs
   - Maintient l'historique des parties jouées

#### Composants off-chain :

1. **Module crypto** : Gère les paires de clés et la signature des mouvements
2. **Module merkle** : Implémente la génération des arbres de Merkle et des preuves
3. **Client** : Interface utilisateur pour interagir avec les contrats

### Mécanisme de jeu sécurisé

Le cœur de l'innovation est le système de commit-reveal avec arbres de Merkle :

1. **Phase d'initialisation** :
   - Chaque joueur place ses pièces et génère un arbre de Merkle
   - Chaque position et rang de pièce est associé à un nonce aléatoire
   - Seule la racine de l'arbre (Merkle Root) est publiée sur la blockchain

2. **Phase de jeu** :
   - Les joueurs effectuent leurs mouvements à tour de rôle
   - Les mouvements sont signés cryptographiquement
   - La validité des mouvements est vérifiée par le contrat

3. **Batailles** :
   - Lors d'une rencontre entre deux pièces, les joueurs fournissent :
     - Le rang de leur pièce
     - Le nonce associé
     - Une preuve Merkle prouvant que cette information était dans l'engagement initial
   - Le contrat vérifie ces preuves et résout le conflit selon les règles du jeu
   - Seules les pièces impliquées dans la bataille sont révélées

4. **Fin de partie** :
   - La partie se termine quand un joueur capture le drapeau adverse
   - Les statistiques sont mises à jour dans le contrat PlayerNFT

### Structure des données principales

Les structures de données principales du contrat StrategoGame sont :

1. **GAME** : Stocke les informations de la partie (joueurs, racines Merkle, état actuel)
2. **BATTLE** : Représente une confrontation entre deux pièces (positions, preuves, résolution)
3. **MOVE** : Enregistre un mouvement (positions de départ/arrivée, signature, horodatage)

Le contrat PlayerNFT utilise également :

1. **TOKEN_META** : Métadonnées du NFT selon le standard TZIP-12
2. **GAME_KEY** : Clés cryptographiques associées à chaque partie pour un joueur

## Description de la DApp dans son ensemble

### Composants principaux et leurs interactions

1. **Smart Contracts (On-chain)**
   - **PlayerNFT** : Gère l'identité des joueurs, stocke les clés et statistiques
   - **StrategoGame** : Implémente les règles du jeu et vérifie les preuves cryptographiques

2. **Cryptographie (Off-chain)**
   - **Module keypair** : Génère et gère les paires de clés ED25519 pour signer les mouvements
   - **Module signer** : Signe et vérifie les mouvements et les preuves de bataille
   - **Module merkle_tree** : Construit les arbres de Merkle et génère les preuves d'appartenance

3. **Interface utilisateur**
   - Affichage du plateau (vue limitée pour les pièces adverses)
   - Interface de placement initial des pièces
   - Gestion des parties et visualisation des statistiques

4. **Stockage local**
   - Sauvegarde des clés privées et de l'état du jeu
   - Création et vérification des preuves Merkle

### Flux d'utilisation principal

1. **Création de compte joueur**
   - L'utilisateur génère une paire de clés
   - Un NFT joueur est créé via le contrat PlayerNFT
   - Les statistiques initiales sont établies

2. **Création ou participation à une partie**
   - Un joueur crée une nouvelle partie via le contrat
   - L'adversaire rejoint la partie existante
   - Les deux joueurs génèrent des clés spécifiques pour la partie

3. **Placement initial et engagement**
   - Chaque joueur place secrètement ses pièces
   - Un arbre de Merkle est généré à partir des positions et rangs
   - La racine de l'arbre est publiée sur la blockchain (commit)

4. **Phase de jeu**
   - Les joueurs effectuent leurs mouvements alternativement
   - Chaque mouvement est signé cryptographiquement
   - Les mouvements sont vérifiés et enregistrés sur la blockchain

5. **Résolution des batailles**
   - Quand deux pièces se rencontrent, les joueurs soumettent leurs preuves
   - Le contrat vérifie l'authenticité des pièces via les preuves Merkle
   - Le conflit est résolu selon les règles du jeu (rang supérieur gagne)

6. **Fin de partie**
   - La partie se termine quand un joueur capture le drapeau adverse
   - Les statistiques des joueurs sont mises à jour
   - Les clés privées peuvent être révélées pour vérification complète

### Sécurité et confidentialité

Le système est conçu pour prévenir plusieurs types de tricherie :

1. **Changement de pièces** : Impossible grâce à l'engagement via la racine Merkle
2. **Mensonge sur le rang** : Vérifié par les preuves Merkle lors des batailles
3. **Mouvements invalides** : Vérifiés par le contrat selon les règles du jeu
4. **Abandon abusif** : Géré par des timeouts et des pénalités

## Diagrammes UI et interactions

### Interface d'accueil
```
+-----------------------------------------------+
|                STRATEGO-TEZOS                 |
+-----------------------------------------------+
|                                               |
|   [Connecter votre wallet Tezos]              |
|                                               |
|   OU                                          |
|                                               |
|   [Créer un nouveau compte]                   |
|                                               |
+-----------------------------------------------+
```

### Tableau de bord
```
+-----------------------------------------------+
| STRATEGO-TEZOS           Joueur: Alice        |
+-----------------------------------------------+
|                                               |
| Mes statistiques:                             |
| - Parties jouées: 15                          |
| - Victoires: 8                                |
| - Défaites: 7                                 |
| - Classement: 1025                            |
|                                               |
| [Créer une partie]    [Rejoindre une partie]  |
|                                               |
| Parties en cours:                             |
| - vs Bob (Tour: Vous)                         |
| - vs Charlie (Tour: Adversaire)               |
|                                               |
| Parties terminées:                            |
| - vs Dave (Victoire)                          |
| - vs Eve (Défaite)                            |
|                                               |
+-----------------------------------------------+
```

### Placement initial des pièces
```
+-----------------------------------------------+
| STRATEGO-TEZOS     Nouvelle partie vs Bob     |
+-----------------------------------------------+
|                                               |
| Placez vos pièces:                            |
|                                               |
| Pièces disponibles:                           |
| - Drapeau (x1)     - Maréchal (x1)            |
| - Général (x2)     - Colonel (x3)             |
| - ...                                         |
|                                               |
| +---+---+---+---+---+---+---+---+             |
| |   |   |   |   |   |   |   |   | 8           |
| +---+---+---+---+---+---+---+---+             |
| |   |   |   |   |   |   |   |   | 7           |
| +---+---+---+---+---+---+---+---+             |
| |   |   |   |   |   |   |   |   | 6           |
| +---+---+---+---+---+---+---+---+             |
| |   |   |   |   |   |   |   |   | 5           |
| +---+---+---+---+---+---+---+---+             |
| |   |   | X | X | X | X |   |   | 4           |
| +---+---+---+---+---+---+---+---+             |
| |   |   | X | X | X | X |   |   | 3           |
| +---+---+---+---+---+---+---+---+             |
| |   |   |   |   |   |   |   |   | 2           |
| +---+---+---+---+---+---+---+---+             |
| |   |   |   |   |   |   |   |   | 1           |
| +---+---+---+---+---+---+---+---+             |
|   A   B   C   D   E   F   G   H               |
|                                               |
| [Placement aléatoire]     [Confirmer]         |
|                                               |
+-----------------------------------------------+
```

### Interface de jeu
```
+-----------------------------------------------+
| STRATEGO-TEZOS     Partie vs Bob              |
+-----------------------------------------------+
|                                               |
| Tour: À vous de jouer                         |
|                                               |
| +---+---+---+---+---+---+---+---+             |
| | ? | ? | ? | ? | ? | ? | ? | ? | 8           |
| +---+---+---+---+---+---+---+---+             |
| | ? | ? | ? | ? | ? | ? | ? | ? | 7           |
| +---+---+---+---+---+---+---+---+             |
| | ? | ? | ? | ? | ? | ? | ? | ? | 6           |
| +---+---+---+---+---+---+---+---+             |
| | ? | ? |///|///|///|///| ? | ? | 5           |
| +---+---+---+---+---+---+---+---+             |
| | ? | ? |///|///|///|///| ? | ? | 4           |
| +---+---+---+---+---+---+---+---+             |
| | 9 | ? | ? | ? | ? | ? | ? | ? | 3           |
| +---+---+---+---+---+---+---+---+             |
| | 3 | 5 | 5 | 7 | 8 | 9 | 9 |11 | 2           |
| +---+---+---+---+---+---+---+---+             |
| | 1 | 2 | B |11 | F |11 |10 | 4 | 1           |
| +---+---+---+---+---+---+---+---+             |
|   A   B   C   D   E   F   G   H               |
|                                               |
| Dernier coup: Bob a déplacé de G7 à G6        |
|                                               |
| [Abandonner]        [Historique]              |
|                                               |
+-----------------------------------------------+
```

### Résolution d'une bataille
```
+-----------------------------------------------+
| STRATEGO-TEZOS     Bataille en D4             |
+-----------------------------------------------+
|                                               |
| Votre pièce: Colonel (3)                      |
| Pièce ennemie: Capitaine (6)                  |
|                                               |
| Résultat: Victoire!                           |
|                                               |
| [Continuer]                                   |
|                                               |
+-----------------------------------------------+
```

### Diagramme de flux d'interaction
```
+---------------+        +------------------+        +-------------+
|               |        |                  |        |             |
| Joueur 1      |<------>| Smart Contracts  |<------>| Joueur 2    |
|               |        |                  |        |             |
+---------------+        +------------------+        +-------------+
       ^                         ^                         ^
       |                         |                         |
+------+------+           +------+------+           +------+------+
|             |           |             |           |             |
| Client      |           | Blockchain  |           | Client      |
| Off-chain   |           | Tezos       |           | Off-chain   |
|             |           |             |           |             |
+-------------+           +-------------+           +-------------+
```

## Améliorations potentielles

1. **Optimisation on-chain/off-chain**
   - Implémenter un système de canaux d'état pour réduire les interactions avec la blockchain
   - Batching des mouvements pour réduire les coûts de transaction
   - Optimisation des preuves Merkle pour minimiser leur taille

2. **Amélioration du système cryptographique**
   - Intégration de preuves à divulgation nulle de connaissance (ZKPs)
   - Utilisation de l'extension Sapling de Tezos pour des transactions confidentielles
   - Renforcement de la sécurité des clés utilisateur avec MPC (Multi-Party Computation)

3. **Expansions du gameplay**
   - Support pour diverses variantes des règles de Stratego
   - Système de tournois avec classement global
   - Mode spectateur pour observer des parties en cours
   - Implémentation de délais d'échecs pour des parties plus dynamiques

4. **Interface utilisateur avancée**
   - Application mobile cross-platform avec notifications push
   - Interface de jeu 3D avec animations des batailles
   - Tutoriels interactifs pour les nouveaux joueurs
   - Fonctionnalités sociales (chat, liste d'amis, défis)

5. **Tokenomics et monétisation**
   - Système de paris sur les parties avec escrow automatique
   - NFTs de personnalisation (skins pour les pièces)
   - Tournois avec frais d'inscription et pot de récompense
   - Modèle de gouvernance DAO pour l'évolution du jeu

6. **Scalabilité et performances**
   - Optimisation des smart contracts pour réduire les coûts de gas
   - Implémentation de solutions Layer 2 pour une meilleure scalabilité
   - Système de matchmaking intelligent pour des parties équilibrées

7. **Accessibilité et interopérabilité**
   - Support multi-wallet (Temple, Kukai, etc.)
   - Intégration avec d'autres plateformes blockchain
   - API pour permettre à des développeurs tiers de créer des extensions