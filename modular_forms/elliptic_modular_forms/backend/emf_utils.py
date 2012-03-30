# -*- coding: utf-8 -*-
#*****************************************************************************
#  Copyright (C) 2010 Fredrik Strömberg <fredrik314@gmail.com>,
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.
#
#  The full text of the GPL is available at:
#
#                  http://www.gnu.org/licenses/
#*****************************************************************************
r"""
Utilities file for elliptic (holomorphic) modular forms.

AUTHOR: Fredrik Strömberg

"""
import random
from flask import  jsonify
from utils import *
from modular_forms.elliptic_modular_forms import EMF,emf, emf_logger, default_prec
logger = emf_logger
from sage.all import dimension_new_cusp_forms,vector,dimension_modular_forms,dimension_cusp_forms,is_odd,loads,dumps,Gamma0,Gamma1,Gamma
from modular_forms.backend.mf_utils import my_get
from plot_dom import draw_fundamental_domain
import base
from pymongo.binary import *

def parse_range(arg, parse_singleton=int):
    # TODO: graceful errors
    if type(arg)==parse_singleton:
        return arg
    if ',' in arg:
        return [parse_range(a) for a in arg.split(',')]
    elif '-' in arg[1:]:
        ix = arg.index('-', 1)
        start, end = arg[:ix], arg[ix+1:]
        q = {}
        if start:
            q['min'] = parse_singleton(start)
        if end:
            q['max'] = parse_singleton(end)
        return q
    else:
        return parse_singleton(arg)

def extract_limits_as_tuple(arg, field, defaults=(1,10)):
    if type(arg.get(field))==dict:
        limits=(arg[field]['min'],arg[field]['max'])
    else:
        if arg.get(field):
            limits=(arg[field],arg[field])
        else:
            limits=defaults
    return limits
    
def extract_data_from_jump_to(s):
    label=None;weight=None;character=None;level=None
    weight = 2  # this is default for jumping
    character = 0 # this is default for jumping
    if s == 'delta':
        weight = 12; level = 1; label = "a"
        exit
    # first see if we have a label or not, i.e. if we have precisely one string of letters at the end
    test = re.findall("[a-z]+",s)
    if len(test)==1: 
        label = test[0]
    else:
        label='a'  # the default is the first one
    #emf_logger.debug("label1={0}".format(label))
    # the first string of integers should be the level
    test = re.findall("\d+",s)
    emf_logger.debug("level mat={0}".format(test))
    if test:
        level = int(test[0])
    if len(test)>1: ## we also have weight
        weight = int(test[1])
    if len(test)>2: ## we also have character
        character = int(test[2])
    emf_logger.debug("label=%s"%label)
    emf_logger.debug("level=%s"%level)
    args=dict()
    args['level']=int(level); args['weight']=int(weight)
    args['character']=int(character); args['label']=label
    return args

def ajax_more2(callback, *arg_list, **kwds):
    r"""
    Like ajax_more but accepts increase in two directions.
    Call with
    ajax_more2(function,{'arg1':[x1,x2,...,],'arg2':[y1,y2,...]},'text1','text2')
    where function takes two named argument 'arg1' and 'arg2'
    """
    inline = kwds.get('inline', True)
    text = kwds.get('text', 'more')
    emf_logger.debug("inline={0}".format(inline))
    emf_logger.debug("text={0}".format(text))
    text0 = text[0]
    text1 = text[1]
    emf_logger.debug("arglist={0}".format(arg_list))
    nonce = hex(random.randint(0, 1<<128))
    if inline:
        args = arg_list[0]
        emf_logger.debug("args={0}".format(args))
        key1,key2=args.keys()
        l1=args[key1]
        l2=args[key2]
        emf_logger.debug("key1={0}".format(key1))
        emf_logger.debug("key2={0}".format(key2))
        emf_logger.debug("l1={0}".format(l1))
        emf_logger.debug("l2={0}".format(l2))
        args={key1:l1[0],key2:l2[0]}
        l11=l1[1:]; l21=l2[1:]
        #arg_list = arg_list[1:]
        arg_list1 = {key1:l1,key2:l21}
        arg_list2 = {key1:l11,key2:l2}
        #emf_logger.debug("arglist1={0}".format(arg_list))
        if isinstance(args, tuple):
            res = callback(*arg_list)
        elif isinstance(args, dict):
            res = callback(**args)
        else:
            res = callback(args)
            res = web_latex(res)
    else:
        res = ''
    emf_logger.debug("arg_list1={0}".format(arg_list1))
    emf_logger.debug("arg_list2={0}".format(arg_list2))
    arg_list1=(arg_list1,)
    arg_list2=(arg_list2,)
    if arg_list1 or arg_list2:
        url1 = ajax_url(ajax_more2, callback, *arg_list1, inline=True, text=text)
        url2 = ajax_url(ajax_more2, callback, *arg_list2, inline=True, text=text)
        emf_logger.debug("arg_list1={0}".format(url1))
        emf_logger.debug("arg_list2={0}".format(url2))
        s0 = """<span id='%(nonce)s'>%(res)s """  % locals()
        s1 = """[<a onclick="$('#%(nonce)s').load('%(url1)s', function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text0)s</a>""" % locals()
        t = """| <a onclick="$('#%(nonce)s').load('%(url2)s', function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text1)s</a>]</span>""" % locals()
        return (s0+s1+t)
    else:
        return res

def ajax_url(callback, *args, **kwds):
    if '_ajax_sticky' in kwds:
        _ajax_sticky = kwds.pop('_ajax_sticky')
    else:
        _ajax_sticky = False
    if not isinstance(args, tuple):
        args = args,
    nonce = hex(random.randint(0, 1<<128))
    pending[nonce] = callback, args, kwds, _ajax_sticky
    return url_for('ajax_result', id=nonce)


def ajax_once(callback,*arglist,**kwds):
    r"""
    """
    
    text = kwds.get('text', 'more')
    emf_logger.debug("text={0}".format(text))
    emf_logger.debug("arglist={0}".format(arglist))
    emf_logger.debug("kwds={0}".format(kwds))
    #emf_logger.debug("req={0}".format(request.args
    nonce = hex(random.randint(0, 1<<128))
    res = callback()
    url = ajax_url(ajax_once,arglist,kwds,inline=True)
    s0 = """<span id='%(nonce)s'>%(res)s """  % locals()
    #	s1 = """[<a onclick="$('#%(nonce)s').load('%(url)s', {'level':22,'weight':4},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text)s</a>""" % locals()
    s1 = """[<a onclick="$('#%(nonce)s').load('%(url)s', {a:1},function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text)s</a>""" % locals()
    return s0+s1


def ajax_later(callback,*arglist,**kwds):
    r"""
    Try to make a function that gets called after displaying the page.
    """
    
    text = kwds.get('text', 'more')
    text = 'more'
    emf_logger.debug("text={0}".format(text))
    emf_logger.debug("arglist={0}".format(arglist))
    emf_logger.debug("kwds={0}".format(kwds))
    emf_logger.debug("callback={0}".format(callback))
    #emf_logger.debug("req={0}".format(request.args
    nonce = hex(random.randint(0, 1<<128))
    # do not call the first time around
    if kwds.has_key("do_now"):
        if kwds['do_now']==1:
            do_now=0
        else:
            do_now=1
    else:
        do_now=0
    if not do_now:
        url = ajax_url(ajax_later,callback,*arglist,inline=True,do_now=do_now,_ajax_sticky=True)
        emf_logger.debug("ajax_url={0}".format(url))
        s0 = """<span id='%(nonce)s'></span>"""  % locals()
        s1 = """<a class='later' href=# id='%(nonce)s' onclick='this_fun()'>%(text)s</a>""" % locals()
        s2= """<script>
        function this_fun(){
        $.getJSON('%(url)s',{do_now:1},
        function(data) {
        $(\"span#%(nonce)s\").text(data.result);
        });
        return true;
        };
        </script>
        
        """ % locals()
        emf_logger.debug("s0+s1={0}".format(s2+s0))
        return s2+s0+s1
    else:
        res = callback(do_now=do_now)
        return jsonify(result=res)


class MyNewGrp (object):
    def __init__(self,level,info):
        self._level=level
        self._info=info
    def plot(self,**kwds):
        return render_fd_plot(self._level,self._info,**kwds)
            
def render_fd_plot(level,info,**kwds):
    group = None
    if(info.has_key('group')):
        group = info['group']
        # we only allow standard groups
    if info.has_key('grouptype'):
        type=int(info['grouptype'])
        if info['grouptype']==0:
            group='Gamma0'
        elif info['grouptype']==1:
            group='Gamma1'
    if (group  not in ['Gamma0','Gamma','Gamma1']):
        group = 'Gamma0'
        type=int(0)
    else:
        if group=='Gamma':
            type=int(-1)
        else:
            type=(1)
    db_name = 'SL2Zsubgroups'
    collection='groups'
    C = base.getDBConnection()
    emf_logger.debug("C={0}".format(C))
    if not C:
        emf_logger.critical("Could not connect to Database! C={0}".format(C))
    if not db_name in C.database_names():
        emf_logger.critical("Incorrect database name {0}. \n Available databases are:{1}".format(db_name,C.database_names()))
    if not collection in C[db_name].collection_names():
        emf_logger.critical("Incorrect collection {0} in database {1}. \n Available collections are:{2}".format(collection,db_name,C[db_name].collection_names()))
    
    find=C[db_name][collection].find_one({'level':level,'type':type})
    if find:
        if find.get('domain'):
            domain=loads(str(find['domain']))
        emf_logger.debug('Found fundamental domain in database')
    else:
        emf_logger.debug('Drawing fundamental domain for group {0}({1})'.format(group,level))
        domain=draw_fundamental_domain(level,group,**kwds)
            #G=Gamma0(level)
            #C[db_name][collection].insert({'level':int(level), 'type':type, 'index':int(G.index), 'G':pymongo.binary.Binary(dumps(G)), 'domain': pymongo.binary.Binary(dumps(domain))})
            #emf_logger.debug('Inserting group and fundamental domain in database')
    return domain


def is_data_in_db(level=0,weight=0,character=0):
    r"""
     Checks whether we have the requested data in the database.
    """
    
    return True
    
