##
# Copyright (c) 2008-2010 Sprymix Inc.
# All rights reserved.
#
# See LICENSE for details.
##


from semantix.utils import ast, parsing, debug

from semantix.caos.caosql.parser.errors import CaosQLSyntaxError
from semantix.caos.caosql import ast as qlast, CaosQLQueryError
from semantix.caos import types as caos_types


class CaosQLParser(parsing.Parser):
    def get_parser_spec_module(self):
        from . import caosql
        return caosql

    def get_debug(self):
        return 'caos.caosql.parser' in debug.channels

    def get_exception(self, native_err):
        return CaosQLQueryError(native_err.args[0])

    def normalize_select_query(self, query, filters=None, sort=None, context=None):
        nodetype = type(query)

        qtree = query

        if nodetype != qlast.SelectQueryNode:
            selnode = qlast.SelectQueryNode()
            selnode.targets = [qlast.SelectExprNode(expr=qtree)]
            qtree = selnode

        if context:
            context_selector = None

            for anchor, object in context.items():
                if isinstance(object.__class__, caos_types.ConceptClass):
                    source = object
                else:
                    source = object._instancedata.source

                assert source

                origproto = caos_types.prototype(object.__class__)
                clsproto = caos_types.prototype(source.__class__)

                objnode = qlast.PathNode(steps=[qlast.PathStepNode(expr=clsproto.name.name,
                                                                   namespace=clsproto.name.module)])

                path = qlast.PathNode(steps=[objnode,
                                             qlast.LinkExprNode(expr=qlast.LinkNode(name='id'))])
                cond = qlast.BinOpNode(left=path, op=ast.ops.EQ,
                                       right=qlast.ConstantNode(value=None,
                                                                index='__context_%s' % anchor))

                if isinstance(object.__class__, caos_types.ConceptClass):
                    objnode.var = qlast.VarNode(name=anchor)
                else:
                    objnode.var = qlast.VarNode(name='%s_source' % anchor)
                    cond.right.index = '__context_%s_source' % anchor

                    link = qlast.LinkExprNode(expr=qlast.LinkNode(name=origproto.normal_name().name,
                                                                  namespace=origproto.name.module))

                    link = qlast.PathNode(steps=[link], lvar=qlast.VarNode(name=anchor))

                    objnode = qlast.PathNode(steps=[qlast.PathStepNode(expr=clsproto.name.name,
                                                                   namespace=clsproto.name.module)])

                    path = qlast.PathNode(steps=[objnode, link])

                    lcond = qlast.BinOpNode(left=path, op=ast.ops.IN,
                                            right=qlast.PathNode(steps=[qlast.PathStepNode(expr='%')]))

                    cond = qlast.BinOpNode(left=cond,
                                           op=ast.ops.AND,
                                           right=lcond)

                if context_selector:
                    context_selector = qlast.BinOpNode(left=context_selector,
                                                       op=ast.ops.AND,
                                                       right=cond)
                else:
                    context_selector = cond

            if qtree.where:
                qtree.where = qlast.BinOpNode(left=qtree.where,
                                              op=ast.ops.AND,
                                              right=context_selector)
            else:
                qtree.where = context_selector

        if filters:
            targets = {t.alias: t.expr for t in qtree.targets}

            for name, value in filters.items():
                target = targets.get(name)
                if not target:
                    err = 'filters reference column %s which is not in query targets' % name
                    raise CaosQLQueryError(err)

                if qtree.where:
                    const = qlast.ConstantNode(value=None, index='__filter%s' % name)
                    left = qtree.where
                    right = qlast.BinOpNode(left=target, right=const, op=ast.ops.EQ)
                    qtree.where = qlast.BinOpNode(left=left, right=right, op=ast.ops.AND)

        if sort:
            targets = {t.alias: t.expr for t in qtree.targets}
            newsort = []

            for name, direction in sort:
                target = targets.get(name)
                if not target:
                    err = 'sort reference column %s which is not in query targets' % name
                    raise CaosQLQueryError(err)

                newsort.append(qlast.SortExprNode(path=target, direction=direction))

            qtree.orderby = newsort

        return qtree
