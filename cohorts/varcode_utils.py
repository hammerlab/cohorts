from varcode import EffectCollection, VariantCollection

def filter_variants_with_metadata(variant_collection, filter_fn):
    """Filter variants from the Variant Collection

    Parameters
    ----------
    variant_collection : varcode.VariantCollection
    filter_fn: function
        Takes a variant and it's metadata and returns a boolean. Only variants returning True are preserved.

    Returns
    -------
    varcode.VariantCollection
        Filtered variant collection, with only the variants passing the filter
    """
    if filter_fn:
        return VariantCollection([variant
                                  for variant in variant_collection
                                  if filter_fn(variant, variant_collection.metadata[variant])
                                  ],
                                 metadata=variant_collection.metadata)
    else:
        return variant_collection

def filter_effects_with_metadata(effect_collection, variant_collection_metadata, filter_fn):
    """Filter variants from the Effect Collection

    Parameters
    ----------
    effect_collection : varcode.EffectCollection
    filter_fn: function
        Takes an effect and it's variant's metadata and returns a boolean. Only effects returning True are preserved.

    Returns
    -------
    varcode.EffectCollection
        Filtered effect collection, with only the variants passing the filter
    """
    if filter_fn:
        return EffectCollection([effect
                                  for effect in effect_collection
                                  if filter_fn(effect, variant_collection_metadata[effect.variant])
                                  ])
    else:
        return effect_collection

def filter_neoantigens_with_metadata(neoantigens_df, variants, filter_fn):
    if filter_fn:
        filter_mask = neoantigens_df.apply(
            lambda row: filter_fn(row, variants), axis=1)
        return neoantigens_df[filter_mask]
    else:
        return neoantigens_df

def filter_polyphen_with_metadata(annotations_df, variants, filter_fn):
    if filter_fn:
        filter_mask = annotations_df.apply(
            lambda row: filter_fn(row, variants), axis=1)
        return annotations_df[filter_mask]
    else:
        return annotations_df
