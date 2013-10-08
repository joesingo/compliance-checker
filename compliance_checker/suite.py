"""
Compliance Checker suite runner
"""

import inspect
import itertools
from netCDF4 import Dataset
from lxml import etree as ET
from wicken.netcdf_dogma import NetCDFDogma
from compliance_checker.base import BaseCheck, fix_return_value

class CheckSuite(object):

    def _get_checks(self, checkclass):
        """
        Helper method to retreive check methods from a Checker class.

        The name of the methods in the Checker class should start with "check_" for this
        method to find them.
        """
        meths = inspect.getmembers(checkclass, inspect.ismethod)
        return [x[1] for x in meths if x[0].startswith("check_")]

    def _run_check(self, check_method, ds):
        val = check_method(ds)

        if isinstance(val, list):
            return [fix_return_value(v, check_method.im_func.func_name) for v in val]

        return [fix_return_value(val, check_method.im_func.func_name)]

    def run(self, dataset_location, *args):
        """
        Runs this CheckSuite on the dataset with all the passed Checker instances.

        Returns a dictionary mapping Checkers to their grouped scores.
        """

        ret_val = {}

        for a in args:
            checks = self._get_checks(a)

            ds = self.load_dataset(dataset_location, a.beliefs())

            #vals = list(itertools.chain.from_iterable([[v] if not isinstance(v, list) else v for v in [c(ds) for c in checks]]))
            vals = list(itertools.chain.from_iterable(map(lambda c: self._run_check(c, ds), checks)))

            # remove Nones?

            # transform to scores
            scores = self.scores(vals)

            ret_val[a] = scores

        return ret_val

    class DSPair(object):
        def __init__(self, ds, dogma):
            self.dataset = ds
            self.dogma = dogma

    def load_dataset(self, ds_str, belief_map):
        """
        Helper method to load a dataset.
        """
        ds = Dataset(ds_str)
        data_object = NetCDFDogma('ds', belief_map, ds)

        return self.DSPair(ds, data_object)

    def scores(self, raw_scores):
        """
        Transforms raw scores from a single checker into a fully tallied and grouped scoreline.
        """
        grouped = self._group_raw(raw_scores)

        # score each top level item in groups
        weights = [x[1] for x in grouped]
        scores = [x[2] for x in grouped]

        def score(acc, cur):
            # cur is ((x, x), weight)
            cs, weight = cur

            # acc is (score, total possible)
            cas, catotal = acc

            pts = 0
            if cs[1] == 0:
                return acc  # effectively a skip @TODO keep track of that?

            if cs[0] == cs[1]:
                return (cas + (1 * weight), catotal + weight)
            elif cs[0] == 0:
                return (cas, catotal + weight)

            # @TODO: could do cs[0] / cs[1] for exact pct points
            return (cas + (0.5 * weight), catotal + weight)

        cur_score = reduce(score, zip(scores, weights), (0, 0))

        return (cur_score, grouped)

    def _group_raw(self, raw_scores, cur=None, level=1):
        """
        Internal recursive method to group raw scores into a cascading score summary.

        Only top level items are tallied for scores.
        """
        #print "_group_raw", level, cur, len(raw_scores), raw_scores[0]

        def build_group(label=None, weight=None, value=None, sub=None):
            label  = label
            weight = weight
            value  = self._translate_value(value)
            sub    = sub or []

            return (label, weight, value, sub)

        def trim_groups(r):
            if isinstance(r[2], tuple) or isinstance(r[2], list):
                new_r2 = r[2][1:]
            else:
                new_r2 = []

            return r[0:2] + tuple([new_r2])

        # CHECK FOR TERMINAL CONDITION: all raw_scores[2] are single length
        terminal = map(lambda x: len(x[2]), raw_scores)
        if terminal == [0] * len(raw_scores):
            return []

        def group_func(r):
            """
            Slices off first element (if list/tuple) of classification or just returns it if scalar.
            """
            if isinstance(r[2], tuple) or isinstance(r[2], list):
                return r[2][0:1][0]
            return r[2]

        grouped = itertools.groupby(sorted(raw_scores, key=group_func), key=group_func)
        ret_val = []

        for k, v in grouped:
            v = list(v)
            #print "group", k, level

            cv = self._group_raw(map(trim_groups, v), k, level+1)
            if len(cv):
                # if this node has children, max weight of children + sum of all the scores
                max_weight = max(map(lambda x: x[1], cv))
                sum_scores = tuple(map(sum, zip(*(map(lambda x: x[2], cv)))))
            else:
                max_weight = max(map(lambda x: x[0], v))
                sum_scores = tuple(map(sum, zip(*(map(lambda x: self._translate_value(x[1]), v)))))

            ret_val.append(build_group(k, max_weight, sum_scores, cv))

        return ret_val

    def _translate_value(self, val):
        """
        Turns shorthand True/False checks into full scores (1, 1)/(0, 1).
        Leaves full scores alone.
        """
        if val == True:
            return (1, 1)
        elif val == False:
            return (0, 1)
        elif val is None:
            return (0, 0)

        return val

