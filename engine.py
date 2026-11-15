import math
import pandas as pd


def budget_breakdown(people, days, nights, transport, lodging, food, activities, other, buffer_percent):
    values = [people, days, nights, transport, lodging, food, activities, other, buffer_percent]
    if any(not math.isfinite(float(v)) or v < 0 for v in values) or people < 1 or days < 1:
        raise ValueError('Enter finite non-negative values, at least one person and one day.')
    if nights > days:
        raise ValueError('Nights cannot exceed trip days.')
    costs = {'Transport': transport, 'Accommodation': lodging * nights,
             'Food': food * people * days, 'Activities': activities * people, 'Other': other}
    costs['Reserve'] = sum(costs.values()) * buffer_percent / 100
    return pd.DataFrame({'Category': costs.keys(), 'MNT': costs.values()})
