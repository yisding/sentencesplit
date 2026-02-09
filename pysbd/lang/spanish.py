# -*- coding: utf-8 -*-
from pysbd.abbreviation_replacer import AbbreviationReplacer
from pysbd.lang.common import Common, Standard

class Spanish(Common, Standard):

    iso_code = 'es'

    class AbbreviationReplacer(AbbreviationReplacer):
        SENTENCE_STARTERS = []

    class Abbreviation(Standard.Abbreviation):
        ABBREVIATIONS = ['a.c', 'a/c', 'abr', 'adj', 'admón', 'afmo', 'ago', 'almte', 'ap', 'apdo', 'arq', 'art', 'atte', 'av', 'avda', 'bco', 'bibl', 'bs. as', 'c', 'c.f', 'c.g', 'c/c', 'c/u', 'cap', 'cc.aa', 'cdad', 'cm', 'co', 'cra', 'cta', 'cv', 'd.e.p', 'da', 'dcha', 'dcho', 'dep', 'dic', 'dicc', 'dir', 'dn', 'doc', 'dom', 'dpto', 'dr', 'dra', 'dto', 'ee', 'ej', 'en', 'entlo', 'esq', 'etc', 'excmo', 'ext', 'f.c', 'fca', 'fdo', 'febr', 'ff. aa', 'ff.cc', 'fig', 'fil', 'fra', 'g.p', 'g/p', 'gob', 'gr', 'gral', 'grs', 'hnos', 'hs', 'igl', 'iltre', 'imp', 'impr', 'impto', 'incl', 'ing', 'inst', 'izdo', 'izq', 'izqdo', 'j.c', 'jue', 'jul', 'jun', 'kg', 'km', 'lcdo', 'ldo', 'let', 'lic', 'ltd', 'lun', 'mar', 'may', 'mg', 'min', 'mié', 'mm', 'máx', 'mín', 'mt', 'n. del t', 'n.b', 'no', 'nov', 'ntra. sra', 'núm', 'oct', 'p', 'p.a', 'p.d', 'p.ej', 'p.v.p', 'párrf', 'ph.d', 'ppal', 'prev', 'prof', 'prov', 'ptas', 'pts', 'pza', 'pág', 'págs', 'párr', 'q.e.g.e', 'q.e.p.d', 'q.e.s.m', 'reg', 'rep', 'rr. hh', 'rte', 's', 's. a', 's.a.r', 's.e', 's.l', 's.r.c', 's.r.l', 's.s.s', 's/n', 'sdad', 'seg', 'sept', 'sig', 'sr', 'sra', 'sres', 'srta', 'sta', 'sto', 'sáb', 't.v.e', 'tamb', 'tel', 'tfno', 'ud', 'uu', 'uds', 'univ', 'v.b', 'v.e', 'vd', 'vds', 'vid', 'vie', 'vol', 'vs', 'vto']
        PREPOSITIVE_ABBREVIATIONS = ['dr', 'ee', 'lic', 'mt', 'prof', 'sra', 'srta']
        NUMBER_ABBREVIATIONS = ['cra', 'ext', 'no', 'nos', 'p', 'pp', 'tel']
