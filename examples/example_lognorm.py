"""Example of data with lognormal distribution - this example demonstrates the
    importance of properly accounting for measurement uncertainty.

This file is part of LEO-Py --
Likelihood Estimation of Observational data with Python

Copyright 2019 University of Zurich, Robert Feldmann

LEO-Py is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

LEO-Py is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with LEO-Py. If not, see <https://www.gnu.org/licenses/>.
"""
import numpy as np
import pandas as pd
import scipy.stats
import scipy.optimize

import pytest

import leopy

np.random.seed(1)

print('Example: Correlated data with a lognormal distribution and measurement '
      'errors. In one case the measurement uncertainty is known, while in the '
      'second case, it is unknown.')

dist = scipy.stats.lognorm
Ndata = 300
rho = 0.8
R = np.array([[1., rho], [rho, 1.]])
loc_true = np.array([0., 2.])
scale_true = np.array([1., 3.])
shape_true = np.array([0.5, 1.5])

## -- create observational data
x = scipy.stats.multivariate_normal.rvs(cov=R, size=Ndata)
print('rho(x) = {}'.format(np.corrcoef(x.T)))

y = dist.ppf(scipy.stats.norm.cdf(x),
             shape_true, loc=loc_true, scale=scale_true)
y_true = np.copy(y)
ey = np.zeros_like(y)
ey[:, 0] = 0.25
ey[:, 1] = 0.1
y[:, 0] += ey[:, 0] * np.random.randn(Ndata)
y[:, 1] += ey[:, 1] * np.random.randn(Ndata)

print('rho(y) = {}'.format(np.corrcoef(y.T)))
df = pd.DataFrame(np.array([y[:, 0], y[:, 1], ey[:, 0], ey[:, 1]]).T,
                  columns=['v0', 'v1', 'e_v0', 'e_v1'])
obs = leopy.Observation(df, 'test', verbosity=0)

## --
print('Population parameter values: {:.3g} {:.3g} {:.3g} {:.3g} {:.3g} {:.3g} '
      '{:.3g}'.format(loc_true[0], loc_true[1], scale_true[0], scale_true[1],
                      shape_true[0], shape_true[1], rho))

## -- set up Likelihood and find maximum likelihood parameters
like = leopy.Likelihood(obs, p_true='lognorm', p_cond='norm')

like2 = leopy.Likelihood(obs, p_true='lognorm')

# return minus-log-likelihood/Ndata of params given data with meas. uncertainty
def f_mlnlike(x):
    #print(x)
    loc_true = x[0:2]
    scale_true = x[2:4]
    shape_true = x[4:6]
    rho = x[6]
    R = np.array([[1., rho], [rho, 1.]])
    if np.any(np.linalg.eigvalsh(R) < 0):  # ensure pos.-semidefinite
        return 1000.

    pp = like.p(loc_true, scale_true, shape_true=shape_true, R_true=R)
    if np.sum(pp==0) > 0:
        return 1000.
    else:
        return -np.sum(np.log(pp))/Ndata

# return minus-log-likelihood of parameters of data lacking meas. uncertainty
def f_mlnlike2(x):
    # print(x)
    loc_true = x[0:2]
    scale_true = x[2:4]
    shape_true = x[4:6]
    rho = x[6]
    R = np.array([[1., rho], [rho, 1.]])
    if np.any(np.linalg.eigvalsh(R) < 0):  # ensure pos.-semidefinite
        return 1000.

    pp = like2.p(loc_true, scale_true, shape_true=shape_true, R_true=R)
    if np.sum(pp==0) > 0:
        if np.sum(pp==0) <= 7:
            return -np.sum(np.log(pp[pp>0]))/Ndata
        return 1000.
    else:
        return -np.sum(np.log(pp))/Ndata

bounds = scipy.optimize.Bounds(
    [-np.inf, -np.inf, 1e-3, 1e-3, 1e-3, 1e-3, 1e-3],
    [np.inf, np.inf, 10., 10., 10., 10., 1-1e-3])

if 1:
    print('Maximizing likelihood - This may take a while...')
    optres = scipy.optimize.minimize(f_mlnlike, [0., 0., 1., 1., 1., 1., 0.3],
                                     bounds=bounds, method='SLSQP',
                                     options={'disp': True})
    print('Most likely parameters when meas. uncert. is taken into account')
    print(optres.x)

if 1:
    print('Maximizing likelihood - This may take a while...')
    optres = scipy.optimize.minimize(f_mlnlike2, [0., 0., 1., 1., 1., 1., 0.3],
                                     bounds=bounds, method='SLSQP',
                                     options={'disp': True})
    print('Most likely parameters when meas. uncert. is not properly modeled')
    print(optres.x)
