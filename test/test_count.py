# Copyright (c) 2016. Mount Sinai School of Medicine
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

from varcode import ExonicSpliceSite, Substitution, Variant, VariantCollection

from .data_generate import generate_vcfs
from .functions import *

from nose.tools import raises, eq_, ok_
from mock import MagicMock
from os import path
from shutil import rmtree

from .test_basic import make_simple_cohort

FILE_FORMAT_1 = "patient_format1_%s.vcf"
FILE_FORMAT_2 = "patient_format2_%s.vcf"
FILE_FORMAT_3 = "patient_format3_%s.vcf"

def make_cohort(file_formats, merge_type="union"):
    cohort = make_simple_cohort(merge_type=merge_type)
    patient_ids = [patient.id for patient in cohort]
    vcf_dir = generate_vcfs(id_to_mutation_count=dict(zip(patient_ids, [3, 3, 6])),
                            file_format=FILE_FORMAT_1,
                            template_name="vcf_template_1.vcf")
    _ = generate_vcfs(id_to_mutation_count=dict(zip(patient_ids, [4, 1, 5])),
                      file_format=FILE_FORMAT_2,
                      template_name="vcf_template_1.vcf")
    _ = generate_vcfs(id_to_mutation_count=dict(zip(patient_ids, [5, 2, 3])),
                      file_format=FILE_FORMAT_3,
                      template_name="vcf_template_2.vcf")
    for patient in cohort:
        vcf_paths = []
        for file_format in file_formats:
            vcf_filename = (file_format % patient.id)
            vcf_path = path.join(vcf_dir, vcf_filename)
            vcf_paths.append(vcf_path)
        patient.snv_vcf_paths = vcf_paths
    return vcf_dir, cohort

def test_snv_counts():
    """
    Generate VCFs per-sample, and confirm that the counting functions work as expected.
    """
    vcf_dir, cohort = None, None
    try:
        # Use all three VCF sources
        vcf_dir, cohort = make_cohort([FILE_FORMAT_1])

        # The SNV count should be exactly what we generated
        count_col, df = cohort.as_dataframe(snv_count)
        eq_(len(df), 3)
        eq_(list(df[count_col]), [3, 3, 6])

        count_col, df = cohort.as_dataframe(missense_snv_count)
        eq_(len(df), 3)
        eq_(list(df[count_col]), [2, 2, 4])
    finally:
        if vcf_dir is not None and path.exists(vcf_dir):
            rmtree(vcf_dir)
        if cohort is not None:
            cohort.clear_caches()

def test_merge_three():
    """
    Generate three VCFs per-sample and confirm that merging works as expected.
    """
    vcf_dir, cohort = None, None
    try:
        # Use all three VCF sources
        vcf_dir, cohort = make_cohort([FILE_FORMAT_1, FILE_FORMAT_2, FILE_FORMAT_3],
                                      merge_type="union")

        # [3, 3, 6] and [4, 1, 5] use the same template, resulting in a union of [4, 3, 6] unique variants
        # [5, 2, 3] uses a separate template, resulting in a union of [4, 3, 6] + [5, 2, 3] = [9, 5, 9] unique variants
        count_col, df = cohort.as_dataframe(snv_count)
        eq_(len(df), 3)
        eq_(list(df[count_col]), [9, 5, 9])

        # For intersection, variants need to appear in *all*, here. None of them do.
        vcf_dir, cohort = make_cohort([FILE_FORMAT_1, FILE_FORMAT_2, FILE_FORMAT_3],
                                      merge_type="intersection")
        count_col, df = cohort.as_dataframe(snv_count)
        eq_(list(df[count_col]), [0, 0, 0])
    finally:
        if vcf_dir is not None and path.exists(vcf_dir):
            rmtree(vcf_dir)
        if cohort is not None:
            cohort.clear_caches()

def test_merge_two():
    """
    Generate two VCFs per-sample and confirm that merging works as expected.
    """
    vcf_dir, cohort = None, None
    try:
        # Now, with only two VCF sources
        vcf_dir, cohort = make_cohort([FILE_FORMAT_1, FILE_FORMAT_2],
                                      merge_type="union")

        # [3, 3, 6] and [4, 1, 5] use the same template, resulting in a union of [4, 3, 6] unique variants
        count_col, df = cohort.as_dataframe(snv_count)
        eq_(len(df), 3)
        eq_(list(df[count_col]), [4, 3, 6])

        # For intersection, some variants do appear in both.
        vcf_dir, cohort = make_cohort([FILE_FORMAT_1, FILE_FORMAT_2],
                                      merge_type="intersection")
        count_col, df = cohort.as_dataframe(snv_count)
        eq_(len(df), 3)
        eq_(list(df[count_col]), [3, 1, 5])

        cohort_variants = cohort.load_variants(filter_fn=None)
        for (sample, variants) in cohort_variants.items():
            for variant in variants:
                metadata = variants.metadata[variant]
                eq_(len(metadata), 2) # Each variant has two metadata entries

    finally:
        if vcf_dir is not None and path.exists(vcf_dir):
            rmtree(vcf_dir)
        if cohort is not None:
            cohort.clear_caches()

def test_filter_variants():
    vcf_dir, cohort = None, None
    try:
        vcf_dir, cohort = make_cohort([FILE_FORMAT_1, FILE_FORMAT_2])

        def filter_g_variants(filterable_variant):
            return filterable_variant.variant.ref == 'G'
        g_variants = {'1': 2, '4': 1, '5': 3}

        cohort_variants = cohort.load_variants(filter_fn=filter_g_variants)

        for (sample, variants) in cohort_variants.items():
            eq_(len(variants), g_variants[sample])

    finally:
        if vcf_dir is not None and path.exists(vcf_dir):
            rmtree(vcf_dir)
        if cohort is not None:
            cohort.clear_caches()

def test_filter_effects():
    vcf_dir, cohort = None, None
    try:
        vcf_dir, cohort = make_cohort([FILE_FORMAT_1])

        def filter_substitution_effects(filterable_effect):
            return type(filterable_effect.effect) == Substitution
        missense_counts = {'1': 2, '4': 2, '5': 4}

        cohort_effects = cohort.load_effects(only_nonsynonymous=True, filter_fn=filter_substitution_effects)
        for (sample, effects) in cohort_effects.items():
            eq_(len(effects), missense_counts[sample])

        def filter_exonic_splice_site_effects(filterable_effect):
            return type(filterable_effect.effect) == ExonicSpliceSite
        splice_site_counts = {'1': 1, '4': 1, '5': 2}

        cohort_effects = cohort.load_effects(only_nonsynonymous=True, filter_fn=filter_exonic_splice_site_effects)
        for (sample, effects) in cohort_effects.items():
            eq_(len(effects), splice_site_counts[sample])

    finally:
        if vcf_dir is not None and path.exists(vcf_dir):
            rmtree(vcf_dir)
        if cohort is not None:
            cohort.clear_caches()

def test_multiple_effects():
    """
    Make sure variants are not double counted when multiple effects exist.
    """
    cohort = None
    try:
        cohort = make_simple_cohort(merge_type="snv")
        """
        <EffectCollection with 2 elements>
        -- StopLoss(variant=chr1 g.46501738G>C, transcript_name=MAST2-001, transcript_id=ENST00000361297, effect_description=p.*1799Y (stop-loss))
        -- StopLoss(variant=chr1 g.46501738G>C, transcript_name=MAST2-201, transcript_id=ENST00000372009, effect_description=p.*1609Y (stop-loss))
        """
        variants = VariantCollection([Variant("1", 46501738, "G", "C", ensembl=75)])
        effects = variants.effects()
        effects_dict = {}
        for patient in cohort:
            effects_dict[patient.id] = effects
        cohort.load_effects = MagicMock(return_value=effects_dict)
        col_nonsyn, df_nonsyn = cohort.as_dataframe(nonsynonymous_snv_count)
        col_missense, df_missense = cohort.as_dataframe(missense_snv_count)
        ok_((df_missense[col_missense] == 1).all(),
            "Variant should only be counted once for each patient, but: %s" % df_missense[col_missense])
        ok_((df_nonsyn[col_nonsyn] == 1).all(),
            "Variant should only be counted once for each patient, but: %s" % df_nonsyn[col_nonsyn])
    finally:
        if cohort is not None:
            cohort.clear_caches()
