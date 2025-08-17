# sources/__init__.py
from .remotive import fetch_remotive
from .adzuna import fetch_adzuna
from .linkedin import fetch_linkedin
SOURCES = {
    "remotive": fetch_remotive,
    "adzuna": fetch_adzuna,
    "linkedin": fetch_linkedin,
}
