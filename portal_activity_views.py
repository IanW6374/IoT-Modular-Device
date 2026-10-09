"""Searchable update activity, separate from the installation workspace."""

import web_portal_ui as ui
from portal_http import html_escape
from portal_settings_views import _health_time_text


def activity_tone(event):
    event = str(event).lower()
    if any(word in event for word in ('fail', 'reject', 'rolled_back', 'error')):
        return 'bad'
    if any(word in event for word in ('unconfirmed', 'trial', 'stag', 'pending', 'interrupted', 'verified', 'ready')):
        return 'warn'
    if any(word in event for word in ('confirmed', 'complete', 'installed', 'success')):
        return 'good'
    return 'info'


def render_update_activity_page(token, status):
    entries = list(status.get('update_history') or ()) + list(status.get('release_check_history') or ())
    entries.sort(key=lambda entry: int(entry.get('time', 0) or 0), reverse=True)
    rows = []
    for entry in entries:
        event = str(entry.get('event') or 'Recorded')
        label = event.replace('_', ' ')
        label = label[:1].upper() + label[1:]
        tone = activity_tone(event)
        details = ' · '.join(str(entry[key]) for key in ('version', 'detail') if entry.get(key))
        rows.append(
            '<article class="history-event" data-activity-tone="' + tone + '">'
            '<time class="history-time">' + html_escape(_health_time_text(entry.get('time'), status.get('timezone_name', 'UTC'))) +
            '</time><span class="history-marker" data-tone="' + tone + '" role="img" title="' + html_escape(label) +
            '" aria-label="' + html_escape(label) + '"></span><div class="history-copy"><strong>' +
            html_escape(label + (' · ' + str(entry['kind']) if entry.get('kind') else '')) +
            '</strong><p>' + html_escape(details) + '</p></div></article>'
        )
    body = ui.page_heading('Logging', 'Update log', 'Release checks, staging, installation and rollback events.')
    body += (
        '<section class="card"><div class="grid"><label class="field">Search activity'
        '<input id="activity-search" type="search" placeholder="Version, event, date or detail"></label>'
        '<label class="field">Status<select id="activity-tone"><option value="">All statuses</option>'
        '<option value="good">Successful</option><option value="warn">Pending / staged</option>'
        '<option value="bad">Failed / rolled back</option><option value="info">Information</option></select></label></div>'
        '<p id="activity-count" class="muted" role="status" aria-live="polite"></p>'
        '<div class="history-timeline">' + ''.join(rows) + '</div>'
        '<p id="activity-empty" class="muted" hidden>No activity matches your search.</p></section>'
    )
    script = (
        'var search=document.getElementById("activity-search"),tone=document.getElementById("activity-tone"),'
        'rows=Array.from(document.querySelectorAll("[data-activity-tone]"));'
        'function filterActivity(){var terms=search.value.toLocaleLowerCase().trim().split(/\\s+/).filter(Boolean),count=0;'
        'rows.forEach(function(row){var text=row.textContent.toLocaleLowerCase();row.hidden=!!tone.value&&'
        'row.dataset.activityTone!==tone.value||!terms.every(function(term){return text.indexOf(term)>=0;});'
        'if(!row.hidden)count++;});document.getElementById("activity-count").textContent=count+" of "+rows.length+" events";'
        'document.getElementById("activity-empty").hidden=count>0;}search.oninput=filterActivity;tone.onchange=filterActivity;filterActivity();'
    )
    return ui.shell('IoT-MD update log', 'update_activity', body, token, script)
