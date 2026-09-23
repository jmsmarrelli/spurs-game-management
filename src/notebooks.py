"""Create and execute the three review notebooks with the current Python environment."""

import os, sys, json
import nbformat as nb
from nbclient import NotebookClient
from .common import ROOT


def run():
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    for key, folder in [
        ("JUPYTER_RUNTIME_DIR", "runtime"),
        ("IPYTHONDIR", "ipython"),
        ("MPLCONFIGDIR", "matplotlib"),
    ]:
        p = cache / folder
        p.mkdir(exist_ok=True)
        os.environ[key] = str(p)
    spec = cache / "jupyter/kernels/research"
    spec.mkdir(parents=True, exist_ok=True)
    (spec / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [
                    sys.executable,
                    "-m",
                    "ipykernel_launcher",
                    "-f",
                    "{connection_file}",
                ],
                "display_name": "Python 3",
                "language": "python",
            }
        )
    )
    os.environ["JUPYTER_PATH"] = str(cache / "jupyter")
    jobs = [
        (
            "01_turnover_cost",
            "turnover_cost",
            "turnover_adjusted",
            "turnover_clock",
            "turnover_adjusted",
        ),
        (
            "02_timeout_reset",
            "timeout_reset",
            "timeout_sensitivity",
            "timeout_rebound",
            "timeout_balance",
        ),
        (
            "03_quarter_clock",
            "quarter_clock",
            "quarter_groups",
            "quarter_return",
            "quarter_forecast",
        ),
    ]
    for stem, module, table, fig1, fig2 in jobs:
        article = (ROOT / f"reports/{stem}.md").read_text()
        book = nb.v4.new_notebook(
            metadata={
                "kernelspec": {
                    "name": "python3",
                    "display_name": "Python 3",
                    "language": "python",
                },
                "language_info": {"name": "python", "version": "3.12"},
            }
        )
        book.cells = [
            nb.v4.new_markdown_cell(article.split("##")[0]),
            nb.v4.new_code_cell(
                "from pathlib import Path\nimport os, sys\nroot = Path.cwd()\nif root.name == 'notebooks':\n    root = root.parent\nsys.path.insert(0, str(root))\nos.chdir(root)\nimport pandas as pd\nfrom IPython.display import display, Image\nfrom src import "
                + module
                + "\nsummary = "
                + module
                + ".run()\nfrom src import figures\nfigures.run()\nsummary"
            ),
            nb.v4.new_markdown_cell(
                "## Results\nThe following table is regenerated from the pinned inputs."
            ),
            nb.v4.new_code_cell(f"pd.read_csv('results/{table}.csv')"),
            nb.v4.new_code_cell(
                f"display(Image(filename='figures/{fig1}.png'))\ndisplay(Image(filename='figures/{fig2}.png'))"
            ),
        ]
        if module == "turnover_cost":
            code = "display(pd.read_csv('results/game_audit.csv').query(\"status != 'valid'\"))\nd = pd.read_csv('data/turnovers.csv.gz')\nassert d.allowed_12.ge(d.allowed_8).all() and d.allowed_16.ge(d.allowed_12).all()\ndisplay(d.groupby('kind')[['allowed_8','allowed_12','allowed_16']].mean())\ndisplay(pd.read_csv('results/turnover_review_queue.csv').head(8))"
            explanation = "## Check source exclusions and window boundaries\nScoring is cumulative across horizons. The selected review queue contains adverse examples rather than representative film coding."
        elif module == "timeout_reset":
            code = "import numpy as np\npairs = pd.read_csv('results/timeout_pairs.csv')\nassert np.allclose(pairs.groupby(['game_id','event_id']).weight.sum(), 1)\nassert (pairs.treated_pre_net == pairs.control_pre_net).all()\neffect = pairs.assign(difference=pairs.weight*(pairs.treated_post_net-pairs.control_post_net)).groupby(['game_id','event_id']).difference.sum().mean()\ndisplay(effect)\ndisplay(pd.read_csv('results/timeout_match_audit.csv').controls.value_counts().sort_index())\ndisplay(pd.read_csv('results/timeout_balance.csv'))"
            explanation = "## Recalculate the matched comparison\nEach timeout has equal total weight, regardless of how many controls it has."
        else:
            code = "import json, numpy as np\nfrom src.quarter_clock import design\nheld = pd.read_csv('results/quarter_holdout.csv')\nmodel = json.loads(Path('results/quarter_model.json').read_text())\ncoef = np.array(list(model['coefficients'].values()))\np = 1 / (1 + np.exp(-(design(held) @ coef + model['intercept'])))\nassert np.allclose(p, held.prediction)\ndisplay(held[['date','seconds','return_attempt','prediction','baseline']].head(12))\ndisplay(model)"
            explanation = "## Reproduce predictions from the saved coefficients\nThe fit uses only pre-January quarters. The later outcomes are used for evaluation."
        book.cells += [nb.v4.new_markdown_cell(explanation), nb.v4.new_code_cell(code)]
        book.cells += [
            nb.v4.new_markdown_cell(
                "## Interpretation and limits\nRead the complete accompanying article for denominators, uncertainty, model selection, and the basketball decisions this analysis cannot identify. The results here are historical research, not a claim of team deployment."
            )
        ]
        path = ROOT / f"notebooks/{stem}.ipynb"
        NotebookClient(
            book,
            timeout=600,
            kernel_name="research",
            resources={"metadata": {"path": str(ROOT)}},
        ).execute()
        for cell in book.cells:
            cell.metadata.pop("execution", None)
        nb.write(book, path)
        print(path.name, "executed", flush=True)


if __name__ == "__main__":
    run()
