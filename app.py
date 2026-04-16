from flask import Flask, request, jsonify
from scraper import scrape_timetable, build_timetable_url, get_monday_of_week
from models import ScheduleWeek
from typing import Dict, Tuple, Optional
from datetime import datetime
import time
import config

app = Flask(__name__)

# Cache principal : clé (group_name, week_number) -> (week_object, timestamp)
cache: Dict[Tuple[str, int], Tuple[ScheduleWeek, float]] = {}

# Cache secondaire pour retrouver rapidement à partir d'une URL
url_cache: Dict[str, Tuple[str, int]] = {}

def get_cached_week(group_name: str, week_number: int, force_refresh: bool = False) -> Optional[ScheduleWeek]:
    key = (group_name, week_number)
    if force_refresh:
        if key in cache:
            del cache[key]
        return None

    if key in cache:
        week, timestamp = cache[key]
        if time.time() - timestamp < config.CACHE_TTL:
            return week
        else:
            del cache[key]
    return None

def store_week_in_cache(week: ScheduleWeek) -> None:
    key = (week.group_name, week.week_number)
    cache[key] = (week, time.time())

# ------------------------- Endpoint central RESTful -------------------------
@app.route('/api/timetable/<string:date_str>', methods=['GET'])
def get_timetable_by_date(date_str: str):
    """
    Récupère l'emploi du temps de la semaine contenant la date fournie.
    Format de date : YYYY-MM-DD (ex: 2026-04-22)
    
    Paramètres de requête optionnels (pour surcharger les valeurs par défaut) :
    - arg0, arg1, arg2, arg3, arg4, lang
    - refresh : true/false (force un nouveau scraping)
    - scrape_if_missing : true/false (par défaut true)
    """
    # Validation de la date
    try:
        input_date = datetime.fromisoformat(date_str)
    except ValueError:
        return jsonify({'error': 'Format de date invalide. Utilisez YYYY-MM-DD'}), 400

    # Construire les paramètres du groupe
    params = {
        'arg0': request.args.get('arg0', config.DEFAULT_GROUP_PARAMS['arg0']),
        'arg1': request.args.get('arg1', config.DEFAULT_GROUP_PARAMS['arg1']),
        'arg2': request.args.get('arg2', config.DEFAULT_GROUP_PARAMS['arg2']),
        'arg3': request.args.get('arg3', config.DEFAULT_GROUP_PARAMS['arg3']),
        'arg4': request.args.get('arg4', config.DEFAULT_GROUP_PARAMS['arg4']),
        'lang': request.args.get('lang', config.DEFAULT_GROUP_PARAMS['lang'])
    }

    monday = get_monday_of_week(input_date)
    date_for_url = monday.strftime('%d.%m.%Y') + ' 00:00:00'
    params_for_url = params.copy()
    params_for_url['date'] = date_for_url
    url = build_timetable_url(params_for_url)

    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    scrape_if_missing = request.args.get('scrape_if_missing', 'true').lower() == 'true'

    week = None
    if not force_refresh:
        if url in url_cache:
            group_name, week_number = url_cache[url]
            week = get_cached_week(group_name, week_number)

    if week is None and (force_refresh or scrape_if_missing):
        week = scrape_timetable(url)
        if week:
            store_week_in_cache(week)
            url_cache[url] = (week.group_name, week.week_number)
        else:
            return jsonify({'error': 'Échec du scraping'}), 500
    elif week is None:
        return jsonify({'error': 'Données non trouvées en cache. Utilisez refresh=true'}), 404

    return jsonify(week.to_dict())

# ------------------------- Autres endpoints (inchangés ou adaptés) -------------------------
# (On conserve les endpoints précédents pour la rétrocompatibilité et la gestion avancée)

@app.route('/api/scrape', methods=['POST'])
def scrape_and_cache():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL manquante'}), 400

    url = data['url']
    week = scrape_timetable(url)
    if week is None:
        return jsonify({'error': 'Échec du scraping'}), 500

    store_week_in_cache(week)
    url_cache[url] = (week.group_name, week.week_number)
    return jsonify({
        'message': 'Emploi du temps extrait et mis en cache',
        'group_name': week.group_name,
        'week_number': week.week_number,
        'days_count': len(week.days)
    }), 201

@app.route('/api/timetable/group/<group_name>/<int:week_number>', methods=['GET'])
def get_timetable_by_group(group_name, week_number):
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    week = get_cached_week(group_name, week_number, force_refresh)

    if force_refresh:
        url = request.args.get('url')
        if url:
            week = scrape_timetable(url)
            if week:
                store_week_in_cache(week)
                url_cache[url] = (week.group_name, week.week_number)
            else:
                return jsonify({'error': 'Échec du scraping avec l\'URL fournie'}), 500
        elif week is None:
            return jsonify({'error': 'Aucune donnée en cache et aucune URL fournie pour le refresh'}), 404

    if week is None:
        return jsonify({'error': 'Emploi du temps non trouvé dans le cache'}), 404

    return jsonify(week.to_dict())

@app.route('/api/groups', methods=['GET'])
def list_groups():
    groups = set()
    for (g, _) in cache.keys():
        groups.add(g)
    return jsonify({'groups': sorted(groups)})

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    cache.clear()
    url_cache.clear()
    return jsonify({'message': 'Cache vidé'}), 200

@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    return jsonify({
        'entries': len(cache),
        'url_entries': len(url_cache),
        'groups': len({g for (g, _) in cache.keys()}),
        'ttl_seconds': config.CACHE_TTL
    })

# ------------------------- Gestion d'erreurs -------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint non trouvé'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Erreur interne du serveur'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)