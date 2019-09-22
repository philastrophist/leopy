"""Example of data with missing values and with a lognormal distribution

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

np.random.seed(16)

dist = scipy.stats.lognorm
Ndata = 500
rho = 0.5
R = np.array([[1., rho], [rho, 1.]])
loc_true = np.array([0., 2.])
scale_true = np.array([1., 3.])
shape_true = np.array([0.5, 1.5])

print('population parameters: [{} {} {} {} {} {} {}]'.format(
    *loc_true, *scale_true, *shape_true, rho))

mean_pop = scale_true * np.exp(0.5*shape_true**2) + loc_true
std_pop = (mean_pop - loc_true) * np.sqrt(np.exp(shape_true**2)-1.)
print('population statistics (mean, std, corr): [{:.3g} {:.3g} {:.3g} {:.3g} '
      '{:.3g}]'.format(
    *mean_pop, *std_pop, rho))

## -- create observational data
x = scipy.stats.multivariate_normal.rvs(cov=R, size=Ndata)

# print('rho(x) = {}'.format(np.corrcoef(x.T)))
rho_x_sample = np.corrcoef(x.T)[0, 1]

y = dist.ppf(scipy.stats.norm.cdf(x),
             shape_true, loc=loc_true, scale=scale_true)
y_true = np.copy(y)
ey = np.zeros_like(y)
ey[:, 0] = 0.2  # 1e-6  # 0.2 # 0.1
ey[:, 1] = 0.1 # 1e-6   # 0.1
y[:, 0] += ey[:, 0] * np.random.randn(Ndata)
y[:, 1] += ey[:, 1] * np.random.randn(Ndata)

print('sample statistics (mean, std, corr): [{:.3g} {:.3g} {:.3g} {:.3g} '
      '{:.3g}]'.format(
    np.nanmean(y[:, 0]), np.nanmean(y[:, 1]),
    np.nanstd(y[:, 0]), np.nanstd(y[:, 1]), rho_x_sample))

def logistic(x):
    res = np.ones_like(x)
    sel = x < 20
    res[sel] = np.exp(x[sel]) / (np.exp(x[sel]) + 1.)
    return res

# data missing data at random (MAR) based on values of other column
m1 = scipy.stats.bernoulli.rvs(logistic(y[:, 0]-3.)).astype(bool)  # for col 1
m0 = scipy.stats.bernoulli.rvs(logistic(y[:, 1]-6.)).astype(bool)  # for col 0
y[m1, 1] = np.float('NaN')
y[m0, 0] = np.float('NaN')

print('sample statistics (w/ missing as NaN): [{:.3g} {:.3g} {:.3g} {:.3g} '
      'N/A]'.format(
    np.nanmean(y[:, 0]), np.nanmean(y[:, 1]),
    np.nanstd(y[:, 0]), np.nanstd(y[:, 1])))

# complete cases:
ycc = y[np.all(~np.isnan(y), axis=1)]
eycc = ey[np.all(~np.isnan(y), axis=1)]

print('sample statistics (complete cases): [{:.3g} {:.3g} {:.3g} {:.3g} '
    '{:.3g}]'.format(
    np.nanmean(ycc[:, 0]), np.nanmean(ycc[:, 1]),
    np.nanstd(ycc[:, 0]), np.nanstd(ycc[:, 1]), np.corrcoef(ycc.T)[0, 1]))

ncc = np.sum(np.all(~np.isnan(y), axis=1))
ncm = np.sum(np.all(np.isnan(y), axis=1))
print('{} total cases, {} complete, {} incomplete, {} completely '
      'missing'.format(Ndata, ncc, Ndata - ncc, ncm))

for irun in range(2):

    if irun == 0:
        print('--- Using all data (incl. missing) ---')
        ly = y
        ley = ey
    else:
        print('--- Using only complete cases ---')
        ly = ycc
        ley = eycc

    df = pd.DataFrame(np.array([ly[:, 0], ly[:, 1], ley[:, 0], ley[:, 1]]).T,
                      columns=['v0', 'v1', 'e_v0', 'e_v1'])
    obs = leopy.Observation(df, 'test', verbosity=0)

    ## -- set up Likelihood and find maximum likelihood parameters
    like = leopy.Likelihood(obs, p_true='lognorm', p_cond='norm',
                            verbosity=-1)

    def f_mlnlike(x):
        #print(x)
        loc_true = x[0:2]
        scale_true = x[2:4]
        shape_true = x[4:6]
        rho = x[6]
        R = np.array([[1., rho], [rho, 1.]])
        pp = like.p(loc_true, scale_true, shape_true=shape_true, R_true=R)
        if np.sum(pp==0) > 0:
            return np.inf
        else:
            return -np.sum(np.log(pp))

    bounds = scipy.optimize.Bounds(
        [-np.inf, -np.inf, 1e-3, 1e-3, 1e-3, 1e-3, 1e-3],
        [np.inf, np.inf, 10., 10., 10., 10., 1-1e-3])

    print('Maximizing likelihood - This may take a while...')
    optres = scipy.optimize.minimize(f_mlnlike, [0., 0., 1., 1., 1., 1., 0.3],
                                     bounds=bounds, method='SLSQP',
                                     options={'disp': True})

    print('Maximum likelihood parameters: [{:.3g} {:.3g} {:.3g} {:.3g} '
          '{:.3g} {:.3g} {:.3g}]'.format(*optres.x))
    loc_opt = optres.x[0:2]
    scale_opt = optres.x[2:4]
    shape_opt = optres.x[4:6]
    rho_opt = optres.x[6]

    mean_opt = scale_opt * np.exp(0.5*shape_opt**2) + loc_opt
    std_opt = (mean_opt - loc_opt) * np.sqrt(np.exp(shape_opt**2)-1.)
    print('Maximum likelihood statistics: [{:.3g} {:.3g} {:.3g} {:.3g} '
          '{:.3g}]'.format(*mean_opt, *std_opt, rho_opt))
