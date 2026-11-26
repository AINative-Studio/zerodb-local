use std::fs;
use std::path::Path;

fn main() {
    assert_package_json_version_matches_cargo_toml();
    tauri_build::build()
}

/// Refs #147: Cargo.toml's [package] version is the single source of
/// truth for the app version -- tauri.conf.json has no "version" field
/// of its own and falls back to reading Cargo.toml, and tray.rs reads it
/// via env!("CARGO_PKG_VERSION") at compile time. package.json is the
/// one remaining surface Cargo can't automatically keep in sync (it's
/// consumed by `npm run build`/`next build`, not by Cargo), so this
/// build-time check fails loudly on drift instead of letting it happen
/// silently again -- the exact failure mode this issue was filed for.
fn assert_package_json_version_matches_cargo_toml() {
    let cargo_version = env!("CARGO_PKG_VERSION");

    // desktop/src-tauri/build.rs -> desktop/package.json
    let package_json_path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("src-tauri has a parent directory")
        .join("package.json");

    let contents = fs::read_to_string(&package_json_path).unwrap_or_else(|e| {
        panic!(
            "Refs #147: could not read {} to verify its version matches Cargo.toml's {}: {}",
            package_json_path.display(),
            cargo_version,
            e
        )
    });

    let package_json_version = extract_json_string_field(&contents, "version").unwrap_or_else(|| {
        panic!(
            "Refs #147: {} has no top-level \"version\" field to compare against Cargo.toml's {}",
            package_json_path.display(),
            cargo_version
        )
    });

    assert_eq!(
        package_json_version, cargo_version,
        "Refs #147: version mismatch -- {}'s \"version\" is \"{}\" but Cargo.toml's \
         [package] version is \"{}\". Cargo.toml is the single source of truth for the \
         app version (tauri.conf.json and tray.rs both derive from it); update \
         package.json's \"version\" to match before building.",
        package_json_path.display(),
        package_json_version,
        cargo_version
    );
}

/// Minimal top-level "field": "value" extractor -- avoids pulling in a
/// JSON parsing crate as a build-dependency just to read one string
/// field out of package.json.
fn extract_json_string_field(json: &str, field: &str) -> Option<String> {
    let needle = format!("\"{field}\"");
    let field_pos = json.find(&needle)?;
    let after_field = &json[field_pos + needle.len()..];
    let colon_pos = after_field.find(':')?;
    let after_colon = after_field[colon_pos + 1..].trim_start();
    let value = after_colon.strip_prefix('"')?;
    let end_quote = value.find('"')?;
    Some(value[..end_quote].to_string())
}
