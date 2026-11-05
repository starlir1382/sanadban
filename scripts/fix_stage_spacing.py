import re

def fix_stage_css():
    path = r'templates/dossiers/list.html'
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace the entire Stage cell CSS block using regex
    old_pattern = re.compile(
        r'  /\* Stage cell \*/\s*\.dl-stage \{.*?\}.*?\.dl-status\.ret\s*\{[^}]*\}',
        re.DOTALL
    )

    new_css = """  /* Stage cell */
  .dl-stage {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.12rem;
    text-align: center;
  }
  .dl-stage-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.32rem;
    padding: 0.22rem 0.65rem;
    border-radius: 8px;
    font-size: 0.78rem;
    font-weight: 700;
    border: 1px solid transparent;
    line-height: 1.4;
    white-space: nowrap;
  }
  .dl-stage-pill .lbl { font-weight: 600; opacity: 0.85; }
  .dl-stage-pill .no  { font-weight: 800; }
  .dl-stage-pill.brokerage  { background: var(--c-primary-soft); color: #4338ca; border-color: var(--c-primary-line); }
  .dl-stage-pill.directorate { background: var(--c-green-soft);  color: #047857; border-color: #a7f3d0; }
  .dl-stage-pill.done       { background: #dcfce7; color: #166534; border-color: #86efac; }
  .dl-stage-title {
    font-size: 0.67rem;
    font-weight: 500;
    color: var(--c-soft);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 190px;
    line-height: 1.25;
    text-align: center;
    display: block;
  }
  .dl-date {
    display: inline-flex;
    align-items: center;
    gap: 0.28rem;
    font-size: 0.72rem;
    color: var(--c-muted);
    font-weight: 600;
    white-space: nowrap;
  }
  .dl-date svg { color: var(--c-soft); flex-shrink: 0; }
  .dl-stage-meta { display: flex; align-items: center; justify-content: center; gap: 0.35rem; flex-wrap: wrap; }
  .dl-status { display: inline-flex; align-items: center; gap: 3px; font-size: 0.67rem; font-weight: 800; padding: 1px 6px; border-radius: 6px; white-space: nowrap; border: 1px solid transparent; }
  .dl-status.red    { background: #fee2e2; color: #991b1b; border-color: #fecaca; }
  .dl-status.orange { background: #ffedd5; color: #c2410c; border-color: #fed7aa; }
  .dl-status.green  { background: #dcfce7; color: #15803d; border-color: #86efac; }
  .dl-status.ret    { background: #fee2e2; color: #b91c1c; border-color: #fca5a5; cursor: help; }"""

    if old_pattern.search(content):
        content = old_pattern.sub(new_css, content, count=1)
        print("Stage CSS updated in list.html")
    else:
        print("Pattern not found in list.html")
        return

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix_stage_css()
