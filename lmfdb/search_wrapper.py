
from lmfdb.search_parsing import parse_start, parse_count
from sage.misc.decorators import decorator_keywords
from flask import render_template, jsonify
from psycopg2.extensions import QueryCanceledError
from lmfdb.base import ctx_proc_userdata
from lmfdb.utils import flash_error, to_dict

class SearchWrapper(object):
    def __init__(self, f, template, table, title, err_title, per_page=50, shortcuts={}, longcuts={}, projection = 1, cleaners = {}, postprocess=None, **kwds):
        self.f = f
        self.template = template
        self.table = table
        self.title = title
        self.err_title = err_title
        self.per_page = per_page
        self.shortcuts = shortcuts
        self.longcuts = longcuts
        self.projection = projection
        self.cleaners = cleaners
        self.postprocess = postprocess
        self.kwds = kwds

    def __call__(self, info):
        info = to_dict(info) # I'm not sure why this is required...
        for key, func in self.shortcuts.items():
            if info.get(key,'').strip():
                return func(info)
        query = {}
        template_kwds = {}
        for key in self.kwds:
            template_kwds[key] = info.get(key, self.kwds[key]())

        try:
            errpage = self.f(info, query)
        except ValueError as err:
            # Errors raised in parsing
            info['err'] = str(err)
            err_title = query.pop('__err_title__', self.err_title)
            return render_template(self.template, info=info, title=err_title, **template_kwds)
        if errpage is not None:
            return errpage
        if 'result_count' in info:
            nres = self.table.count(query)
            return jsonify({"nres":str(nres)})
        sort = query.pop('__sort__', None)
        table = query.pop('__table__', self.table)
        proj = query.pop('__projection__', self.projection)
        # We want to pop __title__ even if overridden by info.
        title = query.pop('__title__', self.title)
        title = info.get('title', title)
        template = query.pop('__template__', self.template)
        count = parse_count(info, self.per_page)
        start = parse_start(info)
        try:
            res = table.search(query, proj, limit=count, offset=start, sort=sort, info=info)
        except QueryCanceledError as err:
            ctx = ctx_proc_userdata()
            flash_error('The search query took longer than expected! Please help us improve by reporting this error  <a href="%s" target=_blank>here</a>.' % ctx['feedbackpage'])
            info['err'] = str(err)
            info['query'] = dict(query)
            return render_template(self.template, info=info, title=self.err_title, **template_kwds)
        else:
            if self.cleaners:
                for v in res:
                    for name, func in self.cleaners.items():
                        v[name] = func(v)
            if self.postprocess is not None:
                res = self.postprocess(res, info, query)
            for key, func in self.longcuts.items():
                if info.get(key,'').strip():
                    return func(res, info, query)
            info['results'] = res
            return render_template(template, info=info, title=title, **template_kwds)

@decorator_keywords
def search_wrap(f, **kwds):
    return SearchWrapper(f, **kwds)
