"""Run with: streamlit run streamlit_app.py"""
from copy import deepcopy
import json
import pandas as pd
import streamlit as st
from network_model import load_data, metrics, solve, lp_text

st.set_page_config(page_title='The Rookie · Network Studio', page_icon='🏭', layout='wide')
DATA = load_data()
st.title('The Rookie · Network Studio')
st.caption('India cement network design · FY2030 · Volumes in Mt · Annual costs in ₹ crore')
options = [s['name'] for s in DATA['scenarios']]
if 'custom' in st.session_state: options += ['Custom network']
name = st.sidebar.selectbox('Active scenario', options, key='scenario')
s = st.session_state['custom'] if name == 'Custom network' else deepcopy(next(x for x in DATA['scenarios'] if x['name'] == name))
m = metrics(DATA, s)
st.sidebar.info('Custom scenarios and results are kept for this browser session. Export them before closing the app.')
st.sidebar.download_button('Download scenario JSON', json.dumps(s, indent=2), 'network-scenario.json', 'application/json')
st.sidebar.download_button('Download optimization model', lp_text(DATA, s), 'network-model.lp', 'text/plain')
descriptions = {'base': 'Base demand, ₹3.03/t-km cement freight, and ₹1.60/t-km clinker freight.', 'a': 'Regional demand shifts toward central and eastern markets. National demand stays at 33.78 Mt.', 'b': 'Freight shock: ₹3.75/t-km cement and ₹1.85/t-km clinker.', 'c': 'Chittorgarh–Nimbahera (I1) is unavailable.', 'custom': 'Optimized using the assumptions in your custom scenario.'}
st.write(descriptions[s['id']])
if m['errors']: st.error(', '.join(m['errors']))
else: st.caption('✓ Demand, clinker balance, capacity, closed-site flows, and lane checks passed')
cols = st.columns(4)
cols[0].metric('Annual relevant cost', f"₹{m['total']:,.1f} cr", f"{m['total'] - DATA['scenarios'][0]['workbookCost']:+,.1f} vs base", delta_color='inverse')
cols[1].metric('Demand served', f"{m['demand']:.2f} Mt")
cols[2].metric('Open facilities', f"{sum(k >= 0 for k in s['modules'][:6])} plants + {sum(k >= 0 for k in s['modules'][6:])} grinders")
cols[3].metric('Average cement lead', f"{m['cement_lead']:.0f} km")
overview, routes, compare, designer, model = st.tabs(['Network overview', 'Supply routes', 'Compare & stress-test', 'Design a scenario', 'Model & sources'])

with overview:
    left, right = st.columns([2, 1])
    with left:
        st.subheader('Facilities & capacity')
        facilities = pd.DataFrame(m['facilities'])
        st.dataframe(facilities, hide_index=True, width="stretch")
        st.caption(f"Utilization is actual production / nameplate. Current limit: {s['utilization']:.1%}.")
        st.download_button('Export facility results', facilities.to_csv(index=False), 'facilities.csv', 'text/csv')
    with right:
        st.subheader('Annual cost breakdown')
        costs = pd.DataFrame({'Component': m['costs'].keys(), '₹ crore / year': m['costs'].values()})
        st.bar_chart(costs.set_index('Component'), horizontal=True)
        st.dataframe(costs, hide_index=True, width="stretch")
        st.download_button('Export cost breakdown', costs.to_csv(index=False), 'costs.csv', 'text/csv')
    st.write(f"**Installed capacity:** {m['clinker_capacity']:.1f} MTPA clinker and {m['grinding_capacity']:.1f} MTPA total grinding. **Clinker shipped:** {m['clinker_shipped']:.3f} Mt, with a weighted average lead of {m['clinker_lead']:.1f} km.")

with routes:
    material = st.radio('Material', ['Cement', 'Clinker'], horizontal=True)
    source = st.selectbox('Source facility', ['All'] + [f['id'] for f in DATA['sites']])
    key = material.lower()
    records = []
    for i, row in enumerate(s[key]):
        for j, volume in enumerate(row):
            if volume <= 1e-7 or source != 'All' and source != DATA['sites'][i]['id']: continue
            distance = DATA[key + 'Distances'][i][j]
            records.append({'From': DATA['sites'][i]['id'] + ' · ' + DATA['sites'][i]['name'], 'To': DATA['markets'][j]['name'] if key == 'cement' else DATA['sites'][6+j]['name'], 'Volume (Mt)': volume, 'Distance (km)': distance, 'Freight (₹ cr)': .1 * volume * distance * s[key + 'Rate']})
    if records:
        frame = pd.DataFrame(records)
        st.dataframe(frame, hide_index=True, width="stretch")
        st.download_button('Export these routes', frame.to_csv(index=False), 'routes.csv', 'text/csv')
    else: st.info('No active routes match this selection.')
    st.subheader('Market demand balance')
    st.dataframe(pd.DataFrame([{'Market': market['name'], 'Demand (Mt)': s['demand'][j], 'Delivered (Mt)': sum(row[j] for row in s['cement']), 'Supplied by': ', '.join(f"{DATA['sites'][i]['id']} ({row[j]:.3f})" for i, row in enumerate(s['cement']) if row[j] > 1e-7)} for j, market in enumerate(DATA['markets'])]), hide_index=True, width="stretch")

with compare:
    st.subheader('Scenario-specific optima')
    records = []
    for case in DATA['scenarios']:
        cm = metrics(DATA, case)
        records.append({'Scenario': case['name'], 'Annual cost (₹ cr)': cm['total'], 'Clinker capacity (Mt)': cm['clinker_capacity'], 'Grinding capacity (Mt)': cm['grinding_capacity'], 'Cement lead (km)': cm['cement_lead'], 'Clinker lead (km)': cm['clinker_lead'], 'Modules': ', '.join(f"{f['Site']}-{f['Module']}" for f in cm['facilities'] if f['Module'] != 'Closed'), **cm['costs']})
    st.dataframe(pd.DataFrame(records), hide_index=True, width="stretch")
    st.subheader('Base installed network under each scenario')
    st.caption('Base capacity modules stay fixed. Only flows are re-optimized; unavailable I1 is removed in Scenario C.')
    for col, case in zip(st.columns(3), DATA['scenarios'][1:]):
        with col:
            st.markdown('**' + case['name'] + '**')
            result = case['robustness']
            if result['status'] == 'Optimal':
                cost = metrics(DATA, result['solution'])['total']
                st.success('Base network remains feasible')
                st.metric('Annual cost', f'₹{cost:,.1f} cr')
                st.write(f"₹{cost - case['workbookCost']:,.1f} cr above the scenario-specific optimum.")
            else:
                st.error('Base network is infeasible')
                st.write('Without I1, usable clinker capacity is 17.55 Mt against 22.295 Mt required. Replacement capacity is needed.')

with designer:
    st.subheader('Design a scenario')
    st.write('Edit demand, freight, lane limits, and capacities. The optimizer chooses modules and routes to minimize annual relevant cost.')
    seed_name = st.selectbox('Start from', [x['name'] for x in DATA['scenarios']], key='seed')
    seed = deepcopy(next(x for x in DATA['scenarios'] if x['name'] == seed_name))
    fixed_base = st.checkbox('Start with base modules fixed', key='fixed_base')
    prefix = seed['id'] + ('_fixed' if fixed_base else '_auto')
    with st.form('custom_scenario_' + prefix):
        cfg = deepcopy(seed)
        columns = st.columns(3)
        specs = [('cementRate', 'Cement freight (₹ / t-km)', 0., 20., .01, 1), ('clinkerRate', 'Clinker freight (₹ / t-km)', 0., 20., .01, 1), ('utilization', 'Maximum utilization (%)', 1., 100., .1, 100), ('cementLimit', 'Maximum cement lane (km)', 0., 5000., 10., 1), ('clinkerLimit', 'Maximum clinker lane (km)', 0., 5000., 10., 1), ('factor', 'Clinker factor', .01, 1., .01, 1), ('rate', 'Hurdle rate (%)', 0., 50., .1, 100), ('life', 'Asset life (years)', 1., 100., 1., 1)]
        for i, (key, label, low, high, step, scale) in enumerate(specs):
            cfg[key] = columns[i % 3].number_input(label, low, high, float(seed[key] * scale), step, key=prefix + key) / scale
        st.markdown('**Facility decisions**')
        choices = []
        columns = st.columns(5)
        for i, site in enumerate(DATA['sites']):
            labels = ['Optimize', 'Closed / unavailable', 'S', 'M', 'L']
            default = 1 if site['id'] in seed['unavailable'] else DATA['scenarios'][0]['modules'][i] + 2 if fixed_base else 0
            choice = columns[i % 5].selectbox(site['id'] + ' · ' + site['name'], labels, index=default, key=prefix + site['id'])
            choices.append('auto' if choice == 'Optimize' else str(labels.index(choice) - 2))
        st.markdown('**Market demand (Mt)**')
        columns = st.columns(4)
        cfg['demand'] = [columns[i % 4].number_input(market['name'], 0., 100., float(seed['demand'][i]), .001, format='%.3f', key=prefix + market['id']) for i, market in enumerate(DATA['markets'])]
        submitted = st.form_submit_button('Optimize network', type='primary')
    if submitted:
        cfg.update(id='custom', name='Custom network', unavailable=[], moduleChoices=choices)
        try:
            with st.spinner('Optimizing network. This can take up to 60 seconds…'):
                result = solve(DATA, cfg)
            st.session_state['custom'] = result
            st.session_state['show_custom'] = True
            st.rerun()
        except (ValueError, RuntimeError) as exc: st.error(str(exc))
    if st.session_state.pop('show_custom', False):
        st.success('Custom network solved and validated. Select “Custom network” in the sidebar to view and export the results.')
        st.metric('Custom annual relevant cost', f"₹{metrics(DATA, st.session_state['custom'])['total']:,.1f} cr")
    st.caption('SciPy / HiGHS MILP · 0.01% relative gap target · 60-second limit. No browser worker or external solver service is required.')

with model:
    st.subheader('Model formulation')
    st.markdown('**Variables:** one binary for each site/module combination, continuous cement flows from sites to markets, and continuous clinker flows from integrated plants to split grinders.')
    st.code('Minimize annualized capex + fixed opex + limestone cost\n       + cement freight + clinker freight')
    st.markdown('''1. Select at most one module per site.
2. Serve each market’s exact demand.
3. Limit clinker and grinding independently to the selected utilization fraction of nameplate capacity.
4. Integrated clinker production equals on-site cement × clinker factor plus outbound clinker.
5. Each split grinder receives exactly its cement output × clinker factor.
6. Disallow lanes above the distance limits and all production at closed or unavailable sites.''')
    st.code('CRF = r(1+r)^n / ((1+r)^n - 1)\nBase CRF = 0.125575637 at 11% over 20 years\nLimestone = 1.5 tonnes / tonne of clinker\n1 Mt × ₹1/t = ₹0.1 crore')
    st.markdown('**Source:** The_Rookie solution.xlsx — Case Brief, 2030 Demand, Candidate Facilities, Planning Distances, Scenarios & Deliverables, and the four solution sheets.')
    st.write('The supplied planning distances and exact Scenario A volumes are retained. Warehouses, last-mile distribution, common conversion costs, taxes, working capital, terminal value, inflation, and implementation phasing are outside the model. The original workbook is unchanged.')
