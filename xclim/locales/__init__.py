# -*- coding: utf-8 -*-
"""xclim Internationalization module

Defines methods and object to help the internationalization of metadata for the
climate indicators computed by xclim.

All the methods and objects in this module use localization data given in json files.
These files are expected to be defined as in this example for french:

```json
{
    "attrs_mapping" : {
        "modifiers": ["", "_f", "_mpl", "_fpl"],
        "YS" : ["annuel", "annuelle", "annuels", "annuelles"],
        ... and so on for other frequent parameters translation...
    },
    "atmos.dtrvar" : {
        "long_name": "Variabilité de l'intervalle de température moyen",
        "description": "Variabilité {freq_f} de l'intervalle de température moyen."
    },
    ... and so on for other indicators...
}
```

Indicators are named by their module and identifier, which can differ from the callable name.
In this case, the indicator is called through `atmos.daily_temperature_range_variability`,
but its identifier is `dtrvar`.

Here, the usual parameter passed to the formatting of "description" is "freq" and is usually
translated from "YS" to "annual". However, in french and in this sentence, the feminine
form should be used, so the "_f" modifier is added by the translator so that the
formatting function knows which translation to use. Acceptable entries for the mappings
are limited to what is already defined in `xclim.utils.Indicator._attrs_mapping`.

The "attrs_mapping" and its key "modifiers" are mandatory in the locale dict, all other
entries (translations of frequent parameters and all indicator entries) are optional.

Attributes
----------
LOCALES : list
    List of currently set locales. Computing indicator through a xclim.utils.Indicator
    object will add metadata in these languages as available.
TRANSLATABLE_ATTRS : list
    List of attributes to consider translatable when generating locale dictionaries.
"""
import json
import warnings
from collections import UserString
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union

import pkg_resources

LOCALES = []
TRANSLATABLE_ATTRS = ["long_name", "description", "comment", "title"]


def list_locales():
    """Return a list of available locales in xclim."""
    locale_list = pkg_resources.resource_listdir(__package__, "")
    return [locale.split(".")[0] for locale in locale_list if locale.endswith(".json")]


def get_best_locale(locale: str):
    """Get the best fitting available locale.

    for existing locales : ['fr', 'fr-BE', 'en-US'],
    'fr-CA' returns 'fr', 'en' -> 'en-US' and 'en-GB' -> 'en-US'.

    Parameters
    ----------
    locale : str
        The requested locale, as an IETF language tag (lang or lang-territory)

    Returns
    -------
    str or None:
        The best available locale. None is none are available.
    """
    available = list_locales()
    if locale in available:
        return locale
    locale = locale.split("-")[0]
    if locale in available:
        return locale
    if locale in [av.split("-")[0] for av in available]:
        return [av for av in available if av.split("-")[0] == locale][0]
    return None


def get_local_dict(locale: Union[str, Sequence[str], Tuple[str, dict]]):
    """Return all translated metadata for a given locale.

    Parameters
    ----------
    locale : str or sequence of str
        IETF language tag or a tuple of the language tag and a translation dict, or
        a tuple of the language tag and a path to a json file defining translation
        of attributes.

    Raises
    ------
    UnavailableLocaleError
        If the given locale is not available.

    Returns
    -------
    str
        The best fitting locale string
    dict
        The available translations in this locale.
    """
    if isinstance(locale, str):
        locale = get_best_locale(locale)
        if locale is None:
            raise UnavailableLocaleError(locale)

        return (
            locale,
            json.load(pkg_resources.resource_stream(__package__, f"{locale}.json")),
        )
    if isinstance(locale[1], dict):
        return locale
    with open(locale[1]) as locf:
        return locale[0], json.load(locf)


class TranslatableStr(UserString):
    """A string that can to translate certain arguments passed to format()`.

    See the doc of format() for more details.
    """

    def __init__(
        self,
        string: str,
        translations: Mapping[str, Sequence[str]],
        modifiers: Sequence[str],
    ):
        """Initialize the translatable string.

        Parameters
        ----------
        string : str
            Data to potentatially translate.
        translations : Mapping[str, Sequence[str]]
            A mapping from a string to translate to its possible translations.
        modifiers : Sequence[str]
            The list of modifiers, must be the as long as the longest value of `translations`.
        """
        super().__init__(string)
        self.translations = translations
        self.modifiers = modifiers

    def format(self, *args, **kwargs):
        """Format the string by translating translatable arguments.

        Does the same as str.format(), but if any of the input
        keyword arguments is a translatable string (identified by braces { }),
        all possible translations are passed to the formatting. The keyword is
        removed from the arguments and replaces by all versions of `keyword` + `modifier`.

        Example
        -------
        Let's say the string "The dog is {adj1}, the goose is {adj2}" is to be translated
        to french and that we know that possible values of `adj` are `nice` and `evil`.
        In french, the genre of the noun changes the adjective (cat = chat is masculine,
        and goose = oie is feminine) so we initialize the string as:

        >>> s = TranslatableStr("Le chien est {adj1_m}, l'oie est {adj2_f}",
                                {'nice': ['beau', 'belle'], 'evil' : ['méchant', 'méchante']},
                                ['_m', '_f'])
        >>> s.format(adj1='{nice}', adj2='{evil}')
        "Le chien est beau, l'oie est méchante"

        `TranslatableStr.format()` saw that '{nice}' was translatable and added
        `adj1_m='beau', adj1_f='belle'` to the arguments passed to `str.format`.
        If a string is to be translate is has to be encapsulated in curly braces,
        or else it is given as is and the modifer it not applied:

        >>> s.format(adj1='nice', adj2=`evil`)
        "Le chien est nice, l'oie est evil"
        """
        if self.translations is not None:
            for key, val in kwargs.copy().items():
                if (
                    isinstance(val, str)
                    and val.startswith("{")
                    and val[1:-1] in self.translations
                ):
                    kwargs.update(
                        {
                            f"{key}{modifier}": value
                            for modifier, value in zip(
                                self.modifiers, self.translations[val[1:-1]]
                            )
                        }
                    )
        return super().format(*args, **kwargs)


def get_local_attrs(
    indicator: Any,
    *locales: Union[str, Sequence[str], Tuple[str, dict]],
    names: Optional[Sequence[str]] = None,
    fill_missing: bool = True,
    append_locale_name: bool = True,
):
    """Get all attributes of an indicator in the requested locales.

    Parameters
    ----------
    indicator : Union[utils.Indicator, utils.Indicator2D]
        Indicator object
    *locales : str
        IETF language tag or a tuple of the language tag and a translation dict, or
        a tuple of the language tag and a path to a json file defining translation
        of attributes. If none are given, defaults to the currently globally set in
        xclim.locales.LOCALES
    names : Optional[Sequence[str]]
        If given, only returns translations of attributes in this list.
    fill_missing : bool
        If True (default), fill untranslated attributes by the default (english) ones.
    append_locale_name : bool
        If True (default), append the language tag (as "{attr_name}_{locale}") to the
        returned attributes.

    Raises
    ------
    ValueError
        If `append_locale_name` is False and multiple `locales` are requested.
        .

    Returns
    -------
    dict
        All CF attributes available for given indicator and locales.
        Warns and returns an empty dict if none were available.
    """
    if not locales:
        locales = LOCALES

    if not append_locale_name and len(locales) > 1:
        raise ValueError(
            "`append_locale_name` cannot be False if multiple locales are requested."
        )

    attrs = {}
    for locale in locales:
        loc_name, loc_dict = get_local_dict(locale)
        loc_name = f"_{loc_name}" if append_locale_name else ""
        ind_name = f"{indicator.__module__.split('.')[1]}.{indicator.identifier}"
        local_attrs = loc_dict.get(ind_name)
        if local_attrs is None:
            warnings.warn(
                f"Attributes of indicator {ind_name} in language {locale} were requested, but none were found."
            )
        else:
            for name in TRANSLATABLE_ATTRS:
                if (names is None or name in names) and (
                    fill_missing or name in local_attrs
                ):
                    ind_dict = loc_dict["attrs_mapping"].copy()
                    mods = ind_dict.pop("modifiers", [""])
                    attrs[f"{name}{loc_name}"] = TranslatableStr(
                        local_attrs.get(name, getattr(indicator, name)), ind_dict, mods,
                    )
    return attrs


def set_locales(*locales: Union[str, Sequence[str], Tuple[str, dict]]):
    """Set the current locales.

    All indicators computed through atmos, land or seaIce will have additionnal metadata
    in the given languages, as available and defined in xclim.locales data files or in given file.

    Parameters
    ----------
    *locales : str or tuple of str
        IETF language tag or a tuple of the language tag and a translation dict, or
        a tuple of the language tag and a path to a json file defining translation
        of attributes.

    Raises
    ------
    UnavailableLocaleError
        If a requested locale is not available.
    """
    for locale in locales:
        if (isinstance(locale, str) and get_best_locale(locale) is None) or (
            not isinstance(locale, str)
            and isinstance(locale[1], str)
            and not Path(locale[1]).is_file()
        ):
            raise UnavailableLocaleError(locale)
    LOCALES[:] = locales


class metadata_locale:
    """Set a locale for the metadata output within a context.
    """

    def __init__(self, *locales: Union[str, Sequence[str], Tuple[str, dict]]):
        """Create the context object to manage locales.

        Parameters
        ----------
        **locales : str
            IETF language tag or a tuple of the language tag and a translation dict, or
            a tuple of the language tag and a path to a json file defining translation
            of attributes.

        Raises
        ------
        UnavailableLocaleError
            If a requested locale is not defined in `xclim.locales`.

        Examples
        --------
        >>> with metadata_locale("fr", "de"):
        >>>     gdd = atmos.growing_degree_days(ds.tas)  # Will be created with english, french and german metadata.
        >>> gdd = atmos.growing_degree_days(ds.tas)  # Will be created with english metadata only.
        """

        self.locales = locales

    def __enter__(self):
        self.old_locales = LOCALES[:]
        set_locales(*self.locales)

    def __exit__(self, type, value, traceback):
        set_locales(*self.old_locales)


class UnavailableLocaleError(ValueError):
    """Error raised when a locale is requested but doesn"t exist.
    """

    def __init__(self, locale):
        super().__init__(
            f"Locale {locale} not available. Use `xclim.locales.list_locales()` to see available languages."
        )


def generate_local_dict(locale: str, init_english: bool = False):
    """Generate a dictionary with keys for each indicators and translatable attributes.

    Parameters
    ----------
    locale : str
        Locale in the IETF format
    init_english : bool
        If True, fills the initial dictionary with the english versions of the attributes.
        Defaults to False.
    """
    import xclim as xc

    indicators = {}
    for module in [xc.atmos, xc.land, xc.seaIce]:
        for indicator in module.__dict__.values():
            if not isinstance(indicator, (xc.utils.Indicator, xc.utils.Indicator2D)):
                continue
            ind_name = f"{indicator.__module__.split('.')[1]}.{indicator.identifier}"
            indicators[ind_name] = indicator

    best_locale = get_best_locale(locale)
    if best_locale is not None:
        locname, attrs = get_local_dict(best_locale)
        for ind_name in attrs.copy().keys():
            if ind_name not in indicators:
                attrs.pop(ind_name)
    else:
        attrs = {}

    attrs_mapping = attrs.setdefault("attrs_mapping", {})
    attrs_mapping.setdefault("modifiers", [""])
    for key, value in xc.utils.Indicator._attrs_mapping.items():
        attrs_mapping.setdefault(key, [value])

    eng_attr = ""
    for ind_name, indicator in indicators.items():
        ind_attrs = attrs.setdefault(ind_name, {})
        for translatable_attr in TRANSLATABLE_ATTRS:
            if init_english:
                eng_attr = getattr(indicator, translatable_attr)
                if not isinstance(eng_attr, str):
                    eng_attr = ""
            ind_attrs.setdefault(f"{translatable_attr}", eng_attr)
    return attrs