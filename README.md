# Network Design — The Rookie

Streamlit app for the FY2030 India cement manufacturing network case. Compare the four supplied scenarios, inspect capacities and routes, stress-test the base network, and optimize your own assumptions.

## Deploy on Streamlit Community Cloud

1. Open https://share.streamlit.io/ and choose **Create app**.
2. Select repository **Shubhamtos/Network-Design**.
3. Select branch **main**.
4. Set the main file path to **streamlit_app.py**.
5. Under advanced settings, select **Python 3.11** and deploy.

No secrets, API keys, external database, or separately installed solver are needed. `requirements.txt` installs all dependencies, including SciPy's bundled HiGHS solver.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

On Windows, activate with `.venv\Scripts\activate`.

## Use

- Pick the active scenario in the sidebar.
- **Network overview** shows facility modules, capacities, utilization, and annual costs.
- **Supply routes** filters cement or clinker flows and reports each market's demand balance.
- **Compare & stress-test** compares all four optima and tests the base installed network under A–C.
- **Design a scenario** allows custom freight, demand, utilization, financing assumptions, lane limits, and site/module choices. After solving, select **Custom network** in the sidebar.
- Export scenario JSON, the current LP formulation, facility results, cost breakdowns, and routes.

Custom results persist for the current Streamlit session. Download results before closing the app. Preset data remains unchanged.

## Model

The mixed-integer model has 30 binary site/module choices, 120 continuous cement flows, and 24 continuous clinker flows. It minimizes annualized capex, fixed opex, limestone, and freight costs, subject to demand balance, clinker balance, separate clinker/grinding capacity limits, facility closure rules, and lane limits.

All costs are in ₹ crore/year; flows are Mt. Base utilization is limited to 90%, the clinker factor is 0.66, limestone use is 1.5 tonnes per tonne of clinker, and capex is annualized over 20 years at 11%. The relative MILP gap target is 0.01%, with a 60-second time limit. Infeasible or unfinished solves do not replace previous results.

Data is extracted from the supplied `The_Rookie solution.xlsx`. Scenario A retains the exact listed target volumes. The app does not modify or include the original workbook. Common conversion costs, last-mile distribution, warehouses, taxes, working capital, terminal value, inflation, and implementation phasing are outside the case model.

## Validation

```bash
python -m unittest discover -s tests -v
```

Tests compare all four re-solved scenario objectives to the workbook, check fixed-base resilience and infeasibility, and exercise the Streamlit designer.

## Files

- `streamlit_app.py`: Streamlit interface
- `network_model.py`: MILP formulation, validation, and LP export
- `data.json`: case inputs and supplied/computed scenario results
- `requirements.txt`: tested dependencies
- `.streamlit/config.toml`: theme

The earlier browser app remains at https://rookie-cement-network.toshniwals21.chatgpt.site/. This repository runs independently of that site.
