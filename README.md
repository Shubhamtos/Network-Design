# The Rookie · Network Studio

Interactive FY2030 cement network design case app with the original navy-and-teal interface. Live app: https://networkdesign.streamlit.app

## Deploy on Streamlit Community Cloud

- Repository: `Shubhamtos/Network-Design`
- Branch: `main`
- Entrypoint: `streamlit_app.py`
- Recommended Python: **3.12**
- Runtime dependencies: `requirements.txt`

The Python host uses Streamlit and the standard library only. It does not import SciPy, NumPy, pandas, or Altair. The bundled HiGHS WebAssembly solver runs in a browser worker, so changing Python versions cannot break the optimization engine. No API keys, external solver service, Node installation, or local server are needed in deployment.

```sh
python -m pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Features

- Four validated workbook scenarios, facility capacities, utilization and cost breakdown.
- Cement and clinker route filters and market demand reconciliation.
- Scenario comparison and fixed-base-capacity stress tests.
- Custom freight rates, utilization, distance limits, clinker factor, financing assumptions, site modules, and twelve market demands.
- Draft edits retained across tabs within the browser session; optimal validated custom results are selected automatically.
- Cancellation, infeasibility and input validation; previous successful results remain available.
- CSV results and LP model exports.

Custom designs are session-only. Export before refreshing or closing the app. The solver accepts only a validated optimum within a 0.01% relative gap; solving is limited to 60 seconds, with a 90-second load/solve watchdog. An infeasible or timed-out solve never replaces a successful result.

## Source and maintenance

`frontend.zip` contains all readable HTML, CSS and JavaScript source, case data, the component bridge, HiGHS loader, WASM binary and license. Streamlit safely extracts this versioned application archive to a temporary directory and serves its assets as a custom component. The archive hash changes the component identity when deployed assets change.

To edit the UI, extract `frontend.zip`, edit the source and recreate the archive with `index.html` at its root. No build is needed for `app.mjs`, `engine.mjs`, `solver-worker.mjs` or `style.css`. `bridge.js` is prebuilt from streamlit-component-lib; it handles only the component handshake and resizing.

`network_model.py` remains an optional independent Python reference implementation; it is not on the app's startup or solver path. `data.json` at repository root is the reference-model fixture; keep it synchronized with the copy in the frontend archive.

## Validation

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m zipfile -e frontend.zip work/frontend
node test-network.mjs work/frontend
```

The JS suite checks all four workbook optima, fixed-base stress tests, custom inputs, infeasible cases, invalid inputs, and malformed solver results. The Python suite independently reconciles the four optima and verifies Streamlit component startup. Browser checks cover all five tabs, preset selection, route filters, successful/infeasible/cancelled custom solves, draft retention, both downloads, and desktop/mobile layouts.

Expected annual costs (₹ crore): Base 7792.260789; A 7889.444090; B 8518.148393; C 8215.102262. Fixed-base C is infeasible after I1 is removed.

Source: `The_Rookie solution.xlsx`. Workbook instructions are case context; the original workbook is unchanged. Planning distances and the model's stated exclusions are retained.
