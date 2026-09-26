"""Cement network MILP, using SciPy's bundled HiGHS solver."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


def load_data():
    return json.loads((Path(__file__).parent / 'data.json').read_text())


def crf(rate, life):
    return 1 / life if rate == 0 else rate * (1 + rate) ** life / ((1 + rate) ** life - 1)


def metrics(data, s):
    cement, clinker = np.array(s['cement']), np.array(s['clinker'])
    output = cement.sum(axis=1)
    production = s['factor'] * output[:6] + clinker.sum(axis=1)
    capex = opex = kcap = gcap = 0.0
    facilities, errors = [], []
    for i, site in enumerate(data['sites']):
        module = data['modules'][site['type']][s['modules'][i]] if s['modules'][i] >= 0 else None
        grind, kiln = (module['grinding'], module.get('clinker', 0)) if module else (0, 0)
        if module:
            capex += module['capex']; opex += module['opex']; kcap += kiln; gcap += grind
        used = float(production[i]) if i < 6 else 0.0
        facilities.append({'Site': site['id'], 'Location': site['name'], 'Type': 'Integrated' if i < 6 else 'Split grinder', 'Module': module['name'] if module else 'Closed', 'Grinding capacity (Mt)': grind, 'Cement output (Mt)': float(output[i]), 'Grinding utilization (%)': float(output[i] / grind * 100) if grind else 0, 'Clinker capacity (Mt)': kiln, 'Clinker production (Mt)': used, 'Clinker utilization (%)': used / kiln * 100 if kiln else 0})
        if output[i] > s['utilization'] * grind + 1e-5 or used > s['utilization'] * kiln + 1e-5:
            errors.append('Capacity: ' + site['id'])
        if site['id'] in s.get('unavailable', []) and module:
            errors.append('Unavailable site: ' + site['id'])
    if np.max(np.abs(cement.sum(axis=0) - s['demand'])) > 1e-5: errors.append('Demand balance')
    if np.max(np.abs(clinker.sum(axis=0) - s['factor'] * output[6:])) > 1e-5: errors.append('Clinker balance')
    if np.any(cement < -1e-7) or np.any(clinker < -1e-7): errors.append('Negative flow')
    if np.any(cement[np.array(data['cementDistances']) > s['cementLimit']] > 1e-7): errors.append('Cement lane')
    if np.any(clinker[np.array(data['clinkerDistances']) > s['clinkerLimit']] > 1e-7): errors.append('Clinker lane')
    ctkm = float((cement * data['cementDistances']).sum())
    ktkm = float((clinker * data['clinkerDistances']).sum())
    demand, shipped = sum(s['demand']), float(clinker.sum())
    costs = {'Annualized capex': capex * crf(s['rate'], s['life']), 'Fixed operating cost': opex, 'Limestone': float(sum(production[i] * 1.5 * data['sites'][i]['limestone'] * .1 for i in range(6))), 'Cement freight': ctkm * s['cementRate'] * .1, 'Clinker freight': ktkm * s['clinkerRate'] * .1}
    return dict(facilities=facilities, costs=costs, total=sum(costs.values()), demand=demand, cement_lead=ctkm / demand if demand else 0, clinker_lead=ktkm / shipped if shipped else 0, clinker_shipped=shipped, clinker_capacity=kcap, grinding_capacity=gcap, errors=errors)


def formulate(data, s, choices=None):
    """30 module binaries, 120 cement flows, and 24 clinker flows."""
    if len(s['demand']) != 12 or not all(np.isfinite(x) and x >= 0 for x in s['demand']) or sum(s['demand']) <= 0:
        raise ValueError('Enter nonnegative market demands with a positive total.')
    limits = {'cementRate': (0, 20), 'clinkerRate': (0, 20), 'utilization': (.01, 1), 'factor': (.01, 1), 'rate': (0, .5), 'life': (1, 100), 'cementLimit': (0, 5000), 'clinkerLimit': (0, 5000)}
    for key, (low, high) in limits.items():
        if not np.isfinite(s[key]) or not low <= s[key] <= high: raise ValueError(f'Invalid {key}.')
    choices = choices if choices is not None else s.get('moduleChoices', ['auto'] * 10)
    if len(choices) != 10 or any(str(x) not in ['auto', '-1', '0', '1', '2'] for x in choices): raise ValueError('Invalid module choices.')
    c, lower, upper, integer = np.zeros(174), np.zeros(174), np.full(174, np.inf), np.zeros(174)
    upper[:30], integer[:30] = 1, 1
    rows, lbs, ubs = [], [], []
    def add(coeff, low=-np.inf, high=np.inf):
        row = np.zeros(174)
        for index, value in coeff: row[index] += value
        rows.append(row); lbs.append(low); ubs.append(high)
    for i, site in enumerate(data['sites']):
        mods = data['modules'][site['type']]
        add([(i * 3 + k, 1) for k in range(3)], high=1)
        for k, mod in enumerate(mods):
            index = i * 3 + k
            c[index] = mod['capex'] * crf(s['rate'], s['life']) + mod['opex']
            if site['id'] in s.get('unavailable', []): upper[index] = 0
            elif str(choices[i]) != 'auto': lower[index] = upper[index] = int(int(choices[i]) == k)
        flows = [(30 + i * 12 + j, 1) for j in range(12)]
        add(flows + [(i * 3 + k, -s['utilization'] * m['grinding']) for k, m in enumerate(mods)], high=0)
        for j in range(12):
            index, dist = 30 + i * 12 + j, data['cementDistances'][i][j]
            c[index] = .1 * (dist * s['cementRate'] + (1.5 * site['limestone'] * s['factor'] if i < 6 else 0))
            if dist > s['cementLimit']: upper[index] = 0
        if i < 6:
            add([(n, s['factor']) for n, _ in flows] + [(150 + i * 4 + j, 1) for j in range(4)] + [(i * 3 + k, -s['utilization'] * m['clinker']) for k, m in enumerate(mods)], high=0)
            for j in range(4):
                index, dist = 150 + i * 4 + j, data['clinkerDistances'][i][j]
                c[index] = .1 * (dist * s['clinkerRate'] + 1.5 * site['limestone'])
                if dist > s['clinkerLimit']: upper[index] = 0
    for j in range(12): add([(30 + i * 12 + j, 1) for i in range(10)], s['demand'][j], s['demand'][j])
    for j in range(4): add([(150 + i * 4 + j, 1) for i in range(6)] + [(30 + (6 + j) * 12 + k, -s['factor']) for k in range(12)], 0, 0)
    return c, integer, lower, upper, np.array(rows), np.array(lbs), np.array(ubs)


def solve(data, s, choices=None):
    c, integer, lower, upper, a, lb, ub = formulate(data, s, choices)
    result = milp(c, integrality=integer, bounds=Bounds(lower, upper), constraints=LinearConstraint(a, lb, ub), options={'mip_rel_gap': .0001, 'time_limit': 60})
    if result.status == 2: raise ValueError('No feasible network satisfies these demands, lane limits, and module choices. Try allowing more sites or larger modules.')
    if result.status != 0: raise ValueError('Solver did not reach the 0.01% gap target within the run limit. Previous results are unchanged. Try fixing some facility modules.')
    solution = deepcopy(s)
    x = np.where(np.abs(result.x) < 1e-8, 0, result.x)
    solution['modules'] = [next((k for k in range(3) if x[i * 3 + k] > .5), -1) for i in range(10)]
    solution['cement'] = x[30:150].reshape(10, 12).tolist()
    solution['clinker'] = x[150:].reshape(6, 4).tolist()
    solution['solverGap'] = float(result.mip_gap)
    m = metrics(data, solution)
    if m['errors'] or abs(m['total'] - result.fun) > 1e-4: raise RuntimeError('The solution failed model validation.')
    return solution


def lp_text(data, s):
    c, integer, lower, upper, a, lb, ub = formulate(data, s)
    names = [f'y{i}_{k}' for i in range(10) for k in range(3)] + [f'x{i}_{j}' for i in range(10) for j in range(12)] + [f'z{i}_{j}' for i in range(6) for j in range(4)]
    def expr(row): return ' '.join(f'{v:+.12g} {names[i]}' for i, v in enumerate(row) if v) or '0 y0_0'
    lines = ['Minimize', ' cost: ' + expr(c), 'Subject To']
    for i, row in enumerate(a):
        lines.append(f' r{i}: {expr(row)} ' + (f'= {lb[i]:.12g}' if lb[i] == ub[i] else f'<= {ub[i]:.12g}'))
    lines += ['Bounds']
    for i, name in enumerate(names): lines.append(f' {lower[i]:.12g} <= {name}' + (f' <= {upper[i]:.12g}' if np.isfinite(upper[i]) else ''))
    return '\n'.join(lines + ['Binary', ' '.join(names[:30]), 'End'])
