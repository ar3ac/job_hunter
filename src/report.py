from __future__ import annotations
from datetime import datetime
from html import escape
from typing import Any


def _safe(s: object) -> str:
    return escape(str(s or ""))


def _date10(s: str | None) -> str:
    # Prende solo YYYY-MM-DD se presente
    return str(s or "")[:10]


def render_html(jobs: list[dict], summary: dict[str, Any] | None = None) -> str:
    if not jobs:
        if not summary:
            return "<p>Nessun nuovo annuncio.</p>"
        failures = summary.get("source_failures") or []
        failure_html = "".join(f"<li>{_safe(item)}</li>" for item in failures)
        return (
            "<div style='font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif'>"
            "<h2>Job Hunter — nessun nuovo annuncio consigliato</h2>"
            f"<p>Raccolti: {_safe(summary.get('found', 0))} · "
            f"da valutare: {_safe(summary.get('review', 0))} · "
            f"scartati: {_safe(summary.get('rejected', 0))}</p>"
            + (f"<h3>Ricerche non completate</h3><ul>{failure_html}</ul>" if failures else "")
            + "</div>"
        )

    # Prima la compatibilità, poi la data.
    jobs_sorted = sorted(
        jobs,
        key=lambda j: (int(j.get("score") or 0), j.get("posted_at") or ""),
        reverse=True
    )

    show_search = any("search" in j for j in jobs_sorted)

    header_cells = []
    if show_search:
        header_cells.append("<th style='padding:8px 12px'>Ricerca</th>")
    header_cells += [
        "<th style='padding:8px 12px'>Titolo</th>",
        "<th style='padding:8px 12px'>Compatibilità</th>",
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
        score = int(j.get("score") or 0)
        reasons = j.get("score_reasons") or []
        contract = _safe((j.get("contract_type") or "").replace("_", " "))
        experience = ""
        if j.get("experience_min") is not None:
            experience = f"{j['experience_min']}–{j.get('experience_max', j['experience_min'])} anni"
        details = " · ".join(part for part in (contract, _safe(experience)) if part)
        reason_html = "<br>".join(_safe(reason) for reason in reasons[:4])

        cells = []
        if show_search:
            cells.append(
                f"<td style='padding:8px 12px'>{_safe(j.get('search'))}</td>")
        cells += [
            f"<td style='padding:8px 12px'>{title}</td>",
            (
                f"<td style='padding:8px 12px'><strong>{score}/100</strong>"
                f"<div style='font-size:12px;color:#555'>{reason_html}</div>"
                f"<div style='font-size:12px;color:#2563eb'>{details}</div></td>"
            ),
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

    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    summary = summary or {}
    summary_html = ""
    if summary:
        summary_html = (
            "<p style='margin:0 0 16px;color:#555'>"
            f"Raccolti: {_safe(summary.get('found', 0))} · "
            f"consigliati: {_safe(summary.get('recommended', 0))} · "
            f"da valutare: {_safe(summary.get('review', 0))} · "
            f"scartati: {_safe(summary.get('rejected', 0))}"
            "</p>"
        )
        failures = summary.get("source_failures") or []
        if failures:
            summary_html += (
                "<p style='padding:10px;background:#fff3cd;color:#664d03'>"
                f"Attenzione: {len(failures)} ricerche non completate."
                "</p>"
            )
    return f"""
    <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif">
      <h2 style="margin:0 0 12px">Job Hunter — nuovi annunci</h2>
      <p style="margin:0 0 16px; color:#555">Generato il {now}</p>
      {summary_html}
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
