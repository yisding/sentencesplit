use std::collections::{BTreeMap, HashMap};
use std::path::Path;
use std::sync::OnceLock;

use fancy_regex::Regex;
use serde::Deserialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct LanguageData<'a> {
    pub code: &'a str,
    pub iso_code: &'a str,
    pub punctuations: &'a [String],
    pub latin_uppercase_resplit: bool,
    pub abbreviations: &'a [String],
    pub prepositive_abbreviations: &'a [String],
    pub number_abbreviations: &'a [String],
}

#[derive(Debug, Deserialize)]
pub(crate) struct RawLanguageData {
    code: String,
    iso_code: String,
    punctuations: Vec<String>,
    latin_uppercase_resplit: bool,
    abbreviations: Vec<String>,
    prepositive_abbreviations: Vec<String>,
    number_abbreviations: Vec<String>,
    sentence_boundary_regex: String,
    quotation_end_regex: String,
    split_quotation_regex: String,
    parens_dq_regex: String,
    continuous_punct_regex: String,
    numbered_ref_regex: String,
    double_punct_regex: String,
    cjk_reporting_clause_regex: Option<String>,
}

pub(crate) fn load_language_data(
    directory: &Path,
) -> Result<BTreeMap<String, RawLanguageData>, DataError> {
    let mut languages = BTreeMap::new();
    for entry in directory
        .read_dir()
        .map_err(|error| DataError(format!("cannot read {}: {error}", directory.display())))?
    {
        let path = entry.map_err(|error| DataError(error.to_string()))?.path();
        if path.extension().is_none_or(|extension| extension != "json") {
            continue;
        }
        let source = std::fs::read_to_string(&path)
            .map_err(|error| DataError(format!("cannot read {}: {error}", path.display())))?;
        let language: RawLanguageData = serde_json::from_str(&source)
            .map_err(|error| DataError(format!("invalid {}: {error}", path.display())))?;
        if language.code
            != path
                .file_stem()
                .and_then(|stem| stem.to_str())
                .unwrap_or_default()
        {
            return Err(DataError(format!(
                "language code does not match {}",
                path.display()
            )));
        }
        let duplicate = languages.insert(language.code.clone(), language).is_some();
        if duplicate {
            return Err(DataError("duplicate language code".to_string()));
        }
    }
    if languages.is_empty() {
        return Err(DataError("no language data found".to_string()));
    }
    Ok(languages)
}

fn embedded_languages() -> &'static BTreeMap<String, RawLanguageData> {
    static LANGUAGES: OnceLock<BTreeMap<String, RawLanguageData>> = OnceLock::new();
    LANGUAGES.get_or_init(|| {
        load_language_data(Path::new(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../data/lang"
        )))
        .expect("embedded language data is valid")
    })
}

pub fn built_in_codes() -> Vec<&'static str> {
    embedded_languages().keys().map(String::as_str).collect()
}

pub fn language(code: &str) -> Option<LanguageData<'static>> {
    let value = embedded_languages().get(code)?;
    Some(LanguageData {
        code: &value.code,
        iso_code: &value.iso_code,
        punctuations: &value.punctuations,
        latin_uppercase_resplit: value.latin_uppercase_resplit,
        abbreviations: &value.abbreviations,
        prepositive_abbreviations: &value.prepositive_abbreviations,
        number_abbreviations: &value.number_abbreviations,
    })
}

pub(crate) fn raw_language(code: &str) -> Option<&'static RawLanguageData> {
    embedded_languages().get(code)
}

fn compiled_regex(code: &str, kind: &str) -> Result<&'static Regex, DataError> {
    static REGEXES: OnceLock<HashMap<&'static str, Regex>> = OnceLock::new();
    let regexes = REGEXES.get_or_init(|| {
        HashMap::from_iter(embedded_languages().values().flat_map(|language| {
            [
                (
                    "sentence_boundary",
                    language.sentence_boundary_regex.as_str(),
                ),
                ("quotation_end", language.quotation_end_regex.as_str()),
                ("split_quotation", language.split_quotation_regex.as_str()),
                ("parens_dq", language.parens_dq_regex.as_str()),
                ("continuous_punct", language.continuous_punct_regex.as_str()),
                ("numbered_ref", language.numbered_ref_regex.as_str()),
                ("double_punct", language.double_punct_regex.as_str()),
                (
                    "cjk_reporting_clause",
                    language.cjk_reporting_clause_regex.as_deref().unwrap_or(""),
                ),
            ]
            .into_iter()
            .filter(|(_, pattern)| !pattern.is_empty())
            .map(move |(kind, pattern)| {
                (
                    format!("{}/{}", language.code, kind).leak() as &'static str,
                    Regex::new(pattern).unwrap(),
                )
            })
        }))
    });
    let key = format!("{code}/{kind}");
    match regexes.get(key.as_str()) {
        Some(regex) => Ok(regex),
        None => Err(DataError(format!("unknown regex {key}"))),
    }
}

/// Compile every embedded boundary regex, proving that the shared Python-source
/// patterns are valid for the Rust engine selected by the port plan.
pub fn validate_regexes() -> Result<(), DataError> {
    const KINDS: [&str; 8] = [
        "sentence_boundary",
        "quotation_end",
        "split_quotation",
        "parens_dq",
        "continuous_punct",
        "numbered_ref",
        "double_punct",
        "cjk_reporting_clause",
    ];
    for code in built_in_codes() {
        for kind in KINDS {
            if raw_language(code).is_some_and(|language| {
                kind != "cjk_reporting_clause" || language.cjk_reporting_clause_regex.is_some()
            }) {
                compiled_regex(code, kind)?;
            }
        }
    }
    Ok(())
}

#[derive(Debug, PartialEq, Eq)]
pub struct DataError(pub String);

impl std::fmt::Display for DataError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

impl std::error::Error for DataError {}
