from __future__ import division
import numpy as np
from _step_generators import _generate_step
from scipy import misc
from scipy.ndimage.filters import convolve1d
from _derivative_numdiff import extrapolate


def hessdiag(f, x, **options):
    """
    Diagonal elements of Hessian of a function

    Parameters
    ----------
    f : function
        ``f(x)`` returning a scalar.
    x : array
        parameters at which the hessdiag is to be evaluated
    options : dict
        options for specifying the method, order of hessdiag,
        order of error and other parameters for step generation.

    Returns
    -------
    hessdiag : array
        Hessian diagonal


    Examples
    --------
    >>> hessian(lambda x : x[0] + x[1]**2 + x[2]**3, [1,2,3])
    [  1.81898940e-12   2.00000000e+00   1.80000000e+01]

     References
    ----------
    1. https://github.com/pbrod/numdifftools/tree/master/numdifftools

    2. https://en.wikipedia.org/wiki/Finite_difference

    3. D Levy, Numerical Differentiation, Section 5
    """

    x = np.asarray(x)
    method = options.pop('method', 'central')
    n = 2
    order = options.pop('order', 2)
    step = options.pop('step', None)
    if step not in ['max_step', 'min_step', None]:
        raise ValueError('step can only take values'
                         ' as `max_step` or `min_step`')
    step_ratio = options.pop('step_ratio', None)
    if n == 0:
        hessdiag = f(x)
    else:
        if step_ratio is None:
            if n == 1:
                step_ratio = 2.0
            else:
                step_ratio = 1.6
        if step is None:
            step = 'max_step'
        options.update(x=x, n=n, order=order,
                       method=method, step=step, step_ratio=step_ratio)
        step_gen = _generate_step(**options)
        steps = [stepi for stepi in step_gen]
        fact = 1.0
        step_ratio_inv = 1.0 / step_ratio
        if method is 'central':
            fxi = f(x)
            ni = len(x)
            increments = [np.identity(ni) * h for h in steps]
            results = np.array([(f(x + hi) + f(x - hi)) / 2.0 - fxi
                                for hi in increments])
            fd_step = 2
            offset = 2
        if method is 'forward':
            fxi = f(x)
            ni = len(x)
            increments = [np.identity(ni) * h for h in steps]
            results = np.array([f(x + hi) - fxi for hi in increments])
            fd_step = 1
            offset = 1
        if method is 'backward':
            fxi = f(x)
            ni = len(x)
            increments = [np.identity(ni) * h for h in steps]
            results = np.array([fxi - f(x - hi) for hi in increments])
            fd_step = 1
            offset = 1
        fun = np.vstack(list(np.ravel(r)) for r in results)
        h = np.vstack(list(
                np.ravel(np.ones(np.shape(
                                         results[0]))*step)) for step in steps)
        richardson_step = 1
        if method is 'central':
            richardson_step = 2
        richardson_order = max(
                (order // richardson_step) * richardson_step, richardson_step)
        richarson_terms = 2
        num_terms = (n+richardson_order-1) // richardson_step
        term = (n-1) // richardson_step
        c = fact / misc.factorial(
                np.arange(offset, fd_step * num_terms + offset, fd_step))
        [i, j] = np.ogrid[0:num_terms, 0:num_terms]
        fd = np.atleast_2d(c[j] * step_ratio_inv**(i * (fd_step * j + offset)))
        fd = np.linalg.pinv(fd)
        if n % 2 == 0 and method is 'backward':
            fdi = -fd[term]
        else:
            fdi = fd[term]
        if h.shape[0] < n + order - 1:
            raise ValueError('num_steps must be larger than n + order - 1')
        fdiff = convolve1d(fun, fdi[::-1], axis=0, origin=(fdi.size - 1) // 2)
        hessdiag = fdiff / (h**n)
        num_steps = max(h.shape[0] + 1 - fdi.size, 1)
        hessdiag = extrapolate(order, richarson_terms, richardson_step,
                               step_ratio, hessdiag[:num_steps],
                               h[:num_steps], np.shape(results[0]))
    return hessdiag
