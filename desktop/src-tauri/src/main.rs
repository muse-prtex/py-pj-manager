// PJマネージャー Desktop (Tauri) — モダンUIシェル。
//
// ロジックは持たない。Python コア（pj_manager.cli --json）を子プロセスで
// 呼び、その結果を描画するだけ。CLI は GUI / エージェント / この画面の
// 共通インターフェース。
//
// pj_manager の場所の探し方（先勝ち）:
//   1. 環境変数 PJ_MANAGER_SRC（src フォルダへのパス）
//   2. 実行ファイルと同じフォルダ・親方向の src/
//   3. カレントディレクトリの src/
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use std::process::Command;

fn find_src() -> Option<PathBuf> {
    let mut candidates: Vec<PathBuf> = Vec::new();
    if let Ok(v) = std::env::var("PJ_MANAGER_SRC") {
        if !v.is_empty() {
            candidates.push(PathBuf::from(v));
        }
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            candidates.push(dir.join("src"));
            candidates.push(dir.join("../src"));
            candidates.push(dir.join("../../src"));
            candidates.push(dir.join("../../../src"));
        }
    }
    if let Ok(cwd) = std::env::current_dir() {
        candidates.push(cwd.join("src"));
    }
    candidates
        .into_iter()
        .find(|p| p.join("pj_manager").join("cli.py").exists())
}

fn python_cmd() -> &'static str {
    if cfg!(windows) {
        "py"
    } else {
        "python3"
    }
}

/// pj_manager.cli を --json で実行し、JSON をそのまま返す。
#[tauri::command]
fn pj(args: Vec<String>) -> Result<serde_json::Value, String> {
    let src = find_src().ok_or_else(|| {
        "pj_manager の場所が見つかりません。PJ_MANAGER_SRC 環境変数で src フォルダを指定してください。"
            .to_string()
    })?;
    let mut cmd = Command::new(python_cmd());
    cmd.arg("-m")
        .arg("pj_manager.cli")
        .args(&args)
        .arg("--json")
        .env("PYTHONPATH", &src)
        .env("PYTHONUTF8", "1");
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
    }
    let out = cmd
        .output()
        .map_err(|e| format!("Python を起動できませんでした: {e}"))?;
    let text = String::from_utf8_lossy(&out.stdout).to_string();
    serde_json::from_str(&text)
        .map_err(|e| format!("CLI の出力を読めませんでした: {e}\n{text}"))
}

/// ターミナル / VS Code / フォルダ / GitHub を開く（OS 側の操作）。
#[tauri::command]
fn open_target(kind: String, path: String) -> Result<(), String> {
    let p = PathBuf::from(&path);
    match kind.as_str() {
        "folder" => {
            #[cfg(windows)]
            Command::new("explorer").arg(&path).spawn().map_err(|e| e.to_string())?;
            #[cfg(target_os = "macos")]
            Command::new("open").arg(&path).spawn().map_err(|e| e.to_string())?;
            #[cfg(all(unix, not(target_os = "macos")))]
            Command::new("xdg-open").arg(&path).spawn().map_err(|e| e.to_string())?;
            Ok(())
        }
        "vscode" => {
            Command::new("code").arg(&path).spawn().map_err(|e| e.to_string())?;
            Ok(())
        }
        "terminal" => {
            #[cfg(windows)]
            {
                let activate = p.join(".venv").join("Scripts").join("activate.bat");
                let inner = if activate.exists() {
                    format!("cd /d \"{}\" && \"{}\"", path, activate.display())
                } else {
                    format!("cd /d \"{}\"", path)
                };
                Command::new("cmd")
                    .args(["/C", "start", "", "cmd", "/k", &inner])
                    .spawn()
                    .map_err(|e| e.to_string())?;
            }
            #[cfg(not(windows))]
            {
                Command::new("x-terminal-emulator")
                    .arg("-e")
                    .arg("bash")
                    .current_dir(&p)
                    .spawn()
                    .map_err(|e| e.to_string())?;
            }
            Ok(())
        }
        "github" => {
            // origin が GitHub ならブラウザで開く（URL は git から取る）
            let out = Command::new("git")
                .args(["-C", &path, "remote", "get-url", "origin"])
                .output()
                .map_err(|e| e.to_string())?;
            let url = String::from_utf8_lossy(&out.stdout).trim().to_string();
            let web = url
                .replace("git@github.com:", "https://github.com/")
                .trim_end_matches(".git")
                .to_string();
            if web.starts_with("https://github.com/") {
                #[cfg(windows)]
                Command::new("cmd").args(["/C", "start", "", &web]).spawn().map_err(|e| e.to_string())?;
                #[cfg(target_os = "macos")]
                Command::new("open").arg(&web).spawn().map_err(|e| e.to_string())?;
                #[cfg(all(unix, not(target_os = "macos")))]
                Command::new("xdg-open").arg(&web).spawn().map_err(|e| e.to_string())?;
                Ok(())
            } else {
                Err("GitHub の URL が分かりません（origin 未設定か、GitHub 以外のリモートです）".into())
            }
        }
        _ => Err(format!("unknown target: {kind}")),
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![pj, open_target])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
