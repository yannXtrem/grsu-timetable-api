# API RESTful – Emploi du temps GRSU

**Version :** 1.0  
**Base URL :** `http://localhost:5000/api` (par défaut)  
**Format des données :** JSON  
**Encodage :** UTF-8  

## Table des matières

- [Présentation générale](#présentation-générale)
- [Installation rapide (optionnelle)](#installation-rapide-optionnelle)
- [Endpoints](#endpoints)
  - [GET `/timetable/{date}`](#get-timetabledate) – **Principal**
  - [GET `/timetable/group/{group_name}/{week_number}`](#get-timetablegroupgroup_nameweek_number)
  - [POST `/scrape`](#post-scrape)
  - [GET `/groups`](#get-groups)
  - [GET `/cache/stats`](#get-cachestats)
  - [POST `/cache/clear`](#post-cacheclear)
- [Gestion du cache](#gestion-du-cache)
- [Codes d’erreur](#codes-derreur)
- [Exemples d’intégration](#exemples-dintégration)
  - [JavaScript (fetch)](#javascript-fetch)
  - [Python (requests)](#python-requests)
- [Limitations et remarques](#limitations-et-remarques)

---

## Présentation générale

Cette API permet de récupérer **l’emploi du temps hebdomadaire** des groupes d’étudiants de l’Université d’État de Grodno (GRSU) à partir du site officiel `raspisanie.grsu.by`.

Les données sont extraites en temps réel via scraping HTML, puis mises en cache mémoire pour améliorer les performances et éviter de surcharger le site source. L’API ne nécessite **aucune base de données externe** – tout est conservé dans la mémoire du processus Flask.

### Fonctionnalités principales

- **Endpoint RESTful simple** : une date suffit pour obtenir l’emploi du temps de la semaine correspondante.
- **Paramètres par défaut configurables** (groupe, année, etc.).
- **Mise en cache automatique** avec durée de vie configurable.
- **Rafraîchissement manuel** possible pour forcer une mise à jour.
- **Support complet du modèle de données** (jour, heure, matière, enseignant, salle, sous‑groupe).

### Structure d’une réponse type

```json
{
  "week_number": 2,
  "group_name": "СДП-УИР-251.1.1",
  "days": [
    {
      "weekday": 0,
      "monthday": 20,
      "classes": [
        {
          "subject": {
            "name": "Физическая культура",
            "lecturer": { "name": "ст.пр. Зенкевич В.Н." }
          },
          "time": { "start": "15:05", "end": "16:30" },
          "subgroup": "Tous",
          "door": "спортзал"
        }
      ]
    }
  ]
}
```

**Convention des jours** : `weekday` suit la norme `0 = Lundi`, `1 = Mardi`, …, `6 = Dimanche`.  
**Sous‑groupe** : `"Tous"` indique un cours pour l’ensemble du groupe, sinon `"1"`, `"2"`, etc.

---

## Installation rapide (optionnelle)

Si vous souhaitez exécuter l’API en local :

```bash
git clone <repository>
cd timetable_api
pip install -r requirements.txt
python app.py
```

L’API sera accessible sur `http://localhost:5000`.

> **Remarque** : pour une utilisation en production, il est recommandé d’utiliser un serveur WSGI (Gunicorn, Waitress) et d’ajuster la variable `CACHE_TTL` dans `config.py`.

---

## Endpoints

### GET `/timetable/{date}`

**Endpoint principal recommandé.**  
Retourne l’emploi du temps de la semaine contenant la date fournie, en utilisant les paramètres de groupe par défaut (définis dans `config.py`).

#### Paramètres de chemin

| Nom    | Type   | Description                                      | Exemple      |
|--------|--------|--------------------------------------------------|--------------|
| `date` | string | Date au format ISO `YYYY-MM-DD`                  | `2026-04-22` |

#### Paramètres de requête (query string)

| Nom                | Type    | Défaut | Description                                                                                     |
|--------------------|---------|--------|-------------------------------------------------------------------------------------------------|
| `refresh`          | boolean | `false`| Si `true`, ignore le cache et effectue un nouveau scraping.                                      |
| `scrape_if_missing`| boolean | `true` | Si `true` et que la donnée n’est pas en cache, lance automatiquement le scraping.                |
| `arg0`             | string  | *valeur par défaut* | Identifiant principal du groupe (cf. URL du site source).                           |
| `arg1`             | string  | *valeur par défaut* | Paramètre supplémentaire (généralement `3`).                                        |
| `arg2`             | string  | *valeur par défaut* | Numéro de semaine (si connu, sinon le scraping le déduit automatiquement).          |
| `arg3`             | string  | *valeur par défaut* | Paramètre de filtre (ex: `1`).                                                      |
| `arg4`             | string  | *valeur par défaut* | Paramètre de filtre (ex: `1`).                                                      |
| `lang`             | string  | *valeur par défaut* | Langue (laisser vide).                                                              |

#### Exemple de requête

```bash
curl "http://localhost:5000/api/timetable/2026-04-22"
```

#### Réponse (succès – 200 OK)

Corps : objet JSON représentant un `ScheduleWeek` (cf. [structure détaillée](#structure-dune-réponse-type)).

#### Codes de réponse possibles

| Code | Signification                                                           |
|------|-------------------------------------------------------------------------|
| 200  | Succès – L’emploi du temps est retourné.                                 |
| 400  | Format de date invalide.                                                 |
| 404  | Donnée absente du cache ET `scrape_if_missing=false`.                    |
| 500  | Échec du scraping (site source inaccessible ou structure HTML modifiée). |

---

### GET `/timetable/group/{group_name}/{week_number}`

Récupère l’emploi du temps d’un groupe spécifique pour un numéro de semaine donné.  
Utile lorsque l’on connaît déjà le nom exact du groupe et le numéro de semaine.

#### Paramètres de chemin

| Nom           | Type    | Description                                      |
|---------------|---------|--------------------------------------------------|
| `group_name`  | string  | Nom complet du groupe (ex: `СДП-УИР-251.1.1`)     |
| `week_number` | integer | Numéro de la semaine (ex: `2`)                   |

#### Paramètres de requête

| Nom       | Type    | Défaut | Description                                                                   |
|-----------|---------|--------|-------------------------------------------------------------------------------|
| `refresh` | boolean | `false`| Si `true`, force un nouveau scraping. **Nécessite le paramètre `url` associé.** |
| `url`     | string  | -      | URL complète à scraper (obligatoire si `refresh=true`).                         |

#### Exemple

```bash
curl "http://localhost:5000/api/timetable/group/СДП-УИР-251.1.1/2"
```

#### Réponse (200 OK)

Même structure JSON que l’endpoint principal.

---

### POST `/scrape`

Effectue le scraping d’une URL brute et stocke le résultat dans le cache.  
Cet endpoint est surtout destiné à l’administration ou au pré-chargement du cache.

#### Corps de la requête (JSON)

```json
{
  "url": "https://raspisanie.grsu.by/TimeTable/PrintPage.aspx?arg0=18156&arg1=3&arg2=2&arg3=1&arg4=1&date=20.04.2026%200:00:00&lang="
}
```

#### Réponse (201 Created)

```json
{
  "message": "Emploi du temps extrait et mis en cache",
  "group_name": "СДП-УИР-251.1.1",
  "week_number": 2,
  "days_count": 5
}
```

---

### GET `/groups`

Liste tous les noms de groupes actuellement présents dans le cache.

#### Exemple

```bash
curl "http://localhost:5000/api/groups"
```

#### Réponse (200 OK)

```json
{
  "groups": ["СДП-УИР-251.1.1", "ПОИТ-251.1.2"]
}
```

---

### GET `/cache/stats`

Retourne des statistiques sur l’état du cache mémoire.

#### Réponse (200 OK)

```json
{
  "entries": 3,
  "url_entries": 3,
  "groups": 2,
  "ttl_seconds": 3600
}
```

| Champ          | Description                                                       |
|----------------|-------------------------------------------------------------------|
| `entries`      | Nombre total de semaines en cache.                                |
| `url_entries`  | Nombre d’URL distinctes indexées.                                 |
| `groups`       | Nombre de groupes distincts.                                      |
| `ttl_seconds`  | Durée de vie du cache en secondes (configurable dans `config.py`). |

---

### POST `/cache/clear`

Vide intégralement le cache (données principales et index d’URL).

#### Exemple

```bash
curl -X POST "http://localhost:5000/api/cache/clear"
```

#### Réponse (200 OK)

```json
{
  "message": "Cache vidé"
}
```

---

## Gestion du cache

- **Type** : mémoire volatile (dictionnaire Python).  
- **Durée de vie (TTL)** : par défaut **3600 secondes** (1 heure). Modifiable dans `config.py`.  
- **Indexation** :  
  - Clé primaire : `(group_name, week_number)`  
  - Index secondaire : `url → (group_name, week_number)` pour éviter de scraper deux fois la même URL.  
- **Comportement** :  
  - Les données expirées sont supprimées lors de la tentative d’accès.  
  - Un appel avec `refresh=true` invalide l’entrée de cache correspondante et force un nouveau scraping.

> **Note** : Un redémarrage du serveur Flask **vide le cache**. Pour une persistance, envisagez d’utiliser Redis ou une base de données.

---

## Codes d’erreur

| Code | Message type                                        | Cause probable                                                                 |
|------|-----------------------------------------------------|--------------------------------------------------------------------------------|
| 400  | `Format de date invalide. Utilisez YYYY-MM-DD`      | La date fournie n’est pas au format ISO.                                        |
| 400  | `URL manquante`                                     | Corps JSON absent ou incomplet sur `POST /scrape`.                              |
| 404  | `Emploi du temps non trouvé dans le cache`          | La combinaison groupe/semaine n’existe pas en cache et `scrape_if_missing=false`.|
| 404  | `Endpoint non trouvé`                               | URL mal orthographiée ou méthode HTTP non supportée.                            |
| 500  | `Échec du scraping`                                 | Le site source est injoignable ou sa structure a changé.                         |
| 500  | `Erreur interne du serveur`                         | Exception non gérée (vérifiez les logs du serveur).                             |

---

## Exemples d’intégration

### JavaScript (fetch)

```javascript
async function getTimetable(date) {
  const response = await fetch(`http://localhost:5000/api/timetable/${date}`);
  if (!response.ok) {
    throw new Error(`Erreur API : ${response.status}`);
  }
  const data = await response.json();
  console.log(`Emploi du temps du groupe ${data.group_name} (semaine ${data.week_number})`);
  data.days.forEach(day => {
    console.log(`Jour ${day.weekday} (${day.monthday}) : ${day.classes.length} cours`);
  });
  return data;
}

// Utilisation
getTimetable('2026-04-22').catch(console.error);
```

### Python (requests)

```python
import requests

def get_timetable(date: str, base_url: str = "http://localhost:5000/api"):
    url = f"{base_url}/timetable/{date}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    data = get_timetable("2026-04-22")
    print(f"Groupe : {data['group_name']}")
    for day in data['days']:
        print(f"  Jour {day['weekday']} :")
        for cls in day['classes']:
            print(f"    {cls['time']['start']}-{cls['time']['end']} : {cls['subject']['name']} ({cls['subject']['lecturer']['name']})")
```

---

## Limitations et remarques

1. **Dépendance au site source** : Tout changement de structure HTML de `raspisanie.grsu.by` peut casser le scraping. L’API devra être mise à jour en conséquence.
2. **Cache non persistant** : Après un redémarrage, le cache est vide. Les premiers appels seront donc plus lents (scraping à la volée).
3. **Paramètres par défaut** : L’API est configurée pour un groupe spécifique (défini dans `config.py`). Pour utiliser d’autres groupes, surchargez les paramètres via les query strings `arg0`, `arg1`, etc., ou modifiez la configuration par défaut.
4. **Performances** : Le scraping peut prendre 1 à 3 secondes selon la latence réseau. Le cache rend les appels suivants quasi instantanés (< 10 ms).
5. **Sécurité** : Aucune authentification n’est implémentée. Pour une exposition publique, il est conseillé d’ajouter une couche d’authentification (clé API, JWT) et de limiter le taux d’appels (rate limiting).

---

## Contact / Support

Pour toute question ou signalement de bug, merci d’ouvrir une issue sur le dépôt GitHub du projet.

*Documentation générée le 16 avril 2026.*