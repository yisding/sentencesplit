use sentencesplit_data::{built_in_codes, language, validate_regexes};

const EXPECTED_CODES: [&str; 26] = [
    "am", "ar", "bg", "da", "de", "el", "en", "en_es_zh", "en_legal", "es", "fa", "fr", "hi", "hy",
    "it", "ja", "kk", "mr", "my", "nl", "pl", "ru", "sk", "tl", "ur", "zh",
];

#[test]
fn embeds_every_built_in_language() {
    assert_eq!(built_in_codes(), EXPECTED_CODES);
}

#[test]
fn exposes_english_profile_values() {
    let english = language("en").expect("English exists");
    assert_eq!(english.iso_code, "en");
    assert!(english.latin_uppercase_resplit);
    assert_eq!(
        english.punctuations,
        ["。", "．", ".", "！", "!", "?", "？"].map(String::from)
    );
    assert_eq!(english.abbreviations.len(), 199);
    assert!(
        english
            .prepositive_abbreviations
            .contains(&String::from("adm"))
    );
    assert!(english.number_abbreviations.contains(&String::from("no")));
}

#[test]
fn unknown_language_returns_none() {
    assert!(language("xx").is_none());
}

#[test]
fn abbreviation_lists_are_canonical() {
    for code in built_in_codes() {
        let value = language(code).expect("known code");
        for list in [
            value.abbreviations,
            value.prepositive_abbreviations,
            value.number_abbreviations,
        ] {
            let mut sorted = list.to_vec();
            sorted.sort();
            sorted.dedup();
            assert_eq!(
                list,
                sorted.as_slice(),
                "{code} list is not sorted and unique"
            );
        }
    }
}

#[test]
fn all_shared_patterns_compile_in_fancy_regex() {
    validate_regexes().expect("all Python-source patterns compile");
}
