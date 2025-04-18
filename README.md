# Bot Telegram pour Emploi du Temps Pronote

## Description

Ce projet propose un **bot Telegram** capable de :

1. Se connecter à **Pronote** via Selenium  
2. Récupérer l’heure de début, la première matière et l’heure de fin des cours de **demain**  
3. Envoyer ces informations directement dans le chat Telegram de l’utilisateur  
4. Programmer un **rappel quotidien** à l’heure souhaitée  
5. Gérer les identifiants Pronote en ne les demandant qu’**une seule fois**, grâce à un stockage sécurisé en JSON  

L’objectif est d’automatiser la consultation de l’emploi du temps sans intervention manuelle, et de recevoir chaque matin un message synthétique dans Telegram.

---

## Table des matières

1. [Prérequis](#prérequis)  
2. [Installation & Configuration](#installation--configuration)  
3. [Structure du projet](#structure-du-projet)  
4. [Commandes disponibles](#commandes-disponibles)  
5. [Flux d’utilisation](#flux-dutilisation)  
6. [Explication détaillée du code](#explication-détaillée-du-code)  
7. [Stockage et cache](#stockage-et-cache)  
8. [Personnalisation](#personnalisation)  
9. [Dépannage](#dépannage)  
10. [Sécurité](#sécurité)  
11. [Licence](#licence)  

---

## Prérequis

- **Python 3.7+**  
- **Google Chrome** installé  
- **ChromeDriver** (version compatible avec Chrome) dans le `PATH` ou spécifié explicitement  
- **Bot Telegram** : un token obtenu via **BotFather**  
- Bibliothèques Python :

  ```bash
  pip install selenium python-telegram-bot==20.0
  ```

> ⚙️ *Optionnel* : créez et activez un environnement virtuel :

```bash
python -m venv venv
# Linux/Mac
source venv/bin/activate
# Windows
venv\Scripts\activate
```

---

## Installation & Configuration

1. **Cloner le dépôt**  
   ```bash
   git clone https://.../bot-pronote-telegram.git
   cd bot-pronote-telegram
   ```

2. **Définir le token Telegram**  
   Dans `main.py`, modifiez la ligne :

   ```python
   BOT_TOKEN = "VOTRE_TOKEN_TELEGRAM"
   ```

   ou, de manière plus sécurisée, utilisez une variable d’environnement :

   ```python
   import os
   BOT_TOKEN = os.getenv("BOT_TOKEN")
   ```

3. **Adapter l’URL Pronote**  
   Si votre établissement utilise une URL Pronote différente, remplacez :

   ```python
   driver.get("https://keycloak.moncollege-valdoise.fr/.../pronote/eleve.html")
   ```

4. **Installer ChromeDriver**  
   Vérifiez la version de votre Chrome (`chrome://version/`) et téléchargez le ChromeDriver correspondant. Placez-le dans `/usr/local/bin` ou un dossier de votre `PATH`.

---

## Structure du projet

```
.
├── main.py            # Script principal du bot
├── users.json         # Stocke les identifiants Pronote par chat_id
├── rappels.json       # Stocke les heures de rappel par chat_id
├── edt_cache.json     # Cache temporaire de l’emploi du temps
└── README.md          # Documentation (ce fichier)
```

- Les fichiers JSON sont **créés automatiquement** lors des premières utilisations.
- **Ne versionnez pas** les fichiers JSON (ajoutez-les à `.gitignore`).

---

## Commandes disponibles

| Commande  | Description                                                      |
|-----------|------------------------------------------------------------------|
| `/start`  | Présentation des fonctionnalités et liste des commandes          |
| `/login`  | Enregistrement de ton **nom d’utilisateur** et **mot de passe**  |
| `/edt`    | Affiche l’heure de début et la première matière de **demain**    |
| `/rappel` | Programme un **rappel quotidien** à l’heure de ton choix         |
| `/reset`  | Supprime les données (identifiants, rappels, cache)             |
| `/aide`   | Affiche l’aide détaillée                                         |

---

## Flux d’utilisation

1. **Démarrage**  
   ```bash
   python main.py
   ```
2. Envoie `/start` dans Telegram pour afficher les commandes.  
3. Exécute `/login` et suis la conversation pour saisir ton **username** et ton **password** Pronote.  
   - Ces informations sont sauvegardées dans `users.json`.  
   - **Une seule saisie** suffit pour toutes les futures requêtes.  
4. Utilise `/edt` pour récupérer immédiatement l’emploi du temps de demain.  
5. Pour un envoi quotidien, exécute `/rappel` et indique l’heure (HH:MM).  
6. Chaque matin à l’heure choisie, le bot envoie automatiquement le message.  
7. Si besoin, `/reset` pour tout supprimer et repartir de zéro.

---

## Explication détaillée du code

### 1. Gestion des JSON

- **`load_json(path)`** / **`save_json(path, data)`** : fonctions utilitaires pour charger/sauver les fichiers `users.json`, `rappels.json` et `edt_cache.json`.

### 2. Connexion Pronote

- **Selenium Chrome** : ouverture d’une session, saisie automatique des champs `username` et `password`, puis clic sur le bouton de connexion.
- **Extraction** : 
  ```python
  cours_list = driver.find_elements(By.CSS_SELECTOR, 'ul.liste-cours > li.flex-contain')
  ```
  puis itération pour récupérer :
  - `heure_debut` : début du **premier cours**
  - `premiere_matiere` : intitulé de la première matière
  - `derniere_heure` : heure de fin du **dernier cours**

### 3. Commandes Telegram

- **Framework** : `python-telegram-bot` version 20  
- **Handlers** :
  - **CommandHandler** pour `/start`, `/edt`, `/aide`  
  - **ConversationHandler** pour `/login`, `/rappel`, `/reset`  
- **Flux** :
  - Le bot utilise `context.user_data` pour stocker temporairement les réponses utilisateur.
  - À la fin de chaque conversation, les données sont persistées en JSON.

### 4. Rappel automatique

- Fonction `planifier_rappel(chat_id, heure_str, bot)` :
  - Calcule le délai jusqu’à la prochaine occurrence (aujourd’hui ou demain).  
  - Lance une **tâche asyncio** récurrente (`while True`) qui s’endort 24 h après chaque envoi.

---

## Stockage et cache

- **`users.json`** :  
  ```json
  {
    "123456789": {
      "username": "mon.login",
      "password": "monMotDePasse"
    }
  }
  ```
- **`rappels.json`** :  
  ```json
  {
    "123456789": "07:30"
  }
  ```
- **`edt_cache.json`** (optionnel) : cache des derniers résultats pour éviter de recharger Pronote trop fréquemment.

---

## Personnalisation

- **URL et sélecteurs Pronote** : adaptez les `By.CSS_SELECTOR` si la structure HTML diffère.  
- **Format du message** : modifiez les templates Markdown dans `edt()` et `boucle()`.  
- **Fuseau horaire** : si vous êtes hors de France, gérez `datetime.now()` et `timedelta` en conséquence.

---

## Dépannage

1. **Échec ChromeDriver**  
   - Vérifiez la version via `chrome://version/` et téléchargez la version correspondante.  
   - Spécifiez `webdriver.Chrome(executable_path="…")` si nécessaire.

2. **Login bloqué**  
   - Pronote peut imposer un CAPTCHA ou redirection.  
   - Vérifiez manuellement la page et ajustez les sélecteurs.

3. **Bot Telegram ne répond pas**  
   - Assurez-vous que le token est valide et que le bot est démarré dans Telegram.  
   - Consultez les logs imprimés dans la console.

4. **Tâche de rappel non déclenchée**  
   - Vérifiez que le script tourne en continu (ne pas fermer le terminal).  
   - Contrôlez l’heure système et le calcul de `delta`.

---

## Sécurité

- **Identifiants Pronote** : stockés en clair dans `users.json`.  
  - **Recommandation** : utilisez un chiffrement ou un gestionnaire de secrets pour une production.  
- **JSON sensibles** : ajoutez `users.json` et `rappels.json` à `.gitignore`.  
- **Bot_token** : ne le partagez jamais publiquement.

---

## Licence

Please just don't steal my code..
