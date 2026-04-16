import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, parse_qs
from typing import Optional
from models import ScheduleWeek, ScheduleDay, ScheduleClass, Subject, Lecturer, ScheduleTime
from datetime import time, datetime, timedelta
from urllib.parse import urlencode

def get_monday_of_week(date: datetime) -> datetime:
    """Retourne le lundi de la semaine contenant la date donnée (lundi = 0)."""
    days_to_subtract = date.weekday()  # lundi=0, dimanche=6
    monday = date - timedelta(days=days_to_subtract)
    return monday

def build_timetable_url(params: dict) -> str:
    """
    Construit l'URL complète à partir des paramètres du groupe et d'une date.
    params attendu : {
        'arg0': str, 'arg1': str, 'arg2': str, 'arg3': str, 'arg4': str,
        'date': str (format 'dd.MM.yyyy HH:mm:ss' encodé),
        'lang': str
    }
    """
    base_url = "https://raspisanie.grsu.by/TimeTable/PrintPage.aspx"
    # Filtrer les valeurs None ou vides
    clean_params = {k: v for k, v in params.items() if v is not None and v != ''}
    query_string = urlencode(clean_params)
    return f"{base_url}?{query_string}"

def fetch_html(url: str) -> Optional[str]:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération de la page : {e}")
        return None

def extract_group_name(soup: BeautifulSoup) -> str:
    group_span = soup.find('span', class_='group-name')
    if group_span:
        return group_span.get_text(strip=True)
    header = soup.find('h1') or soup.find('h2')
    if header:
        return header.get_text(strip=True)
    table = soup.find('table', id='Table')
    if table:
        prev_paragraph = table.find_previous('p')
        if prev_paragraph:
            return prev_paragraph.get_text(strip=True)
    return "Groupe inconnu"

def extract_week_number_from_url(url: str) -> int:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    week_str = params.get('arg2', ['0'])[0]
    try:
        return int(week_str)
    except ValueError:
        return 0

def parse_time_range(time_str: str) -> Optional[ScheduleTime]:
    parts = time_str.split('-')
    if len(parts) != 2:
        return None
    try:
        start = time.fromisoformat(parts[0].strip())
        end = time.fromisoformat(parts[1].strip())
        return ScheduleTime(start=start, end=end)
    except ValueError:
        return None

def weekday_name_to_int(day_name: str) -> int:
    mapping = {
        'Понедельник': 0,
        'Вторник': 1,
        'Среда': 2,
        'Четверг': 3,
        'Пятница': 4,
        'Суббота': 5,
        'Воскресенье': 6
    }
    return mapping.get(day_name, -1)

def scrape_timetable(url: str) -> Optional[ScheduleWeek]:
    html = fetch_html(url)
    if not html:
        return None
    soup = BeautifulSoup(html, 'html.parser')
    group_name = extract_group_name(soup)
    week_number = extract_week_number_from_url(url)

    table = soup.find('table', id='Table')
    if not table:
        return None

    rows = table.find_all('tr')
    week = ScheduleWeek(week_number=week_number, group_name=group_name)
    days_dict = {}

    current_day_name = None
    current_date_str = None

    for row in rows:
        if 'row-separator' in row.get('class', []):
            continue

        date_cell = row.find('td', class_='cell-date')
        if date_cell:
            day_span = date_cell.find('span', class_='day')
            date_span = date_cell.find('span', class_='date')
            if day_span and date_span:
                current_day_name = day_span.get_text(strip=True)
                current_date_str = date_span.get_text(strip=True)

        time_cell = row.find('td', class_='cell-time')
        if time_cell and current_day_name and current_date_str:
            time_str = time_cell.get_text(strip=True)
            schedule_time = parse_time_range(time_str)
            if not schedule_time:
                continue

            subgroup_cell = row.find('td', class_='cell-subgroup')
            subgroup = subgroup_cell.get_text(strip=True) if subgroup_cell else ''
            subgroup = subgroup if subgroup else "Tous"

            discipline_cell = row.find('td', class_='cell-discipline')
            discipline = discipline_cell.get_text(" ", strip=True) if discipline_cell else ''

            staff_cell = row.find('td', class_='cell-staff')
            staff = staff_cell.get_text(strip=True) if staff_cell else ''

            auditory_cell = row.find('td', class_='cell-auditory')
            auditory = auditory_cell.get_text(strip=True) if auditory_cell else None

            lecturer = Lecturer(name=staff)
            subject = Subject(name=discipline, lecturer=lecturer)
            course = ScheduleClass(
                subject=subject,
                time=schedule_time,
                subgroup=subgroup,
                door=auditory
            )

            weekday = weekday_name_to_int(current_day_name)
            monthday = 0
            date_match = re.search(r'(\d{1,2})\.\d{1,2}\.\d{4}', current_date_str)
            if date_match:
                monthday = int(date_match.group(1))

            day_key = (weekday, monthday)
            if day_key not in days_dict:
                days_dict[day_key] = ScheduleDay(weekday=weekday, monthday=monthday)
            days_dict[day_key].classes.append(course)

    week.days = sorted(days_dict.values(), key=lambda d: d.weekday)
    return week