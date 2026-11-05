"""Remove only owned, unchanged project extension files before runtime removal."""

import json
from codex_economy.store import Store
from codex_economy.extensions import setup

with Store() as store:
    projects = store.rows(
        "SELECT DISTINCT p.name FROM jobs j JOIN projects p ON j.project=p.id WHERE j.state='installed' AND j.id LIKE 'extension-%'"
    )
    results = []
    for project in projects:
        try:
            results.append(setup(store, project["name"], remove=True))
        except (OSError, ValueError) as error:
            results.append({"project": project["name"], "preserved": True, "reason": str(error)})
    print(json.dumps({"extensions": results}))
