# -*- coding: utf-8 -*-
from pysbd.abbreviation_replacer import AbbreviationReplacer
from pysbd.lang.common import Common, Standard
from pysbd.utils import Rule

class Spanish(Common, Standard):

    iso_code = 'es'

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = [
            'A', 'Al', 'Como', 'Con', 'De', 'El', 'Ella', 'En', 'Es', 'Esta', 'Esto',
            'Fue', 'La', 'Las', 'Lo', 'Los', 'No', 'Para', 'Por', 'Se', 'Su', 'Trabaja',
            'Un', 'Una', 'Y', 'Yo'
        ]
        SENTENCE_BOUNDARY_ABBREVIATIONS = AbbreviationReplacer.SENTENCE_BOUNDARY_ABBREVIATIONS + [
            'Ph∯D', 'Ph.D', 'M∯D', 'M.D', 'B∯A', 'B.A', 'B∯S', 'B.S', 'M∯A', 'M.A',
            'M∯B∯A', 'M.B.A'
        ]

    class AmPmRules(Common.AmPmRules):
        _TZ = Common.AmPmRules._TZ

        # Spaced AM/PM: replace periods in "a. m." / "p. m." with ∯
        SpacedLowerAmPeriodRule = Rule(r'(?<=\d )(a)\. (m)\.', r'\1∯ \2∯')
        SpacedLowerPmPeriodRule = Rule(r'(?<=\d )(p)\. (m)\.', r'\1∯ \2∯')
        SpacedUpperAmPeriodRule = Rule(r'(?<=\d )(A)\. (M)\.', r'\1∯ \2∯')
        SpacedUpperPmPeriodRule = Rule(r'(?<=\d )(P)\. (M)\.', r'\1∯ \2∯')

        # Sentence boundary restoration for spaced AM/PM followed by uppercase
        SpacedLowerAmBoundaryRule = Rule(r'(?<=a∯ m)∯(?=\s(?!' + _TZ + r')[A-Z])', '.')
        SpacedLowerPmBoundaryRule = Rule(r'(?<=p∯ m)∯(?=\s(?!' + _TZ + r')[A-Z])', '.')
        SpacedUpperAmBoundaryRule = Rule(r'(?<=A∯ M)∯(?=\s(?!' + _TZ + r')[A-Z])', '.')
        SpacedUpperPmBoundaryRule = Rule(r'(?<=P∯ M)∯(?=\s(?!' + _TZ + r')[A-Z])', '.')

        All = [
            # First: escape periods in spaced AM/PM
            SpacedLowerAmPeriodRule, SpacedLowerPmPeriodRule,
            SpacedUpperAmPeriodRule, SpacedUpperPmPeriodRule,
            # Then: standard AM/PM boundary rules (for compact form)
            *Common.AmPmRules.All,
            # Then: spaced AM/PM boundary rules
            SpacedLowerAmBoundaryRule, SpacedLowerPmBoundaryRule,
            SpacedUpperAmBoundaryRule, SpacedUpperPmBoundaryRule,
        ]

    class Abbreviation(Standard.Abbreviation):
        ABBREVIATIONS = ['a.c', 'a/c', 'abr', 'adj', 'admón', 'afmo', 'ago', 'almte', 'ap', 'apdo', 'arq', 'art', 'atte', 'av', 'avda', 'bco', 'bibl', 'bs. as', 'c', 'c.f', 'c.g', 'c/c', 'c/u', 'cap', 'cc.aa', 'cdad', 'cm', 'co', 'cra', 'cta', 'cv', 'd.e.p', 'da', 'dcha', 'dcho', 'dep', 'dic', 'dicc', 'dir', 'dn', 'doc', 'dom', 'dpto', 'dr', 'dra', 'dto', 'ee', 'ej', 'en', 'entlo', 'esq', 'etc', 'excmo', 'ext', 'f.c', 'fca', 'fdo', 'febr', 'ff. aa', 'ff.cc', 'fig', 'fil', 'fra', 'g.p', 'g/p', 'gob', 'gr', 'gral', 'grs', 'hnos', 'hs', 'igl', 'iltre', 'imp', 'impr', 'impto', 'incl', 'ing', 'inst', 'izdo', 'izq', 'izqdo', 'j.c', 'jue', 'jul', 'jun', 'kg', 'km', 'lcdo', 'ldo', 'let', 'lic', 'ltd', 'lun', 'mar', 'may', 'mg', 'min', 'mié', 'mm', 'máx', 'mín', 'mt', 'n. del t', 'n.b', 'no', 'nov', 'ntra. sra', 'núm', 'oct', 'p', 'p.a', 'p.d', 'p.ej', 'p.v.p', 'párrf', 'ph.d', 'ppal', 'prev', 'prof', 'prov', 'ptas', 'pts', 'pza', 'pág', 'págs', 'párr', 'q.e.g.e', 'q.e.p.d', 'q.e.s.m', 'reg', 'rep', 'rr. hh', 'rte', 's', 's. a', 's.a.r', 's.e', 's.l', 's.r.c', 's.r.l', 's.s.s', 's/n', 'sdad', 'seg', 'sept', 'sig', 'sr', 'sra', 'sres', 'srta', 'sta', 'sto', 'sáb', 't.v.e', 'tamb', 'tel', 'tfno', 'ud', 'uu', 'uds', 'univ', 'v.b', 'v.e', 'vd', 'vds', 'vid', 'vie', 'vol', 'vs', 'vto']
        PREPOSITIVE_ABBREVIATIONS = ['dr', 'ee', 'lic', 'mt', 'prof', 'sra', 'srta']
        NUMBER_ABBREVIATIONS = ['cra', 'ext', 'no', 'nos', 'p', 'pp', 'tel']
