from __future__ import annotations
from datetime import datetime
from html import escape


def _safe(s: object) -> str:
    return escape(str(s or ""))


def _date10(s: str | None) -> str:
    # Prende solo YYYY-MM-DD se presente
    return (s or "")[:10]


def render_html(jobs: list[dict]) -> str:
    if not jobs:
        return "<p>Nessun nuovo annuncio.</p>"

    # Ordina: più recente prima (se posted_at esiste)
    jobs_sorted = sorted(
        jobs,
        key=lambda j: j.get("posted_at") or "",
        reverse=True
    )

    show_search = any("search" in j for j in jobs_sorted)

    header_cells = []
    if show_search:
        header_cells.append("<th style='padding:8px 12px'>Ricerca</th>")
    header_cells += [
        "<th style='padding:8px 12px'>Titolo</th>",
        "<th style='padding:8px 12px'>Azienda</th>",
        "<th style='padding:8px 12px'>Location</th>",
        "<th style='padding:8px 12px'>Location Azienda</th>",
        "<th style='padding:8px 12px'>Link</th>",
        "<th style='padding:8px 12px'>Data</th>",
    ]

    rows = []
    for j in jobs_sorted:
        title = _safe(j.get("title"))
        company = _safe(j.get("company"))
        location = _safe(j.get("location"))
        loc_company = _safe(j.get("loc_company"))
        url = j.get("url") or ""
        posted = _date10(j.get("posted_at"))

        cells = []
        if show_search:
            cells.append(
                f"<td style='padding:8px 12px'>{_safe(j.get('search'))}</td>")
        cells += [
            f"<td style='padding:8px 12px'>{title}</td>",
            f"<td style='padding:8px 12px'>{company}</td>",
            f"<td style='padding:8px 12px'>{location}</td>",
            f"<td style='padding:8px 12px'>{loc_company}</td>",
            (
                f"<td style='padding:8px 12px'>"
                f"<a href='{_safe(url)}' target='_blank' rel='noopener noreferrer'>link</a>"
                f"</td>"
                if url else "<td style='padding:8px 12px'>—</td>"
            ),
            f"<td style='padding:8px 12px'>{_safe(posted)}</td>",
        ]
        rows.append(f"<tr>{''.join(cells)}</tr>")

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"""
    <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif">
      <h2 style="margin:0 0 12px">Job Hunter — nuovi annunci</h2>
      <p style="margin:0 0 16px; color:#555">Generato il {now}</p>
      <table cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; width:100%; max-width:1000px">
        <thead>
          <tr style="text-align:left; background:#f3f4f6">
            {''.join(header_cells)}
          </tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
    </div>
    """
