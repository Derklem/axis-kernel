use anyhow::Result;
use clap::Parser;
use jsonschema::JSONSchema;
use serde_json::Value;
use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

mod canonical;
use canonical::{hash_file, hash_json};

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    run_id: String,

    #[arg(long, default_value = "data/ledger")]
    ledger_dir: PathBuf,

    #[arg(long, default_value = "data/runs")]
    runs_dir: PathBuf,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Status {
    Pass,
    Unverifiable,
    Fail,
}

impl Status {
    fn as_str(&self) -> &'static str {
        match self {
            Status::Pass => "PASS",
            Status::Unverifiable => "UNVERIFIABLE",
            Status::Fail => "FAIL",
        }
    }
}

struct VerifierState {
    checks: Vec<Value>,
    overall: Status,
    run_id: String,
}

impl VerifierState {
    fn new(run_id: String) -> Self {
        Self {
            checks: Vec::new(),
            overall: Status::Pass,
            run_id,
        }
    }

    fn add_check(&mut self, name: &str, status: Status, expected: Option<Value>, observed: Option<Value>) {
        let mut check = serde_json::json!({
            "name": name,
            "status": status.as_str()
        });
        if let Some(exp) = expected {
            check.as_object_mut().unwrap().insert("expected".to_string(), exp);
        }
        if let Some(obs) = observed {
            check.as_object_mut().unwrap().insert("observed".to_string(), obs);
        }
        self.checks.push(check);

        // FAIL > UNVERIFIABLE > PASS
        match (self.overall, status) {
            (Status::Pass, Status::Unverifiable) => self.overall = Status::Unverifiable,
            (_, Status::Fail) => self.overall = Status::Fail,
            _ => {}
        }
    }

    fn to_report(&self) -> Value {
        serde_json::json!({
            "run_id": self.run_id,
            "overall_status": self.overall.as_str(),
            "checks": self.checks
        })
    }
}

fn get_schema(name: &str) -> Option<JSONSchema> {
    let s = match name {
        "event_schema.json" => include_str!("../../laboratory/schemas/event_schema.json"),
        "receipt.json" => include_str!("../../laboratory/schemas/receipt.json"),
        "experiment.json" => include_str!("../../laboratory/schemas/experiment.json"),
        _ => return None,
    };
    let v: Value = serde_json::from_str(s).unwrap_or_else(|_| {
        eprintln!("Failed to parse schema {}", name);
        std::process::exit(2);
    });
    Some(JSONSchema::compile(&v).unwrap_or_else(|_| {
        eprintln!("Failed to compile schema {}", name);
        std::process::exit(2);
    }))
}

fn get_files_recursively(dir: &Path) -> HashSet<String> {
    let mut files = HashSet::new();
    if !dir.exists() {
        return files;
    }
    for entry in WalkDir::new(dir).into_iter().filter_map(|e| e.ok()) {
        if entry.file_type().is_file() {
            let rel_path = entry.path().strip_prefix(dir).unwrap();
            let mut posix_path = String::new();
            for comp in rel_path.components() {
                if !posix_path.is_empty() {
                    posix_path.push('/');
                }
                posix_path.push_str(&comp.as_os_str().to_string_lossy());
            }
            files.insert(posix_path);
        }
    }
    files
}

fn run_verification(args: &Args) -> Value {
    let mut state = VerifierState::new(args.run_id.clone());

    // 1. ledger_load
    let ledger_file = args.ledger_dir.join("ledger.jsonl");
    if !ledger_file.exists() {
        state.add_check("ledger_load", Status::Unverifiable, None, None);
        return state.to_report();
    }

    let mut events = Vec::new();
    if let Ok(content) = fs::read_to_string(&ledger_file) {
        let mut ok = true;
        for line in content.lines() {
            let line = line.trim();
            if !line.is_empty() {
                if let Ok(val) = serde_json::from_str::<Value>(line) {
                    events.push(val);
                } else {
                    ok = false;
                    break;
                }
            }
        }
        if ok {
            state.add_check("ledger_load", Status::Pass, None, None);
        } else {
            state.add_check("ledger_load", Status::Fail, None, None);
            return state.to_report();
        }
    } else {
        state.add_check("ledger_load", Status::Fail, None, None);
        return state.to_report();
    }

    // 2. ledger_chain
    let event_schema = get_schema("event_schema.json");
    let mut expected_seq = 0;
    let mut expected_prev_hash = Value::Null;
    let mut chain_valid = true;

    for (idx, event) in events.iter().enumerate() {
        if let Some(ref schema) = event_schema {
            if let Err(_) = schema.validate(event) {
                state.add_check("ledger_chain", Status::Fail, None, None);
                chain_valid = false;
                break;
            }
        }

        if event["sequence"] != expected_seq {
            state.add_check("ledger_chain", Status::Fail, Some(serde_json::json!(expected_seq)), Some(event["sequence"].clone()));
            chain_valid = false;
            break;
        }

        if event["previous_hash"] != expected_prev_hash {
            state.add_check("ledger_chain", Status::Fail, Some(expected_prev_hash.clone()), Some(event["previous_hash"].clone()));
            chain_valid = false;
            break;
        }

        let mut test_event = event.clone();
        let stored_hash = test_event.as_object_mut().unwrap().remove("hash").unwrap_or(Value::Null);
        let recomputed = match hash_json(&test_event) {
            Ok(h) => h,
            Err(_) => {
                state.add_check("ledger_chain", Status::Fail, None, None);
                chain_valid = false;
                break;
            }
        };
        if stored_hash.as_str().unwrap_or("") != recomputed {
            state.add_check("ledger_chain", Status::Fail, Some(stored_hash), Some(serde_json::json!(recomputed)));
            chain_valid = false;
            break;
        }

        expected_prev_hash = Value::String(recomputed);
        expected_seq += 1;
    }

    if chain_valid {
        state.add_check("ledger_chain", Status::Pass, None, None);
    } else {
        return state.to_report();
    }

    // 3. run_started_event
    let starts: Vec<&Value> = events.iter().filter(|e| {
        e["event_type"] == "RUN_STARTED" && e["payload"]["run_id"] == args.run_id
    }).collect();

    if starts.len() != 1 {
        state.add_check("run_started_event", if starts.is_empty() { Status::Unverifiable } else { Status::Fail }, Some(serde_json::json!(1)), Some(serde_json::json!(starts.len())));
        return state.to_report();
    }
    let start_event = starts[0];
    state.add_check("run_started_event", Status::Pass, None, None);

    // 4. terminal_event
    let terminals: Vec<&Value> = events.iter().filter(|e| {
        let ty = e["event_type"].as_str().unwrap_or("");
        (ty == "RUN_COMPLETED" || ty == "RUN_FAILED" || ty == "RUN_ABORTED") && e["payload"]["run_id"] == args.run_id
    }).collect();

    if terminals.len() != 1 {
        state.add_check("terminal_event", if terminals.is_empty() { Status::Unverifiable } else { Status::Fail }, Some(serde_json::json!(1)), Some(serde_json::json!(terminals.len())));
        return state.to_report();
    }
    let term_event = terminals[0];
    state.add_check("terminal_event", Status::Pass, None, None);

    // 5. terminal_event_sequence
    if term_event["sequence"].as_u64().unwrap_or(0) <= start_event["sequence"].as_u64().unwrap_or(0) {
        state.add_check("terminal_event_sequence", Status::Fail, None, None);
    } else {
        state.add_check("terminal_event_sequence", Status::Pass, None, None);
    }

    let run_dir = args.runs_dir.join(&args.run_id);
    let receipt_path = run_dir.join("receipt.json");
    
    // 6. receipt_presence
    if !receipt_path.exists() {
        state.add_check("receipt_presence", Status::Unverifiable, None, None);
        return state.to_report();
    }
    let receipt_str = fs::read_to_string(&receipt_path).unwrap_or_default();
    let receipt: Value = match serde_json::from_str(&receipt_str) {
        Ok(v) => v,
        Err(_) => {
            state.add_check("receipt_presence", Status::Fail, None, None);
            return state.to_report();
        }
    };
    state.add_check("receipt_presence", Status::Pass, None, None);

    // 7. receipt_schema
    let receipt_schema = get_schema("receipt.json");
    if let Some(ref schema) = receipt_schema {
        if let Err(_) = schema.validate(&receipt) {
            state.add_check("receipt_schema", Status::Fail, None, None);
            return state.to_report();
        }
    }
    state.add_check("receipt_schema", Status::Pass, None, None);

    // 8. receipt_hash
    let recomputed_receipt_hash = match hash_json(&receipt) {
        Ok(h) => h,
        Err(_) => {
            state.add_check("receipt_hash", Status::Fail, None, None);
            return state.to_report();
        }
    };
    let expected_receipt_hash = term_event["payload"]["receipt_hash"].as_str().unwrap_or("");
    if expected_receipt_hash != recomputed_receipt_hash {
        state.add_check("receipt_hash", Status::Fail, Some(serde_json::json!(expected_receipt_hash)), Some(serde_json::json!(recomputed_receipt_hash)));
    } else {
        state.add_check("receipt_hash", Status::Pass, None, None);
    }

    // 9. run_started_link
    let run_started_hash = start_event["hash"].as_str().unwrap_or("");
    if receipt["run_started_hash"].as_str().unwrap_or("") != run_started_hash {
        state.add_check("run_started_link", Status::Fail, Some(serde_json::json!(run_started_hash)), Some(receipt["run_started_hash"].clone()));
    } else {
        state.add_check("run_started_link", Status::Pass, None, None);
    }

    // 10. experiment_presence
    let exp_path = run_dir.join("experiment.json");
    if !exp_path.exists() {
        state.add_check("experiment_presence", Status::Unverifiable, None, None);
        return state.to_report();
    }
    let exp_str = fs::read_to_string(&exp_path).unwrap_or_default();
    let experiment: Value = match serde_json::from_str(&exp_str) {
        Ok(v) => v,
        Err(_) => {
            state.add_check("experiment_presence", Status::Fail, None, None);
            return state.to_report();
        }
    };
    state.add_check("experiment_presence", Status::Pass, None, None);

    // 11. experiment_schema
    let exp_schema = get_schema("experiment.json");
    if let Some(ref schema) = exp_schema {
        if let Err(_) = schema.validate(&experiment) {
            state.add_check("experiment_schema", Status::Fail, None, None);
            return state.to_report();
        }
    }
    state.add_check("experiment_schema", Status::Pass, None, None);

    // 12. experiment_hash
    let recomputed_exp_hash = match hash_json(&experiment) {
        Ok(h) => h,
        Err(_) => {
            state.add_check("experiment_hash", Status::Fail, None, None);
            return state.to_report();
        }
    };
    let receipt_exp_hash = receipt["experiment_hash"].as_str().unwrap_or("");
    if receipt_exp_hash != recomputed_exp_hash {
        state.add_check("experiment_hash", Status::Fail, Some(serde_json::json!(receipt_exp_hash)), Some(serde_json::json!(recomputed_exp_hash)));
    } else {
        state.add_check("experiment_hash", Status::Pass, None, None);
    }

    // 13. start_experiment_hash
    let start_exp_hash = start_event["payload"]["experiment_hash"].as_str().unwrap_or("");
    if start_exp_hash != recomputed_exp_hash {
        state.add_check("start_experiment_hash", Status::Fail, Some(serde_json::json!(start_exp_hash)), Some(serde_json::json!(recomputed_exp_hash)));
    } else {
        state.add_check("start_experiment_hash", Status::Pass, None, None);
    }

    // 14. inputs_manifest
    let inputs_dir = run_dir.join("inputs");
    let actual_inputs = get_files_recursively(&inputs_dir);
    let mut expected_inputs = HashSet::new();
    let mut inputs_ok = true;

    if let Some(map) = receipt["inputs"].as_object() {
        for (k, v) in map {
            expected_inputs.insert(k.clone());
            let expected_h = v.get("hash").and_then(|h| h.as_str()).unwrap_or("");
            let expected_s = v.get("size").and_then(|s| s.as_u64()).unwrap_or(0);
            let file_path = inputs_dir.join(k);
            
            if let Ok(metadata) = fs::metadata(&file_path) {
                if metadata.len() != expected_s {
                    inputs_ok = false;
                }
            } else {
                inputs_ok = false;
            }

            if let Ok(h) = hash_file(&file_path) {
                if h != expected_h {
                    inputs_ok = false;
                }
            } else {
                inputs_ok = false;
            }
        }
    }
    if actual_inputs != expected_inputs || !inputs_ok {
        state.add_check("inputs_manifest", Status::Fail, None, None);
    } else {
        state.add_check("inputs_manifest", Status::Pass, None, None);
    }

    // 15. artifacts_manifest
    let artifacts_dir = run_dir.join("artifacts");
    let actual_artifacts = get_files_recursively(&artifacts_dir);
    let mut expected_artifacts = HashSet::new();
    let mut artifacts_ok = true;

    if let Some(map) = receipt["artifacts"].as_object() {
        for (k, v) in map {
            expected_artifacts.insert(k.clone());
            let expected_h = v.as_str().unwrap_or("");
            let file_path = artifacts_dir.join(k);
            if let Ok(h) = hash_file(&file_path) {
                if h != expected_h {
                    artifacts_ok = false;
                }
            } else {
                artifacts_ok = false;
            }
        }
    }
    if actual_artifacts != expected_artifacts || !artifacts_ok {
        state.add_check("artifacts_manifest", Status::Fail, None, None);
    } else {
        state.add_check("artifacts_manifest", Status::Pass, None, None);
    }

    // 16. stdout_hash
    let stdout_path = run_dir.join("stdout.txt");
    let expected_stdout = receipt["execution"]["stdout_hash"].as_str().unwrap_or("");
    let actual_stdout = hash_file(&stdout_path).unwrap_or_else(|_| "".to_string());
    if actual_stdout != expected_stdout {
        state.add_check("stdout_hash", Status::Fail, Some(serde_json::json!(expected_stdout)), Some(serde_json::json!(actual_stdout)));
    } else {
        state.add_check("stdout_hash", Status::Pass, None, None);
    }

    // 17. stderr_hash
    let stderr_path = run_dir.join("stderr.txt");
    let expected_stderr = receipt["execution"]["stderr_hash"].as_str().unwrap_or("");
    let actual_stderr = hash_file(&stderr_path).unwrap_or_else(|_| "".to_string());
    if actual_stderr != expected_stderr {
        state.add_check("stderr_hash", Status::Fail, Some(serde_json::json!(expected_stderr)), Some(serde_json::json!(actual_stderr)));
    } else {
        state.add_check("stderr_hash", Status::Pass, None, None);
    }

    state.to_report()
}

fn main() {
    let args = Args::parse();
    let report = run_verification(&args);
    
    let json_output = serde_json::to_string_pretty(&report).unwrap();
    println!("{}", json_output);
    
    let status = report["overall_status"].as_str().unwrap();
    match status {
        "PASS" => std::process::exit(0),
        "FAIL" => std::process::exit(1),
        "UNVERIFIABLE" => std::process::exit(3),
        _ => std::process::exit(2),
    }
}
