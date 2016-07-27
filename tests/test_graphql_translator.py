##
# Copyright (c) 2016 MagicStack Inc.
# All rights reserved.
#
# See LICENSE for details.
##


import os
import re
import textwrap

from edgedb.lang import _testbase as lang_tb
from edgedb.lang.common import markup
from edgedb.lang import graphql as edge_graphql

from edgedb.lang.schema import declarative as s_decl


class TranslatorTest(lang_tb.BaseParserTest):
    re_filter = re.compile(r'''[\s,]+|(\#.*?\n)''')

    def assert_equal(self, expected, result):
        expected_stripped = self.re_filter.sub('', expected).lower()
        result_stripped = self.re_filter.sub('', result).lower()

        assert expected_stripped == result_stripped, \
            '[test]expected: {}\n[test] != returned: {}'.format(
                expected, result)

    def run_test(self, *, source, spec, expected=None):
        debug = bool(os.environ.get('DEBUG_GRAPHQL'))
        if debug:
            print('\n--- GRAPHQL ---')
            markup.dump_code(textwrap.dedent(source).strip(), lexer='graphql')

        result = edge_graphql.translate(self.schema, source)

        if debug:
            print('\n--- EDGEQL ---')
            markup.dump_code(result, lexer='edgeql')

        self.assert_equal(expected, result)

    def setUp(self):
        schema_text = textwrap.dedent(self.SCHEMA)
        self.schema = s_decl.load_module_declarations(
            [('test', schema_text)])


class TestGraphQLTranslation(TranslatorTest):
    SCHEMA = r"""
        concept Group:
            required link name -> str
            link settings -> Setting:
                mapping: 1*

        concept Setting:
            required link name -> str
            required link value -> str

        concept User:
            required link name -> str
            required link active -> bool
            link groups -> Group:
                mapping: **
    """

    def test_graphql_translation_query01(self):
        r"""
        query @edgedb(module: "test") {
            User {
                name,
                groups {
                    id
                    name
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups[
                    id,
                    name
                ]
            ]
        """

    def test_graphql_translation_fragment01(self):
        r"""
        fragment groupFrag on Group {
            id
            name
        }

        query @edgedb(module: "test") {
            User {
                name,
                groups {
                    ... groupFrag
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups[
                    id,
                    name
                ]
            ]
        """

    def test_graphql_translation_fragment02(self):
        r"""
        fragment userFrag1 on User {
            name
            ... userFrag2
        }

        fragment userFrag2 on User {
            groups {
                ... groupFrag
            }
        }

        fragment groupFrag on Group {
            id
            name
        }

        query @edgedb(module: "test") {
            User {
                ... userFrag1
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups[
                    id,
                    name
                ]
            ]
        """

    def test_graphql_translation_fragment03(self):
        r"""
        fragment userFrag2 on User {
            groups {
                ... groupFrag
            }
        }

        fragment groupFrag on Group {
            id
            name
        }

        query @edgedb(module: "test") {
            User {
                ... {
                    name
                    ... userFrag2
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups[
                    id,
                    name
                ]
            ]
        """

    def test_graphql_translation_fragment04(self):
        r"""
        fragment userFrag1 on User {
            name
            ... {
                groups {
                    ... groupFrag
                }
            }
        }

        fragment groupFrag on Group {
            id
            name
        }

        query @edgedb(module: "test") {
            User {
                ... userFrag1
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups[
                    id,
                    name
                ]
            ]
        """

    def test_graphql_translation_directives01(self):
        r"""
        query @edgedb(module: "test") {
            User {
                name @include(if: true),
                groups @include(if: false) {
                    id
                    name
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
            ]
        """

    def test_graphql_translation_directives02(self):
        r"""
        query @edgedb(module: "test") {
            User {
                name @skip(if: true),
                groups @skip(if: false) {
                    id @skip(if: false)
                    name @skip(if: true)
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                groups[
                    id,
                ]
            ]
        """

    def test_graphql_translation_directives03(self):
        r"""
        query @edgedb(module: "test") {
            User {
                name @skip(if: true), @include(if: true),

                groups @skip(if: false), @include(if: true) {
                    id @skip(if: false), @include(if: true)
                    name @skip(if: true), @include(if: true)
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                groups[
                    id,
                ]
            ]
        """

    def test_graphql_translation_directives04(self):
        r"""
        fragment userFrag1 on User {
            name
            ... {
                groups @include(if: false) {
                    ... groupFrag
                }
            }
        }

        fragment groupFrag on Group {
            id
            name
        }

        query @edgedb(module: "test") {
            User {
                ... userFrag1
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
            ]
        """

    def test_graphql_translation_directives05(self):
        r"""
        fragment userFrag1 on User {
            name
            ... @skip(if: true) {
                groups {
                    ... groupFrag
                }
            }
        }

        fragment groupFrag on Group {
            id
            name
        }

        query @edgedb(module: "test") {
            User {
                ... userFrag1
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
            ]
        """

    def test_graphql_translation_directives06(self):
        r"""
        fragment userFrag1 on User {
            name
            ... {
                groups {
                    ... groupFrag @skip(if: true)
                    id
                }
            }
        }

        fragment groupFrag on Group {
            name
        }

        query @edgedb(module: "test") {
            User {
                ... userFrag1
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups [
                    id,
                ]
            ]
        """

    def test_graphql_translation_arguments01(self):
        r"""
        query @edgedb(module: "test") {
            User(name: "John") {
                name,
                groups {
                    id
                    name
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups[
                    id,
                    name
                ]
            ]
        WHERE
            (User.name = 'John')
        """

    def test_graphql_translation_arguments02(self):
        r"""
        query @edgedb(module: "test") {
            User(name: "John", active: true) {
                name,
                groups {
                    id
                    name
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups[
                    id,
                    name
                ]
            ]
        WHERE
            (
                (User.name = 'John') AND
                (User.active = True)
            )
        """

    def test_graphql_translation_arguments03(self):
        r"""
        query @edgedb(module: "test") {
            User {
                name,
                groups(name: "admin") {
                    id
                    name
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                (groups WHERE (User.groups.name = 'admin')) [
                    id,
                    name
                ]
            ]
        """

    def test_graphql_translation_arguments04(self):
        r"""
        query @edgedb(module: "test") {
            User(groups__name: "admin") {
                name,
                groups {
                    id
                    name
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups [
                    id,
                    name
                ]
            ]
        WHERE
            (User.groups.name = 'admin')
        """

    def test_graphql_translation_arguments05(self):
        r"""
        query @edgedb(module: "test") {
            User(groups__name__in: ["admin", "support"]) {
                name,
                groups {
                    id
                    name
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups [
                    id,
                    name
                ]
            ]
        WHERE
            (User.groups.name IN ('admin', 'support'))
        """

    def test_graphql_translation_arguments06(self):
        r"""
        query @edgedb(module: "test") {
            User(groups__name__ni: ["admin", "support"]) {
                name,
                groups {
                    id
                    name
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups [
                    id,
                    name
                ]
            ]
        WHERE
            (User.groups.name NOT IN ('admin', 'support'))
        """

    def test_graphql_translation_arguments07(self):
        r"""
        query @edgedb(module: "test") {
            User(groups__name__ne: "admin") {
                name,
                groups {
                    id
                    name
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups [
                    id,
                    name
                ]
            ]
        WHERE
            (User.groups.name != 'admin')
        """

    def test_graphql_translation_arguments08(self):
        r"""
        query @edgedb(module: "test") {
            User(groups__name__eq: "admin") {
                name,
                groups {
                    id
                    name
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups [
                    id,
                    name
                ]
            ]
        WHERE
            (User.groups.name = 'admin')
        """

    def test_graphql_translation_arguments09(self):
        r"""
        query @edgedb(module: "test") {
            User {
                name,
                groups {
                    id
                    name
                    settings(name__in: ["level", "description"]) {
                        name
                        value
                    }
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups [
                    id,
                    name,
                    (settings WHERE
                            (User.groups.settings.name IN
                                ('level', 'description'))) [
                        name,
                        value
                    ]
                ]
            ]
        """

    def test_graphql_translation_variables01(self):
        r"""
        query($name: String) @edgedb(module: "test") {
            User(name: $name) {
                name,
                groups {
                    id
                    name
                }
            }
        }

% OK %

        USING
            NAMESPACE test
        SELECT
            User[
                name,
                groups[
                    id,
                    name
                ]
            ]
        WHERE
            (User.name = $name)
        """