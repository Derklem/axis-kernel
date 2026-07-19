use serde_json::Value;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{self, Read};
use std::path::Path;
use std::fmt;

#[derive(Debug)]
pub enum CanonicalError {
    FloatDetected,
    IntegerOutOfRange,
}

impl fmt::Display for CanonicalError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CanonicalError::FloatDetected => write!(f, "Floating point numbers are prohibited in canonically hashed structures"),
            CanonicalError::IntegerOutOfRange => write!(f, "Integer outside safe interoperable bounds [-9007199254740991, 9007199254740991]"),
        }
    }
}

impl std::error::Error for CanonicalError {}

fn check_no_floats(value: &Value) -> Result<(), CanonicalError> {
    match value {
        Value::Number(n) => {
            if n.is_f64() {
                return Err(CanonicalError::FloatDetected);
            }
            if let Some(i) = n.as_i64() {
                if i < -9007199254740991 || i > 9007199254740991 {
                    return Err(CanonicalError::IntegerOutOfRange);
                }
            } else if let Some(u) = n.as_u64() {
                if u > 9007199254740991 {
                    return Err(CanonicalError::IntegerOutOfRange);
                }
            }
        }
        Value::Array(a) => {
            for v in a {
                check_no_floats(v)?;
            }
        }
        Value::Object(o) => {
            for v in o.values() {
                check_no_floats(v)?;
            }
        }
        _ => {}
    }
    Ok(())
}

/// Serializes a JSON Value into Canonical JSON.
pub fn serialize_canonical(value: &Value) -> Result<String, CanonicalError> {
    check_no_floats(value)?;
    Ok(serde_json::to_string(value).expect("Failed to serialize to canonical JSON"))
}

/// Computes the SHA-256 hash of a canonicalized JSON Value.
pub fn hash_json(value: &Value) -> Result<String, CanonicalError> {
    let canonical = serialize_canonical(value)?;
    let mut hasher = Sha256::new();
    hasher.update(canonical.as_bytes());
    Ok(hex::encode(hasher.finalize()))
}

/// Computes the SHA-256 hash of a file, chunking to handle large files.
pub fn hash_file<P: AsRef<Path>>(path: P) -> io::Result<String> {
    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = vec![0; 1024 * 1024]; // 1MB chunks on the heap

    loop {
        let count = file.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        hasher.update(&buffer[..count]);
    }

    Ok(hex::encode(hasher.finalize()))
}
