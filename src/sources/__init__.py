# sources/__init__.py
from .remotive import fetch_remotive
from .adzuna import fetch_adzuna

SOURCES = {
    "remotive": fetch_remotive,
    "adzuna": fetch_adzuna,
}
